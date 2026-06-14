"""
agents/fraud_safety_agent.py — Fraud Detection and Safety Filter

Responsibility: Two-layer safety check on the assembled response:
  Layer 1 — Deterministic regex rules (no LLM, guaranteed fast)
  Layer 2 — Gemini Flash classifier for nuanced soft checks

Single responsibility — this agent only filters responses for safety.
It never generates content. It either passes through, adds disclaimers,
or hard-blocks with a replacement template.
"""

import re
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from graph.state import AgentState
from utils.logger import log_agent_entry, log_agent_exit, log_agent_error

# ─── Model (only for Layer 2) ─────────────────────────────────────────────────
_llm = ChatVertexAI(
    model_name=settings.FLASH_MODEL,
    project=settings.VERTEX_AI_PROJECT_ID,
    location=settings.VERTEX_AI_REGION,
    temperature=0,
)

# ─── Standard disclaimer template ────────────────────────────────────────────
DISCLAIMER_TEMPLATE = """
[Important: This information is for guidance only. Always verify with
official government portals or your nearest Common Service Centre (CSC).
Never share your OTP, PIN, or banking password with anyone.]
"""

HARD_BLOCK_TEMPLATE = """
[This response has been blocked for safety reasons. The system detected content
that could be harmful or misleading.

Please note:
- Never share your OTP, PIN, or banking password with anyone.
- Government schemes are applied through official portals or CSC centres only.
- No genuine scheme requires payment to agents or middlemen.

For help, visit: pmkisan.gov.in | pfms.nic.in | your nearest Common Service Centre]
"""

# ─── Layer 1: Deterministic fraud patterns ────────────────────────────────────
# (pure Python regex, no LLM — always runs first, always fast)
FRAUD_PATTERNS = [
    (r"\bOTP\b.*shar", "otp_sharing_risk"),
    (r"\bPIN\b.*bata", "pin_sharing_risk"),
    (r"password.*do", "credential_sharing_risk"),
    (r"specific bank.*recommend", "bank_recommendation"),
    (r"invest.*guaranteed.*return", "investment_fraud"),
    (r"guaranteed.*profit", "guaranteed_profit_claim"),
    (r"100%.*return", "unrealistic_return_claim"),
    (r"send.*money.*agent", "agent_payment_fraud"),
]

# ─── Layer 2: LLM system prompt ───────────────────────────────────────────────
_SAFETY_SYSTEM_PROMPT = """You are a safety classifier for a financial inclusion assistant.

Classify this response as SAFE, SOFT_WARNING, or HARD_BLOCK.

HARD_BLOCK if:
- Recommends a specific private financial product or bank
- Asks or implies user should share credentials (OTP, PIN, password)
- Guarantees specific financial returns or profits
- Promotes unofficial agents or middlemen for government scheme registration

SOFT_WARNING if:
- Directionally advisory without being explicitly harmful
- Mentions third-party agents in passing
- Contains information that could be misinterpreted

SAFE otherwise.

Return JSON: {"classification": str, "reason": str, "suggested_disclaimer": str or null}"""


def _layer1_check(text: str) -> list[str]:
    """
    Apply deterministic regex patterns. Returns list of triggered flag names.
    Fast, no LLM, runs unconditionally.
    """
    flags = []
    for pattern, flag_name in FRAUD_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            flags.append(flag_name)
    return flags


def _layer2_check(text: str) -> dict:
    """
    LLM-based soft classifier. Returns classification dict.
    Only called if Layer 1 found no hard blocks.
    """
    messages = [
        SystemMessage(content=_SAFETY_SYSTEM_PROMPT),
        HumanMessage(content=f"Response to classify:\n\n{text}"),
    ]
    response = _llm.invoke(messages)
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


def fraud_safety_agent(state: AgentState) -> AgentState:
    """
    Two-layer safety filter. Writes: fraud_flags, safety_blocks_applied,
    original_response_before_safety, final_response (potentially modified).
    """
    start_time = log_agent_entry("fraud_safety", state)

    try:
        # Use the assembled response if available, else the reasoning answer
        reasoning = state.get("reasoning_output", {})
        response_text = reasoning.get("answer", state.get("final_response", ""))

        fraud_flags: list[str] = []
        safety_blocks_applied = False
        original_response_before_safety = None

        # ── Layer 1: Deterministic check ──────────────────────────────────────
        layer1_flags = _layer1_check(response_text)
        if layer1_flags:
            fraud_flags.extend(layer1_flags)
            original_response_before_safety = response_text
            response_text = HARD_BLOCK_TEMPLATE
            safety_blocks_applied = True

        # ── Layer 2: LLM soft check (only if Layer 1 didn't hard-block) ───────
        if not safety_blocks_applied:
            try:
                classification = _layer2_check(response_text)
                level = classification.get("classification", "SAFE")
                disclaimer = classification.get("suggested_disclaimer")

                if level == "HARD_BLOCK":
                    fraud_flags.append("llm_hard_block")
                    fraud_flags.append(classification.get("reason", "")[:80])
                    original_response_before_safety = response_text
                    response_text = HARD_BLOCK_TEMPLATE
                    safety_blocks_applied = True

                elif level == "SOFT_WARNING":
                    fraud_flags.append("soft_warning")
                    if disclaimer:
                        response_text += f"\n\n{disclaimer}"
                    else:
                        response_text += DISCLAIMER_TEMPLATE

            except Exception as llm_exc:
                # Layer 2 failure is non-fatal — append generic disclaimer and continue
                state = log_agent_error("fraud_safety_layer2", llm_exc, state)
                response_text += DISCLAIMER_TEMPLATE

        # Write back to reasoning_output for the formatter to pick up
        if state.get("reasoning_output"):
            state["reasoning_output"]["answer"] = response_text

        state["fraud_flags"] = fraud_flags
        state["safety_blocks_applied"] = safety_blocks_applied
        state["original_response_before_safety"] = original_response_before_safety

    except Exception as exc:
        state = log_agent_error("fraud_safety", exc, state)
        # Non-blocking: append disclaimer as a safe fallback
        if state.get("reasoning_output"):
            state["reasoning_output"]["answer"] = (
                state["reasoning_output"].get("answer", "") + DISCLAIMER_TEMPLATE
            )

    return log_agent_exit(
        "fraud_safety",
        state,
        start_time,
        extra={
            "fraud_flags": state.get("fraud_flags", []),
            "safety_blocks_applied": state.get("safety_blocks_applied", False),
        },
    )


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(session_id="test-fraud-001", raw_input="test")
    test_state["reasoning_output"] = {
        "answer": "Share your OTP with our agent to complete registration.",
        "evidence": [],
        "confidence": 0.9,
    }

    result = fraud_safety_agent(test_state)
    print("fraud_flags:", result["fraud_flags"])
    print("safety_blocks_applied:", result["safety_blocks_applied"])
    print("original_response_before_safety:", result["original_response_before_safety"][:60])
    print("modified answer:", result["reasoning_output"]["answer"][:120])
    print("errors:", result["errors"])
