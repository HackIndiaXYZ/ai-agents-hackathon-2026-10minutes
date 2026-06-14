"""
rag/bge_retriever.py — BGE-M3 hybrid retrieval via Qdrant RRF.

Pipeline:
  Query
    → BGE-M3 (dense + sparse in one pass, on CUDA if available)
    → Qdrant hybrid RRF fusion (top_k_candidates, default 50)
    → Return top_k_final results sorted by RRF score
"""

import os
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from utils.logger import logger

# ─── Singletons ──────────────────────────────────────────────────────────────

_embed_model = None
_qdrant      = None


def _embed():
    global _embed_model
    if _embed_model is None:
        from FlagEmbedding import BGEM3FlagModel
        import torch
        use_gpu = torch.cuda.is_available()
        device  = "cuda" if use_gpu else "cpu"
        logger.info(f"BGE-M3: loading {settings.BGE_MODEL_NAME} on {device} (fp16={use_gpu})...")
        _embed_model = BGEM3FlagModel(
            settings.BGE_MODEL_NAME,
            use_fp16=use_gpu,
            device=device,
        )
        logger.info(f"BGE-M3: ready on {device}.")
    return _embed_model


def _client():
    global _qdrant
    if _qdrant is None:
        from qdrant_client import QdrantClient
        _qdrant = QdrantClient(url=settings.QDRANT_URL, timeout=30)
        logger.info(f"Qdrant: connected to {settings.QDRANT_URL}")
    return _qdrant


# ─── Encoding ─────────────────────────────────────────────────────────────────

def _encode_query(query: str) -> tuple:
    """Returns (dense_vec: list[float], sparse_vec: SparseVector)."""
    from qdrant_client.models import SparseVector

    model = _embed()
    out = model.encode(
        [query],
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
        batch_size=1,
    )
    dense_vec  = out["dense_vecs"][0].tolist()
    lex        = out["lexical_weights"][0]
    indices    = [int(k) for k in lex.keys()]
    values     = [float(v) for v in lex.values()]
    sparse_vec = SparseVector(indices=indices, values=values)
    return dense_vec, sparse_vec


# ─── Search ───────────────────────────────────────────────────────────────────

def search(
    query: str,
    top_k_candidates: int = 50,
    top_k_final: int = 5,
    collection: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Hybrid BGE-M3 retrieval — dense + sparse → Qdrant RRF fusion.
    No reranker: RRF scores are used directly for ranking.
    """
    coll = collection or settings.QDRANT_COLLECTION
    qc   = _client()

    # ── 1. Encode ─────────────────────────────────────────────────────────────
    dense_vec, sparse_vec = _encode_query(query)

    # ── 2. Hybrid Qdrant search (dense + sparse → RRF) ────────────────────────
    scored_points = []
    try:
        from qdrant_client.models import Prefetch, FusionQuery, Fusion

        raw = qc.query_points(
            collection_name=coll,
            prefetch=[
                Prefetch(query=dense_vec,  using="dense",  limit=top_k_candidates),
                Prefetch(query=sparse_vec, using="sparse", limit=top_k_candidates),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k_final,
            with_payload=True,
        )
        scored_points = raw.points if hasattr(raw, "points") else raw

    except Exception as hybrid_err:
        logger.warning(f"Hybrid search failed ({hybrid_err}), falling back to dense-only")
        try:
            scored_points = qc.search(
                collection_name=coll,
                query_vector=("dense", dense_vec),
                limit=top_k_final,
                with_payload=True,
            )
        except Exception as dense_err:
            logger.error(f"Dense-only search also failed: {dense_err}")
            return []

    if not scored_points:
        logger.warning("Qdrant returned 0 candidates.")
        return []

    logger.info(f"Qdrant: {len(scored_points)} results retrieved")

    # ── 3. Format results ─────────────────────────────────────────────────────
    results: List[Dict[str, Any]] = []
    for rank, sp in enumerate(scored_points, start=1):
        p = sp.payload or {}

        actions_raw = p.get("actions_suggestions_next_step", "")
        actions = (
            [a.strip().rstrip(".") for a in actions_raw.split(";") if a.strip()]
            if actions_raw else []
        )

        results.append({
            "rank":                rank,
            "retrieval_score":     round(float(sp.score), 4),
            "rerank_score":        round(float(sp.score), 4),  # same as retrieval
            "user_query":          p.get("user_query", ""),
            "enhanced_completion": p.get("enhanced_completion", ""),
            "enhanced_prompt":     p.get("enhanced_prompt", ""),
            "answer_guidance":     p.get("answer_guidance", ""),
            "domain_category":     p.get("domain_category", ""),
            "subdomain":           p.get("subdomain", ""),
            "source":              p.get("source", ""),
            "userprofile":         p.get("userprofile", ""),
            "actions":             actions,
            "learning_outcome":    p.get("learning_outcome", ""),
            "language_code":       p.get("language_code", "en"),
            "language_name":       p.get("language_name", "English"),
            "page_content":        p.get("page_content", ""),
        })

    return results


# ─── Health check ─────────────────────────────────────────────────────────────

def health_check() -> bool:
    """Return True if Qdrant is reachable and the target collection exists."""
    try:
        qc    = _client()
        names = [c.name for c in qc.get_collections().collections]
        return settings.QDRANT_COLLECTION in names
    except Exception:
        return False
