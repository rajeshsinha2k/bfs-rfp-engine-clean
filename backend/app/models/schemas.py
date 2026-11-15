from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    RUNNING = "RUNNING"
    PAUSED_HITL_1 = "PAUSED_HITL_1"
    PAUSED_HITL_2 = "PAUSED_HITL_2"
    NO_GO = "NO_GO"
    COMPLETED = "COMPLETED"


class HITLActionButton(BaseModel):
    action_id: str            # e.g., "NEW_RFP", "EXISTING_RFP", "GO", "NO_GO", "AUTHORIZE_TRANSMISSION"
    label: str                # Rendered button label in chat stream
    variant: str = "primary"  # "primary" | "danger" | "secondary"


class ChatMessageEvent(BaseModel):
    rfp_id: Optional[str] = None
    sender: str               # "System Orchestrator" | "Triage Director" | etc.
    phase: int
    message_english: str
    message_native: Optional[str] = None
    artifact_type: Optional[str] = None   # "EFFORT_MATRIX" | "RACI" | "CLARIFICATION_LOG" | "TCO" | "FINAL_PACKAGE"
    artifact_payload: Optional[dict] = None
    hitl_buttons: List[HITLActionButton] = Field(default_factory=list)


class RFPProjectCreate(BaseModel):
    client_name: str
    detected_language: str = "en"
    custom_template_path: Optional[str] = None
    created_by_user: str


class QuestionSlice(BaseModel):
    slice_id: str
    rfp_id: str
    section_anchor: str
    question_native: str
    question_english: str
    assigned_owner: Optional[str] = None
    raci_role: Optional[str] = None
    kb_confidence_score: float
    is_clarification_required: bool
    draft_response_english: Optional[str] = None
    draft_response_native: Optional[str] = None
    external_citations: List[str] = Field(default_factory=list)
    guardrail_status: str = "PENDING"
