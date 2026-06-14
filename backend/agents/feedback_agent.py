"""
agents/feedback_agent.py — Structured Feedback Logger

Responsibility: Persist a complete turn record (query, response, confidence,
agents fired, fraud flags, rating) to Redis for batch analysis. No LLM call.

Single responsibility — this agent only persists structured feedback.
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from graph.state import AgentState
from memory.session_store import append_feedback, save_session
from utils.logger import log_agent_entry, log_agent_exit, log_agent_error


def feedback_agent(state: AgentState) -> AgentState:
    """
    Persists a complete turn record to Redis. No LLM call.
    This is always the last node before END.
    Writes: nothing new to state, but saves to Redis.
    """
    start_time = log_agent_entry("feedback", state)

    try:
        feedback_record = {
            "session_id": state["session_id"],
            "turn_number": state["turn_number"],
            "query": state["raw_input"],
            "final_response": state.get("final_response", ""),
            "confidence_score": state.get("confidence_score", 0.0),
            "agents_fired": [t["agent"] for t in state.get("agent_trace", [])],
            "fraud_flags": state.get("fraud_flags", []),
            "safety_blocks_applied": state.get("safety_blocks_applied", False),
            "detected_language": state.get("detected_language", "English"),
            "needs_clarification": state.get("needs_clarification", False),
            "sub_queries_count": len(state.get("sub_queries", [])),
            "web_results_count": len(state.get("web_search_results", [])),
            "errors": state.get("errors", []),
            "rating": state.get("feedback_rating"),  # populated via /feedback endpoint
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Write to per-session feedback list and global list
        append_feedback(state["session_id"], feedback_record)

        # Also persist the full session state for /session/{id} debugging endpoint
        save_session(state["session_id"], dict(state))

    except Exception as exc:
        state = log_agent_error("feedback", exc, state)

    return log_agent_exit("feedback", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(session_id="test-feedback-001", raw_input="PM Kisan?")
    test_state["final_response"] = "PM Kisan mein aapko 6000 rupaye milte hain."
    test_state["confidence_score"] = 0.85
    test_state["agent_trace"] = [
        {"agent": "language", "latency_ms": 120},
        {"agent": "context", "latency_ms": 350},
    ]
    test_state["fraud_flags"] = []

    result = feedback_agent(test_state)
    print("Feedback logged. Errors:", result["errors"])
