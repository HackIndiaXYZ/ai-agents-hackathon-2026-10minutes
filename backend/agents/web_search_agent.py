"""
agents/web_search_agent.py — Web Search Agent

Responsibility: Perform Google searches for sub-queries that require fresh,
real-world data (prices, deadlines, recent news). Applies freshness filtering.
Uses LangChain's Google Search API wrapper — no LLM call in this agent.

Single responsibility — this agent only fetches and filters search results.
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from graph.state import AgentState
from utils.logger import log_agent_entry, log_agent_exit, log_agent_error

# ─── Search wrapper (lazy — only initialised when credentials are present) ────
_search = None

def _get_search():
    global _search
    if _search is None:
        from langchain_google_community import GoogleSearchAPIWrapper
        _search = GoogleSearchAPIWrapper(
            google_api_key=settings.GOOGLE_SEARCH_API_KEY,
            google_cse_id=settings.GOOGLE_SEARCH_ENGINE_ID,
            k=5,
        )
    return _search

def _web_search_enabled() -> bool:
    return bool(settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_ENGINE_ID)


def _parse_date(date_str: str) -> datetime | None:
    """Attempt to parse a date string from search metadata."""
    if not date_str:
        return None
    formats = ["%Y-%m-%d", "%B %d, %Y", "%d %B %Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _is_fresh(date_str: str, query_type: str) -> bool:
    """
    Returns True if the result is fresh enough for the query type.
    market_price: max 7 days
    deadline_query: max 30 days
    All others: always fresh
    """
    parsed = _parse_date(date_str)
    if parsed is None:
        return True  # can't determine age, allow through

    now = datetime.now(timezone.utc)
    age_days = (now - parsed).days

    if query_type == "market_price":
        return age_days <= settings.MARKET_PRICE_MAX_AGE_DAYS
    elif query_type == "deadline_query":
        return age_days <= settings.DEADLINE_MAX_AGE_DAYS
    return True


def _search_single_query(sub_query: Dict) -> List[Dict]:
    """Run one search and return structured result dicts."""
    results = []
    try:
        raw_results = _get_search().results(sub_query["query"], num_results=5)
        for r in raw_results:
            date_str = r.get("snippet", "")[:30] if r.get("snippet") else ""
            result = {
                "fact": r.get("snippet", ""),
                "source_url": r.get("link", ""),
                "title": r.get("title", ""),
                "date": date_str,
                "query_type": sub_query.get("type", "general_guidance"),
                "is_fresh": _is_fresh(date_str, sub_query.get("type", "")),
            }
            results.append(result)
    except Exception as e:
        results.append({
            "fact": f"Search failed: {str(e)}",
            "source_url": "",
            "title": "",
            "date": "",
            "query_type": sub_query.get("type", ""),
            "is_fresh": False,
        })
    return results


def web_search_agent(state: AgentState) -> AgentState:
    """
    Executes web searches for sub-queries flagged requires_web_search=True.
    Applies freshness filtering. Writes: web_search_results.
    """
    start_time = log_agent_entry("web_search", state)

    try:
        if not _web_search_enabled():
            state["web_search_results"] = []
            return log_agent_exit("web_search", state, start_time,
                                  extra={"results_count": 0, "skipped": "credentials not set"})

        sub_queries = state.get("sub_queries", [])
        all_results: List[Dict] = []

        for sq in sub_queries:
            if sq.get("requires_web_search", False):
                results = _search_single_query(sq)
                for r in results:
                    if not r["is_fresh"]:
                        r["fact"] = f"[STALE RESULT - may be outdated] {r['fact']}"
                all_results.extend(results)

        state["web_search_results"] = all_results

    except Exception as exc:
        state = log_agent_error("web_search", exc, state)
        state["web_search_results"] = []

    return log_agent_exit(
        "web_search",
        state,
        start_time,
        extra={"results_count": len(state.get("web_search_results", []))},
    )


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(
        session_id="test-websearch-001",
        raw_input="Wheat MSP 2024 in Punjab",
    )
    test_state["sub_queries"] = [
        {
            "query": "Wheat MSP price 2024 Punjab India",
            "type": "market_price",
            "requires_web_search": True,
            "status": "pending",
        }
    ]
    test_state["current_sub_query"] = test_state["sub_queries"][0]

    result = web_search_agent(test_state)
    print(f"Found {len(result['web_search_results'])} results")
    for r in result["web_search_results"]:
        print(f"  [{r['is_fresh']}] {r['title']}: {r['fact'][:80]}")
    print("errors:", result["errors"])
