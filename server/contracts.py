"""Shared tool contracts and message models for Pico (Contract v1).

Strictly models messages from docs/contract-examples.json and docs/tool-contracts.md.
Rules:
- Envelope fields: contract_version (int, literal 1), task_id (str), type (str).
- Tool calls and results carry step_id and call_id.
- Extra fields are strictly forbidden (extra="forbid").
- Discriminated union on 'type'.
- Permissions, approvals, and schema validation are enforced in code, never in prompts.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Base Envelope & Enums
# -----------------------------------------------------------------------------

class ContractBase(BaseModel):
    """Base message envelope required across all Pico communications."""
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[1] = 1
    task_id: str = Field(..., description="Unique task identifier")


class TaskState(str, Enum):
    """Standard lifecycle states defined in docs/tool-contracts.md."""
    QUEUED = "queued"
    PLANNING = "planning"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_APPROVAL = "needs_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    AWAITING_RECEIPT = "awaiting_receipt"
    # Terminal states
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorCode(str, Enum):
    """Standard error codes defined in docs/tool-contracts.md."""
    PERMISSION_DENIED = "permission_denied"
    DEVICE_OFFLINE = "device_offline"
    NO_MATCH = "no_match"
    CANDIDATE_CHANGED = "candidate_changed"
    TIMEOUT = "timeout"
    UNSUPPORTED_TOOL = "unsupported_tool"


class ToolName(str, Enum):
    """Initial tools defined in contract."""
    SEARCH_DOCUMENTS = "search_documents"
    TRANSFER_SELECTED_FILE = "transfer_selected_file"
    CREATE_CHECKLIST = "create_checklist"
    READ_BACK_FILE = "read_back_file"
    OPEN_RESOURCE = "open_resource"
    CAPTURE_CURRENT_TAB = "capture_current_tab"


# -----------------------------------------------------------------------------
# 1. Existing Messages (from docs/contract-examples.json)
# -----------------------------------------------------------------------------

class RequestMessage(ContractBase):
    """Initial user task request from phone."""
    type: Literal["request"] = "request"
    device_id: str = Field(..., description="Target device identifier")
    text: str = Field(..., description="User request prompt / instruction")


class ToolCallMessage(ContractBase):
    """Model-directed validated tool call dispatched to helper."""
    type: Literal["tool_call"] = "tool_call"
    step_id: str = Field(..., description="Identifier for this workflow step")
    call_id: str = Field(..., description="Identifier for this tool invocation")
    tool: str = Field(..., description="Name of the tool being invoked")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments dictionary")
    idempotency_key: Optional[str] = Field(None, description="Key ensuring safe retries")
    deadline_seconds: Optional[int] = Field(None, description="Timeout for tool execution")


class SearchCandidate(BaseModel):
    """Candidate document returned by search_documents."""
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., description="Opaque candidate ID (never raw path)")
    name: str = Field(..., description="Display filename")
    size_bytes: int = Field(..., description="File size in bytes")


class ToolResultData(BaseModel):
    """Payload data for tool result."""
    model_config = ConfigDict(extra="forbid")

    candidates: Optional[List[SearchCandidate]] = None
    # Extensible for other tools while preserving extra="forbid" per field
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    digest: Optional[str] = None
    items: Optional[List[str]] = None
    content: Optional[str] = None


class ToolResultEvidence(BaseModel):
    """Evidence supplied by native helper or device."""
    model_config = ConfigDict(extra="forbid")

    grant_id: Optional[str] = None
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    simulated: Optional[bool] = None


class ToolResultMessage(ContractBase):
    """Execution result returned from native helper."""
    type: Literal["tool_result"] = "tool_result"
    step_id: str = Field(..., description="Step ID matching the tool call")
    call_id: str = Field(..., description="Call ID matching the tool call")
    status: Literal["succeeded", "failed"] = Field(..., description="Execution outcome")
    data: Optional[Dict[str, Any]] = Field(None, description="Result payload")
    evidence: Optional[Dict[str, Any]] = Field(None, description="Cryptographic or grant evidence")
    error_code: Optional[str] = Field(None, description="Standard error code if failed")
    error_message: Optional[str] = Field(None, description="Short human error description")


class ProgressMessage(ContractBase):
    """Progress event sent to phone/overlay."""
    type: Literal["progress"] = "progress"
    state: TaskState = Field(..., description="Current lifecycle state")
    message: str = Field(..., description="Short progress description")
    task_version: Optional[int] = Field(None, description="Monotonically increasing version")


class VerificationResultMessage(ContractBase):
    """Independent verification result (Santosh's verifier)."""
    type: Literal["verification_result"] = "verification_result"
    step_id: str = Field(..., description="Step ID verified")
    status: Literal["verified", "pending", "failed"] = Field(..., description="Verification status")
    reason: Optional[str] = Field(None, description="Outcome explanation or check failure reason")


# -----------------------------------------------------------------------------
# 2. Proposed Messages (Decisions to confirm with Aditya & Santosh)
# -----------------------------------------------------------------------------

class ApprovalRequestMessage(ContractBase):
    """PROPOSAL: Server requests user approval on phone before executing sensitive action.
    Bound to exact operation, candidate, task version and expiry.
    """
    type: Literal["approval_request"] = "approval_request"
    step_id: str
    approval_id: str = Field(..., description="Unique ID for this approval grant request")
    operation: str = Field(..., description="Operation to be approved (e.g. transfer_selected_file)")
    candidate_id: str = Field(..., description="Opaque candidate ID being approved")
    candidate_name: str = Field(..., description="Display filename shown to user")
    task_version: int = Field(..., description="Task version this approval applies to")
    expires_at_unix: int = Field(..., description="Expiry timestamp in unix epoch seconds")


class ApprovalGrantMessage(ContractBase):
    """PROPOSAL: User responds to approval request from phone."""
    type: Literal["approval_grant"] = "approval_grant"
    approval_id: str = Field(..., description="Approval ID matching request")
    approved: bool = Field(..., description="Whether user granted approval")
    candidate_id: str = Field(..., description="Candidate ID confirmed by user")
    task_version: int = Field(..., description="Must match current task version")


class ClarificationQuestionMessage(ContractBase):
    """PROPOSAL: Agent pauses and asks clarifying question to user."""
    type: Literal["clarification_question"] = "clarification_question"
    question_id: str = Field(..., description="Unique question identifier")
    task_version: int = Field(..., description="Current task version")
    question_text: str = Field(..., description="Question prompt to user")
    options: Optional[List[str]] = Field(None, description="Optional choices")


class ClarificationAnswerMessage(ContractBase):
    """PROPOSAL: User answers clarification question from phone."""
    type: Literal["clarification_answer"] = "clarification_answer"
    question_id: str = Field(..., description="Question ID matching the question")
    task_version: int = Field(..., description="Must match task version to prevent race")
    answer_text: str = Field(..., description="User response text")


class PhoneReceiptMessage(ContractBase):
    """PROPOSAL: Authenticated phone acknowledges actual receipt of file.
    Separate from upload; required for verifier to declare success.
    """
    type: Literal["phone_receipt"] = "phone_receipt"
    step_id: str
    candidate_id: str
    received_bytes: int = Field(..., description="Actual bytes received by phone")
    received_sha256: str = Field(..., description="SHA-256 digest calculated by phone")


class CancelMessage(ContractBase):
    """PROPOSAL: User or system requests cancellation of task."""
    type: Literal["cancel"] = "cancel"
    reason: Optional[str] = Field(None, description="Optional cancellation reason")


class ErrorMessage(ContractBase):
    """PROPOSAL: Structured error message emitted on fatal failure."""
    type: Literal["error"] = "error"
    error_code: ErrorCode = Field(..., description="Standard stable error code")
    message: str = Field(..., description="Short error message")
    step_id: Optional[str] = None


# -----------------------------------------------------------------------------
# Discriminated Union of All Messages
# -----------------------------------------------------------------------------

# Established Contract Messages (contract-examples.json)
EstablishedMessage = Annotated[
    Union[
        RequestMessage,
        ToolCallMessage,
        ToolResultMessage,
        ProgressMessage,
        VerificationResultMessage,
    ],
    Field(discriminator="type"),
]

# Complete Protocol Message Union (Including Proposed Extensions)
PicoMessage = Annotated[
    Union[
        RequestMessage,
        ToolCallMessage,
        ToolResultMessage,
        ProgressMessage,
        VerificationResultMessage,
        ApprovalRequestMessage,
        ApprovalGrantMessage,
        ClarificationQuestionMessage,
        ClarificationAnswerMessage,
        PhoneReceiptMessage,
        CancelMessage,
        ErrorMessage,
    ],
    Field(discriminator="type"),
]


def parse_pico_message(raw_dict: Dict[str, Any]) -> PicoMessage:
    """Parse and validate any Pico protocol message strictly enforcing schema."""
    from pydantic import TypeAdapter
    adapter = TypeAdapter(PicoMessage)
    return adapter.validate_python(raw_dict)

