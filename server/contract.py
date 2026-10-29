"""Contract v1 validation. Shared by agent, verifier and network endpoints.

Implements docs/tool-contracts.md without network or model calls.
Device IDs identify targets; they never authorize access. Owner identity
always comes from authentication, never from a request body.
"""
from __future__ import annotations

CONTRACT_VERSION = 1

MESSAGE_TYPES = (
    "request",
    "tool_call",
    "tool_result",
    "progress",
    "verification_result",
    "approval",
    "clarification",
    "receipt",
)

STATES = (
    "queued",
    "planning",
    "needs_clarification",
    "needs_approval",
    "executing",
    "verifying",
    "awaiting_receipt",
    "completed",
    "partial",
    "failed",
    "cancelled",
)

TERMINAL_STATES = ("completed", "partial", "failed", "cancelled")

ERROR_CODES = (
    "permission_denied",
    "device_offline",
    "no_match",
    "candidate_changed",
    "timeout",
    "unsupported_tool",
    "invalid_message",
    "expired",
    "conflict",
    "unauthorized",
    "cancelled",
)

# Initial tools plus the documented next set. Legacy phone kinds map to
# these: find_document -> search_documents, send_file -> transfer_selected_file.
SUPPORTED_TOOLS = (
    "search_documents",
    "transfer_selected_file",
    "capture_current_tab",
    "create_checklist",
    "read_back_file",
    "open_resource",
    "open_app",
    "open_website",
    "manage_permissions",
    "fs_list",
    "fs_read",
    "fs_write",
    "process_run",
    "fetch_upload",
    "organize_photos",
    "open_document",
)


class ContractError(Exception):
    def __init__(self, code: str, message: str):
        if code not in ERROR_CODES:
            code = "invalid_message"
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _require_str(value, name: str, max_len: int = 2000) -> str:
    if not isinstance(value, str) or not value or len(value) > max_len:
        raise ContractError("invalid_message", f"Invalid {name}.")
    return value


def validate_envelope(message: dict) -> dict:
    """All messages carry contract_version, task_id and type."""
    if not isinstance(message, dict):
        raise ContractError("invalid_message", "Expected a message object.")
    if message.get("contract_version") != CONTRACT_VERSION:
        raise ContractError("invalid_message", "Unsupported contract version.")
    _require_str(message.get("task_id"), "task_id", 128)
    if message.get("type") not in MESSAGE_TYPES:
        raise ContractError("invalid_message", "Unsupported message type.")
    return message


def validate_tool_call(message: dict) -> dict:
    """Tool calls carry step_id, call_id, tool, arguments, idempotency and deadline."""
    validate_envelope(message)
    if message.get("type") != "tool_call":
        raise ContractError("invalid_message", "Not a tool call.")
    _require_str(message.get("step_id"), "step_id", 128)
    _require_str(message.get("call_id"), "call_id", 128)
    tool = message.get("tool")
    if tool not in SUPPORTED_TOOLS:
        raise ContractError("unsupported_tool", f"Unsupported tool: {tool}.")
    args = message.get("arguments")
    if not isinstance(args, dict):
        raise ContractError("invalid_message", "Tool arguments must be an object.")
    _require_str(message.get("idempotency_key"), "idempotency_key", 256)
    deadline = message.get("deadline_seconds")
    if not isinstance(deadline, int) or not 1 <= deadline <= 120:
        raise ContractError("invalid_message", "Deadline must be 1-120 seconds.")
    _validate_tool_args(tool, args)
    return message


def _validate_tool_args(tool: str, args: dict) -> None:
    if tool == "search_documents":
        _require_str(args.get("query"), "query", 500)
        if "grant_id" in args:
            _require_str(args.get("grant_id"), "grant_id", 128)
    elif tool == "transfer_selected_file":
        _require_str(args.get("candidate_id"), "candidate_id", 128)
        _require_str(args.get("approval_id"), "approval_id", 128)
    elif tool == "create_checklist":
        items = args.get("items")
        if not isinstance(items, list) or not items or len(items) > 30:
            raise ContractError("invalid_message", "Checklist needs 1-30 items.")
        for item in items:
            _require_str(item, "checklist item", 300)
    elif tool == "read_back_file":
        _require_str(args.get("candidate_id"), "candidate_id", 128)
    elif tool in ("open_resource", "open_website"):
        _require_str(args.get("url"), "url", 2000)
    elif tool == "open_app":
        _require_str(args.get("app"), "app", 64)
    elif tool == "capture_current_tab":
        pass
    elif tool == "manage_permissions":
        pass
    elif tool == "fs_list":
        if "path" in args:
            _require_str(args.get("path"), "path", 512)
    elif tool == "fs_read":
        _require_str(args.get("path"), "path", 512)
    elif tool == "fs_write":
        _require_str(args.get("path"), "path", 512)
        _require_str(args.get("content"), "content", 2000)
        if "base_revision" in args:
            _require_str(args.get("base_revision"), "base_revision", 128)
    elif tool == "process_run":
        _require_str(args.get("argv_json"), "argv_json", 2000)


def validate_tool_result(message: dict) -> dict:
    validate_envelope(message)
    if message.get("type") != "tool_result":
        raise ContractError("invalid_message", "Not a tool result.")
    _require_str(message.get("step_id"), "step_id", 128)
    _require_str(message.get("call_id"), "call_id", 128)
    if message.get("status") not in ("succeeded", "failed", "denied"):
        raise ContractError("invalid_message", "Invalid tool result status.")
    if message.get("status") == "failed":
        code = (message.get("error") or {}).get("code") if isinstance(message.get("error"), dict) else None
        if code not in ERROR_CODES:
            raise ContractError("invalid_message", "Failed results need a stable error code.")
    return message


def validate_approval(approval: dict, owner: str, task_id: str, task_version: int) -> dict:
    """Bind each approval to owner, task, exact operation, version and expiry."""
    import time

    if not isinstance(approval, dict):
        raise ContractError("invalid_message", "Invalid approval.")
    if approval.get("owner") != owner:
        raise ContractError("unauthorized", "Approval owner mismatch.")
    if approval.get("task_id") != task_id:
        raise ContractError("invalid_message", "Approval task mismatch.")
    if approval.get("task_version") != task_version:
        raise ContractError("conflict", "Approval is for another task version.")
    _require_str(approval.get("approval_id"), "approval_id", 128)
    _require_str(approval.get("operation"), "operation", 128)
    expiry = approval.get("expires_at")
    if not isinstance(expiry, (int, float)) or expiry <= time.time():
        raise ContractError("expired", "Approval expired.")
    return approval


def validate_progress(message: dict) -> dict:
    validate_envelope(message)
    if message.get("type") != "progress":
        raise ContractError("invalid_message", "Not a progress message.")
    if message.get("state") not in STATES:
        raise ContractError("invalid_message", "Unknown task state.")
    if "message" in message and not isinstance(message["message"], str):
        raise ContractError("invalid_message", "Invalid progress message.")
    # Never embed secrets, unrestricted paths or document contents in logs.
    text = str(message.get("message", ""))
    lowered = text.lower()
    for marker in ("bearer ", "api_key", "apikey", "-----begin", "/users/", "/home/", "c:\\"):
        if marker in lowered:
            raise ContractError("invalid_message", "Progress must not carry secrets or paths.")
    if len(text) > 500:
        raise ContractError("invalid_message", "Progress message too long.")
    return message


def is_terminal(state: str) -> bool:
    return state in TERMINAL_STATES


def check_transition(old: str, new: str) -> None:
    """Terminal states never leave; cancellation cannot be reversed by a late result."""
    if old not in STATES or new not in STATES:
        raise ContractError("invalid_message", "Unknown task state.")
    if is_terminal(old):
        raise ContractError("cancelled" if old == "cancelled" else "conflict",
                             f"Task already {old}; late results are ignored.")
