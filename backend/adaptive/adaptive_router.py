"""
adaptive/adaptive_router.py — Endpoints for the adaptive data loop.

  GET  /adaptive/stats     → queue + staging counts
  GET  /adaptive/preview   → last N anonymised staged rows (for review)
  POST /adaptive/harvest   → format queued events into the staging JSONL
  POST /adaptive/ingest    → promote the staging file into Qdrant (manual step)

Promotion is explicit and human-triggered — staged user data only reaches the
live RAG index when someone calls /adaptive/ingest.
"""

import sys
import os
import json
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import settings
from adaptive import dataset_builder
from utils.logger import logger

router = APIRouter(prefix="/adaptive", tags=["Adaptive Loop"])


class HarvestRequest(BaseModel):
    max_events: int = 200
    batch_size: int = 8


@router.get("/stats")
async def stats():
    return dataset_builder.stats()


@router.get("/preview")
async def preview(limit: int = Query(10, ge=1, le=100)):
    """Return the last `limit` anonymised rows from the staging file for review."""
    path = dataset_builder._staging_path()
    if not os.path.exists(path):
        return {"rows": [], "staging_path": path}
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        for line in lines[-limit:]:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read staging file: {exc}")
    return {"rows": rows, "count": len(rows), "staging_path": path}


@router.post("/harvest")
async def harvest(req: HarvestRequest):
    """Anonymise + format queued interactions into the staging dataset."""
    try:
        return dataset_builder.harvest(max_events=req.max_events, batch_size=req.batch_size)
    except Exception as exc:
        logger.error(f"[adaptive] harvest endpoint failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Harvest failed: {exc}")


@router.post("/ingest")
async def ingest(collection: Optional[str] = Query(None, description="Target Qdrant collection")):
    """
    Promote the staging dataset into Qdrant (append, no recreate).
    This is the manual review->publish step. Loads BGE-M3, so it can take a while.
    """
    path = dataset_builder._staging_path()
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No staging dataset to ingest yet. Run /adaptive/harvest first.")

    # Make sure there is at least one row
    with open(path, "r", encoding="utf-8") as f:
        has_rows = any(line.strip() for line in f)
    if not has_rows:
        raise HTTPException(status_code=400, detail="Staging dataset is empty.")

    try:
        from rag.ingest_bge import ingest as bge_ingest
        bge_ingest(
            jsonl_path=path,
            collection=collection or settings.QDRANT_COLLECTION,
            qdrant_url=settings.QDRANT_URL,
            batch_size=16,
            recreate=False,  # append to the existing collection
        )
    except Exception as exc:
        logger.error(f"[adaptive] ingest failed: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"Ingest failed: {exc}. Ensure Qdrant is running and BGE deps are installed.",
        )

    return {
        "status": "ingested",
        "staging_path": path,
        "collection": collection or settings.QDRANT_COLLECTION,
    }
