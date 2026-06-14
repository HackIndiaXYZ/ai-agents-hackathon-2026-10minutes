"""
utils/logger.py — Structured agent lifecycle logger.

Every agent calls log_agent_entry() at the start and log_agent_exit() at the
end. All output is newline-delimited JSON so GCP Cloud Logging can ingest it
without any additional configuration.
"""

import json
import time
import logging
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graph.state import AgentState

# ─── Root logger wired to stdout as JSON ─────────────────────────────────────
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))  # raw JSON lines

logger = logging.getLogger("financial_inclusion")
logger.setLevel(logging.DEBUG)
logger.addHandler(_handler)
logger.propagate = False  # don't double-print


def _emit(record: dict) -> None:
    """Write a single structured JSON line to stdout."""
    print(json.dumps(record, default=str), flush=True)


def log_agent_entry(agent_name: str, state: "AgentState") -> float:
    """
    Log agent entry. Returns the monotonic start time (use with log_agent_exit).

    Args:
        agent_name: The canonical agent name (same as the LangGraph node name).
        state:      Current AgentState.

    Returns:
        start_time: float — pass to log_agent_exit to compute latency.
    """
    start_time = time.monotonic()
    _emit(
        {
            "severity": "INFO",
            "event": "agent_start",
            "agent": agent_name,
            "session_id": state.get("session_id", "unknown"),
            "turn_number": state.get("turn_number", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    return start_time


def log_agent_exit(
    agent_name: str,
    state: "AgentState",
    start_time: float,
    extra: dict | None = None,
) -> "AgentState":
    """
    Log agent exit, compute latency, append to state["agent_trace"], return state.

    Args:
        agent_name: The canonical agent name.
        state:      Current AgentState (will be mutated: agent_trace appended).
        start_time: The float returned by log_agent_entry.
        extra:      Optional dict of extra fields to record in the trace entry.

    Returns:
        The updated state (same object, mutated in place).
    """
    latency_ms = int((time.monotonic() - start_time) * 1000)

    trace_entry = {
        "agent": agent_name,
        "latency_ms": latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }

    # Append to the agent_trace list
    state["agent_trace"] = state.get("agent_trace", []) + [trace_entry]

    _emit(
        {
            "severity": "INFO",
            "event": "agent_complete",
            "agent": agent_name,
            "session_id": state.get("session_id", "unknown"),
            "turn_number": state.get("turn_number", 0),
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    return state


def log_agent_error(
    agent_name: str,
    error: Exception,
    state: "AgentState",
) -> "AgentState":
    """
    Log an agent-level error, append message to state["errors"], return state.

    Agents call this in their except block so the graph continues gracefully
    rather than crashing the entire pipeline.
    """
    error_msg = f"[{agent_name}] {type(error).__name__}: {str(error)}"

    state["errors"] = state.get("errors", []) + [error_msg]

    _emit(
        {
            "severity": "ERROR",
            "event": "agent_error",
            "agent": agent_name,
            "session_id": state.get("session_id", "unknown"),
            "turn_number": state.get("turn_number", 0),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    return state
