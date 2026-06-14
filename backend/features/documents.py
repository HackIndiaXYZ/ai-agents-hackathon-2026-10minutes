"""
features/documents.py — Document Checklist Generator.

Given a scheme/service the user wants to apply for (e.g. "Kisan Credit Card")
plus their state and profile, Gemini (grounded on live Google Search) returns
the exact, current document checklist — what each document is, why it's needed,
where to get it, and whether this user probably already has it.

Real, current data via grounding. Nothing hardcoded.
"""

import sys
import os
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from features.gemini_grounded import generate_grounded
from utils.logger import logger


def generate_checklist(
    scheme_or_service: str,
    profile: Dict[str, Any],
    language: str = "English",
) -> Dict[str, Any]:
    """
    Build a document checklist for applying to a scheme/service.

    Returns:
      {
        "scheme": str,
        "summary": str,
        "documents": [
          {"name", "why_needed", "where_to_get", "user_likely_has" (bool),
           "mandatory" (bool)}
        ],
        "where_to_submit": str,
        "estimated_time": str,
        "tips": [str, ...],
        "sources": [{title, uri}],
        "grounded": bool,
      }
    """
    state = profile.get("state", "India")
    occupation = profile.get("occupation", "")
    known = {
        "has_bank_account": profile.get("has_bank_account"),
        "has_smartphone": profile.get("has_smartphone"),
    }

    prompt = f"""You are an expert on Indian government application procedures. A user wants to
apply for: "{scheme_or_service}".

USER CONTEXT:
- State: {state}
- Occupation: {occupation}
- Known facts: {known}

Using CURRENT (2026) official requirements for {state}, produce the exact document
checklist. Search official sources for the latest list.

Return ONLY this JSON object:
{{
  "scheme": "the scheme/service name (cleaned up)",
  "summary": "one-line what this application is for, in {language}",
  "documents": [
    {{
      "name": "document name",
      "why_needed": "short reason, in {language}",
      "where_to_get": "where/how to obtain it if the user lacks it, in {language}",
      "mandatory": true or false,
      "user_likely_has": true or false (infer from the known facts above; Aadhaar -> usually true)
    }}
  ],
  "where_to_submit": "exact office / portal / CSC, in {language}",
  "estimated_time": "realistic time to complete the application",
  "tips": ["1-3 short practical tips in {language}"]
}}

Rules:
- List documents in the order the user should gather them
- Be specific to {state} where it matters
- Do not invent documents; reflect real current requirements
- Respond with the {language} text fields in {language}, but keep JSON keys in English."""

    result = generate_grounded(prompt, temperature=0.2, want_json=True)
    parsed = result.get("json") or {}

    if not isinstance(parsed, dict):
        parsed = {}

    documents: List[Dict[str, Any]] = []
    for d in parsed.get("documents", []) if isinstance(parsed.get("documents"), list) else []:
        if not isinstance(d, dict):
            continue
        documents.append({
            "name": d.get("name", ""),
            "why_needed": d.get("why_needed", ""),
            "where_to_get": d.get("where_to_get", ""),
            "mandatory": bool(d.get("mandatory", True)),
            "user_likely_has": bool(d.get("user_likely_has", False)),
        })

    if not documents:
        logger.warning(f"[documents] no checklist parsed for '{scheme_or_service}'")

    return {
        "scheme": parsed.get("scheme", scheme_or_service),
        "summary": parsed.get("summary", ""),
        "documents": documents,
        "where_to_submit": parsed.get("where_to_submit", ""),
        "estimated_time": parsed.get("estimated_time", ""),
        "tips": parsed.get("tips", []) if isinstance(parsed.get("tips"), list) else [],
        "sources": result.get("sources", []),
        "grounded": result.get("grounded", False),
    }
