"""Unit tests for server/agent/meta_client.py."""
import unittest
from unittest.mock import MagicMock, patch

from server.agent.meta_client import MetaClient, MetaResponse, UsageMetrics
from server.config import PicoConfig


class TestMetaClient(unittest.TestCase):
    def setUp(self):
        self.mock_config = PicoConfig(
            meta_api_key="",
            meta_model="muse-spark-1.3",
            meta_base_url="https://api.meta.ai/v1",
            max_model_turns=5,
            max_tool_calls=6,
            request_timeout_seconds=5.0,
            tool_timeout_seconds=5.0,
            task_deadline_seconds=30.0,
            spending_limit_dollars=1.0,
            mock_model=True,
        )

    def test_mock_chat_emits_search_tool_call(self):
        client = MetaClient(self.mock_config)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
                },
            }
        ]
        resp = client.chat(messages=[{"role": "user", "content": "Find brief"}], tools=tools)

        self.assertTrue(resp.simulated)
        self.assertIn("[SIMULATED]", resp.model_name)
        self.assertEqual(len(resp.tool_calls), 1)
        self.assertEqual(resp.tool_calls[0]["function"]["name"], "search_documents")
        self.assertEqual(client.usage.call_count, 1)
        self.assertGreater(client.usage.total_tokens, 0)

    def test_spending_limit_enforced(self):
        # Set an ultra low spending limit that gets exceeded
        low_limit_config = PicoConfig(
            meta_api_key="",
            meta_model="muse-spark-1.3",
            meta_base_url="https://api.meta.ai/v1",
            max_model_turns=5,
            max_tool_calls=6,
            request_timeout_seconds=5.0,
            tool_timeout_seconds=5.0,
            task_deadline_seconds=30.0,
            spending_limit_dollars=0.000001,
            mock_model=True,
        )
        client = MetaClient(low_limit_config)
        # First call records token usage and incurs a small cost
        client.chat(messages=[{"role": "user", "content": "Query 1"}])
        # Second call should trip spending limit check
        with self.assertRaises(RuntimeError) as ctx:
            client.chat(messages=[{"role": "user", "content": "Query 2"}])
        self.assertIn("Spending limit exceeded", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

