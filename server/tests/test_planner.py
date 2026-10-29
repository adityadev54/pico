"""Tests for the model planner (server/agent/planner.py).

All tests are deterministic: no actual model calls are made.  The HTTP
call is replaced by an injected fake so the planner's JSON-parsing and
output-shaping logic is exercised independently of any API.
"""
import json
import io
import unittest
from unittest.mock import patch, MagicMock

from server.agent.planner import plan, _tool_summary


TOOLS = [
    {"name": "search_documents",
     "description": "Find files.", "args": {"query": {"required": True}},
     "available": True},
    {"name": "capture_current_tab",
     "description": "Not implemented.", "args": {}, "available": False},
]

CFG = {"url": "https://example.muse/v1/chat/completions",
       "key": "test-key", "model": "muse-spark-1.3"}


def _fake_response(content: str):
    """Return a mock that looks like urllib's urlopen context manager."""
    payload = {"choices": [{"message": {"content": content}}]}
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read = lambda: json.dumps(payload).encode()
    # json.load reads from a file-like object.
    mock.read = io.BytesIO(json.dumps(payload).encode()).read
    # Patch json.load inside urlopen context.
    mock._payload = payload
    return mock


class PlannerTests(unittest.TestCase):

    def _plan_with(self, content: str) -> dict:
        payload = {"choices": [{"message": {"content": content}}]}

        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self):
                return json.dumps(payload).encode()

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            # json.load(response) is called inside plan(); patch it at the
            # module level so the fake bytes are decoded correctly.
            import urllib.request as _ur
            orig = _ur.urlopen
            result = {}

            import server.agent.planner as planner_mod
            original_urlopen = planner_mod.urllib.request.urlopen

            def fake_urlopen(req, timeout=None):
                class Ctx:
                    def __enter__(self):
                        return self
                    def __exit__(self, *_):
                        return False
                ctx = Ctx()
                # Make json.load work by monkey-patching json.load for this call.
                import builtins
                ctx._data = payload
                return ctx

            with patch.object(planner_mod.urllib.request, "urlopen",
                              side_effect=lambda req, timeout=None: _make_ctx(payload)):
                return plan({"id": "t1", "input": "find my brief"}, TOOLS, CFG)

    def test_tool_summary_excludes_unavailable(self):
        summary = _tool_summary(TOOLS)
        self.assertIn("search_documents", summary)
        self.assertNotIn("capture_current_tab", summary)

    def test_returns_error_when_unconfigured(self):
        result = plan({"id": "t1", "input": "x"}, TOOLS, {"url": "", "key": ""})
        self.assertIn("error", result)
        self.assertNotIn("tool_call", result)

    def test_rejects_non_https_endpoint(self):
        result = plan({"id": "t1", "input": "x"}, TOOLS,
                      {"url": "http://plain.example.com", "key": "k", "model": "m"})
        self.assertIn("error", result)

    def test_tool_call_shape_from_model(self):
        model_reply = json.dumps({
            "action": "tool_call",
            "tool": "search_documents",
            "arguments": {"query": "brief"},
        })
        result = _parse_and_shape("t1", model_reply)
        self.assertIn("tool_call", result)
        tc = result["tool_call"]
        self.assertEqual(tc["tool"], "search_documents")
        self.assertEqual(tc["arguments"]["query"], "brief")
        self.assertEqual(tc["type"], "tool_call")
        self.assertEqual(tc["contract_version"], 1)
        self.assertIn("step_id", tc)
        self.assertIn("call_id", tc)
        self.assertIn("idempotency_key", tc)
        self.assertEqual(tc["deadline_seconds"], 30)

    def test_clarify_shape_from_model(self):
        model_reply = json.dumps({
            "action": "clarify",
            "question": "Which folder should I search?",
        })
        result = _parse_and_shape("t1", model_reply)
        self.assertIn("question", result)
        self.assertEqual(result["question"], "Which folder should I search?")

    def test_json_in_markdown_block_is_extracted(self):
        model_reply = '```json\n{"action":"clarify","question":"Which one?"}\n```'
        result = _parse_and_shape("t1", model_reply)
        self.assertIn("question", result)

    def test_garbage_response_returns_error(self):
        result = _parse_and_shape("t1", "I'll search for your file right away!")
        self.assertIn("error", result)

    def test_unknown_action_returns_error(self):
        result = _parse_and_shape("t1", json.dumps({"action": "dance"}))
        self.assertIn("error", result)

    def test_missing_arguments_defaults_to_empty_dict(self):
        result = _parse_and_shape("t1", json.dumps({
            "action": "tool_call", "tool": "fs_list",
        }))
        self.assertIn("tool_call", result)
        self.assertIsInstance(result["tool_call"]["arguments"], dict)

    def test_model_network_error_returns_error(self):
        import server.agent.planner as planner_mod
        with patch.object(planner_mod.urllib.request, "urlopen",
                          side_effect=OSError("connection refused")):
            result = plan({"id": "t1", "input": "x"}, TOOLS, CFG)
        self.assertIn("error", result)


def _parse_and_shape(task_id: str, content: str) -> dict:
    """Call plan() with a fake model response; no real HTTP."""
    import server.agent.planner as planner_mod
    payload = {"choices": [{"message": {"content": content}}]}

    class FakeCtx:
        def __enter__(self): return self
        def __exit__(self, *_): return False

    ctx = FakeCtx()
    ctx._payload = payload

    original_json_load = json.load

    def fake_urlopen(req, timeout=None):
        return ctx

    with patch.object(planner_mod.urllib.request, "urlopen", fake_urlopen):
        with patch("json.load", side_effect=lambda f: payload):
            return plan({"id": task_id, "input": "find brief"}, TOOLS, CFG)


def _make_ctx(payload):
    class FakeCtx:
        def __enter__(self): return self
        def __exit__(self, *_): return False
    ctx = FakeCtx()
    ctx._payload = payload
    return ctx


if __name__ == "__main__":
    unittest.main()
