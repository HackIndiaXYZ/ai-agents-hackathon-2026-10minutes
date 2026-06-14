"""
rag/rag_router.py — FastAPI router for the BGE-M3 / Qdrant RAG pipeline.

Endpoints:
  POST /rag/similar   → hybrid search + BGE-Reranker + Gemini 2.5 Flash synthesis
  GET  /rag/health    → Qdrant + collection connectivity
"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from rag.bge_retriever import search as rag_search, health_check as qdrant_health
from utils.logger import logger

router = APIRouter(prefix="/rag", tags=["RAG"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SimilarQuestion(BaseModel):
    rank: int
    user_query: str
    domain_category: str
    subdomain: str
    language_code: str
    language_name: str
    actions: List[str]
    source: str
    userprofile: str
    learning_outcome: str
    rerank_score: float
    retrieval_score: float


class RAGSearchResponse(BaseModel):
    query: str
    query_language: str
    similar_questions: List[SimilarQuestion]
    gemini_answer: str
    candidates_retrieved: int


# ─── Language detection ───────────────────────────────────────────────────────

_LANG_NAMES = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "mr": "Marathi",
    "ta": "Tamil",   "te": "Telugu", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu",
}


def _detect_language(query: str) -> str:
    try:
        from langdetect import detect
        return _LANG_NAMES.get(detect(query[:400]), "English")
    except Exception:
        return "English"


# ─── Gemini synthesis ─────────────────────────────────────────────────────────

def _gemini_synthesize(query: str, results: list, query_language: str) -> str:
    """
    Use Gemini 2.5 Flash (Vertex AI) to synthesize an answer from the top results.

    The enhanced_prompt and enhanced_completion from each result are used as
    high-quality reference material. The synthesis is always delivered in the
    detected query language.
    """
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(
            project=settings.VERTEX_AI_PROJECT_ID,
            location=settings.VERTEX_AI_REGION,
        )

        # Use top 3 results as context (enough signal without over-stuffing the prompt)
        context_blocks = []
        for r in results[:3]:
            completion = r.get("enhanced_completion", "")[:1500]
            context_blocks.append(
                f"--- Similar Case {r['rank']} "
                f"({r['domain_category']} > {r['subdomain']}) ---\n"
                f"Question: {r['user_query']}\n"
                f"Expert Answer:\n{completion}"
            )

        context = "\n\n".join(context_blocks)

        prompt = f"""You are Sahayak AI, a trusted financial fraud prevention assistant for Indian users.

A user has asked: "{query}"

Here are the most similar cases from our knowledge base with expert-crafted answers:

{context}

Instructions:
- Respond ONLY in {query_language}
- Synthesize the most relevant guidance to directly answer the user's specific question
- Be empathetic, clear, and actionable
- End with 3-5 specific numbered action steps the user should take right now
- Keep the response under 450 words
- If relevant, mention Indian helplines or portals (1930, cybercrime.gov.in, 1947 for UIDAI)
- Do NOT copy-paste the example answers — synthesize and adapt to the user's specific situation
- If the user's query is in Hindi or another Indian language, respond entirely in that language"""

        model    = GenerativeModel(settings.FLASH_MODEL)
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as exc:
        logger.error(f"Gemini synthesis failed: {exc}")
        # Graceful fallback: surface the top result's answer
        if results:
            fallback = results[0]["enhanced_completion"][:600]
            return f"{fallback}\n\n[Note: AI synthesis unavailable. Showing closest matching case answer.]"
        return "Unable to generate response. Ensure Vertex AI credentials are configured."


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/similar", response_model=RAGSearchResponse)
async def search_similar(request: RAGSearchRequest):
    """
    Search for similar fraud cases and synthesize an answer via Gemini 2.5 Flash.

    Flow:
      1. Detect query language (for Gemini synthesis language)
      2. BGE-M3 encode query (dense + sparse)
      3. Qdrant hybrid RRF search (top 50 candidates)
      4. BGE-Reranker-v2-M3 → top K results
      5. Gemini 2.5 Flash synthesis using enhanced_completion context
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    query_language = _detect_language(query)
    logger.info(f"RAG /similar: '{query[:80]}' (lang={query_language})")

    try:
        results = rag_search(
            query=query,
            top_k_candidates=50,
            top_k_final=request.top_k,
        )
    except Exception as exc:
        logger.error(f"RAG search error: {exc}")
        raise HTTPException(
            status_code=503,
            detail=f"RAG search unavailable: {exc}. "
                   "Ensure Qdrant is running and the collection is indexed "
                   "(python rag/ingest_bge.py --path <file.jsonl>).",
        )

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No results found. Index the dataset first: "
                   "python rag/ingest_bge.py --path <file.jsonl>",
        )

    gemini_answer = _gemini_synthesize(query, results, query_language)

    similar_questions = [
        SimilarQuestion(
            rank=r["rank"],
            user_query=r["user_query"],
            domain_category=r["domain_category"],
            subdomain=r["subdomain"],
            language_code=r["language_code"],
            language_name=r["language_name"],
            actions=r["actions"],
            source=r["source"],
            userprofile=r["userprofile"],
            learning_outcome=r["learning_outcome"],
            rerank_score=r["rerank_score"],
            retrieval_score=r["retrieval_score"],
        )
        for r in results
    ]

    return RAGSearchResponse(
        query=query,
        query_language=query_language,
        similar_questions=similar_questions,
        gemini_answer=gemini_answer,
        candidates_retrieved=50,
    )


@router.get("/health")
async def rag_health():
    """Check Qdrant connectivity and collection status."""
    ok = qdrant_health()
    return {
        "qdrant_healthy":    ok,
        "collection":        settings.QDRANT_COLLECTION,
        "qdrant_url":        settings.QDRANT_URL,
        "embed_model":       settings.BGE_MODEL_NAME,
        "reranker_model":    settings.BGE_RERANKER_NAME,
        "status":            "ready" if ok else "not_indexed",
        "setup_command":     "python rag/ingest_bge.py --path <your_file.jsonl>" if not ok else None,
    }
