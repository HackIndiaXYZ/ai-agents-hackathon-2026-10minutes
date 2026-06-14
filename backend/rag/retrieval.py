"""
rag/retrieval.py — Main retrieval entry point for the reasoning agent.

All embedding calls go through Vertex AI (text-multilingual-embedding-002)
using Application Default Credentials — no API key required.

Retrieval strategy (auto-selected based on config):

  A) Vertex AI Vector Search  (VECTOR_SEARCH_INDEX_ENDPOINT_ID is set)
     Full GCP solution — ANN search at scale for 8 000+ rows.
     Requires: gcloud ADC, VERTEX_AI_PROJECT_ID, endpoint deployed via
     build_rag_index.py.

  B) Local cosine similarity  (default fallback)
     Reads RAG_JSONL_PATH + pre-computed embeddings from
     RAG_EMBEDDINGS_CACHE_PATH (written by build_rag_index.py).
     On first call with no cache it embeds all documents live — one-time cost.
     Subsequent calls use the on-disk cache.

Returned format (matches the RAG stub contract in reasoning_agent.py):
  [{
      "chunk":            str,    # relevant text for the reasoning agent
      "source_doc":       str,    # source URL / document name
      "relevance_score":  float,  # cosine similarity [0, 1]
      "last_updated":     str,    # feedback / publish date
      "scheme_name":      str,    # domain_category + " > " + subdomain
  }]
"""

import json
import math
import os
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from rag.embedder import embed_query, embed_documents
from utils.logger import logger


# ─── In-memory cache (loaded once per process) ────────────────────────────────

_corpus: List[Dict[str, Any]] = []          # raw JSONL records
_corpus_embeddings: List[List[float]] = []  # parallel list of embedding vectors
_corpus_loaded = False


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _record_to_embed_text(record: Dict[str, Any]) -> str:
    """Build the text we embed for each JSONL record (document side)."""
    parts = [
        record.get("domain_category", ""),
        record.get("subdomain", ""),
        record.get("user_query", ""),
    ]
    return " | ".join(p for p in parts if p)


def _record_to_chunk(record: Dict[str, Any]) -> str:
    """Build the context chunk surfaced to the reasoning agent."""
    lines = []
    ep = record.get("enhanced_prompt", "").strip()
    ag = record.get("answer_guidance", "").strip()
    ec = record.get("enhanced_completion", "").strip()
    ac = record.get("actions_suggestions_next_step", "").strip()
    if ep:
        lines.append(f"CONTEXT:\n{ep[:800]}")
    if ag:
        lines.append(f"GUIDANCE:\n{ag[:600]}")
    if ec:
        lines.append(f"EXAMPLE RESPONSE:\n{ec[:400]}")
    if ac:
        lines.append(f"SUGGESTED ACTIONS:\n{ac[:300]}")
    return "\n\n".join(lines)


def _load_local_corpus() -> None:
    global _corpus, _corpus_embeddings, _corpus_loaded
    if _corpus_loaded:
        return

    jsonl_path = settings.RAG_JSONL_PATH
    cache_path = settings.RAG_EMBEDDINGS_CACHE_PATH

    # ── Load JSONL records ────────────────────────────────────────────────────
    if not os.path.exists(jsonl_path):
        logger.warning(f"RAG JSONL not found at {jsonl_path}; RAG disabled.")
        _corpus_loaded = True
        return

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    _corpus.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    logger.info(f"RAG: loaded {len(_corpus)} records from {jsonl_path}")

    # ── Try loading pre-computed embeddings cache ─────────────────────────────
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                _corpus_embeddings = json.load(f)
            if len(_corpus_embeddings) == len(_corpus):
                logger.info(f"RAG: loaded embedding cache ({len(_corpus_embeddings)} vectors)")
                _corpus_loaded = True
                return
            else:
                logger.warning("RAG: cache size mismatch — re-embedding")
                _corpus_embeddings = []
        except Exception as exc:
            logger.warning(f"RAG: could not load cache ({exc}) — re-embedding")
            _corpus_embeddings = []

    # ── Compute embeddings live (slow, runs once) ─────────────────────────────
    logger.info("RAG: computing embeddings for corpus (first-time setup)…")
    texts = [_record_to_embed_text(r) for r in _corpus]

    batch_size = 100
    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        all_embeddings.extend(embed_documents(batch))

    _corpus_embeddings = all_embeddings

    # Save cache so next startup is instant
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(_corpus_embeddings, f)
    logger.info(f"RAG: embedding cache saved to {cache_path}")

    _corpus_loaded = True


# ─── Local cosine-similarity retrieval ───────────────────────────────────────

def _retrieve_local(
    query: str,
    top_k: int = 5,
    domain_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _load_local_corpus()

    if not _corpus or not _corpus_embeddings:
        return []

    q_vec = embed_query(query)
    if not q_vec:
        return []

    scored = []
    for i, (record, doc_vec) in enumerate(zip(_corpus, _corpus_embeddings)):
        if domain_filter and record.get("domain_category", "") != domain_filter:
            continue
        score = _cosine(q_vec, doc_vec)
        scored.append((score, i))

    scored.sort(reverse=True)
    top = scored[:top_k]

    results = []
    for score, idx in top:
        r = _corpus[idx]
        results.append({
            "chunk": _record_to_chunk(r),
            "source_doc": r.get("source", ""),
            "relevance_score": round(score, 4),
            "last_updated": r.get("feedback", ""),
            "scheme_name": f"{r.get('domain_category','')} > {r.get('subdomain','')}",
        })
    return results


# ─── Vertex AI Vector Search retrieval ───────────────────────────────────────

def _retrieve_vertex(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Query Vertex AI Vector Search endpoint; fall back to local on error."""
    try:
        from google.cloud import aiplatform

        aiplatform.init(
            project=settings.VERTEX_AI_PROJECT_ID,
            location=settings.VERTEX_AI_REGION,
        )
        endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=settings.VECTOR_SEARCH_INDEX_ENDPOINT_ID
        )
        q_vec = embed_query(query)
        response = endpoint.find_neighbors(
            deployed_index_id=settings.VECTOR_SEARCH_DEPLOYED_INDEX_ID,
            queries=[q_vec],
            num_neighbors=top_k,
        )
        neighbors = response[0] if response else []

        # Neighbors have .id (str) and .distance (float, L2 distance)
        # We need to map IDs back to corpus records
        _load_local_corpus()
        id_to_record = {str(i): r for i, r in enumerate(_corpus)}

        results = []
        for nb in neighbors:
            record_id = str(nb.id)
            r = id_to_record.get(record_id)
            if r is None:
                continue
            # Convert L2 distance → similarity score [0, 1] (approximate)
            sim = max(0.0, 1.0 - nb.distance / 2.0)
            results.append({
                "chunk": _record_to_chunk(r),
                "source_doc": r.get("source", ""),
                "relevance_score": round(sim, 4),
                "last_updated": r.get("feedback", ""),
                "scheme_name": f"{r.get('domain_category','')} > {r.get('subdomain','')}",
            })
        return results

    except Exception as exc:
        logger.warning(f"RAG: Vertex AI Vector Search failed ({exc}), falling back to local")
        return _retrieve_local(query, top_k=top_k)


# ─── Public retrieve function ─────────────────────────────────────────────────

def retrieve(
    query: str,
    detected_language: str = "English",
    user_profile: Optional[Dict[str, Any]] = None,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the top-K most relevant dataset examples for a user query.

    The query is language-agnostic — the multilingual embedding model handles
    cross-lingual matching so Hindi queries retrieve English dataset entries
    (and vice versa) when they are semantically equivalent.

    Args:
        query:             The user's query or the current sub-query text.
        detected_language: Language detected by the language agent.
        user_profile:      Optional profile for future personalised filtering.
        top_k:             Number of results (defaults to config RAG_TOP_K).

    Returns:
        List of result dicts matching the RAG stub contract.
    """
    k = top_k or settings.RAG_TOP_K

    if settings.VECTOR_SEARCH_INDEX_ENDPOINT_ID:
        return _retrieve_vertex(query, top_k=k)
    return _retrieve_local(query, top_k=k)
