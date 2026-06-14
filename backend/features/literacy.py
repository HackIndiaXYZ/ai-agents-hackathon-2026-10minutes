"""
features/literacy.py — Literacy Progress Dashboard.

Turns the user's real knowledge-graph data (current scores + historical
snapshots stored in Redis) into a progress view: how each domain has moved over
time, which domains are weakest, and an AI-suggested set of next learning steps
grounded in the user's actual gaps.

The progress numbers are 100% real user data. Only the "what to learn next"
suggestions come from the model, and they are derived from the real weak domains.
"""

import sys
import os
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from features.gemini_grounded import generate_grounded
from utils.logger import logger

_DOMAINS = [
    "Banking & Digital Payments",
    "Government Schemes",
    "Fraud & Cyber Safety",
    "Savings & Insurance",
    "Credit & Borrowing",
]


def _domain_scores(kg: Dict[str, Any]) -> Dict[str, float]:
    out = {}
    for d in _DOMAINS:
        out[d] = round((kg.get("domains", {}).get(d, {}) or {}).get("score", 0.0) * 100)
    return out


def _build_timeline(history: List[Dict[str, Any]], kg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalise stored snapshots into a timeline of {timestamp, overall, domains}.
    Always append the current KG state as the latest point.
    """
    timeline: List[Dict[str, Any]] = []
    for snap in history:
        timeline.append({
            "timestamp": snap.get("timestamp", ""),
            "overall": round(snap.get("overall_score", 0.0) * 100),
            "domains": {k: round(v * 100) for k, v in (snap.get("domain_scores", {}) or {}).items()},
            "trigger": snap.get("trigger", ""),
        })
    # Current state as the final point
    timeline.append({
        "timestamp": kg.get("last_updated", ""),
        "overall": round(kg.get("overall_score", 0.0) * 100),
        "domains": _domain_scores(kg),
        "trigger": "current",
    })
    return timeline


def _suggest_next_steps(kg: Dict[str, Any], weak_domains: List[str], language: str) -> List[Dict[str, Any]]:
    """Ask Gemini for concrete micro-learning steps targeting the weak domains."""
    if not weak_domains:
        return []

    known = [
        c
        for dom in kg.get("domains", {}).values()
        for c, info in (dom.get("concepts", {}) or {}).items()
        if info.get("known")
    ]

    prompt = f"""You are a financial-literacy coach for rural India. A user has these WEAK
domains that need improvement: {", ".join(weak_domains)}.
They already understand: {", ".join(known[:15]) or "very little so far"}.

Suggest 3-5 concrete, bite-sized next learning steps that target the weak domains.
Each step must be practical and achievable for someone in rural India.

Return ONLY a JSON array of objects:
[
  {{
    "domain": "which of the 5 domains this targets",
    "title": "short lesson title in {language}",
    "why": "one line on why this matters for them, in {language}",
    "action": "one concrete thing to do or learn, in {language}",
    "difficulty": "basic" | "intermediate"
  }}
]
Keep {language} text in {language}; keep JSON keys in English."""

    result = generate_grounded(prompt, temperature=0.3, want_json=True, use_grounding=False)
    parsed = result.get("json")
    if isinstance(parsed, list):
        steps = []
        for s in parsed:
            if isinstance(s, dict):
                steps.append({
                    "domain": s.get("domain", ""),
                    "title": s.get("title", ""),
                    "why": s.get("why", ""),
                    "action": s.get("action", ""),
                    "difficulty": s.get("difficulty", "basic"),
                })
        return steps
    logger.warning("[literacy] next-step suggestions not parseable")
    return []


def build_progress(kg: Dict[str, Any], history: List[Dict[str, Any]], language: str = "English") -> Dict[str, Any]:
    """
    Assemble the full progress dashboard payload.

    Returns:
      {
        "overall_score", "literacy_level", "chat_interactions",
        "current_domains": {domain: percent},
        "timeline": [{timestamp, overall, domains, trigger}],
        "weakest_domains": [domain, ...],
        "strongest_domains": [domain, ...],
        "improvement_since_start": int (percentage points),
        "next_steps": [ ... ],
      }
    """
    if not kg:
        return {
            "overall_score": 0,
            "literacy_level": "not_assessed",
            "current_domains": {},
            "timeline": [],
            "weakest_domains": [],
            "strongest_domains": [],
            "improvement_since_start": 0,
            "next_steps": [],
            "has_data": False,
        }

    current = _domain_scores(kg)
    timeline = _build_timeline(history, kg)

    # Weakest / strongest domains by current score
    ranked = sorted(current.items(), key=lambda x: x[1])
    weakest = [d for d, _ in ranked[:2]]
    strongest = [d for d, _ in ranked[-2:][::-1]]

    # Improvement vs first recorded snapshot
    improvement = 0
    if len(timeline) >= 2:
        improvement = timeline[-1]["overall"] - timeline[0]["overall"]

    next_steps = _suggest_next_steps(kg, weakest, language)

    return {
        "overall_score": round(kg.get("overall_score", 0.0) * 100),
        "literacy_level": kg.get("literacy_level", "beginner"),
        "chat_interactions": kg.get("chat_interactions", 0),
        "current_domains": current,
        "timeline": timeline,
        "weakest_domains": weakest,
        "strongest_domains": strongest,
        "improvement_since_start": improvement,
        "next_steps": next_steps,
        "has_data": True,
    }
