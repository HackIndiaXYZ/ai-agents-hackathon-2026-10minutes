"""
onboarding/question_generator.py — AI-driven adaptive question generator.

Generates the next survey question based on:
  - Which domains still need coverage
  - User answers so far (to avoid redundancy)
  - User profile (language, occupation, state, etc.)

Questions are restricted to the 5 domains:
  1. Banking & Digital Payments
  2. Government Schemes
  3. Fraud & Cyber Safety
  4. Savings & Insurance
  5. Credit & Borrowing

Each question is either MCQ (4 options) or SHORT_TEXT depending on what
yields a better signal for that concept.  Max 12–15 questions total.
"""

import json
import sys
import os
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import settings

# ─── Constants ────────────────────────────────────────────────────────────────

DOMAINS = [
    "Banking & Digital Payments",
    "Government Schemes",
    "Fraud & Cyber Safety",
    "Savings & Insurance",
    "Credit & Borrowing",
]

_SYSTEM_PROMPT = """You are an adaptive financial literacy assessor for rural India.
Your job is to generate ONE survey question at a time to understand a user's financial knowledge.

STRICT RULES:
- Questions MUST belong to exactly one of these 5 domains:
  1. Banking & Digital Payments
  2. Government Schemes
  3. Fraud & Cyber Safety
  4. Savings & Insurance
  5. Credit & Borrowing
- NEVER ask about stocks, trading, mutual funds, derivatives, or any investment products.
- Make questions simple and practical — grounded in everyday Indian financial life.
- Alternate between MCQ and short-text based on what gives better signal.
- Do NOT repeat a concept already covered by previous questions.
- Prioritize domains with less coverage.
- Questions should reveal the user's practical knowledge, not just definitions.

Output ONLY valid JSON in this exact schema (no markdown):
{
  "question_text": "The question to ask",
  "question_type": "MCQ" | "SHORT_TEXT",
  "domain": "one of the 5 domains",
  "concept": "specific financial concept being tested (e.g. UPI, KCC, OTP fraud)",
  "difficulty": "basic" | "intermediate" | "advanced",
  "options": ["A: ...", "B: ...", "C: ...", "D: ..."] // only for MCQ, null for SHORT_TEXT
}"""

_llm = ChatVertexAI(
    model_name=settings.FLASH_MODEL,
    project=settings.VERTEX_AI_PROJECT_ID,
    location=settings.VERTEX_AI_REGION,
    temperature=0.4,
)


def _get_field(answer: Dict, field: str) -> str:
    """Read a field from either flat {domain, concept} or nested {question: {domain, concept}} format."""
    val = answer.get(field)
    if not val:
        val = (answer.get("question") or {}).get(field, "")
    return val or ""


def _domain_coverage(answers: List[Dict]) -> Dict[str, int]:
    """Count how many questions each domain has received so far."""
    coverage = {d: 0 for d in DOMAINS}
    for a in answers:
        domain = _get_field(a, "domain")
        if domain in coverage:
            coverage[domain] += 1
    return coverage


def _pick_required_domain(coverage: Dict[str, int], question_number: int) -> Optional[str]:
    """
    Return a domain the model MUST use, or None if free choice is fine.

    Strategy:
    - Target ~3 questions per domain across 15 questions.
    - Any domain with 0 questions is always required first.
    - Any domain that is 2+ questions behind the most-covered domain is required.
    - After question 10 (all domains covered ≥1), allow free choice.
    """
    # Always force uncovered domains
    uncovered = [d for d, c in coverage.items() if c == 0]
    if uncovered:
        return uncovered[0]

    # After first pass of all domains, enforce balance up to question 10
    if question_number <= 10:
        min_count = min(coverage.values())
        max_count = max(coverage.values())
        if max_count - min_count >= 2:
            # Force the most under-represented domain
            return min(coverage, key=lambda d: coverage[d])

    return None  # free choice


def generate_next_question(
    answers: List[Dict[str, Any]],
    user_profile: Dict[str, Any],
    question_number: int,
) -> Optional[Dict[str, Any]]:
    """
    Generate the next adaptive question.

    Args:
        answers:         List of previous {question, answer, domain, concept} dicts.
        user_profile:    User metadata (name, occupation, state, language, etc.)
        question_number: 1-based index of the question being generated.

    Returns:
        Question dict with keys: question_text, question_type, domain,
        concept, difficulty, options (or None if we're done).
    """
    if question_number > settings.ONBOARDING_MAX_QUESTIONS:
        return None

    coverage = _domain_coverage(answers)
    required_domain = _pick_required_domain(coverage, question_number)

    covered_domains_summary = ", ".join(f"{d}: {c}" for d, c in coverage.items())

    # Build a detailed history so the model sees exactly what was already asked
    asked_questions_block = ""
    if answers:
        lines = []
        for i, a in enumerate(answers, 1):
            domain   = _get_field(a, "domain")
            concept  = _get_field(a, "concept")
            q_text   = _get_field(a, "question_text")
            lines.append(f"  Q{i} [{domain} | {concept}]: {q_text}")
        asked_questions_block = "Questions already asked (DO NOT repeat or rephrase any of these):\n" + "\n".join(lines)
    else:
        asked_questions_block = "No questions asked yet."

    lang = user_profile.get("preferred_language", "English")
    occupation = user_profile.get("occupation", "general user")
    state = user_profile.get("state", "India")

    if required_domain:
        domain_instruction = (
            f'⚠️ MANDATORY: You MUST generate a question for the domain "{required_domain}". '
            f"Do NOT use any other domain for this question."
        )
    else:
        domain_instruction = (
            "Choose the domain that gives the most balanced coverage across all 5 domains."
        )

    prompt = f"""Generate question #{question_number} for the financial literacy assessment.

User context:
- Name: {user_profile.get("name", "User")}
- Occupation: {occupation}
- State/Region: {state}
- Preferred language for responses: {lang}
- Age group: {user_profile.get("age_group", "adult")}

Domain coverage so far: {covered_domains_summary}

{asked_questions_block}

{domain_instruction}

Additional rules:
- Your question MUST test a completely different concept and scenario from all questions listed above
- If the domain has prior questions, pick a sub-topic not yet tested (e.g. if UPI was tested, test NEFT/IMPS/ATM/net banking/Aadhaar-linked payments instead)
- Mix difficulty: basic for early questions, intermediate/advanced for later ones
- Keep the question practical and grounded in everyday Indian financial life

The question must be in simple, clear English.
Generate the next question JSON."""

    messages = [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=prompt)]

    try:
        response = _llm.invoke(messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        question = json.loads(raw)
        question["question_number"] = question_number

        # Safety net: if model ignored the mandatory domain, override it
        if required_domain and question.get("domain") != required_domain:
            question["domain"] = required_domain

        return question
    except Exception as exc:
        domain = required_domain or DOMAINS[question_number % 5]
        return {
            "question_number": question_number,
            "question_text": f"Have you ever used a {domain.lower().split()[0]}-related service?",
            "question_type": "MCQ",
            "domain": domain,
            "concept": domain.lower(),
            "difficulty": "basic",
            "options": ["A: Yes, regularly", "B: Yes, occasionally", "C: Heard of it but haven't used", "D: No, never heard of it"],
            "_error": str(exc),
        }


def is_survey_complete(answers: List[Dict], question_number: int) -> bool:
    """
    Complete when all 5 domains have ≥1 answer AND total >= MIN_QUESTIONS,
    OR total >= MAX_QUESTIONS.
    """
    if question_number > settings.ONBOARDING_MAX_QUESTIONS:
        return True
    if question_number <= settings.ONBOARDING_MIN_QUESTIONS:
        return False
    coverage = _domain_coverage(answers)
    return all(c >= 1 for c in coverage.values())
