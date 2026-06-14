"""
agents/recommendation_agent.py — Next Steps Recommendation Agent

Responsibility: Given an answer and user profile, generate concrete, actionable
next steps specific to the user's situation. Uses Gemini Flash.

Single responsibility — this agent only generates recommendations. It does not
answer questions or check for safety issues.
"""

import json
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
    temperature=0.2,
)

# ─── System prompt ────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a next-steps recommendation engine for rural Indian financial
assistance. Given an answer and the user's profile, generate concrete,
actionable guidance.

Return ONLY JSON:
{
  "next_steps": [
    {
      "step_number": int,
      "action": "specific action in user's language",
      "where": "physical location or URL",
      "estimated_time": "time estimate",
      "required_documents": list of strings
    }
  ],
  "related_schemes": [
    {
      "scheme_name": str,
      "relevance_reason": str,
      "quick_eligibility": str
    }
  ],
  "estimated_total_time": str
}

Next steps must be:
- Specific to the user's state if state is known
- Ordered by dependency (gather documents before visiting office)
- Written at the user's literacy level
- Maximum 4 steps per response

Related schemes: suggest 1-2 schemes the user likely qualifies for based
on their profile, even if not asked."""


def recommendation_agent(state: AgentState) -> AgentState:
    """
    Generates actionable next steps and related scheme suggestions.
    Writes: recommendations.
    """
    start_time = log_agent_entry("recommendation", state)

    try:
        reasoning_output = state.get("reasoning_output", {})
        user_profile = state.get("user_profile", {})
        literacy_level = user_profile.get("financial_literacy_level", "low")
        user_state = user_profile.get("state", "India")

        prompt = f"""The assistant has produced this answer:
{json.dumps(reasoning_output, indent=2, ensure_ascii=False)}

User profile:
{json.dumps(user_profile, indent=2, ensure_ascii=False)}

User's state: {user_state}
Literacy level: {literacy_level}
Detected language: {state.get('detected_language', 'English')}

Generate concrete next steps and related scheme suggestions. Return JSON only."""

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

        recommendations = json.loads(raw_content)
        state["recommendations"] = recommendations

    except Exception as exc:
        state = log_agent_error("recommendation", exc, state)
        state["recommendations"] = {
            "next_steps": [],
            "related_schemes": [],
            "estimated_total_time": "unknown",
        }

    return log_agent_exit("recommendation", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(
        session_id="test-rec-001",
        raw_input="PM Kisan ke liye kaise apply karein?",
    )
    test_state["detected_language"] = "Hindi"
    test_state["user_profile"] = {
        "occupation": "farmer",
        "state": "Maharashtra",
        "financial_literacy_level": "low",
        "has_aadhaar": True,
    }
    test_state["reasoning_output"] = {
        "answer": "PM Kisan mein apply karne ke liye aapko apne gram panchayat ya CSC jaana hoga.",
        "evidence": [],
        "confidence": 0.8,
    }

    result = recommendation_agent(test_state)
    print("recommendations:", json.dumps(result["recommendations"], indent=2, ensure_ascii=False))
    print("errors:", result["errors"])
