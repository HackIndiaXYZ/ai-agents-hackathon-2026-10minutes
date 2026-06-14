"""
agents/decomposition_agent.py — Query Decomposition Agent

Responsibility: Break a complex user query into atomic, independently answerable
sub-queries, each tagged with its type and whether it needs web search.
Uses Gemini Flash.

Single responsibility — this agent only decomposes. It does not answer anything.
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
    temperature=0,
)

# ─── System prompt ────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a query decomposition specialist. Break the user's query into
atomic, independently answerable sub-queries.

Return ONLY a JSON array:
[
  {
    "query": "specific atomic question",
    "type": "scheme_lookup|eligibility_check|document_requirement|
              deadline_query|market_price|fraud_alert|general_guidance",
    "requires_web_search": boolean,
    "status": "pending"
  }
]

Rules:
- Maximum 4 sub-queries per turn
- Each sub-query must be self-contained
- Tag requires_web_search true only for volatile information types
  (market_price, deadline_query, recent news/policy changes)
- Merge related sub-queries rather than over-decomposing
- status must always be "pending" """


def decomposition_agent(state: AgentState) -> AgentState:
    """
    Decomposes the user query into sub-queries.
    Writes: sub_queries (list), current_sub_query (first pending item).
    """
    start_time = log_agent_entry("decomposition", state)

    try:
        prompt = f"""User message: {state['raw_input']}

Detected language: {state.get('detected_language', 'English')}
User profile: {json.dumps(state.get('user_profile', {}), ensure_ascii=False)}
Max sub-queries: {settings.MAX_SUB_QUERIES}
Web search trigger types: {settings.WEB_SEARCH_TRIGGER_TYPES}

Break this into atomic sub-queries. Return JSON array only."""

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

        sub_queries = json.loads(raw_content)

        # Enforce maximum and ensure status field
        sub_queries = sub_queries[: settings.MAX_SUB_QUERIES]
        for sq in sub_queries:
            sq["status"] = "pending"

        state["sub_queries"] = sub_queries
        state["current_sub_query"] = sub_queries[0] if sub_queries else None

    except Exception as exc:
        state = log_agent_error("decomposition", exc, state)
        # Fallback: treat the whole query as one general_guidance sub-query
        fallback = {
            "query": state["raw_input"],
            "type": "general_guidance",
            "requires_web_search": False,
            "status": "pending",
        }
        state["sub_queries"] = [fallback]
        state["current_sub_query"] = fallback

    return log_agent_exit("decomposition", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(
        session_id="test-decomp-001",
        raw_input="PM Kisan ke liye kya documents chahiye aur aaj wheat ka MSP kya hai?",
    )
    test_state["detected_language"] = "Hindi"
    test_state["user_profile"] = {"occupation": "farmer", "state": "Punjab"}

    result = decomposition_agent(test_state)
    print("sub_queries:")
    for sq in result["sub_queries"]:
        print(" ", sq)
    print("current_sub_query:", result["current_sub_query"])
    print("errors:", result["errors"])
