"""
agents/formatter_agent.py — Final Response Assembler

Responsibility: Take all upstream structured outputs and assemble a single,
user-facing response in the correct language, register, and literacy level.
Also produces a voice-optimised version. Uses Gemini Flash.

Single responsibility — this agent only formats. It never modifies logic.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from graph.state import AgentState
from utils.logger import log_agent_entry, log_agent_exit, log_agent_error

# ─── Model ────────────────────────────────────────────────────────────────────
_llm = ChatVertexAI(
    model_name=settings.FLASH_MODEL,
    project=settings.VERTEX_AI_PROJECT_ID,
    location=settings.VERTEX_AI_REGION,
    temperature=0.2,
)

# ─── System prompt template ───────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """You are a response formatter for a multilingual rural Indian financial
assistant. Your job is to produce ONLY the conversational answer text — do NOT
include next steps or related schemes in the text_response; those are returned
as separate structured fields.

Rules:
- text_response: a clear, direct answer in {detected_language}, using {formality_tier} register.
  - literacy_level=low → short sentences, no jargon, at most 3 short paragraphs
  - literacy_level=high → may use technical terms, paragraph format fine
  - Include a one-sentence citation line only if web sources are present (e.g. "Source: ...")
  - If confidence < 0.8, add one sentence: "Note: confidence is {confidence_pct}%"
  - Do NOT mention "next steps" or "related schemes" — those render separately in the UI
- voice_response: same answer, natural spoken sentences, no markdown, under 120 words
- next_steps: copy the next_steps array from recommendations as-is (or empty list)
- related_schemes: copy the related_schemes array from recommendations as-is (or empty list)

Return ONLY JSON:
{{
  "text_response": str,
  "voice_response": str,
  "next_steps": [...],
  "related_schemes": [...]
}}"""


def formatter_agent(state: AgentState) -> AgentState:
    """
    Assembles the final user-facing response from all upstream outputs.
    Produces separate text_response, next_steps, and related_schemes.
    Writes: final_response, response_for_voice, next_steps, related_schemes.
    """
    start_time = log_agent_entry("formatter", state)

    try:
        # Short-circuit: clarification flow
        if state.get("needs_clarification") and state.get("clarification_question"):
            state["final_response"] = state["clarification_question"]
            state["response_for_voice"] = state["clarification_question"]
            return log_agent_exit("formatter", state, start_time, extra={"mode": "clarification_passthrough"})

        detected_language = state.get("detected_language", "English")
        formality_tier = state.get("formality_tier", "informal")
        literacy_level = state.get("user_profile", {}).get("financial_literacy_level", "low")
        confidence_score = state.get("confidence_score", 0.5)
        confidence_pct = int(confidence_score * 100)

        reasoning = state.get("reasoning_output") or {}
        recommendations = state.get("recommendations") or {}
        web_results = state.get("web_search_results", [])

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            detected_language=detected_language,
            formality_tier=formality_tier,
            confidence_pct=confidence_pct,
        )

        prompt = f"""REASONING ANSWER:
{reasoning.get("answer", "")}

EVIDENCE / SOURCES:
{json.dumps([{"fact": e.get("fact",""), "source": e.get("source","")} for e in reasoning.get("evidence",[])[:4]], ensure_ascii=False)}

WEB SEARCH SOURCES:
{json.dumps([{"title": r.get("title",""), "url": r.get("source_url","")} for r in web_results[:3]], indent=2)}

RECOMMENDATIONS (to pass through as structured data):
{json.dumps(recommendations, indent=2, ensure_ascii=False)}

USER CONTEXT:
- Language: {detected_language}
- Formality: {formality_tier}
- Literacy level: {literacy_level}
- Confidence: {confidence_score:.2f} ({confidence_pct}%)
- Fraud flags: {state.get("fraud_flags", [])}
- Safety blocks applied: {state.get("safety_blocks_applied", False)}

Return JSON with text_response, voice_response, next_steps, related_schemes."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]
        response = _llm.invoke(messages)
        raw_content = response.content.strip()

        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
            raw_content = raw_content.strip()

        formatted = json.loads(raw_content)

        state["final_response"] = formatted.get("text_response", reasoning.get("answer", ""))
        state["response_for_voice"] = formatted.get("voice_response")
        # Write structured panels to dedicated state keys
        state["next_steps"] = formatted.get("next_steps") or recommendations.get("next_steps", [])
        state["related_schemes"] = formatted.get("related_schemes") or recommendations.get("related_schemes", [])

    except Exception as exc:
        state = log_agent_error("formatter", exc, state)
        reasoning = state.get("reasoning_output") or {}
        recommendations = state.get("recommendations") or {}
        state["final_response"] = reasoning.get("answer", "An error occurred while formatting the response.")
        state["response_for_voice"] = state["final_response"]
        state["next_steps"] = recommendations.get("next_steps", [])
        state["related_schemes"] = recommendations.get("related_schemes", [])

    return log_agent_exit("formatter", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(session_id="test-format-001", raw_input="PM Kisan documents?")
    test_state["detected_language"] = "Hindi"
    test_state["formality_tier"] = "colloquial"
    test_state["user_profile"] = {"financial_literacy_level": "low"}
    test_state["confidence_score"] = 0.75
    test_state["reasoning_output"] = {
        "answer": "PM Kisan ke liye Aadhaar, bank passbook, aur zameen ke kagaz chahiye.",
        "evidence": [],
        "confidence": 0.75,
    }
    test_state["recommendations"] = {
        "next_steps": [
            {"step_number": 1, "action": "Aadhaar card lekar aayein", "where": "Ghar pe", "estimated_time": "5 minute", "required_documents": ["Aadhaar"]}
        ],
        "related_schemes": [],
        "estimated_total_time": "1-2 din",
    }

    result = formatter_agent(test_state)
    print("final_response:", result["final_response"][:300])
    print("response_for_voice:", result["response_for_voice"])
    print("errors:", result["errors"])
