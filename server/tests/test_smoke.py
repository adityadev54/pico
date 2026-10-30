"""Unit tests for smoke test runner (synthetic mock testing)."""
import unittest

from server.config import PicoConfig
from server.smoke_test import run_mock_smoke_test


class TestSmokeTest(unittest.TestCase):
    def test_mock_smoke_test(self):
        cfg = PicoConfig(
            meta_api_key="",
            meta_model="muse-spark-1.3",
            meta_base_url="https://api.meta.ai/v1",
            max_model_turns=5,
            max_tool_calls=6,
            request_timeout_seconds=30.0,
            tool_timeout_seconds=30.0,
            task_deadline_seconds=120.0,
            spending_limit_dollars=5.0,
            mock_model=True,
        )
        result = run_mock_smoke_test(cfg)
        self.assertEqual(result["mode"], "SIMULATED")
        self.assertIn("[SIMULATED]", result["model_confirmed"])
        self.assertTrue(result["tool_calling_supported"])
        self.assertEqual(result["tool_call_emitted"], "search_documents")
        self.assertTrue(result["image_input_supported"])
        self.assertIn("prompt_tokens", result["usage"])
        self.assertIn("completion_tokens", result["usage"])
        self.assertIn("total_tokens", result["usage"])


if __name__ == "__main__":
    unittest.main()

