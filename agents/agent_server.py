"""Local agent tool server — the bridge between server/app.py and native handlers.

Binds to 127.0.0.1 only.  The main Pico relay and the phone never reach
this port.  The server/app.py backend calls POST /execute with a validated
tool_call dict; this process runs the real native handler and returns the
structured result.

Run from the repository root (after pairing and granting folders):

    PICO_AGENT_TOKEN=<shared-secret> python3 -m agents.agent_server

Companion integration: Companion passes its grants list and context hooks
so handlers can open URLs, reopen apps and notify.  When running without
the companion (e.g. unit tests), supply grants via the PICO_SEARCH_ROOTS
environment variable.

Endpoints
---------
GET  /health   — heartbeat + capabilities
POST /execute  — run one validated tool call, return structured result
"""
from __future__ import annotations

import json
import hmac
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

# Allow running as a module from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from handlers import dispatch, HANDLERS  # noqa: E402
from native_search import NativeError  # noqa: E402
from tools import TOOL_REGISTRY, ToolError  # noqa: E402

DEFAULT_PORT = 8001
_LOCK = threading.Lock()


def _grants_from_env() -> list[dict]:
    """Fallback: read granted roots from PICO_SEARCH_ROOTS colon-separated list."""
    roots = os.environ.get("PICO_SEARCH_ROOTS", "")
    return [{"path": p.strip(), "access": "write"}
            for p in roots.split(os.pathsep) if p.strip()]


def _make_ctx(grants: list[dict]) -> dict:
    """Build a minimal handler context from grants (no GUI side-effects here)."""
    opened_urls: list[str] = []
    opened_apps: list[str] = []
    notifications: list[str] = []
    transferred: list[tuple] = []

    def open_url(url: str) -> None:
        import webbrowser
        opened_urls.append(url)
        webbrowser.open(url)

    def reopen(bundle: str) -> None:
        opened_apps.append(bundle)
        # On macOS: open the app by bundle ID; no-op on other platforms.
        if sys.platform == "darwin":
            import subprocess
            try:
                subprocess.Popen(["open", "-b", bundle])
            except OSError:
                pass

    def notify() -> None:
        notifications.append("permissions_requested")

    def transfer(raw: bytes, evidence: dict) -> None:
        transferred.append((raw, evidence))

    return {
        "grants": grants,
        "open_url": open_url,
        "reopen": reopen,
        "notify": notify,
        "transfer": transfer,
        "_transferred": transferred,
        "_opened_urls": opened_urls,
        "_opened_apps": opened_apps,
    }


def execute_tool(tool_call: dict, grants: list[dict]) -> dict:
    """Validate and run one tool call.  Returns a tool_result dict."""
    call_id = tool_call.get("call_id", "")
    step_id = tool_call.get("step_id", "")
    task_id = tool_call.get("task_id", "")
    tool = tool_call.get("tool", "")

    # Validate argument shapes first.
    try:
        clean_args = TOOL_REGISTRY.validate(tool, tool_call.get("arguments") or {})
    except ToolError as error:
        return _fail(task_id, step_id, call_id, error.code, error.message)

    if tool not in ('open_app', 'open_website', 'manage_permissions') and not grants:
        return _fail(task_id, step_id, call_id, 'permission_denied', 'Choose an explicit folder grant first.')
    ctx = _make_ctx(grants)
    try:
        data, evidence = dispatch(tool, clean_args, ctx)
    except NativeError as error:
        return _fail(task_id, step_id, call_id, error.code, error.message)
    except ToolError as error:
        return _fail(task_id, step_id, call_id, error.code, error.message)
    except Exception as exc:
        return _fail(task_id, step_id, call_id, "timeout",
                     f"Handler raised {type(exc).__name__}: {exc}")

    result: dict = {
        "contract_version": 1,
        "type": "tool_result",
        "task_id": task_id,
        "step_id": step_id,
        "call_id": call_id,
        "status": "succeeded",
        "data": data,
        "evidence": evidence,
    }

    # Attach transfer bytes separately when a file was transferred.
    transferred = ctx.get("_transferred") or []
    if transferred and tool == "transfer_selected_file":
        raw, ev = transferred[0]
        result["transfer_size_bytes"] = len(raw)
        result["evidence"] = ev

    return result


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


def make_handler(token: str, grants: list[dict]):
    if not token:
        raise ValueError('PICO_AGENT_TOKEN is required for the local tool server.')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, status: int, body: dict) -> None:
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _check_auth(self) -> bool:
            if self.headers.get('Origin') is not None:
                return False
            bearer = self.headers.get("Authorization", "").removeprefix("Bearer ")
            return hmac.compare_digest(bearer.encode(), token.encode())

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/health":
                return self.send(200, {
                    "status": "ok",
                    "tools": list(HANDLERS.keys()),
                    "grant_count": len(grants),
                    "platform": sys.platform,
                })
            self.send(404, {"error": "not_found"})

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            if path != "/execute":
                return self.send(404, {"error": "not_found"})
            if not self._check_auth():
                return self.send(401, {"error": "Unauthorized."})
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 32_000:
                return self.send(400, {"error": "Invalid body size."})
            try:
                body = json.loads(self.rfile.read(length))
            except ValueError:
                return self.send(400, {"error": "Invalid JSON."})
            if not isinstance(body, dict):
                return self.send(400, {"error": "Expected a tool_call object."})
            with _LOCK:
                result = execute_tool(body, grants)
            self.send(200, result)

    return Handler


def main(argv=None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Pico local agent tool server")
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("PICO_AGENT_PORT", DEFAULT_PORT)))
    parser.add_argument("--roots", default=os.environ.get("PICO_SEARCH_ROOTS", ""))
    args = parser.parse_args(argv)

    token = os.environ.get("PICO_AGENT_TOKEN", "")
    grants = _grants_from_env()
    if args.roots:
        grants = [{"path": p.strip(), "access": "write"}
                  for p in args.roots.split(os.pathsep) if p.strip()]

    print(
        f"Pico agent tool server: http://127.0.0.1:{args.port}  "
        f"grants={len(grants)}  auth={'required'}",
        flush=True,
    )
    ThreadingHTTPServer(
        ("127.0.0.1", args.port), make_handler(token, grants)
    ).serve_forever()


if __name__ == "__main__":
    main()
