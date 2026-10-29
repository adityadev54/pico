"""Local agent backend. Binds to localhost only.

Run from the repository root:
  python3 -m server.app --env-file server/.env

Endpoints:
  GET  /health      explicit status; never claims connectivity it lacks
  GET  /contracts   sample messages, not real task data
  POST /request     authenticated: create task from phone text
  POST /plan        authenticated: one planner turn (tool call or clarification)
  POST /tool_result authenticated: consume native tool result
  POST /approve     authenticated: bind exact-file approval
  POST /cancel      authenticated: cancel task; late results are ignored
  GET  /task?id=..  authenticated: read own task (no secrets, no paths)
"""
from __future__ import annotations

import argparse
import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from .agent.loop import AgentLoop
from .agent.planner import plan as model_plan
from .agent.tools_proxy import dispatch_to_helper
from .config import load_env_file, muse_config, muse_configured
from .contract import ContractError

CONTRACT = Path(__file__).resolve().parents[1] / "docs" / "contract-examples.json"
TASKS: dict[str, dict] = {}
LOCK = threading.RLock()
LOOP = AgentLoop()


def _dispatch_and_record(task: dict, tool_call: dict) -> None:
    """Background: send tool_call to the native helper and feed the result back."""
    result = dispatch_to_helper(tool_call)
    with LOCK:
        if task.get("id") not in TASKS:
            return  # Task was removed or never stored (race); ignore.
        try:
            LOOP.on_tool_result(task, result)
        except ContractError:
            pass  # Cancelled or terminal before result arrived.


def owner_from_auth(token: str) -> str:
    """Derive owner from authentication, never from a request body.

    Local dev: when PICO_ALLOW_LOCAL_AUTH=1, a non-empty Bearer token is the
    owner id. Otherwise SUPABASE_URL + service key validate via /auth/v1/user.
    """
    if not token:
        raise ContractError("unauthorized", "Sign in first.")
    if os.environ.get("PICO_ALLOW_LOCAL_AUTH") == "1":
        return "local:" + token[:64]
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise ContractError("unauthorized", "Server auth is not configured.")
    import urllib.request

    req = urllib.request.Request(
        url.rstrip("/") + "/auth/v1/user",
        headers={"apikey": key, "Authorization": "Bearer " + token},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)["id"]
    except Exception:
        raise ContractError("unauthorized", "Session expired. Sign in again.") from None


def make_handler():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, status: int, body: dict):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            try:
                path = urlsplit(self.path).path
                if path == "/health":
                    return self.send(200, {
                        "status": "ok", "mode": "agent-local",
                        "meta_configured": muse_configured(),
                        "meta_connected": False,
                        "device_connected": False,
                        "execution_available": True,
                    })
                if path == "/contracts":
                    return self.send(200, json.loads(CONTRACT.read_text()))
                if path == "/task":
                    owner = owner_from_auth(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    task_id = parse_qs(urlsplit(self.path).query).get("id", [""])[0]
                    with LOCK:
                        task = TASKS.get(task_id)
                    if not task or task.get("owner") != owner:
                        return self.send(404, {"error": "not_found"})
                    view = {k: task.get(k) for k in (
                        "id", "status", "version", "candidates", "question", "error")}
                    return self.send(200, view)
                return self.send(404, {"error": "not_found"})
            except ContractError as error:
                self.send(401 if error.code == "unauthorized" else 400,
                           {"error": error.message, "code": error.code})
            except Exception:
                self.send(500, {"error": "Request failed."})

        def do_POST(self):
            try:
                path = urlsplit(self.path).path
                length = int(self.headers.get("Content-Length", 0))
                if length < 0 or length > 16000:
                    raise ContractError("invalid_message", "Message too large.")
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ContractError("invalid_message", "Expected a message object.")
                owner = owner_from_auth(self.headers.get("Authorization", "").removeprefix("Bearer "))
                with LOCK:
                    if path == "/request":
                        text = str(body.get("text", ""))[:2000]
                        if not text.strip():
                            raise ContractError("invalid_message", "Missing request text.")
                        task_id = str(uuid.uuid4())
                        task = LOOP.start(task_id, text)
                        task["owner"] = owner
                        task["device_id"] = str(body.get("device_id", ""))[:128]
                        TASKS[task_id] = task
                        # Auto-plan: call the model immediately if configured.
                        if muse_configured():
                            from .agent.tools_proxy import TOOL_LIST
                            cfg = muse_config()
                            plan_result = model_plan(task, TOOL_LIST, cfg)
                            if "tool_call" in plan_result:
                                LOOP.plan(task, plan_result["tool_call"])
                                # Dispatch to the native helper in the background.
                                import threading
                                threading.Thread(
                                    target=_dispatch_and_record,
                                    args=(task, plan_result["tool_call"]),
                                    daemon=True,
                                ).start()
                            elif "question" in plan_result:
                                LOOP.plan(task, None, question=plan_result["question"])
                            # If "error": leave task in queued; caller sees status.
                        return self.send(200, {"task_id": task_id, "status": task["status"]})
                    task = TASKS.get(str(body.get("task_id", "")))
                    if not task or task.get("owner") != owner:
                        return self.send(404, {"error": "not_found"})
                    if path == "/plan":
                        LOOP.plan(task, body.get("tool_call"), body.get("question"))
                        return self.send(200, {"status": task["status"],
                                               "question": task.get("question")})
                    if path == "/tool_result":
                        LOOP.on_tool_result(task, body.get("result") or {})
                        return self.send(200, {"status": task["status"],
                                               "candidates": task.get("candidates", [])})
                    if path == "/approve":
                        LOOP.approve(task, body.get("approval") or {})
                        return self.send(200, {"ok": True})
                    if path == "/cancel":
                        LOOP.cancel(task)
                        return self.send(200, {"status": task["status"]})
                return self.send(404, {"error": "not_found"})
            except ContractError as error:
                code = 401 if error.code == "unauthorized" else 400
                if error.code in ("conflict", "cancelled", "expired"):
                    code = 409
                self.send(code, {"error": error.message, "code": error.code})
            except (ValueError, KeyError, TypeError):
                self.send(400, {"error": "Invalid message.", "code": "invalid_message"})
            except Exception:
                self.send(500, {"error": "Request failed."})

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Pico local agent backend")
    parser.add_argument("--env-file", default=os.environ.get("PICO_ENV_FILE"))
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    load_env_file(args.env_file)
    print(f"Pico agent (local only): http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler()).serve_forever()


if __name__ == "__main__":
    main()
