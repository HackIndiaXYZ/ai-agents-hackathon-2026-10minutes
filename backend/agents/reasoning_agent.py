"""
agents/reasoning_agent.py — Synthesis / Reasoning Core

Responsibility: Synthesise web search results and RAG knowledge-base results
into a grounded, accurate answer. Never invents facts. Uses Gemini Pro.

Single responsibility — this agent only synthesises evidence into an answer.
It does not format, recommend next steps, or check for fraud.
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
    model_name=settings.PRO_MODEL,
    project=settings.VERTEX_AI_PROJECT_ID,
    location=settings.VERTEX_AI_REGION,
    temperature=0,
)

# ─── System prompt ────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are the reasoning engine for a financial fraud prevention and inclusion assistant
serving rural India. You synthesise multiple evidence sources into one grounded answer.

Evidence priority (highest → lowest):
  1. DATASET EXPERT CASES — top-K similar cases retrieved from the fraud knowledge base.
     These contain detailed expert guidance for identical or very similar situations.
     Treat them as your primary reference. Adapt (don't copy-paste) the expert answers.
  2. WEB SEARCH RESULTS — for current prices, recent policy changes, and time-sensitive facts.
  3. GENERAL KNOWLEDGE — only when datasets and web are silent.

Produce ONLY a JSON reasoning output:
{
  "answer": "direct, empathetic answer in the user's language — prose, no bullet points here",
  "evidence": [{"fact": str, "source": str}],
  "confidence": float 0-1,
  "contradictions_found": boolean,
  "contradiction_resolution": string or null,
  "answer_language": "same as detected_language",
  "flagged_uncertainties": list of strings
}

Hard rules:
- Never invent facts not in evidence
- If dataset cases cover this exact issue, confidence must be >= 0.7
- Never recommend specific banks, investments, or private products
- Never ask user to share OTP, PIN, or password
- Respond in the user's detected language; use empathetic, simple register for low-literacy users"""


# ─── RAG retrieval (BGE-M3 / Qdrant first, old cosine fallback) ───────────────

def _retrieve(query: str, language: str, user_profile: dict) -> list:
    """Try BGE-M3 Qdrant retrieval, fall back to old local cosine similarity."""
    from utils.logger import logger

    # Primary: BGE-M3 + Qdrant hybrid (GPU-accelerated, reranker optional)
    try:
        from rag.bge_retriever import search as bge_search, health_check
        if health_check():
            # bge_search internally falls back to retrieval scores if the
            # reranker can't load (e.g. GPU memory pressure) — never raises.
            results = bge_search(query=query, top_k_candidates=50, top_k_final=5)
            if results:
                return results, "bge_qdrant"
            logger.warning("RAG reasoning: BGE search returned 0 results, trying legacy.")
        else:
            logger.warning("RAG reasoning: Qdrant health check failed, trying legacy.")
    except Exception as bge_err:
        logger.warning(f"RAG reasoning: BGE retrieval failed ({bge_err}), trying legacy.")

    # Fallback: legacy local cosine similarity
    try:
        from rag.retrieval import retrieve as legacy_retrieve
        results = legacy_retrieve(
            query=query,
            detected_language=language,
            user_profile=user_profile,
        )
        return results, "legacy_cosine"
    except Exception as legacy_err:
        logger.warning(f"RAG reasoning: legacy retrieval also failed ({legacy_err}).")
        return [], "none"


def _format_rag_context(results: list, source: str) -> str:
    """Build a structured RAG context block for the reasoning prompt."""
    if not results:
        return "DATASET EXPERT CASES: None retrieved — answer from general knowledge only."

    lines = [f"DATASET EXPERT CASES ({source}, {len(results)} results):"]
    for r in results[:5]:
        # BGE results have richer fields; legacy results have chunk/source_doc
        if "user_query" in r:
            # BGE-M3 result format
            completion = (r.get("enhanced_completion") or "")[:1800]
            actions_list = r.get("actions", [])
            actions_str = "\n    ".join(f"• {a}" for a in actions_list[:5]) if actions_list else ""
            lines.append(
                f"\n[{r['rank']}] Score={r['rerank_score']:.2f} | "
                f"{r['domain_category']} > {r['subdomain']} | lang={r['language_name']}\n"
                f"  Similar Question: {r['user_query']}\n"
                f"  Expert Answer:\n{completion}\n"
                + (f"  Recommended Actions:\n    {actions_str}" if actions_str else "")
            )
        else:
            # Legacy format
            chunk = r.get("chunk", "")[:800]
            lines.append(
                f"\n[{results.index(r)+1}] Relevance={r.get('relevance_score',0):.2f} | "
                f"{r.get('scheme_name','')}\n"
                f"  {chunk}"
            )
    return "\n".join(lines)


def reasoning_agent(state: AgentState) -> AgentState:
    """
    Synthesises dataset expert cases, web search, and general knowledge into a
    grounded, personalised answer. Writes: reasoning_output, confidence_score, rag_results.
    """
    start_time = log_agent_entry("reasoning", state)

    try:
        sub_query_text = (
            state.get("current_sub_query") or {}
        ).get("query") or state.get("raw_input", "")

        language = state.get("detected_language", "English")
        user_profile = state.get("user_profile", {})

        # ── 1. RAG retrieval ─────────────────────────────────────────────────
        rag_results, rag_source = _retrieve(sub_query_text, language, user_profile)
        state["rag_results"] = rag_results

        # ── 2. Web results ────────────────────────────────────────────────────
        web_results = state.get("web_search_results", [])

        # ── 3. Conversation history for follow-up context ─────────────────────
        history = state.get("conversation_history", [])
        history_str = ""
        if len(history) > 1:
            recent = [h for h in history[:-1][-6:]]  # last 3 turns before current
            history_str = "\n".join(
                f"{'User' if h['role']=='user' else 'Assistant'}: {h['content'][:300]}"
                for h in recent
            )

        # ── 4. Knowledge graph summary ────────────────────────────────────────
        kg = state.get("knowledge_graph", {})
        kg_summary = ""
        if kg:
            domains = kg.get("domains", {})
            weak = [d for d, v in domains.items() if isinstance(v, dict) and v.get("score", 100) < 50]
            kg_summary = (
                f"Literacy: {kg.get('literacy_level','unknown')} "
                f"(score {kg.get('overall_score',0):.0f}/100)"
                + (f" | Weak domains: {', '.join(weak[:4])}" if weak else "")
            )

        # ── 5. Build evidence sections ────────────────────────────────────────
        rag_section = _format_rag_context(rag_results, rag_source)

        web_section = ""
        if web_results:
            web_section = "\nWEB SEARCH RESULTS (current / time-sensitive info):\n"
            for i, r in enumerate(web_results[:6], 1):
                web_section += (
                    f"  {i}. {r.get('fact','')}\n"
                    f"     Source: {r.get('source_url','unknown')} | Date: {r.get('date','')}\n"
                )
        else:
            web_section = "\nWEB SEARCH RESULTS: Not fetched for this query."

        current_sub_query = state.get("current_sub_query") or {
            "query": state["raw_input"],
            "type": "general_guidance",
        }

        prompt = f"""QUERY: {current_sub_query.get('query', state['raw_input'])}
QUERY TYPE: {current_sub_query.get('type', 'general_guidance')}

DETECTED LANGUAGE: {language}
USER PROFILE: {json.dumps(user_profile, ensure_ascii=False)}
{f"KNOWLEDGE GRAPH: {kg_summary}" if kg_summary else ""}

{f"CONVERSATION HISTORY (for follow-up context):{chr(10)}{history_str}" if history_str else "CONVERSATION HISTORY: First message."}

{rag_section}

{web_section}

TASK: Synthesise the above evidence into a direct, grounded answer.
- Adapt the most relevant expert case answer for the user's specific situation
- Add any fresh facts from web results (prices, deadlines, policy changes)
- Personalise based on user profile and literacy level
- Answer in {language}

Return JSON reasoning output."""

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = _llm.invoke(messages)
        raw_content = response.content.strip()

        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
            raw_content = raw_content.strip()

        reasoning_output = json.loads(raw_content)
        state["reasoning_output"] = reasoning_output
        state["confidence_score"] = float(reasoning_output.get("confidence", 0.5))

    except Exception as exc:
        state = log_agent_error("reasoning", exc, state)
        state["reasoning_output"] = {
            "answer": "I encountered an error while reasoning. Please try again.",
            "evidence": [],
            "confidence": 0.1,
            "contradictions_found": False,
            "contradiction_resolution": None,
            "answer_language": state.get("detected_language", "English"),
            "flagged_uncertainties": ["reasoning_error"],
        }
        state["confidence_score"] = 0.1

    return log_agent_exit("reasoning", state, start_time)


# ─── Isolated sanity check ────────────────────────────────────────────────────
if __name__ == "__main__":
    from graph.state import default_state

    test_state = default_state(
        session_id="test-reasoning-001",
        raw_input="PM Kisan yojana ke liye kya documents chahiye?",
    )
    test_state["detected_language"] = "Hindi"
    test_state["user_profile"] = {"occupation": "farmer", "state": "UP"}
    test_state["sub_queries"] = [
        {"query": "PM Kisan Samman Nidhi documents required", "type": "document_requirement", "requires_web_search": False, "status": "pending"}
    ]
    test_state["current_sub_query"] = test_state["sub_queries"][0]
    test_state["web_search_results"] = []

    result = reasoning_agent(test_state)
    print("reasoning_output:", json.dumps(result["reasoning_output"], indent=2, ensure_ascii=False))
    print("confidence_score:", result["confidence_score"])
    print("errors:", result["errors"])
