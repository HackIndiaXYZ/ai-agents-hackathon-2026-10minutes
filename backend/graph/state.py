"""
graph/state.py — AgentState TypedDict

This is the single source of truth that flows through every node in the graph.
Every agent reads from and writes to this object. No agent should store state
anywhere other than this TypedDict.
"""

from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict):
    # ─── Input ────────────────────────────────────────────────────────────────
    session_id: str
    raw_input: str
    turn_number: int

    # ─── Conversation memory (persisted across turns) ─────────────────────────
    # [{role: "user"/"assistant", content: str, turn: int}] — last 10 turns kept
    conversation_history: List[Dict]

    # ─── Linked onboarding profile ────────────────────────────────────────────
    profile_id: Optional[str]           # profile_id from the onboarding flow
    knowledge_graph: Dict[str, Any]     # KG from onboarding (literacy, domains, scores)

    # ─── Language layer ───────────────────────────────────────────────────────
    detected_language: str          # e.g. "Hindi", "Bengali", "English"
    detected_script: str            # e.g. "Devanagari", "Roman", "Bengali"
    is_code_switching: bool
    formality_tier: str             # "formal" | "informal" | "colloquial"

    # ─── User profile (persisted to Redis) ───────────────────────────────────
    user_profile: Dict[str, Any]    # occupation, state, literacy_level, etc.

    # ─── Supervisor decisions ─────────────────────────────────────────────────
    routing_manifest: List[str]     # ordered list of agents to invoke
    needs_clarification: bool
    clarification_question: Optional[str]
    estimated_confidence: float

    # ─── Query decomposition ──────────────────────────────────────────────────
    sub_queries: List[Dict]         # [{query: str, type: str, status: str}]
    current_sub_query: Optional[Dict]

    # ─── Retrieval results ────────────────────────────────────────────────────
    web_search_results: List[Dict]  # [{fact: str, source_url: str, date: str}]
    rag_results: List[Dict]         # top-K similar cases from Qdrant/BGE pipeline

    # ─── Reasoning output ─────────────────────────────────────────────────────
    reasoning_output: Optional[Dict]  # {answer: str, evidence: list, confidence: float}

    # ─── Recommendation output ────────────────────────────────────────────────
    recommendations: Optional[Dict]  # {next_steps: list, related_schemes: list}

    # ─── Structured final output (separate from prose answer) ────────────────
    next_steps: List[Dict]          # [{step_number, action, where, estimated_time, required_documents}]
    related_schemes: List[Dict]     # [{scheme_name, relevance_reason, quick_eligibility}]

    # ─── Safety ───────────────────────────────────────────────────────────────
    fraud_flags: List[str]
    safety_blocks_applied: bool
    original_response_before_safety: Optional[str]

    # ─── Final response ───────────────────────────────────────────────────────
    final_response: str
    response_for_voice: Optional[str]
    confidence_score: float

    # ─── Feedback ─────────────────────────────────────────────────────────────
    feedback_rating: Optional[str]  # "helpful" | "not_helpful"

    # ─── Observability ────────────────────────────────────────────────────────
    agent_trace: List[Dict]         # [{agent: str, input: dict, output: dict, latency_ms: int}]
    errors: List[str]


def default_state(session_id: str, raw_input: str, turn_number: int = 1) -> AgentState:
    """
    Returns a fully-initialized AgentState with safe defaults.
    Call this when starting a brand-new session or a new turn without prior state.
    """
    return AgentState(
        session_id=session_id,
        raw_input=raw_input,
        turn_number=turn_number,
        conversation_history=[],
        profile_id=None,
        knowledge_graph={},
        detected_language="English",
        detected_script="Roman",
        is_code_switching=False,
        formality_tier="informal",
        user_profile={},
        routing_manifest=[],
        needs_clarification=False,
        clarification_question=None,
        estimated_confidence=0.0,
        sub_queries=[],
        current_sub_query=None,
        web_search_results=[],
        rag_results=[],
        reasoning_output=None,
        recommendations=None,
        next_steps=[],
        related_schemes=[],
        fraud_flags=[],
        safety_blocks_applied=False,
        original_response_before_safety=None,
        final_response="",
        response_for_voice=None,
        confidence_score=0.0,
        feedback_rating=None,
        agent_trace=[],
        errors=[],
    )
