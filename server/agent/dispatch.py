"""Validated tool dispatch. Model output never executes without these checks."""
from __future__ import annotations

from ..contract import ContractError, validate_tool_call


def validate_dispatch(tool_call: dict, task: dict) -> dict:
    """Check tool call against task ownership, version, cancellation and grants."""
    if task.get("status") in ("cancelled", "completed", "failed", "partial"):
        raise ContractError("cancelled", f"Task already {task.get('status')}.")
    validate_tool_call(tool_call)
    # Device IDs identify targets but never authorize; owner comes from auth.
    # Caller must have already matched task owner to the authenticated user.
    if tool_call.get("task_id") != task.get("id"):
        raise ContractError("invalid_message", "Tool call task mismatch.")
    tool = tool_call["tool"]
    args = tool_call["arguments"]
    if tool == "transfer_selected_file":
        approval = (task.get("approvals") or {}).get(args["approval_id"])
        if not approval:
            raise ContractError("unauthorized", "Missing approval for transfer.")
        if approval.get("candidate_id") != args["candidate_id"]:
            raise ContractError("candidate_changed", "Approval is for another file.")
        if approval.get("task_version") != task.get("version", 1):
            raise ContractError("conflict", "Approval is for another task version.")
    if tool == "search_documents":
        # Query-only; folder grants are enforced again on the helper.
        if len(str(args.get("query", ""))) > 500:
            raise ContractError("invalid_message", "Query too long.")
    return tool_call
