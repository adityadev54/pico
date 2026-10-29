"""Tests for the agent tool server (agents/agent_server.py).

All tests run against execute_tool() directly — no HTTP server is started,
no real files are needed beyond the temp dir fixtures.  Tests verify:
- valid tool calls execute and return succeeded results
- unknown / unavailable tools fail with typed error codes
- bad arguments are caught before dispatch
- the handler context is correctly populated
- transfer sets transfer_size_bytes on the result
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_server import execute_tool  # noqa: E402


def _grants(path):
    return [{"path": str(path), "access": "write"}]


class AgentServerTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="pico-server-")
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # ── fs_write + fs_read round-trip ──────────────────────────────────────

    def test_fs_write_creates_file_and_returns_succeeded(self):
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "fs_write",
            "arguments": {"path": "hello.txt", "content": "Hello Pico"},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "succeeded")
        self.assertIn("digest", result["evidence"])
        self.assertTrue((self.root / "hello.txt").exists())
        self.assertEqual((self.root / "hello.txt").read_text(), "Hello Pico")

    def test_fs_read_returns_content(self):
        (self.root / "note.txt").write_text("my note")
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "fs_read",
            "arguments": {"path": "note.txt"},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["data"]["content"], "my note")

    def test_fs_list_returns_entries(self):
        (self.root / "a.txt").write_text("a")
        (self.root / "b.txt").write_text("b")
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "fs_list", "arguments": {},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "succeeded")
        names = {e["name"] for e in result["data"]["entries"]}
        self.assertIn("a.txt", names)
        self.assertIn("b.txt", names)

    # ── search + transfer ──────────────────────────────────────────────────

    def test_search_returns_candidates(self):
        (self.root / "brief.pdf").write_bytes(b"%PDF")
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "search_documents",
            "arguments": {"query": "brief"},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "succeeded")
        candidates = result["data"]["candidates"]
        self.assertTrue(any("brief.pdf" in c["name"] for c in candidates))

    def test_search_miss_returns_failed_no_match(self):
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "search_documents",
            "arguments": {"query": "xyznonexistent"},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "no_match")

    def test_transfer_sets_size_bytes(self):
        (self.root / "report.txt").write_text("hello world")
        # Search first to get a candidate_id.
        search = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "search_documents",
            "arguments": {"query": "report"},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(search["status"], "succeeded")
        candidate_id = search["data"]["candidates"][0]["candidate_id"]

        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s2", "call_id": "c2",
            "tool": "transfer_selected_file",
            "arguments": {"candidate_id": candidate_id, "approval_id": "ap1"},
            "idempotency_key": "t1:s2", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "succeeded")
        self.assertIn("transfer_size_bytes", result)
        self.assertGreater(result["transfer_size_bytes"], 0)

    # ── error cases ────────────────────────────────────────────────────────

    def test_unknown_tool_returns_unsupported(self):
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "summon_dragons",
            "arguments": {},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "unsupported_tool")

    def test_missing_required_arg_fails_before_dispatch(self):
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "fs_read",
            "arguments": {},  # path is required
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "failed")
        self.assertIn("code", result["error"])

    def test_path_escape_is_rejected(self):
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "fs_read",
            "arguments": {"path": "/etc/passwd"},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "failed")

    def test_no_grants_returns_permission_denied(self):
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "search_documents",
            "arguments": {"query": "anything"},
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, grants=[])  # No grants.
        self.assertEqual(result["status"], "failed")
        # With no grants, native_search falls back to ~/Documents and returns
        # no_match when nothing is found there, or permission_denied when
        # the folder is absent.  Either is an honest failure — the key
        # property is that it is not "succeeded".
        self.assertIn(result["error"]["code"], ("permission_denied", "no_match"))

    # ── process_run ────────────────────────────────────────────────────────

    def test_process_run_returns_real_stdout(self):
        import sys
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "t1", "step_id": "s1", "call_id": "c1",
            "tool": "process_run",
            "arguments": {
                "argv_json": json.dumps([sys.executable, "-c",
                                         "print('pico-ok')"]),
            },
            "idempotency_key": "t1:s1", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["status"], "succeeded")
        self.assertIn("pico-ok", result["data"]["stdout"])

    def test_result_carries_task_step_call_ids(self):
        result = execute_tool({
            "contract_version": 1, "type": "tool_call",
            "task_id": "my-task", "step_id": "my-step", "call_id": "my-call",
            "tool": "fs_list", "arguments": {},
            "idempotency_key": "my-task:my-step", "deadline_seconds": 30,
        }, _grants(self.root))
        self.assertEqual(result["task_id"], "my-task")
        self.assertEqual(result["step_id"], "my-step")
        self.assertEqual(result["call_id"], "my-call")


if __name__ == "__main__":
    unittest.main()
