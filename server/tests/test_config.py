"""Tests for server-only env loading (server/config.py).

Secrets themselves are never fixtures: tests use throwaway keys and a temp
file, and always restore the environment.
"""
import os
import tempfile
import unittest
from pathlib import Path

from server.config import load_env_file, muse_config, muse_configured


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._saved = dict(os.environ)
        self.addCleanup(self._restore)
        self.tmp = tempfile.TemporaryDirectory(prefix="pico-config-")
        self.addCleanup(self.tmp.cleanup)
        self.env_file = Path(self.tmp.name) / "test.env"

    def _restore(self):
        os.environ.clear()
        os.environ.update(self._saved)

    def test_first_key_wins_and_comments_ignored(self):
        self.env_file.write_text(
            "# comment line\n"
            "\n"
            "MUSE_API_URL=https://first.example/v1\n"
            "MUSE_API_KEY=first-key\n"
            "MUSE_API_KEY=second-key\n"
            "QUOTED=\"hello\"\n"
            "SINGLE='world'\n"
            "NOEQUALS LINE IGNORED\n"
        )
        load_env_file(str(self.env_file))
        self.assertEqual(os.environ["MUSE_API_URL"], "https://first.example/v1")
        self.assertEqual(os.environ["MUSE_API_KEY"], "first-key")
        self.assertEqual(os.environ["QUOTED"], "hello")
        self.assertEqual(os.environ["SINGLE"], "world")
        self.assertTrue(muse_configured())
        self.assertEqual(muse_config()["model"], "muse-spark-1.3")

    def test_existing_environment_wins_over_file(self):
        os.environ["MUSE_API_KEY"] = "from-env"
        self.env_file.write_text("MUSE_API_KEY=from-file\nMUSE_API_URL=https://x.example\n")
        load_env_file(str(self.env_file))
        self.assertEqual(os.environ["MUSE_API_KEY"], "from-env")

    def test_missing_file_and_keys_not_configured(self):
        for key in ("MUSE_API_URL", "MUSE_API_KEY"):
            os.environ.pop(key, None)
        self.assertFalse(muse_configured())
        self.assertIsNone(load_env_file(None))
        self.assertIsNone(load_env_file(""))


if __name__ == "__main__":
    unittest.main()
