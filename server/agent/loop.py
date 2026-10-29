"""Minimal agent loop with step limits, deadlines and cancellation.

No network calls here; the HTTP layer supplies model output and native
results. This keeps unit tests deterministic and free of paid API calls.
"""
from __future__ import annotations

import time
import uuid

from ..contract import (
    ContractError,
    check_transition,
    is_terminal,
)
from .dispatch import validate_dispatch


class AgentLoop:
    def __init__(self, max_steps: int = 6, max_model_calls: int = 4):
        self.max_steps = max_steps
        self.max_model_calls = max_model_calls

    def start(self, task_id: str, text: str) -> dict:
        return {
            "id": task_id,
            "input": text[:2000],
            "status": "queued",
            "version": 1,
            "steps": [],
            "model_calls": 0,
            "created_at": time.time(),
            "approvals": {},
        }

    def plan(self, task: dict, tool_call: dict | None, question: str | None = None) -> dict:
        """One planner turn: either a validated tool call or a clarification."""
        if is_terminal(task["status"]):
            raise ContractError("cancelled", f"Task already {task['status']}.")
        if len(task["steps"]) >= self.max_steps:
            return self._finish(task, "failed", "timeout", "Step limit reached.")
        if task["model_calls"] >= self.max_model_calls:
            return self._finish(task, "failed", "timeout", "Model call limit reached.")
        task["model_calls"] += 1
        if tool_call is None:
            check_transition(task["status"], "needs_clarification")
            task["status"] = "needs_clarification"
            task["question"] = {
                "question_id": str(uuid.uuid4()),
                "task_version": task["version"],
                "text": (question or "What exactly should I do?")[:500],
            }
            return task
        validate_dispatch(tool_call, task)
        check_transition(task["status"], "executing")
        task["status"] = "executing"
        task["steps"].append({
            "step_id": tool_call["step_id"],
            "call_id": tool_call["call_id"],
            "tool": tool_call["tool"],
            "idempotency_key": tool_call["idempotency_key"],
            "deadline": time.time() + tool_call["deadline_seconds"],
        })
        task["pending_call"] = tool_call
        return task

    def on_tool_result(self, task: dict, result: dict) -> dict:
        """Consume a native tool result. Late results after terminal state are ignored by caller."""
        if is_terminal(task["status"]):
            raise ContractError("cancelled", f"Task already {task['status']}.")
        pending = task.get("pending_call") or {}
        if result.get("call_id") != pending.get("call_id"):
            raise ContractError("invalid_message", "Result does not match pending call.")
        task.pop("pending_call", None)
        if result.get("status") != "succeeded":
            code = (result.get("error") or {}).get("code", "timeout")
            if pending.get("tool") == "search_documents":
                # A failed search must not become completed delivery.
                return self._finish(task, "failed", code, "Search did not succeed.")
            return self._finish(task, "failed", code, "Tool failed.")
        tool = pending.get("tool")
        if tool == "search_documents":
            check_transition(task["status"], "needs_approval")
            task["status"] = "needs_approval"
            task["candidates"] = (result.get("data") or {}).get("candidates", [])[:20]
            return task
        if tool == "transfer_selected_file":
            check_transition(task["status"], "verifying")
            task["status"] = "verifying"
            task["evidence"] = result.get("evidence") or {}
            return task
        return self._finish(task, "completed", "", "Done.")

    def approve(self, task: dict, approval: dict) -> dict:
        from ..contract import validate_approval

        validate_approval(approval, task["owner"], task["id"], task["version"])
        task.setdefault("approvals", {})[approval["approval_id"]] = approval
        return task

    def cancel(self, task: dict) -> dict:
        if is_terminal(task["status"]):
            return task
        check_transition(task["status"], "cancelled")
        task["status"] = "cancelled"
        task.pop("pending_call", None)
        return task

    def _finish(self, task: dict, status: str, code: str, message: str) -> dict:
        check_transition(task["status"], status)
        task["status"] = status
        task["error"] = {"code": code, "message": message[:300]} if code else None
        task.pop("pending_call", None)
        return task
