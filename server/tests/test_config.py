"""Unit tests for server.config."""
import os
import unittest
from unittest.mock import patch

from server.config import PicoConfig


class TestPicoConfig(unittest.TestCase):
    def test_default_config(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = PicoConfig.from_env()
            self.assertEqual(cfg.meta_model, "muse-spark-1.3")
            self.assertEqual(cfg.max_model_turns, 5)
            self.assertEqual(cfg.max_tool_calls, 6)
            self.assertEqual(cfg.request_timeout_seconds, 30.0)
            self.assertEqual(cfg.tool_timeout_seconds, 30.0)
            self.assertEqual(cfg.task_deadline_seconds, 120.0)
            self.assertEqual(cfg.spending_limit_dollars, 5.0)
            self.assertFalse(cfg.mock_model)

    def test_custom_env_values(self):
        env_vars = {
            "META_API_KEY": "test-key-12345",
            "META_MODEL": "custom-model",
            "MAX_MODEL_TURNS": "3",
            "MAX_TOOL_CALLS": "4",
            "REQUEST_TIMEOUT_SECONDS": "15.5",
            "TOOL_TIMEOUT_SECONDS": "20.0",
            "TASK_DEADLINE_SECONDS": "60.0",
            "SPENDING_LIMIT_DOLLARS": "10.50",
            "MOCK_MODEL": "true",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            cfg = PicoConfig.from_env()
            self.assertEqual(cfg.meta_api_key, "test-key-12345")
            self.assertEqual(cfg.meta_model, "custom-model")
            self.assertEqual(cfg.max_model_turns, 3)
            self.assertEqual(cfg.max_tool_calls, 4)
            self.assertEqual(cfg.request_timeout_seconds, 15.5)
            self.assertEqual(cfg.spending_limit_dollars, 10.50)
            self.assertTrue(cfg.mock_model)
            cfg.validate()

    def test_validation_rejects_non_positive_bounds(self):
        cfg = PicoConfig(
            meta_api_key="",
            meta_model="muse-spark-1.3",
            meta_base_url="https://api.meta.ai/v1",
            max_model_turns=0,
            max_tool_calls=6,
            request_timeout_seconds=30.0,
            tool_timeout_seconds=30.0,
            task_deadline_seconds=120.0,
            spending_limit_dollars=5.0,
            mock_model=False,
        )
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_safe_summary_does_not_leak_key(self):
        cfg = PicoConfig(
            meta_api_key="super_secret_production_key_xyz",
            meta_model="muse-spark-1.3",
            meta_base_url="https://api.meta.ai/v1",
            max_model_turns=5,
            max_tool_calls=6,
            request_timeout_seconds=30.0,
            tool_timeout_seconds=30.0,
            task_deadline_seconds=120.0,
            spending_limit_dollars=5.0,
            mock_model=False,
        )
        summary = cfg.safe_summary()
        self.assertNotIn("super_secret_production_key_xyz", str(summary))
        self.assertTrue(summary["api_key_configured"])
        self.assertEqual(summary["api_key_masked"], "supe...yz")


if __name__ == "__main__":
    unittest.main()

