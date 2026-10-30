"""Proxy that dispatches validated tool calls to the local agent tool server.

The server/app.py backend lives in a different process from agents/.  This
module provides the thin HTTP bridge so the server can call the native
helper without importing Tkinter or platform libraries.

The tool server (agents/agent_server.py) runs on 127.0.0.1:8001 by default.
Configure with PICO_AGENT_URL and PICO_AGENT_TOKEN environment variables.

TOOL_LIST is a static summary used by the planner so it knows which tools
are available on the helper without making a round-trip at plan time.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


AGENT_URL = os.environ.get("PICO_AGENT_URL", "http://127.0.0.1:8001")
AGENT_TOKEN = os.environ.get("PICO_AGENT_TOKEN", "")

# Static tool summary shown to the model.  Matches agents/tools.py BUILTIN_TOOLS.
TOOL_LIST: list[dict] = [
    {"name": "search_documents",
     "description": "Find files by name under granted folders.",
     "args": {"query": {"required": True}, "grant_id": {"required": False}},
     "available": True},
    {"name": "transfer_selected_file",
     "description": "Send the exact approved file to the phone.",
     "args": {"candidate_id": {"required": True}, "approval_id": {"required": True}},
     "available": True},
    {"name": "read_back_file",
     "description": "Return a bounded text excerpt of one file.",
     "args": {"candidate_id": {"required": True}},
     "available": True},
    {"name": "fs_list",
     "description": "List one workspace folder.",
     "args": {"path": {"required": False}},
     "available": True},
    {"name": "fs_read",
     "description": "Read one workspace file (text or binary manifest).",
     "args": {"path": {"required": True}},
     "available": True},
    {"name": "fs_write",
     "description": "Create a missing file or revise one by digest.",
     "args": {
         "path": {"required": True},
         "content": {"required": True},
         "base_revision": {"required": False},
     },
     "available": True},
    {"name": "process_run",
     "description": "Run a command in the workspace. No shell. Bounded.",
     "args": {
         "argv_json": {"required": True},
         "cwd": {"required": False},
         "timeout_s": {"required": False},
     },
     "available": True},
    {"name": "open_website",
     "description": "Open an https URL in the default browser.",
     "args": {"url": {"required": True}},
     "available": True},
    {"name": "open_app",
     "description": "Open one allowlisted application (calculator, calendar, vscode, browser, notes).",
     "args": {"app": {"required": True}},
     "available": True},
    {"name": "open_document",
     "description": "Open one document by name/type. Unique match only.",
     "args": {"query": {"required": True}},
     "available": True},
    {"name": "organize_photos",
     "description": "Copy unique photos into one folder. Copy-only; hash dedupe.",
     "args": {"folder": {"required": True}},
     "available": True},
    {"name": "capture_current_tab",
     "description": "Not implemented on this helper.",
     "args": {},
     "available": False},
    {"name": "create_checklist",
     "description": "Not implemented on this helper.",
     "args": {},
     "available": False},
]


def dispatch_to_helper(tool_call: dict, timeout: int = 35) -> dict:
    """POST the tool_call to the agent tool server and return the result dict.

    Returns a failed tool_result if the helper is unreachable, so the agent
    loop always gets a properly shaped result regardless of connectivity.
    """
    task_id = tool_call.get("task_id", "")
    step_id = tool_call.get("step_id", "")
    call_id = tool_call.get("call_id", "")

    headers = {"Content-Type": "application/json"}
    # The optional env file is loaded after module imports in the local backend.
    token = os.environ.get("PICO_AGENT_TOKEN", AGENT_TOKEN)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = os.environ.get("PICO_AGENT_URL", AGENT_URL).rstrip("/") + "/execute"
    req = urllib.request.Request(
        url,
        data=json.dumps(tool_call).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            body = json.load(exc)
            msg = body.get("error", str(exc))
        except Exception:
            msg = str(exc)
        code = "permission_denied" if exc.code == 401 else "timeout"
        return _fail(task_id, step_id, call_id, code, msg)
    except Exception as exc:
        return _fail(task_id, step_id, call_id, "device_offline",
                     f"Helper unreachable: {type(exc).__name__}")


def _fail(task_id: str, step_id: str, call_id: str,
          code: str, message: str) -> dict:
    return {
        "contract_version": 1,
        "type": "tool_result",
        "task_id": task_id,
        "step_id": step_id,
        "call_id": call_id,
        "status": "failed",
        "error": {"code": code, "message": message[:300]},
    }
