"""
adaptive/logger.py — Capture user interactions for the adaptive data loop.

We queue a small, low-PII event for each meaningful interaction. We deliberately
store only coarse profile context (state, occupation, language) — never name,
profile_id, phone, or account numbers. Full anonymisation/formatting happens
later in dataset_builder.harvest().
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from memory.session_store import log_interaction_event
from utils.logger import logger


def _coarse_profile(profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Keep only non-identifying, generalisable context."""
    p = profile or {}
    return {
        "state": p.get("state", ""),
        "occupation": p.get("occupation", ""),
        "age_group": p.get("age_group", ""),
        "literacy_level": p.get("literacy_level", p.get("financial_literacy_level", "")),
        "language": p.get("preferred_language", ""),
    }


def log_interaction(
    kind: str,
    user_text: str,
    assistant_summary: str,
    profile: Optional[Dict[str, Any]] = None,
    language: str = "English",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Queue one interaction event.

    Args:
        kind:               chat | scheme | document | complaint | fraud_alert
        user_text:          what the user asked / requested (no PII expected)
        assistant_summary:  short summary of what we returned
        profile:            user profile (only coarse fields are kept)
        language:           detected/preferred language
        extra:              optional structured details (domain, actions, etc.)
    """
    try:
        event = {
            "kind": kind,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "language": language,
            "profile": _coarse_profile(profile),
            "user_text": (user_text or "")[:1200],
            "assistant_summary": (assistant_summary or "")[:3000],
            "extra": extra or {},
        }
        log_interaction_event(event)
    except Exception as exc:
        # Logging must never break the user-facing request
        logger.warning(f"[adaptive] log_interaction failed: {exc}")
