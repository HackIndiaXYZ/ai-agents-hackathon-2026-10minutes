"""
agents/context_agent.py — User Context Extraction Agent

Responsibility: Extract and update user profile fields from the conversation.
Merges new evidence into the existing profile and persists to Redis.
Uses Gemini Pro for nuanced understanding.

Single responsibility — this agent updates the profile only. It does not route,
answer, or reason about the query.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from graph.state import AgentState
from memory.session_store import load_profile, save_profile
from utils.logger import log_agent_entry, log_agent_exit, log_agent_error

# ─── Model — Flash is sufficient for JSON field extraction ───────────────────
_llm = ChatVertexAI(
    model_name=settings.FLASH_MODEL,
    project=settings.VERTEX_AI_PROJECT_ID,
    location=settings.VERTEX_AI_REGION,
    temperature=0,
)

# ─── System prompt ────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a user context extractor for a rural Indian financial assistant.
Given the user's message and their existing profile, extract any new
contextual information and return ONLY a JSON object merging new findings
into the profile.

Profile fields to extract or update:
- occupation: farmer/small_business/laborer/student/unemployed/other
- state: Indian state name
- district: district name if mentioned
- landholding_acres: numeric if mentioned
- has_aadhaar: boolean if mentioned
- has_bank_account: boolean if mentioned
- financial_literacy_level: low/medium/high (infer from vocabulary used)
- mentioned_schemes: list of any government schemes mentioned
- implied_need: primary financial need implied by conversation

Only update fields where you have evidence. Return full merged profile as JSON."""


def context_agent(state: AgentState) -> AgentState:
    """
    Extracts user context from the conversation and merges into user_profile.
    Persists the updated profile to Redis.
    Writes: user_profile (updated).
    """
    start_time = log_agent_entry("context", state)

    try:
        # Load the persisted profile (may have data from previous turns)
        persisted_profile = load_profile(state["session_id"])

        # Merge with whatever is already in state (current turn might have added data)
        merged_profile = {**persisted_profile, **state.get("user_profile", {})}

        prompt = f"""Existing profile:
{json.dumps(merged_profile, indent=2)}

User message:
{state['raw_input']}

Detected language: {state.get('detected_language', 'English')}
Formality tier: {state.get('formality_tier', 'informal')}

Return the updated profile as a single JSON object."""

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = _llm.invoke(messages)
        raw_content = response.content.strip()

        # Strip markdown fences
        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
            raw_content = raw_content.strip()

        updated_profile = json.loads(raw_content)

        # Persist the updated profile and write back to state
        save_profile(state["session_id"], updated_profile)
        state["user_profile"] = updated_profile

    except Exception as exc:
        state = log_agent_error("context", exc, state)
        # Keep whatever profile we had — don't lose existing data

    return log_agent_exit("context", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(
        session_id="test-ctx-001",
        raw_input="Main Rajasthan mein ek chota kisan hoon, mere paas 2 acre zameen hai. Kya PM Kisan milega?",
    )
    test_state["detected_language"] = "Hindi"
    test_state["formality_tier"] = "colloquial"

    result = context_agent(test_state)
    print("user_profile:", json.dumps(result["user_profile"], indent=2, ensure_ascii=False))
    print("errors:", result["errors"])
