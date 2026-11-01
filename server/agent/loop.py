"""Bounded Agent Loop and Orchestrator for Pico (Step 5).

Handles:
- Task state machine: queued -> planning -> executing -> needs_approval / needs_clarification.
- Invokes MetaClient with strict Contract v1 tool definitions.
- Validates tool proposals in code before dispatching to helper.
- Enforces hard limits: MAX_MODEL_TURNS, MAX_TOOL_CALLS, deadline_seconds.
- No arbitrary shell execution; opaque candidate IDs only.
- Terminal state safety: late results cannot reverse terminal states.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from server.agent.meta_client import MetaClient
from server.config import PicoConfig, config as default_config
from server.contracts import (
    ApprovalRequestMessage,
    ClarificationQuestionMessage,
    ErrorCode,
    ProgressMessage,
    RequestMessage,
    SearchCandidate,
    TaskState,
    ToolCallMessage,
    ToolName,
    ToolResultMessage,
)

logger = logging.getLogger(__name__)

# Standard Contract v1 Tool Definitions for Meta API
SEARCH_DOCUMENTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": ToolName.SEARCH_DOCUMENTS.value,
        "description": "Search local documents by query text to retrieve candidate IDs and file metadata.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keyword or filename query.",
                },
                "grant_id": {
                    "type": "string",
                    "description": "Optional folder-grant ID authorizing this search.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}

TRANSFER_SELECTED_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": ToolName.TRANSFER_SELECTED_FILE.value,
        "description": "Transfer an exact file candidate that has been explicitly approved by the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "candidate_id": {
                    "type": "string",
                    "description": "Opaque candidate ID returned from search_documents.",
                },
                "approval_id": {
                    "type": "string",
                    "description": "Unique approval ID confirmed by the user.",
                },
            },
            "required": ["candidate_id", "approval_id"],
            "additionalProperties": False,
        },
    },
}

AGENT_TOOLS = [SEARCH_DOCUMENTS_SCHEMA, TRANSFER_SELECTED_FILE_SCHEMA]


@dataclass
class TaskSession:
    """In-memory state container for an active user task."""
    task_id: str
    owner: str
    device_id: str
    user_prompt: str
    state: TaskState = TaskState.QUEUED
    task_version: int = 1
    model_turns: int = 0
    tool_calls_count: int = 0
    start_time: float = field(default_factory=time.time)
    deadline_seconds: float = 120.0
    pending_tool_call: Optional[ToolCallMessage] = None
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    pending_approval: Optional[ApprovalRequestMessage] = None
    clarification: Optional[ClarificationQuestionMessage] = None
    progress_history: List[ProgressMessage] = field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def is_terminal(self) -> bool:
        return self.state in (
            TaskState.COMPLETED,
            TaskState.PARTIAL,
            TaskState.FAILED,
            TaskState.CANCELLED,
        )

    def is_expired(self) -> bool:
        return (time.time() - self.start_time) > self.deadline_seconds


# Type alias for helper dispatcher: takes ToolCallMessage -> returns ToolResultMessage
ToolDispatcher = Callable[[ToolCallMessage], ToolResultMessage]


class AgentLoop:
    """Bounded, contract-enforcing agent loop orchestrator."""

    def __init__(
        self,
        client: Optional[MetaClient] = None,
        dispatcher: Optional[ToolDispatcher] = None,
        cfg: Optional[PicoConfig] = None,
    ):
        self.config = cfg or default_config
        self.client = client or MetaClient(self.config)
        self.dispatcher = dispatcher

    def _transition(self, session: TaskSession, new_state: TaskState, message: str) -> ProgressMessage:
        """Enforces legal state transitions and records progress."""
        if session.is_terminal():
            raise RuntimeError(
                f"Cannot transition task {session.task_id} from terminal state {session.state} to {new_state}."
            )
        session.state = new_state
        progress = ProgressMessage(
            contract_version=1,
            task_id=session.task_id,
            state=new_state,
            message=message,
            task_version=session.task_version,
        )
        session.progress_history.append(progress)
        return progress

    def _fail_task(self, session: TaskSession, code: ErrorCode, msg: str) -> None:
        session.state = TaskState.FAILED
        session.error_code = code.value
        session.error_message = msg
        session.pending_tool_call = None
        session.progress_history.append(
            ProgressMessage(
                contract_version=1,
                task_id=session.task_id,
                state=TaskState.FAILED,
                message=msg,
                task_version=session.task_version,
            )
        )

    def start_task(self, req: RequestMessage, owner: str = "default_user") -> TaskSession:
        """Initializes a new task session from a valid RequestMessage."""
        session = TaskSession(
            task_id=req.task_id,
            owner=owner,
            device_id=req.device_id,
            user_prompt=req.text,
            deadline_seconds=self.config.task_deadline_seconds,
        )
        self._transition(session, TaskState.PLANNING, "Analyzing user request and selecting action.")
        return session

    def step(self, session: TaskSession) -> ProgressMessage:
        """Executes a single bounded turn of the agent loop."""
        if session.is_terminal():
            raise RuntimeError(f"Task {session.task_id} is already in terminal state {session.state}.")

        # Check deadline
        if session.is_expired():
            self._fail_task(session, ErrorCode.TIMEOUT, "Task exceeded overall execution deadline.")
            return session.progress_history[-1]

        # Check turn boundaries
        if session.model_turns >= self.config.max_model_turns:
            self._fail_task(session, ErrorCode.TIMEOUT, f"Exceeded MAX_MODEL_TURNS ({self.config.max_model_turns}).")
            return session.progress_history[-1]

        if session.tool_calls_count >= self.config.max_tool_calls:
            self._fail_task(session, ErrorCode.TIMEOUT, f"Exceeded MAX_TOOL_CALLS ({self.config.max_tool_calls}).")
            return session.progress_history[-1]

        # Increment turn count
        session.model_turns += 1

        # Build prompt messages for MetaClient
        system_instruction = (
            "You are Pico, a secure phone-to-computer assistant. "
            "Help the user find and access files on their paired computer. "
            "To find files, invoke the `search_documents` tool. "
            "Never hallucinate file contents or forge approvals."
        )
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": session.user_prompt},
        ]

        # Invoke model
        response = self.client.chat(messages=messages, tools=AGENT_TOOLS)

        # Case 1: Model proposed tool call(s)
        if response.tool_calls:
            raw_tool = response.tool_calls[0]
            func = raw_tool.get("function", {})
            tool_name = func.get("name")
            raw_args_str = func.get("arguments", "{}")

            try:
                args = json.loads(raw_args_str) if isinstance(raw_args_str, str) else raw_args_str
            except json.JSONDecodeError:
                self._fail_task(session, ErrorCode.UNSUPPORTED_TOOL, "Model produced malformed JSON arguments.")
                return session.progress_history[-1]

            # Validate tool against supported set
            if tool_name not in [t.value for t in ToolName]:
                self._fail_task(session, ErrorCode.UNSUPPORTED_TOOL, f"Tool '{tool_name}' is not supported.")
                return session.progress_history[-1]

            step_id = f"step-{uuid.uuid4().hex[:8]}"
            call_id = raw_tool.get("id") or f"call-{uuid.uuid4().hex[:8]}"

            # Construct strictly validated ToolCallMessage
            tool_call_msg = ToolCallMessage(
                contract_version=1,
                task_id=session.task_id,
                step_id=step_id,
                call_id=call_id,
                tool=tool_name,
                arguments=args,
                idempotency_key=f"{session.task_id}:{step_id}",
                deadline_seconds=int(self.config.tool_timeout_seconds),
            )
            session.pending_tool_call = tool_call_msg
            session.tool_calls_count += 1

            self._transition(session, TaskState.EXECUTING, f"Executing tool: {tool_name}")

            # If a dispatcher is attached, execute immediately
            if self.dispatcher:
                result = self.dispatcher(tool_call_msg)
                return self.handle_tool_result(session, result)

            return session.progress_history[-1]

        # Case 2: Model answered directly or asked clarification without tools
        content = response.content or ""
        if "?" in content:
            session.clarification = ClarificationQuestionMessage(
                contract_version=1,
                task_id=session.task_id,
                question_id=f"q-{uuid.uuid4().hex[:8]}",
                task_version=session.task_version,
                question_text=content,
            )
            return self._transition(session, TaskState.NEEDS_CLARIFICATION, content)
        else:
            # Model replied with regular narration; complete task if no actions needed
            return self._transition(session, TaskState.COMPLETED, content)

    def handle_tool_result(self, session: TaskSession, result: ToolResultMessage) -> ProgressMessage:
        """Processes structured tool execution result returned by helper."""
        if session.is_terminal():
            raise RuntimeError(
                f"Task {session.task_id} is already in terminal state {session.state}. Late results are ignored."
            )

        if not session.pending_tool_call:
            raise RuntimeError("Received tool_result without a matching pending tool_call.")

        if result.call_id != session.pending_tool_call.call_id:
            raise RuntimeError(
                f"Mismatched call_id in tool_result. Expected {session.pending_tool_call.call_id}, got {result.call_id}."
            )

        tool_name = session.pending_tool_call.tool
        session.pending_tool_call = None

        # Hard rule: A failed search must never become a completed delivery
        if result.status != "succeeded":
            err_code = (
                ErrorCode(result.error_code)
                if result.error_code in [e.value for e in ErrorCode]
                else (ErrorCode.NO_MATCH if tool_name == ToolName.SEARCH_DOCUMENTS.value else ErrorCode.PERMISSION_DENIED)
            )
            self._fail_task(
                session,
                err_code,
                result.error_message or f"Tool '{tool_name}' failed to execute.",
            )
            return session.progress_history[-1]

        # Process search_documents result
        if tool_name == ToolName.SEARCH_DOCUMENTS.value:
            data = result.data or {}
            raw_candidates = data.get("candidates", [])
            session.candidates = raw_candidates

            if not raw_candidates:
                self._fail_task(session, ErrorCode.NO_MATCH, "No matching documents found.")
                return session.progress_history[-1]

            # Require user approval before transferring any candidate
            first_cand = raw_candidates[0]
            approval_id = f"appr-{uuid.uuid4().hex[:8]}"
            expiry_unix = int(time.time() + 300)  # 5 min expiry

            session.pending_approval = ApprovalRequestMessage(
                contract_version=1,
                task_id=session.task_id,
                step_id=result.step_id,
                approval_id=approval_id,
                operation=ToolName.TRANSFER_SELECTED_FILE.value,
                candidate_id=first_cand.get("candidate_id", ""),
                candidate_name=first_cand.get("name", "Unknown File"),
                task_version=session.task_version,
                expires_at_unix=expiry_unix,
            )

            return self._transition(
                session,
                TaskState.NEEDS_APPROVAL,
                f"Found {len(raw_candidates)} candidate file(s). Select and approve file to transfer.",
            )

        return self._transition(session, TaskState.COMPLETED, f"Tool {tool_name} finished successfully.")
