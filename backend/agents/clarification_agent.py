"""
agents/clarification_agent.py — Clarification Question Generator

Responsibility: When the supervisor decides a clarifying question is needed,
this agent generates a single, clear question in the user's language.
Uses Gemini Flash. Short-circuits the pipeline — sets final_response directly.

Single responsibility — this agent only generates clarifying questions.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from graph.state import AgentState
from utils.logger import log_agent_entry, log_agent_exit, log_agent_error

# ─── Model ────────────────────────────────────────────────────────────────────
_llm = ChatVertexAI(
    model_name=settings.FLASH_MODEL,
    project=settings.VERTEX_AI_PROJECT_ID,
    location=settings.VERTEX_AI_REGION,
    temperature=0.3,  # slight warmth for natural phrasing
)

# ─── System prompt template ───────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """You are a clarification assistant for a rural Indian financial assistant.
Generate a single, clear clarifying question in the user's detected language.

The question must:
- Be simple enough for a low-literacy user to answer
- Offer numbered options when possible (1. Option A  2. Option B)
- Be in {detected_language} at {formality_tier} register
- Address exactly one missing piece of context
- Never ask more than one question at a time

Return ONLY the question text. No JSON. No preamble."""


def clarification_agent(state: AgentState) -> AgentState:
    """
    Generates a clarifying question in the user's language.
    Writes: clarification_question, final_response (set to the question text).
    This agent only fires when state["needs_clarification"] is True.
    """
    start_time = log_agent_entry("clarification", state)

    try:
        detected_language = state.get("detected_language", "English")
        formality_tier = state.get("formality_tier", "informal")
        clarification_reason = state.get("clarification_question", "The query is ambiguous.")

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            detected_language=detected_language,
            formality_tier=formality_tier,
        )

        prompt = f"""User's original message: {state['raw_input']}

Reason clarification is needed: {clarification_reason}
User profile so far: {state.get('user_profile', {})}

Generate one clarifying question."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]
        response = _llm.invoke(messages)
        question = response.content.strip()

        state["clarification_question"] = question
        # Short-circuit: set final_response so the formatter passes it through
        state["final_response"] = question
        state["confidence_score"] = 0.0  # no answer yet

    except Exception as exc:
        state = log_agent_error("clarification", exc, state)
        # Fallback question
        fallback = "Could you please provide more details about what specific financial help you need? (1. Government scheme information  2. Loan guidance  3. Agricultural support)"
        state["clarification_question"] = fallback
        state["final_response"] = fallback

    return log_agent_exit("clarification", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(
        session_id="test-clarify-001",
        raw_input="Mujhe yojana chahiye",
    )
    test_state["detected_language"] = "Hindi"
    test_state["formality_tier"] = "colloquial"
    test_state["needs_clarification"] = True
    test_state["clarification_question"] = "User did not specify which scheme or their state"

    result = clarification_agent(test_state)
    print("clarification_question:", result["clarification_question"])
    print("final_response:", result["final_response"])
    print("errors:", result["errors"])
