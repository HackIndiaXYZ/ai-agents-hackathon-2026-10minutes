"""
features/complaints.py — Guided Complaint Filing.

The user describes a problem ("my PM Kisan money didn't arrive", "money was
debited by a fraudster", "bank refused to open my account"). This module:

  1. Pulls relevant expert cases from the fraud-QA RAG knowledge base (if indexed)
  2. Asks Gemini (grounded on live Google Search) to identify the correct
     grievance authority, real portal/helpline, and the exact filing steps

Real portals, helplines and procedures come from live grounding + the curated
RAG dataset. Nothing hardcoded.
"""

import sys
import os
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from features.gemini_grounded import generate_grounded
from utils.logger import logger


def _rag_context(issue: str) -> List[Dict[str, Any]]:
    """Best-effort: pull similar fraud/grievance cases from the RAG store."""
    try:
        from rag.bge_retriever import search as bge_search, health_check
        if not health_check():
            return []
        return bge_search(query=issue, top_k_candidates=30, top_k_final=3) or []
    except Exception:
        return []


def build_complaint_guide(
    issue: str,
    profile: Dict[str, Any],
    language: str = "English",
) -> Dict[str, Any]:
    """
    Produce a step-by-step complaint-filing guide for the user's issue.

    Returns:
      {
        "issue_understood": str,
        "grievance_type": str,
        "authority": {"name", "portal", "helpline", "email", "where"},
        "steps": [{"step", "action", "detail"}],
        "documents_to_keep_ready": [str],
        "escalation": [{"level", "authority", "how"}],
        "expected_timeline": str,
        "similar_cases": [{user_query, actions}],
        "sources": [{title, uri}],
        "grounded": bool,
      }
    """
    state = profile.get("state", "India")

    rag_hits = _rag_context(issue)
    rag_block = ""
    if rag_hits:
        blocks = []
        for r in rag_hits:
            actions = r.get("actions", [])
            blocks.append(
                f"- Case ({r.get('domain_category','')}/{r.get('subdomain','')}): "
                f"{r.get('user_query','')[:200]}\n  Expert actions: "
                + "; ".join(actions[:4])
            )
        rag_block = "RELEVANT EXPERT CASES FROM KNOWLEDGE BASE:\n" + "\n".join(blocks)

    prompt = f"""You are a citizen-grievance guide for India. A user from {state} has this problem:

"{issue}"

{rag_block}

Using CURRENT (2026) official grievance channels, tell the user exactly how and
where to file a complaint. Search official sources for the correct authority,
real portal URLs and helpline numbers (e.g. cybercrime.gov.in / 1930 for cyber
fraud, pgportal.gov.in for central grievances, RBI CMS / Banking Ombudsman
cms.rbi.org.in for bank issues, scheme-specific helplines, state portals).

Return ONLY this JSON object:
{{
  "issue_understood": "one-line restatement in {language}",
  "grievance_type": "short category",
  "authority": {{
    "name": "the correct body to complain to",
    "portal": "official complaint URL (empty if none)",
    "helpline": "phone number (empty if none)",
    "email": "official email (empty if none)",
    "where": "physical office to visit if relevant, in {language}"
  }},
  "steps": [
    {{"step": 1, "action": "short action in {language}", "detail": "specifics in {language}"}}
  ],
  "documents_to_keep_ready": ["doc/info to have ready, in {language}"],
  "escalation": [
    {{"level": "if not resolved", "authority": "next authority", "how": "how to escalate, in {language}"}}
  ],
  "expected_timeline": "realistic resolution time"
}}

Rules:
- Use ONLY real, current portals/helplines — never invent a URL or number
- Order steps so the user can follow them top to bottom
- If it is financial fraud, the first step must be calling 1930 / cybercrime.gov.in within the golden hour
- Keep {language} text fields in {language}; keep JSON keys in English."""

    result = generate_grounded(prompt, temperature=0.15, want_json=True)
    parsed = result.get("json") or {}
    if not isinstance(parsed, dict):
        parsed = {}

    if not parsed:
        logger.warning(f"[complaints] no guide parsed for issue: {issue[:80]}")

    return {
        "issue_understood": parsed.get("issue_understood", issue),
        "grievance_type": parsed.get("grievance_type", ""),
        "authority": parsed.get("authority", {}) if isinstance(parsed.get("authority"), dict) else {},
        "steps": parsed.get("steps", []) if isinstance(parsed.get("steps"), list) else [],
        "documents_to_keep_ready": parsed.get("documents_to_keep_ready", []) if isinstance(parsed.get("documents_to_keep_ready"), list) else [],
        "escalation": parsed.get("escalation", []) if isinstance(parsed.get("escalation"), list) else [],
        "expected_timeline": parsed.get("expected_timeline", ""),
        "similar_cases": [
            {"user_query": r.get("user_query", ""), "actions": r.get("actions", [])}
            for r in rag_hits
        ],
        "sources": result.get("sources", []),
        "grounded": result.get("grounded", False),
    }
