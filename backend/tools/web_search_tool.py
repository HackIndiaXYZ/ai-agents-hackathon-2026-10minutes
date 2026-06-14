"""
tools/web_search_tool.py — LangChain Google Search Tool Wrapper

Exposes a LangChain-compatible tool for use in agents or direct calls.
The web_search_agent uses GoogleSearchAPIWrapper directly; this file
provides the tool wrapper for any agent that prefers the Tool interface.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain.tools import Tool
from langchain_google_community import GoogleSearchAPIWrapper

from config import settings

# ─── Wrapper instance ─────────────────────────────────────────────────────────
_search_wrapper = GoogleSearchAPIWrapper(
    google_api_key=settings.GOOGLE_SEARCH_API_KEY,
    google_cse_id=settings.GOOGLE_SEARCH_ENGINE_ID,
    k=5,
)

# ─── LangChain Tool (can be bound to any ReAct/Tool-calling agent) ────────────
google_search_tool = Tool(
    name="google_search",
    description=(
        "Search Google for current information about Indian government schemes, "
        "market prices, policy deadlines, and recent news. "
        "Input should be a specific search query string."
    ),
    func=_search_wrapper.run,
)


def search(query: str, num_results: int = 5) -> list[dict]:
    """
    Run a Google search and return structured results.
    Each result has: title, snippet, link.
    """
    return _search_wrapper.results(query, num_results=num_results)
