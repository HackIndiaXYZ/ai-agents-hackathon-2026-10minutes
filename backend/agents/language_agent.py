"""
agents/language_agent.py — Language Detection Agent

Responsibility: Detect the language, script, code-switching status, and
formality tier of the user's raw input. Uses Gemini Flash for speed.

Single responsibility — this agent does NOTHING else. It does not try to
interpret the query semantically.
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
    temperature=0,
)

# ─── System prompt ────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a language detection specialist for Indian languages.
Analyze the input text and return ONLY a JSON object with these fields:
- detected_language: the primary language (Hindi/Bengali/Marathi/Tamil/Telugu/
  Gujarati/Kannada/Malayalam/Punjabi/Urdu/English)
- detected_script: Devanagari/Roman/Bengali/Tamil/Telugu/Gujarati/
  Kannada/Malayalam/Gurmukhi/Arabic
- is_code_switching: boolean, true if mixing languages mid-sentence
- formality_tier: formal/informal/colloquial

Return only valid JSON. No preamble."""


def language_agent(state: AgentState) -> AgentState:
    """
    Detects language metadata from state["raw_input"].
    Writes: detected_language, detected_script, is_code_switching, formality_tier.
    """
    start_time = log_agent_entry("language", state)

    try:
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=state["raw_input"]),
        ]
        response = _llm.invoke(messages)
        raw_content = response.content.strip()

        # Strip markdown fences if Gemini wraps in ```json ... ```
        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
            raw_content = raw_content.strip()

        parsed = json.loads(raw_content)

        state["detected_language"] = parsed.get("detected_language", "English")
        state["detected_script"] = parsed.get("detected_script", "Roman")
        state["is_code_switching"] = bool(parsed.get("is_code_switching", False))
        state["formality_tier"] = parsed.get("formality_tier", "informal")

    except Exception as exc:
        state = log_agent_error("language", exc, state)
        # Safe defaults — graph must continue
        state["detected_language"] = "English"
        state["detected_script"] = "Roman"
        state["is_code_switching"] = False
        state["formality_tier"] = "informal"

    return log_agent_exit("language", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(
        session_id="test-lang-001",
        raw_input="Mujhe PM Kisan yojana ke baare mein batao — I need help with registration",
    )
    result = language_agent(test_state)
    print("detected_language:", result["detected_language"])
    print("detected_script  :", result["detected_script"])
    print("is_code_switching:", result["is_code_switching"])
    print("formality_tier   :", result["formality_tier"])
    print("errors           :", result["errors"])
