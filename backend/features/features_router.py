"""
features/features_router.py — FastAPI router for the financial-inclusion features.

Endpoints:
  POST /features/schemes/eligibility      → Scheme Eligibility Engine
  POST /features/documents/checklist      → Document Checklist Generator
  POST /features/complaints/guide         → Guided Complaint Filing
  GET  /features/fraud-alerts             → Live Fraud Alert Feed (Google News RSS)
  GET  /features/literacy/progress/{id}   → Literacy Progress Dashboard

All scheme/document/complaint data is produced live via Gemini + Google Search
grounding; fraud alerts come from live news RSS; literacy progress is real KG
history from Redis. Nothing is hardcoded.
"""

import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from memory.session_store import (
    load_user_profile,
    load_knowledge_graph,
    get_kg_history,
)
from features import schemes as schemes_mod
from features import documents as documents_mod
from features import complaints as complaints_mod
from features import literacy as literacy_mod
from features import news_feed
from adaptive.logger import log_interaction
from utils.logger import logger

router = APIRouter(prefix="/features", tags=["Features"])


# ─── Request models ──────────────────────────────────────────────────────────

class SchemeRequest(BaseModel):
    profile_id: str
    language: Optional[str] = None


class ChecklistRequest(BaseModel):
    profile_id: Optional[str] = None
    scheme_or_service: str = Field(..., description="What the user wants to apply for")
    state: Optional[str] = None
    language: Optional[str] = None


class ComplaintRequest(BaseModel):
    profile_id: Optional[str] = None
    issue: str = Field(..., description="The user's problem in their own words")
    state: Optional[str] = None
    language: Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _load_profile_or_404(profile_id: str) -> dict:
    profile = load_user_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create a profile first.")
    return profile


def _language_for(profile: dict, override: Optional[str]) -> str:
    return override or profile.get("preferred_language") or "English"


# ─── Scheme Eligibility Engine ───────────────────────────────────────────────

@router.post("/schemes/eligibility")
async def schemes_eligibility(request: SchemeRequest):
    """Return ranked government schemes the user likely qualifies for."""
    profile = _load_profile_or_404(request.profile_id)
    kg = load_knowledge_graph(request.profile_id)
    language = _language_for(profile, request.language)
    logger.info(f"[features] schemes eligibility for {request.profile_id} ({language})")
    try:
        result = schemes_mod.get_eligible_schemes(profile, kg, language=language)
    except Exception as exc:
        logger.error(f"[features] schemes failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Scheme engine error: {exc}")

    if not result["schemes"]:
        raise HTTPException(
            status_code=503,
            detail="Could not generate scheme matches right now. Ensure Vertex AI "
                   "grounding is available and try again.",
        )

    log_interaction(
        kind="scheme",
        user_text=f"Which government schemes do I qualify for as a {profile.get('occupation','')} in {profile.get('state','')}?",
        assistant_summary="; ".join(f"{s['name']} ({s['match_percent']}%): {s.get('why_eligible','')}" for s in result["schemes"][:5]),
        profile=profile,
        language=profile.get("preferred_language", "English"),
        extra={"schemes": [s["name"] for s in result["schemes"]]},
    )
    return {"profile_id": request.profile_id, **result}


# ─── Document Checklist Generator ────────────────────────────────────────────

@router.post("/documents/checklist")
async def documents_checklist(request: ChecklistRequest):
    """Generate a document checklist for a scheme/service application."""
    profile = load_user_profile(request.profile_id) if request.profile_id else {}
    if request.state:
        profile = {**profile, "state": request.state}
    language = _language_for(profile, request.language)
    logger.info(f"[features] checklist for '{request.scheme_or_service}'")
    try:
        result = documents_mod.generate_checklist(
            scheme_or_service=request.scheme_or_service,
            profile=profile,
            language=language,
        )
    except Exception as exc:
        logger.error(f"[features] checklist failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Checklist engine error: {exc}")

    if not result["documents"]:
        raise HTTPException(
            status_code=503,
            detail="Could not generate a checklist right now. Try rephrasing the scheme name.",
        )

    log_interaction(
        kind="document",
        user_text=f"What documents do I need to apply for {request.scheme_or_service}?",
        assistant_summary=f"{result['scheme']}: " + ", ".join(d["name"] for d in result["documents"]),
        profile=profile,
        language=language,
        extra={"scheme": result["scheme"], "where_to_submit": result.get("where_to_submit", "")},
    )
    return result


# ─── Guided Complaint Filing ─────────────────────────────────────────────────

@router.post("/complaints/guide")
async def complaints_guide(request: ComplaintRequest):
    """Produce a step-by-step complaint-filing guide for the user's issue."""
    profile = load_user_profile(request.profile_id) if request.profile_id else {}
    if request.state:
        profile = {**profile, "state": request.state}
    language = _language_for(profile, request.language)
    logger.info(f"[features] complaint guide: {request.issue[:60]}")
    try:
        result = complaints_mod.build_complaint_guide(
            issue=request.issue,
            profile=profile,
            language=language,
        )
    except Exception as exc:
        logger.error(f"[features] complaint guide failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Complaint engine error: {exc}")

    if not result.get("steps"):
        raise HTTPException(
            status_code=503,
            detail="Could not generate a complaint guide right now. Please try again.",
        )

    authority = result.get("authority", {}) or {}
    log_interaction(
        kind="complaint",
        user_text=request.issue,
        assistant_summary=(
            f"{result.get('grievance_type','')} → complain to {authority.get('name','')} "
            f"({authority.get('helpline','')} / {authority.get('portal','')}). "
            + " | ".join(f"{s.get('step')}. {s.get('action','')}" for s in result.get("steps", [])[:5])
        ),
        profile=profile,
        language=language,
        extra={"grievance_type": result.get("grievance_type", ""), "authority": authority.get("name", "")},
    )
    return result


# ─── Fraud Alert Feed ────────────────────────────────────────────────────────

@router.get("/fraud-alerts")
async def fraud_alerts(
    state: Optional[str] = Query(None, description="State to scope alerts to"),
    profile_id: Optional[str] = Query(None, description="Use profile's state if state not given"),
    limit: int = Query(10, ge=1, le=20),
    enrich: bool = Query(True, description="AI-tag scam type + prevention tip"),
    language: Optional[str] = Query(None, description="Language for AI scam tags / tips"),
):
    """Live fraud-news alerts from Google News RSS, scoped to the user's state."""
    resolved_state = state or ""
    if not resolved_state and profile_id:
        profile = load_user_profile(profile_id)
        resolved_state = profile.get("state", "")
    try:
        return news_feed.get_fraud_alerts(
            state=resolved_state, limit=limit, enrich=enrich, language=language or "English",
        )
    except Exception as exc:
        logger.error(f"[features] fraud alerts failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Fraud feed error: {exc}")


# ─── Literacy Progress Dashboard ─────────────────────────────────────────────

@router.get("/literacy/progress/{profile_id}")
async def literacy_progress(profile_id: str, language: Optional[str] = Query(None)):
    """Real KG-based progress timeline + AI-suggested next learning steps."""
    profile = _load_profile_or_404(profile_id)
    kg = load_knowledge_graph(profile_id)
    if not kg:
        raise HTTPException(
            status_code=404,
            detail="No knowledge graph yet. Complete the assessment first.",
        )
    history = get_kg_history(profile_id)
    language = _language_for(profile, language)
    try:
        result = literacy_mod.build_progress(kg, history, language=language)
    except Exception as exc:
        logger.error(f"[features] literacy progress failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Progress engine error: {exc}")
    return {"profile_id": profile_id, "name": profile.get("name", ""), **result}
