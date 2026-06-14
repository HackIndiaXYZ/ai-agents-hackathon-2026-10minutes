"""
rag/ingest_bge.py — One-command BGE-M3 + Qdrant indexing pipeline.

Usage:
    python ingest_bge.py --path /path/to/indian_financial_fraud_qa.jsonl
    python ingest_bge.py --path /path/to/file.jsonl --collection my_collection
    python ingest_bge.py --path /path/to/file.jsonl --recreate   # drop & rebuild

Pipeline:
    JSONL → language detect → BGE-M3 (dense + sparse) → Qdrant upsert

No chunking — each row is one document.
page_content = "Question: {user_query}\\n\\nAnswer:\\n{enhanced_completion}"
"""

import argparse
import json
import os
import sys
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ─── Dependency checks ────────────────────────────────────────────────────────

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kwargs):
        total = kwargs.get("total", len(it) if hasattr(it, "__len__") else "?")
        print(f"  Processing {total} items (install tqdm for progress bar)...")
        return it

try:
    from langdetect import detect
except ImportError:
    print("ERROR: langdetect not installed. Run:  pip install langdetect")
    sys.exit(1)

try:
    from FlagEmbedding import BGEM3FlagModel
except ImportError:
    print("ERROR: FlagEmbedding not installed. Run:  pip install FlagEmbedding")
    sys.exit(1)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        SparseVectorParams,
        SparseIndexParams,
        PointStruct,
        SparseVector,
    )
except ImportError:
    print("ERROR: qdrant-client not installed. Run:  pip install 'qdrant-client>=1.9.0'")
    sys.exit(1)


# ─── Constants ────────────────────────────────────────────────────────────────

LANG_CODES: Dict[str, str] = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "mr": "Marathi",
    "ta": "Tamil",   "te": "Telugu", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu",
}

# BGE-M3 max tokens = 8192. We cap at ~3000 chars for the answer portion
# so batch encoding stays fast while retaining the key content.
MAX_COMPLETION_CHARS = 3000


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _detect_lang(text: str) -> tuple:
    try:
        code = detect(text[:500])
        return code, LANG_CODES.get(code, code)
    except Exception:
        return "en", "English"


def _build_page_content(row: Dict[str, Any]) -> str:
    q = row.get("user_query", "").strip()
    a = row.get("enhanced_completion", "").strip()
    if len(a) > MAX_COMPLETION_CHARS:
        a = a[:MAX_COMPLETION_CHARS]
    return f"Question: {q}\n\nAnswer:\n{a}"


def _sparse_to_qdrant(lex_weights: dict) -> tuple:
    """Convert BGEM3 lexical_weights dict → (indices, values) for SparseVector."""
    indices = [int(k) for k in lex_weights.keys()]
    values  = [float(v) for v in lex_weights.values()]
    return indices, values


# ─── Main ingest ─────────────────────────────────────────────────────────────

def ingest(
    jsonl_path: str,
    collection: str,
    qdrant_url: str,
    batch_size: int,
    recreate: bool,
) -> None:

    # ── 1. Load JSONL ──────────────────────────────────────────────────────────
    print(f"\n[1/5] Loading JSONL from: {jsonl_path}")
    rows: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  Warning: skipping malformed line {line_no}: {e}")

    print(f"  Loaded {len(rows):,} records")

    # ── 2. Language detection ─────────────────────────────────────────────────
    print("\n[2/5] Detecting languages...")
    for row in tqdm(rows, total=len(rows), desc="  lang-detect"):
        code, name = _detect_lang(row.get("user_query", ""))
        row["_lang_code"] = code
        row["_lang_name"] = name

    dist: Dict[str, int] = {}
    for r in rows:
        dist[r["_lang_name"]] = dist.get(r["_lang_name"], 0) + 1
    top = sorted(dist.items(), key=lambda x: -x[1])[:8]
    print(f"  Language distribution: { {k: v for k, v in top} }")

    # ── 3. Build page contents ────────────────────────────────────────────────
    print("\n[3/5] Building page contents (question + answer)...")
    page_contents = [_build_page_content(r) for r in rows]
    avg_len = sum(len(t) for t in page_contents) // len(page_contents)
    print(f"  Average page_content length: {avg_len} chars")

    # ── 4. BGE-M3 embeddings ──────────────────────────────────────────────────
    print("\n[4/5] Loading BAAI/bge-m3 ...")
    print("  First run downloads ~2.2 GB to ~/.cache/huggingface — this takes a few minutes.")

    import torch
    use_fp16 = torch.cuda.is_available()
    device   = "GPU + fp16" if use_fp16 else "CPU (fp32 — slower but works)"
    print(f"  Device: {device}")

    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=use_fp16)
    print("  Model loaded.")

    print(f"  Embedding {len(page_contents):,} documents (batch_size={batch_size})...")
    all_dense: List[List[float]] = []
    all_sparse: List[Dict]       = []

    for i in tqdm(range(0, len(page_contents), batch_size), desc="  embedding"):
        batch = page_contents[i : i + batch_size]
        output = model.encode(
            batch,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
            batch_size=batch_size,
        )
        all_dense.extend(output["dense_vecs"].tolist())
        all_sparse.extend(output["lexical_weights"])

    dense_dim = len(all_dense[0])
    print(f"  Done. Dense dimension: {dense_dim}")

    # ── 5. Qdrant upsert ──────────────────────────────────────────────────────
    print(f"\n[5/5] Connecting to Qdrant at {qdrant_url} ...")
    client = QdrantClient(url=qdrant_url, timeout=60)

    existing = [c.name for c in client.get_collections().collections]

    if recreate and collection in existing:
        print(f"  Dropping existing collection '{collection}'...")
        client.delete_collection(collection)
        existing = []

    if collection not in existing:
        print(f"  Creating collection '{collection}' (dense={dense_dim}D, sparse=BM25)...")
        client.create_collection(
            collection_name=collection,
            vectors_config={
                "dense": VectorParams(size=dense_dim, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            },
        )
    else:
        print(f"  Collection '{collection}' exists — upserting points.")

    upsert_batch = 64
    total_upserted = 0

    for i in tqdm(range(0, len(rows), upsert_batch), desc="  upserting"):
        batch_rows   = rows[i : i + upsert_batch]
        batch_dense  = all_dense[i : i + upsert_batch]
        batch_sparse = all_sparse[i : i + upsert_batch]

        points = []
        for j, (row, dvec, lex) in enumerate(zip(batch_rows, batch_dense, batch_sparse)):
            sp_idx, sp_vals = _sparse_to_qdrant(lex)

            actions_raw = row.get("actions_suggestions_next_step", "")

            points.append(PointStruct(
                id=i + j,
                vector={
                    "dense":  dvec,
                    "sparse": SparseVector(indices=sp_idx, values=sp_vals),
                },
                payload={
                    "user_query":                   row.get("user_query", ""),
                    "enhanced_completion":           row.get("enhanced_completion", ""),
                    "enhanced_prompt":               row.get("enhanced_prompt", ""),
                    "answer_guidance":               row.get("answer_guidance", ""),
                    "domain_category":               row.get("domain_category", ""),
                    "subdomain":                     row.get("subdomain", ""),
                    "source":                        row.get("source", ""),
                    "userprofile":                   row.get("userprofile", ""),
                    "actions_suggestions_next_step": actions_raw,
                    "learning_outcome":              row.get("learning_outcome", ""),
                    "language_code":                 row.get("_lang_code", "en"),
                    "language_name":                 row.get("_lang_name", "English"),
                    "page_content":                  page_contents[i + j],
                },
            ))

        client.upsert(collection_name=collection, points=points, wait=True)
        total_upserted += len(points)

    count = client.get_collection(collection).points_count
    print(f"\n✓ Indexed {total_upserted:,} points into collection '{collection}'")
    print(f"  Collection now has {count:,} points total.")
    print(f"\n  Ready for hybrid search (dense cosine + sparse BM25 via RRF)")
    print(f"  Next step: start the backend and test at POST /rag/similar")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index a JSONL fraud-QA dataset into Qdrant using BGE-M3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest_bge.py --path ~/Downloads/indian_financial_fraud_qa.jsonl
  python ingest_bge.py --path data/qa.jsonl --collection my_coll --batch-size 8
  python ingest_bge.py --path data/qa.jsonl --recreate   # fresh index
        """,
    )
    parser.add_argument("--path",        required=True,  help="Path to JSONL file")
    parser.add_argument("--collection",  default="sahayak_fraud_qa", help="Qdrant collection name")
    parser.add_argument("--qdrant-url",  default="http://localhost:6333", help="Qdrant URL")
    parser.add_argument("--batch-size",  type=int, default=16, help="BGE-M3 encoding batch size")
    parser.add_argument("--recreate",    action="store_true", help="Drop & recreate the collection")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: file not found: {args.path}")
        sys.exit(1)

    t0 = time.time()
    ingest(
        jsonl_path=args.path,
        collection=args.collection,
        qdrant_url=args.qdrant_url,
        batch_size=args.batch_size,
        recreate=args.recreate,
    )
    print(f"\nTotal elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
