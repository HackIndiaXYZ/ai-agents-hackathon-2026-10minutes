"""
adaptive/dataset_builder.py — Harvest queued interactions into the staging dataset.

Takes the raw, low-PII events queued by logger.log_interaction(), runs them
through Gemini to (1) strip any remaining personal data and (2) reformat them
into the SAME JSONL schema as the source fraud-QA dataset, then appends the
anonymised rows to the staging file (config.ADAPTIVE_DATASET_PATH).

The staging file is what a human later promotes into Qdrant via ingest_bge.py.
Nothing here writes to the live RAG index.
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from memory.session_store import (
    peek_interaction_events,
    drop_interaction_events,
    count_interaction_events,
)
from utils.logger import logger

_DOMAINS = [
    "Banking & Digital Payments",
    "Government Schemes",
    "Fraud & Cyber Safety",
    "Savings & Insurance",
    "Credit & Borrowing",
]

_SOURCE_TAG = "Adaptive user interaction (anonymised)"


# ─── Staging file helpers ────────────────────────────────────────────────────

def _staging_path() -> str:
    path = settings.ADAPTIVE_DATASET_PATH
    if not os.path.isabs(path):
        # Resolve relative to the backend/ directory
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _existing_query_hashes(path: str) -> set:
    hashes = set()
    if not os.path.exists(path):
        return hashes
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    hashes.add(_qhash(row.get("user_query", "")))
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        logger.warning(f"[adaptive] could not read staging file: {exc}")
    return hashes


def _qhash(q: str) -> str:
    return hashlib.sha1((q or "").strip().lower().encode("utf-8")).hexdigest()


# ─── Gemini anonymise + format ───────────────────────────────────────────────

def _format_batch(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert a batch of raw events into anonymised dataset rows via Gemini."""
    if not events:
        return []
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig

        vertexai.init(project=settings.VERTEX_AI_PROJECT_ID, location=settings.VERTEX_AI_REGION)
        model = GenerativeModel(settings.FLASH_MODEL)

        blocks = []
        for i, e in enumerate(events):
            blocks.append(json.dumps({
                "index": i,
                "kind": e.get("kind"),
                "language": e.get("language"),
                "profile": e.get("profile"),
                "user_text": e.get("user_text"),
                "assistant_summary": e.get("assistant_summary"),
                "extra": e.get("extra"),
            }, ensure_ascii=False))

        prompt = f"""You are building an ANONYMISED training dataset for a financial-inclusion
assistant for rural India. Below are raw user interactions. For EACH one, produce a
clean dataset row.

CRITICAL ANONYMISATION RULES:
- Remove ALL personal data: names, phone numbers, account numbers, card numbers,
  OTPs, UPI IDs, email addresses, exact street addresses, vehicle numbers.
- Generalise specific amounts (e.g. "Rs 47,320" -> "around Rs 45,000-50,000").
- Keep only STATE-level location; drop village/district if it identifies a person.
- Never invent facts; if an interaction has no useful learning content, skip it.

For each useful interaction return a JSON object with these EXACT keys:
{{
  "index": the input index,
  "user_query": the user's question rephrased generically, in its original language,
  "enhanced_prompt": a clear instruction an expert could answer (original language),
  "enhanced_completion": a high-quality, anonymised expert answer (original language),
  "answer_guidance": 1-2 sentences of factual guidance (English),
  "domain_category": EXACTLY one of {_DOMAINS},
  "subdomain": a short sub-topic label (English),
  "actions_suggestions_next_step": concrete next steps joined by "; " (original language),
  "learning_outcome": one sentence on what the user learns (English),
  "userprofile": a generic, non-identifying persona description (English),
  "usable": true or false (false if the interaction has no reusable learning value)
}}

Raw interactions (one JSON per line):
{chr(10).join(blocks)}

Return ONLY a JSON array of these objects (one per usable interaction; set usable=false to discard)."""

        resp = model.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0.2, response_mime_type="application/json"),
        )
        data = json.loads(resp.text)
        if not isinstance(data, list):
            return []

        rows = []
        for obj in data:
            if not isinstance(obj, dict) or not obj.get("usable", True):
                continue
            domain = obj.get("domain_category", "")
            if domain not in _DOMAINS:
                domain = "Fraud & Cyber Safety"
            uq = (obj.get("user_query") or "").strip()
            if not uq or not (obj.get("enhanced_completion") or "").strip():
                continue
            rows.append({
                "user_query": uq,
                "enhanced_prompt": obj.get("enhanced_prompt", ""),
                "enhanced_completion": obj.get("enhanced_completion", ""),
                "answer_guidance": obj.get("answer_guidance", ""),
                "domain_category": domain,
                "subdomain": obj.get("subdomain", ""),
                "actions_suggestions_next_step": obj.get("actions_suggestions_next_step", ""),
                "learning_outcome": obj.get("learning_outcome", ""),
                "userprofile": obj.get("userprofile", ""),
                "source": _SOURCE_TAG,
                "contributed_at": datetime.now(timezone.utc).isoformat(),
            })
        return rows
    except Exception as exc:
        logger.error(f"[adaptive] format batch failed: {exc}")
        return []


# ─── Public API ──────────────────────────────────────────────────────────────

def harvest(max_events: int = 200, batch_size: int = 8) -> Dict[str, Any]:
    """
    Process queued events into the staging dataset.

    Returns {processed, written, skipped_duplicates, staging_path, remaining}.
    """
    events = peek_interaction_events()
    if not events:
        return {"processed": 0, "written": 0, "skipped_duplicates": 0,
                "staging_path": _staging_path(), "remaining": 0}

    take = events[:max_events]
    path = _staging_path()
    seen = _existing_query_hashes(path)

    written = 0
    skipped = 0
    out_lines: List[str] = []

    for i in range(0, len(take), batch_size):
        rows = _format_batch(take[i:i + batch_size])
        for row in rows:
            h = _qhash(row["user_query"])
            if h in seen:
                skipped += 1
                continue
            seen.add(h)
            out_lines.append(json.dumps(row, ensure_ascii=False))
            written += 1

    if out_lines:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(out_lines) + "\n")

    # Remove the events we consumed from the queue
    drop_interaction_events(len(take))

    logger.info(f"[adaptive] harvested {len(take)} events → {written} rows ({skipped} dupes)")
    return {
        "processed": len(take),
        "written": written,
        "skipped_duplicates": skipped,
        "staging_path": path,
        "remaining": count_interaction_events(),
    }


def stats() -> Dict[str, Any]:
    """Counts for the queue and the staging dataset."""
    path = _staging_path()
    staged = 0
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                staged = sum(1 for line in f if line.strip())
        except Exception:
            staged = 0
    return {
        "queued_events": count_interaction_events(),
        "staged_rows": staged,
        "staging_path": path,
    }
