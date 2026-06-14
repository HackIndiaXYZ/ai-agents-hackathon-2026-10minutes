"""
main.py — FastAPI Entry Point

Three endpoints:
  POST /chat           → Streaming SSE conversation endpoint
  POST /feedback       → Submit thumbs up/down on a turn
  GET  /session/{id}   → Full session state dump for debugging
  GET  /health         → Redis + model connectivity check
"""

import json
import uuid
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import AsyncGenerator

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from graph.state import default_state, AgentState
from graph.graph_builder import compiled_graph
from memory.session_store import (
    load_session,
    save_session,
    load_profile,
    get_feedback,
    update_feedback_rating,
    health_check,
    save_user_profile,
    load_user_profile,
    list_user_profiles,
    save_knowledge_graph,
    load_knowledge_graph,
    append_kg_snapshot,
)
from models.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    SessionDebugResponse,
    HealthResponse,
    UserProfileRequest,
    UserProfileResponse,
    NextQuestionRequest,
    QuestionResponse,
    CompleteOnboardingRequest,
    KnowledgeGraphResponse,
)

_MAX_HISTORY_TURNS = 6   # keep last 6 exchanges (12 entries) in state
from onboarding.question_generator import generate_next_question, is_survey_complete
from onboarding.knowledge_graph_builder import build_from_survey, kg_to_user_profile_fields
from utils.logger import log_agent_entry, log_agent_exit
from rag.rag_router import router as rag_router
from features.features_router import router as features_router
from i18n.i18n_router import router as i18n_router
from adaptive.adaptive_router import router as adaptive_router
from adaptive.logger import log_interaction

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Financial Inclusion Multi-Agent Assistant",
    description="Enterprise-grade multi-agent AI for rural Indian financial inclusion",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag_router)
app.include_router(features_router)
app.include_router(i18n_router)
app.include_router(adaptive_router)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_initial_state(
    session_id: str,
    message: str,
    language_hint: str | None,
    profile_id: str | None = None,
) -> AgentState:
    """Load existing session from Redis or create a fresh one."""
    existing = load_session(session_id)
    if existing:
        state = AgentState(**existing)
        state["raw_input"] = message
        state["turn_number"] = existing.get("turn_number", 0) + 1
        # Reset per-turn transient fields — keep cross-turn memory fields
        state["agent_trace"] = []
        state["errors"] = []
        state["web_search_results"] = []
        state["rag_results"] = []
        state["reasoning_output"] = None
        state["recommendations"] = None
        state["next_steps"] = []
        state["related_schemes"] = []
        state["fraud_flags"] = []
        state["safety_blocks_applied"] = False
        state["original_response_before_safety"] = None
        state["final_response"] = ""
        state["response_for_voice"] = None
        state["needs_clarification"] = False
        state["clarification_question"] = None
        state["sub_queries"] = []
        state["current_sub_query"] = None
        state["feedback_rating"] = None
        # Reload persisted profile
        profile = load_profile(session_id)
        if profile:
            state["user_profile"] = profile
        # Preserve conversation history (already in state from prior turn)
        # — do NOT reset it here
    else:
        state = default_state(session_id=session_id, raw_input=message, turn_number=1)

    # Apply language hint from UI selector
    if language_hint:
        state["detected_language"] = language_hint

    # ── Knowledge graph injection ──────────────────────────────────────────────
    # If the frontend passes a profile_id (linked onboarding profile), load the KG
    # and enrich the user_profile with literacy / domain data.
    pid = profile_id or state.get("profile_id")
    if pid:
        state["profile_id"] = pid
        if not state.get("knowledge_graph"):
            kg = load_knowledge_graph(pid)
            if kg:
                state["knowledge_graph"] = kg
                # Merge high-value KG fields into user_profile for downstream agents
                state["user_profile"] = {
                    **state.get("user_profile", {}),
                    "literacy_level":   kg.get("literacy_level", "basic"),
                    "overall_score":    kg.get("overall_score", 0),
                    "kg_domains":       kg.get("domains", {}),
                    "financial_literacy_level": kg.get("literacy_level", "low"),
                }

    # ── Append incoming user message to history ────────────────────────────────
    history = list(state.get("conversation_history") or [])
    history.append({"role": "user", "content": message, "turn": state["turn_number"]})
    # Keep only the last MAX_HISTORY_TURNS * 2 entries (user + assistant pairs)
    state["conversation_history"] = history[-(  _MAX_HISTORY_TURNS * 2):]

    return state


async def _stream_graph(state: AgentState) -> AsyncGenerator[str, None]:
    """
    Run the compiled LangGraph and stream SSE events for each agent transition.
    LangGraph's stream() yields (node_name, output_state) tuples for each node.
    We emit agent_start / agent_complete events around each node.
    """
    def _event(data: dict) -> str:
        return f"data: {json.dumps(data, default=str)}\n\n"

    final_state: AgentState | None = None

    try:
        # LangGraph stream — yields a dictionary of {node_name: partial_state} at each step
        for step in compiled_graph.stream(
            state,
            stream_mode="updates",
        ):
            for node_name, chunk in step.items():
                # chunk is a dict of field updates from this node
                # Emit agent_complete event (entry is logged inside each agent)
                agent_trace = chunk.get("agent_trace", [])
                latency_ms = agent_trace[-1]["latency_ms"] if agent_trace else 0

                yield _event(
                    {
                        "event": "agent_complete",
                        "agent": node_name,
                        "latency_ms": latency_ms,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "errors": chunk.get("errors", []),
                        "fraud_flags": chunk.get("fraud_flags", []),
                    }
                )

                # Merge chunk into final_state tracking
                if final_state is None:
                    final_state = state.copy()
                final_state.update(chunk)

            # Small yield to allow client to receive events progressively
            await asyncio.sleep(0)

        # Emit final response event
        if final_state:
            # Append assistant reply to conversation history before saving
            history = list(final_state.get("conversation_history") or [])
            assistant_reply = final_state.get("final_response", "")
            if assistant_reply:
                history.append({
                    "role": "assistant",
                    "content": assistant_reply,
                    "turn": final_state.get("turn_number", 1),
                })
                final_state["conversation_history"] = history[-(_MAX_HISTORY_TURNS * 2):]

                # Adaptive data loop: capture the answered question (no PII stored)
                if not final_state.get("needs_clarification"):
                    log_interaction(
                        kind="chat",
                        user_text=final_state.get("raw_input", ""),
                        assistant_summary=assistant_reply,
                        profile=final_state.get("user_profile", {}),
                        language=final_state.get("detected_language", "English"),
                        extra={
                            "sub_queries": [sq.get("type") for sq in final_state.get("sub_queries", [])],
                            "next_steps": final_state.get("next_steps", []),
                        },
                    )

            yield _event(
                {
                    "event": "final_response",
                    "response": final_state.get("final_response", ""),
                    "voice_response": final_state.get("response_for_voice"),
                    "confidence": final_state.get("confidence_score", 0.0),
                    "agents_fired": [t["agent"] for t in final_state.get("agent_trace", [])],
                    "fraud_flags": final_state.get("fraud_flags", []),
                    "clarification_needed": final_state.get("needs_clarification", False),
                    "detected_language": final_state.get("detected_language", "English"),
                    "turn_number": final_state.get("turn_number", 1),
                    "session_id": final_state.get("session_id", ""),
                    "user_profile": final_state.get("user_profile", {}),
                    "sub_queries": final_state.get("sub_queries", []),
                    # ── Structured outputs for dedicated frontend panels ────────
                    "next_steps":       final_state.get("next_steps", []),
                    "related_schemes":  final_state.get("related_schemes", []),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    except Exception as exc:
        yield _event(
            {
                "event": "error",
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Main conversation endpoint. Returns a streaming SSE response.
    Each SSE event is a newline-delimited JSON object.

    Event types:
      agent_complete — emitted after each agent node completes
      final_response — last event, contains the full response
      error          — emitted on unhandled exceptions
    """
    state = _build_initial_state(
        session_id=request.session_id,
        message=request.message,
        language_hint=request.language_hint,
        profile_id=request.profile_id,
    )

    return StreamingResponse(
        _stream_graph(state),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Accept user feedback (thumbs up/down) for a specific turn.
    Updates the feedback record in Redis.
    """
    if request.rating not in ("helpful", "not_helpful"):
        raise HTTPException(status_code=400, detail="rating must be 'helpful' or 'not_helpful'")

    updated = update_feedback_rating(
        session_id=request.session_id,
        turn_number=request.turn_number,
        rating=request.rating,
    )

    if not updated:
        return FeedbackResponse(
            success=False,
            message=f"No feedback record found for turn {request.turn_number}",
        )

    return FeedbackResponse(success=True, message="Feedback recorded")


@app.get("/session/{session_id}", response_model=SessionDebugResponse)
async def get_session(session_id: str):
    """
    Returns the full session state for debugging.
    Includes agent trace, user profile, sub-queries, fraud flags, and feedback.
    """
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    feedback_records = get_feedback(session_id)

    return SessionDebugResponse(
        session_id=session_id,
        turn_number=session.get("turn_number", 0),
        detected_language=session.get("detected_language", "English"),
        detected_script=session.get("detected_script", "Roman"),
        user_profile=session.get("user_profile", {}),
        sub_queries=session.get("sub_queries", []),
        web_search_results=session.get("web_search_results", []),
        reasoning_output=session.get("reasoning_output"),
        recommendations=session.get("recommendations"),
        fraud_flags=session.get("fraud_flags", []),
        safety_blocks_applied=session.get("safety_blocks_applied", False),
        agent_trace=session.get("agent_trace", []),
        errors=session.get("errors", []),
        feedback_records=feedback_records,
        confidence_score=session.get("confidence_score", 0.0),
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Quick health check — verifies Redis connectivity."""
    return HealthResponse(
        status="ok",
        redis_connected=health_check(),
        model_pro=settings.PRO_MODEL,
        model_flash=settings.FLASH_MODEL,
    )


@app.get("/")
async def root():
    return {
        "service": "Financial Inclusion Multi-Agent Assistant",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ─── User Profile Endpoints ───────────────────────────────────────────────────

@app.post("/profile", response_model=UserProfileResponse)
async def create_profile(request: UserProfileRequest):
    """Create or update a user profile. Returns the profile with its ID."""
    profile_id = request.profile_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    profile = request.model_dump()
    profile["profile_id"] = profile_id

    # Only set created_at on first creation
    existing = load_user_profile(profile_id)
    profile["created_at"] = existing.get("created_at", now)
    profile["updated_at"] = now

    save_user_profile(profile_id, profile)
    return UserProfileResponse(**profile)


@app.get("/profile/{profile_id}", response_model=UserProfileResponse)
async def get_profile(profile_id: str):
    profile = load_user_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return UserProfileResponse(**profile)


@app.get("/profiles", response_model=list)
async def get_all_profiles():
    """Return all saved user profiles (for the profile selector UI)."""
    return list_user_profiles()


# ─── Onboarding / Survey Endpoints ───────────────────────────────────────────

@app.post("/onboarding/next-question", response_model=QuestionResponse)
async def next_question(request: NextQuestionRequest):
    """
    Generate the next adaptive survey question.
    Call repeatedly, incrementing question_number and passing all previous
    answers each time.  When survey_complete=true, call /onboarding/complete.
    """
    profile = load_user_profile(request.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create a profile first.")

    complete = is_survey_complete(request.answers, request.question_number)
    if complete:
        return QuestionResponse(
            question_number=request.question_number,
            question_text="",
            question_type="MCQ",
            domain="",
            concept="",
            difficulty="basic",
            options=None,
            survey_complete=True,
        )

    question = generate_next_question(
        answers=request.answers,
        user_profile=profile,
        question_number=request.question_number,
    )
    if question is None:
        return QuestionResponse(
            question_number=request.question_number,
            question_text="",
            question_type="MCQ",
            domain="",
            concept="",
            difficulty="basic",
            options=None,
            survey_complete=True,
        )

    return QuestionResponse(
        question_number=question["question_number"],
        question_text=question["question_text"],
        question_type=question["question_type"],
        domain=question["domain"],
        concept=question["concept"],
        difficulty=question["difficulty"],
        options=question.get("options"),
        survey_complete=False,
    )


@app.post("/onboarding/complete", response_model=KnowledgeGraphResponse)
async def complete_onboarding(request: CompleteOnboardingRequest):
    """
    Finalise the survey and build the knowledge graph.
    Saves KG to Redis.  Returns the full knowledge graph.
    """
    profile = load_user_profile(request.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    kg = build_from_survey(
        profile_id=request.profile_id,
        answers=request.answers,
    )
    save_knowledge_graph(request.profile_id, kg)
    # Record the first progress snapshot for the Literacy Progress Dashboard
    append_kg_snapshot(request.profile_id, kg, trigger="onboarding")

    # Also enrich the user profile with KG summary for chat personalisation
    kg_fields = kg_to_user_profile_fields(kg)
    profile.update(kg_fields)
    profile["onboarding_complete"] = True
    save_user_profile(request.profile_id, profile)

    return KnowledgeGraphResponse(
        profile_id=kg["profile_id"],
        domains=kg["domains"],
        overall_score=kg["overall_score"],
        literacy_level=kg["literacy_level"],
        chat_interactions=kg.get("chat_interactions", 0),
        created_at=kg.get("created_at"),
        last_updated=kg.get("last_updated"),
    )


@app.get("/knowledge-graph/{profile_id}", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(profile_id: str):
    """Return the stored knowledge graph for a user."""
    kg = load_knowledge_graph(profile_id)
    if not kg:
        raise HTTPException(status_code=404, detail="Knowledge graph not found. Complete onboarding first.")
    return KnowledgeGraphResponse(
        profile_id=kg["profile_id"],
        domains=kg["domains"],
        overall_score=kg["overall_score"],
        literacy_level=kg["literacy_level"],
        chat_interactions=kg.get("chat_interactions", 0),
        created_at=kg.get("created_at"),
        last_updated=kg.get("last_updated"),
    )
