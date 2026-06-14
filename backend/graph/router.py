"""
graph/router.py — Conditional Edge Routing Functions

All routing decisions live here. Each function receives AgentState and returns
a string that LangGraph uses to pick the next node.

Single responsibility — pure routing logic, no LLM calls, no side effects.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from graph.state import AgentState


def route_after_supervisor(state: AgentState) -> str:
    """
    Called after supervisor_agent.
    Returns "clarification" if clarification is needed, else "decomposition".
    """
    if state.get("needs_clarification", False):
        return "clarification"
    return "decomposition"


def route_after_decomposition(state: AgentState) -> str:
    """
    Called after decomposition_agent.
    Returns "web_search" if any sub-query requires it, else "reasoning".
    """
    sub_queries = state.get("sub_queries", [])
    if sub_queries and any(sq.get("requires_web_search", False) for sq in sub_queries):
        return "web_search"
    return "reasoning"
