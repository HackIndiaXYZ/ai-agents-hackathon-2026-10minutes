"""
agents/supervisor_agent.py — Routing Brain Agent

Responsibility: Decide HOW to answer, not what to answer. Produces a routing
manifest that all downstream agents follow. Uses Gemini Pro.

Single responsibility — this agent produces routing decisions only. It never
attempts to answer the user's question.
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
    model_name=settings.PRO_MODEL,
    project=settings.VERTEX_AI_PROJECT_ID,
    location=settings.VERTEX_AI_REGION,
    temperature=0,
)

# ─── System prompt ────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are the supervisor of a multi-agent financial inclusion system for
rural India. Your job is NOT to answer questions — your job is to decide
how to answer them.

Given the user's message, conversation history, and user profile, produce
ONLY a JSON routing manifest:

{
  "needs_clarification": boolean,
  "clarification_reason": string or null,
  "estimated_confidence": float between 0 and 1,
  "sub_query_types": list of types from
    [scheme_lookup, eligibility_check, document_requirement,
     deadline_query, market_price, fraud_alert, general_guidance],
  "requires_web_search": boolean,
  "web_search_reason": string or null,
  "routing_notes": string
}

Set needs_clarification to true if:
- The query is ambiguous about which scheme or benefit they need
- Critical context (state, occupation, crop type) is missing and essential
- The user's intent could mean two very different things

Set requires_web_search to true if:
- The query involves current market prices
- The query involves upcoming or current deadlines
- The query involves recent policy changes or announcements

Be conservative with clarification — only block if truly necessary."""


def supervisor_agent(state: AgentState) -> AgentState:
    """
    Produces the routing manifest. Sets needs_clarification, estimated_confidence,
    and routing_manifest in state.
    """
    start_time = log_agent_entry("supervisor", state)

    try:
        # If we've already clarified enough turns, bypass further clarification
        turn_number = state.get("turn_number", 1)
        force_proceed = turn_number > settings.MAX_CLARIFICATION_TURNS

        # Build a compact history string for context
        history = state.get("conversation_history", [])
        history_str = ""
        if len(history) > 1:  # more than just the current user message
            recent = history[:-1]  # exclude the just-added user message
            pairs = []
            for h in recent[-6:]:  # last 3 turns (6 entries)
                role = "User" if h["role"] == "user" else "Assistant"
                pairs.append(f"{role}: {h['content'][:200]}")
            history_str = "\n".join(pairs)

        # KG summary for routing context
        kg = state.get("knowledge_graph", {})
        kg_str = ""
        if kg:
            kg_str = f"KG literacy: {kg.get('literacy_level','unknown')}, score: {kg.get('overall_score',0):.0f}/100"

        prompt = f"""User message: {state['raw_input']}

Detected language: {state.get('detected_language', 'English')}
User profile: {json.dumps(state.get('user_profile', {}), ensure_ascii=False)}
{f"Knowledge graph: {kg_str}" if kg_str else ""}
Turn number: {turn_number}
Max clarification turns allowed: {settings.MAX_CLARIFICATION_TURNS}
Force proceed (skip clarification): {force_proceed}

{f"Recent conversation history:{chr(10)}{history_str}" if history_str else "First turn — no history yet."}

Produce the routing manifest JSON."""

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

        manifest = json.loads(raw_content)

        # Override clarification if we've hit the max turns
        needs_clarification = manifest.get("needs_clarification", False) and not force_proceed

        # Determine routing_manifest list
        if needs_clarification:
            routing_manifest = ["clarification"]
        else:
            routing_manifest = ["decomposition", "web_search", "reasoning", "recommendation", "fraud_safety", "formatter"]
            if manifest.get("requires_web_search"):
                pass  # web_search is already in the list above

        state["needs_clarification"] = needs_clarification
        state["clarification_question"] = manifest.get("clarification_reason")
        state["estimated_confidence"] = float(manifest.get("estimated_confidence", 0.5))
        state["routing_manifest"] = routing_manifest

    except Exception as exc:
        state = log_agent_error("supervisor", exc, state)
        # Safe fallback — proceed without clarification
        state["needs_clarification"] = False
        state["routing_manifest"] = ["decomposition", "reasoning", "recommendation", "fraud_safety", "formatter"]
        state["estimated_confidence"] = 0.5

    return log_agent_exit("supervisor", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(
        session_id="test-sup-001",
        raw_input="Wheat price kya hai aaj Rajasthan mein?",
    )
    test_state["detected_language"] = "Hindi"
    test_state["user_profile"] = {"state": "Rajasthan", "occupation": "farmer"}

    result = supervisor_agent(test_state)
    print("needs_clarification:", result["needs_clarification"])
    print("estimated_confidence:", result["estimated_confidence"])
    print("routing_manifest:", result["routing_manifest"])
    print("errors:", result["errors"])
