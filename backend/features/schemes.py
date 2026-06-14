"""
features/schemes.py — Scheme Eligibility Engine.

Takes the user's real profile + knowledge graph and asks Gemini (grounded on
live Google Search) which central and state government schemes they currently
qualify for. Returns a ranked list with a match %, why they qualify, the exact
documents needed, and where to apply — all derived from live data, nothing
hardcoded.
"""

import sys
import os
import json
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from features.gemini_grounded import generate_grounded
from utils.logger import logger


def _profile_summary(profile: Dict[str, Any], kg: Dict[str, Any]) -> str:
    """Compact, human-readable summary of who the user is."""
    fields = [
        ("Name", profile.get("name")),
        ("Age group", profile.get("age_group")),
        ("Gender", profile.get("gender")),
        ("State", profile.get("state")),
        ("Occupation", profile.get("occupation")),
        ("Education", profile.get("education_level")),
        ("Has bank account", profile.get("has_bank_account")),
        ("Has smartphone", profile.get("has_smartphone")),
        ("Preferred language", profile.get("preferred_language")),
    ]
    lines = [f"- {k}: {v}" for k, v in fields if v not in (None, "")]
    if kg:
        lines.append(f"- Financial literacy level: {kg.get('literacy_level', 'unknown')}")
    return "\n".join(lines)


def get_eligible_schemes(profile: Dict[str, Any], kg: Dict[str, Any], language: str = "English") -> Dict[str, Any]:
    """
    Return ranked government schemes the user likely qualifies for.

    Output:
      {
        "schemes": [
          {
            "name", "level" (Central|State), "category",
            "match_percent" (0-100), "why_eligible",
            "benefit", "documents" [..], "where_to_apply",
            "official_link"
          }, ...
        ],
        "sources": [{title, uri}],
        "grounded": bool,
      }
    """
    state = profile.get("state", "India")
    occupation = profile.get("occupation", "general citizen")
    summary = _profile_summary(profile, kg)

    prompt = f"""You are a government-scheme eligibility expert for India. Using CURRENT
(2026) official information, identify the government welfare/financial schemes this
specific person most likely qualifies for. Prioritise schemes relevant to a
{occupation} in {state}.

USER PROFILE:
{summary}

Search official sources (myscheme.gov.in, ministry sites, state portals) for current
eligibility rules. Consider central schemes (e.g. PM-KISAN, PMJDY, PM Mudra, PMFBY,
PM-SYM, Atal Pension, PMJJBY, PMSBY, Ayushman Bharat, e-Shram, Stand-Up India, etc.)
AND {state} state-specific schemes.

For EACH scheme the user likely qualifies for, return a JSON object:
{{
  "name": "scheme name (keep official scheme names as-is, do not translate them)",
  "level": "Central" or "State",
  "category": "short category e.g. Income support / Insurance / Credit / Pension / Health",
  "match_percent": integer 0-100 (how well this user fits the eligibility),
  "why_eligible": "one sentence tied to THIS user's profile, written in {language}",
  "benefit": "what the user gets, written in {language}",
  "documents": ["doc1", "doc2", ...],
  "where_to_apply": "exact place / portal / office, written in {language}",
  "official_link": "official URL if known, else empty string"
}}

Rules:
- Only include schemes where match_percent >= 40
- Rank by match_percent descending
- Be realistic; do not invent schemes
- Write the {language} text fields in {language}; keep JSON keys, scheme names, and URLs in English
- Return ONLY a JSON array of 4-8 scheme objects, no prose."""

    result = generate_grounded(prompt, temperature=0.2, want_json=True)

    schemes: List[Dict[str, Any]] = []
    parsed = result.get("json")
    if isinstance(parsed, list):
        for s in parsed:
            if not isinstance(s, dict):
                continue
            try:
                match = int(s.get("match_percent", 0))
            except Exception:
                match = 0
            schemes.append({
                "name": s.get("name", ""),
                "level": s.get("level", ""),
                "category": s.get("category", ""),
                "match_percent": max(0, min(100, match)),
                "why_eligible": s.get("why_eligible", ""),
                "benefit": s.get("benefit", ""),
                "documents": s.get("documents", []) if isinstance(s.get("documents"), list) else [],
                "where_to_apply": s.get("where_to_apply", ""),
                "official_link": s.get("official_link", ""),
            })
        schemes.sort(key=lambda x: x["match_percent"], reverse=True)
    else:
        logger.warning("[schemes] Gemini returned no parseable scheme list")

    return {
        "schemes": schemes,
        "sources": result.get("sources", []),
        "grounded": result.get("grounded", False),
    }
