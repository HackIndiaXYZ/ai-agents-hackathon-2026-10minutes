"""
onboarding/knowledge_graph_builder.py — Build and update the user knowledge graph.

The knowledge graph (KG) represents how well a user understands each of the
5 financial domains and their sub-concepts.  It is:

  1. Bootstrapped after the onboarding survey (build_from_survey)
  2. Updated incrementally after each chat interaction (update_from_interaction)

Stored in Redis under key: kg:{profile_id}  (same TTL as profile: 7 days)

Structure:
{
  "profile_id": str,
  "domains": {
    "Banking & Digital Payments": {
      "score": float,          // 0.0–1.0 knowledge confidence
      "level": str,            // "beginner" | "intermediate" | "advanced"
      "questions_asked": int,
      "concepts": {
        "UPI": {"known": bool, "confidence": float, "last_seen": str}
        ...
      }
    },
    ...
  },
  "overall_score": float,
  "literacy_level": str,        // "beginner" | "intermediate" | "advanced"
  "survey_answers": [...],      // raw survey answers
  "chat_interactions": int,
  "created_at": str,
  "last_updated": str
}
"""

import json
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import settings
from onboarding.question_generator import DOMAINS


_llm = ChatVertexAI(
    model_name=settings.FLASH_MODEL,
    project=settings.VERTEX_AI_PROJECT_ID,
    location=settings.VERTEX_AI_REGION,
    temperature=0,
)

_EVAL_SYSTEM = """You are evaluating a user's financial literacy survey answer.
Given a question (with domain, concept, difficulty) and the user's answer,
assess their knowledge level for that concept.

Output ONLY valid JSON (no markdown):
{
  "known": true | false,
  "confidence": float between 0.0 and 1.0,
  "notes": "brief reason"
}

For MCQ: check if the selected option is correct or shows understanding.
For SHORT_TEXT: assess whether the answer shows practical understanding.
Be generous — partial knowledge should still count as "known" with lower confidence."""


def _evaluate_answer(question: Dict[str, Any], answer: str) -> Dict[str, Any]:
    """Use Gemini to evaluate a single survey answer."""
    prompt = f"""Question: {question.get("question_text")}
Domain: {question.get("domain")}
Concept: {question.get("concept")}
Difficulty: {question.get("difficulty")}
Question type: {question.get("question_type")}
Options (if MCQ): {question.get("options")}

User's answer: {answer}

Evaluate the answer."""

    try:
        response = _llm.invoke([
            SystemMessage(content=_EVAL_SYSTEM),
            HumanMessage(content=prompt),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        # Fallback: assume partial knowledge
        return {"known": True, "confidence": 0.4, "notes": "evaluation failed"}


def _score_to_level(score: float) -> str:
    if score >= 0.70:
        return "advanced"
    if score >= 0.40:
        return "intermediate"
    return "beginner"


def build_from_survey(
    profile_id: str,
    answers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a knowledge graph from completed survey answers.

    Args:
        profile_id: Unique user ID.
        answers:    List of {question: {...}, answer: str} dicts.

    Returns:
        Full knowledge graph dict.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Initialise domains
    domains: Dict[str, Any] = {
        d: {
            "score": 0.0,
            "level": "beginner",
            "questions_asked": 0,
            "concepts": {},
        }
        for d in DOMAINS
    }

    # Evaluate each answer
    for entry in answers:
        question = entry.get("question", {})
        answer = entry.get("answer", "")
        domain = question.get("domain", "")
        concept = question.get("concept", "")

        if domain not in domains:
            continue

        evaluation = _evaluate_answer(question, answer)

        domains[domain]["questions_asked"] += 1
        domains[domain]["concepts"][concept] = {
            "known": evaluation.get("known", False),
            "confidence": evaluation.get("confidence", 0.3),
            "last_seen": now,
        }

    # Compute domain scores
    for domain, data in domains.items():
        concepts = data["concepts"]
        if not concepts:
            data["score"] = 0.0
        else:
            data["score"] = round(
                sum(c["confidence"] for c in concepts.values()) / len(concepts), 3
            )
        data["level"] = _score_to_level(data["score"])

    # Compute overall score
    scored_domains = [d["score"] for d in domains.values() if d["questions_asked"] > 0]
    overall_score = round(sum(scored_domains) / max(len(scored_domains), 1), 3)

    kg = {
        "profile_id": profile_id,
        "domains": domains,
        "overall_score": overall_score,
        "literacy_level": _score_to_level(overall_score),
        "survey_answers": answers,
        "chat_interactions": 0,
        "created_at": now,
        "last_updated": now,
    }
    return kg


def update_from_interaction(
    kg: Dict[str, Any],
    domain: str,
    concept: str,
    understood: bool,
    confidence_delta: float = 0.05,
) -> Dict[str, Any]:
    """
    Incrementally update the KG based on a chat interaction signal.

    Args:
        kg:               Existing knowledge graph.
        domain:           Financial domain of the topic discussed.
        concept:          Specific concept (e.g. "UPI", "PM Kisan").
        understood:       Did the user demonstrate understanding?
        confidence_delta: How much to adjust confidence.

    Returns:
        Updated knowledge graph.
    """
    now = datetime.now(timezone.utc).isoformat()

    if domain not in kg["domains"]:
        return kg

    concepts = kg["domains"][domain]["concepts"]
    existing = concepts.get(concept, {"known": False, "confidence": 0.3, "last_seen": now})

    new_conf = existing["confidence"]
    if understood:
        new_conf = min(1.0, new_conf + confidence_delta)
    else:
        new_conf = max(0.0, new_conf - confidence_delta * 0.5)

    concepts[concept] = {
        "known": new_conf >= 0.5,
        "confidence": round(new_conf, 3),
        "last_seen": now,
    }

    # Recompute domain score
    kg["domains"][domain]["score"] = round(
        sum(c["confidence"] for c in concepts.values()) / len(concepts), 3
    )
    kg["domains"][domain]["level"] = _score_to_level(kg["domains"][domain]["score"])

    # Recompute overall
    scored = [d["score"] for d in kg["domains"].values() if d["questions_asked"] > 0]
    kg["overall_score"] = round(sum(scored) / max(len(scored), 1), 3)
    kg["literacy_level"] = _score_to_level(kg["overall_score"])
    kg["chat_interactions"] = kg.get("chat_interactions", 0) + 1
    kg["last_updated"] = now

    return kg


def kg_to_user_profile_fields(kg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a compact summary from the KG to merge into user_profile in AgentState.
    This lets the formatter and reasoning agents adapt their tone and depth.
    """
    return {
        "literacy_level": kg.get("literacy_level", "beginner"),
        "overall_knowledge_score": kg.get("overall_score", 0.0),
        "domain_levels": {
            d: data["level"] for d, data in kg.get("domains", {}).items()
        },
        "known_concepts": [
            c
            for d in kg.get("domains", {}).values()
            for c, info in d.get("concepts", {}).items()
            if info.get("known")
        ],
    }
