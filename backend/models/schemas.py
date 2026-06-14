"""
models/schemas.py — Pydantic models for all API contracts.

All request/response models for FastAPI endpoints live here.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ─── Request models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., description="User's raw message")
    language_hint: Optional[str] = Field(
        None,
        description="Optional language hint from the UI language selector (e.g. 'Hindi')"
    )
    profile_id: Optional[str] = Field(
        None,
        description="Linked onboarding profile_id — enables KG-aware personalization"
    )


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., description="Session the feedback belongs to")
    turn_number: int = Field(..., description="Turn number within the session")
    rating: str = Field(..., description="'helpful' or 'not_helpful'")


# ─── Response models ──────────────────────────────────────────────────────────

class AgentEvent(BaseModel):
    """Streamed SSE event for agent pipeline visualization."""
    event: str                      # agent_start | agent_complete | agent_error | final_response
    agent: Optional[str] = None
    timestamp: Optional[str] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class ChatResponse(BaseModel):
    """Final response payload (also emitted as the last SSE event)."""
    session_id: str
    response: str
    voice_response: Optional[str] = None
    confidence: float
    agents_fired: List[str]
    fraud_flags: List[str]
    clarification_needed: bool
    detected_language: str
    turn_number: int


class FeedbackResponse(BaseModel):
    success: bool
    message: str


class SessionDebugResponse(BaseModel):
    """Full session state for the /session/{session_id} debugging endpoint."""
    session_id: str
    turn_number: int
    detected_language: str
    detected_script: str
    user_profile: Dict[str, Any]
    sub_queries: List[Dict]
    web_search_results: List[Dict]
    reasoning_output: Optional[Dict]
    recommendations: Optional[Dict]
    fraud_flags: List[str]
    safety_blocks_applied: bool
    agent_trace: List[Dict]
    errors: List[str]
    feedback_records: List[Dict]
    confidence_score: float


class HealthResponse(BaseModel):
    status: str
    redis_connected: bool
    model_pro: str
    model_flash: str


# ─── Onboarding / Profile ─────────────────────────────────────────────────────

class UserProfileRequest(BaseModel):
    profile_id: Optional[str] = Field(None, description="Leave empty to auto-generate")
    name: str
    age_group: str = Field(..., description="e.g. '18-25', '26-35', '36-50', '50+'")
    state: str
    occupation: str
    preferred_language: str = "English"
    gender: Optional[str] = None
    education_level: Optional[str] = None
    has_smartphone: bool = True
    has_bank_account: Optional[bool] = None


class UserProfileResponse(BaseModel):
    profile_id: str
    name: str
    age_group: str
    state: str
    occupation: str
    preferred_language: str
    gender: Optional[str]
    education_level: Optional[str]
    has_smartphone: bool
    has_bank_account: Optional[bool]
    created_at: Optional[str] = None


class NextQuestionRequest(BaseModel):
    profile_id: str
    answers: List[Dict[str, Any]] = Field(default_factory=list)
    question_number: int = Field(..., ge=1)


class QuestionResponse(BaseModel):
    question_number: int
    question_text: str
    question_type: str          # "MCQ" | "SHORT_TEXT"
    domain: str
    concept: str
    difficulty: str
    options: Optional[List[str]] = None
    survey_complete: bool = False


class CompleteOnboardingRequest(BaseModel):
    profile_id: str
    answers: List[Dict[str, Any]]


class KnowledgeGraphResponse(BaseModel):
    profile_id: str
    domains: Dict[str, Any]
    overall_score: float
    literacy_level: str
    chat_interactions: int
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
