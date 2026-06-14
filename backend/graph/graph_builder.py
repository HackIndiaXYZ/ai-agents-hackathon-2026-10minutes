"""
graph/graph_builder.py — LangGraph Graph Assembly

This file wires all 11 agents together into a compiled StateGraph.
The structure is:
  language → context → supervisor → [clarification | decomposition]
  clarification → formatter → feedback → END
  decomposition → [web_search | reasoning] → reasoning → recommendation → fraud_safety → formatter → feedback → END

Import build_graph() wherever you need the compiled graph instance.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.router import route_after_supervisor, route_after_decomposition

# ─── Agent imports ────────────────────────────────────────────────────────────
from agents.language_agent import language_agent
from agents.context_agent import context_agent
from agents.supervisor_agent import supervisor_agent
from agents.clarification_agent import clarification_agent
from agents.decomposition_agent import decomposition_agent
from agents.web_search_agent import web_search_agent
from agents.reasoning_agent import reasoning_agent
from agents.recommendation_agent import recommendation_agent
from agents.fraud_safety_agent import fraud_safety_agent
from agents.formatter_agent import formatter_agent
from agents.feedback_agent import feedback_agent


def build_graph():
    """
    Assemble and compile the full agent graph.
    Returns a compiled LangGraph instance ready to invoke.

    Graph topology:
      language → context → supervisor
        ↓ (conditional)
      clarification → formatter → feedback → END
        ↓ (conditional)
      decomposition → [web_search?] → reasoning → recommendation → fraud_safety → formatter → feedback → END
    """
    graph = StateGraph(AgentState)

    # ── Add all nodes ──────────────────────────────────────────────────────────
    graph.add_node("language", language_agent)
    graph.add_node("context", context_agent)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("clarification", clarification_agent)
    graph.add_node("decomposition", decomposition_agent)
    graph.add_node("web_search", web_search_agent)
    graph.add_node("reasoning", reasoning_agent)
    graph.add_node("recommendation", recommendation_agent)
    graph.add_node("fraud_safety", fraud_safety_agent)
    graph.add_node("formatter", formatter_agent)
    graph.add_node("feedback", feedback_agent)

    # ── Entry point ────────────────────────────────────────────────────────────
    graph.set_entry_point("language")

    # ── Linear early pipeline ──────────────────────────────────────────────────
    graph.add_edge("language", "context")
    graph.add_edge("context", "supervisor")

    # ── Conditional: clarification branch vs execution branch ──────────────────
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "clarification": "clarification",
            "decomposition": "decomposition",
        },
    )

    # ── Clarification short-circuits to formatter then feedback ────────────────
    graph.add_edge("clarification", "formatter")
    graph.add_edge("formatter", "feedback")
    graph.add_edge("feedback", END)

    # ── Full execution path ────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "decomposition",
        route_after_decomposition,
        {
            "web_search": "web_search",
            "reasoning": "reasoning",
        },
    )

    graph.add_edge("web_search", "reasoning")
    graph.add_edge("reasoning", "recommendation")
    graph.add_edge("recommendation", "fraud_safety")
    graph.add_edge("fraud_safety", "formatter")

    # formatter and feedback share the same terminal edges for both paths above
    # (LangGraph allows multiple predecessors pointing to the same node)

    return graph.compile()


# ─── Module-level compiled graph ─────────────────────────────────────────────
# Import this singleton in main.py — compiled once at startup.
compiled_graph = build_graph()
