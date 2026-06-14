"""
scripts/test_rag.py — Standalone RAG pipeline smoke test.

Tests the full path: Vertex AI embedding → cosine search → result display.
Run this before starting the server to confirm everything works.

Usage:
    cd backend
    python scripts/test_rag.py
    python scripts/test_rag.py --query "I got a fake UPI payment request"
    python scripts/test_rag.py --query "KCC loan fraud" --top-k 3
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── 1. Config check ───────────────────────────────────────────────────────────
print("\n─── Sahayak RAG Smoke Test ───────────────────────────────────────────")

try:
    from config import settings
    print(f"✓  Config loaded")
    print(f"   Project  : {settings.VERTEX_AI_PROJECT_ID}")
    print(f"   Region   : {settings.VERTEX_AI_REGION}")
    print(f"   Model    : {settings.EMBEDDING_MODEL}")
    print(f"   JSONL    : {settings.RAG_JSONL_PATH}")
    print(f"   Cache    : {settings.RAG_EMBEDDINGS_CACHE_PATH}")
except Exception as e:
    print(f"✗  Config failed: {e}")
    print("   → Create backend/.env with VERTEX_AI_PROJECT_ID set")
    sys.exit(1)

if not settings.VERTEX_AI_PROJECT_ID:
    print("✗  VERTEX_AI_PROJECT_ID is empty in .env")
    sys.exit(1)

# ── 2. Dataset check ──────────────────────────────────────────────────────────
print("\n─── Dataset ──────────────────────────────────────────────────────────")
if not os.path.exists(settings.RAG_JSONL_PATH):
    print(f"✗  JSONL not found at {settings.RAG_JSONL_PATH}")
    sys.exit(1)

records = []
with open(settings.RAG_JSONL_PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

print(f"✓  {len(records)} records loaded from {settings.RAG_JSONL_PATH}")
domains = {}
for r in records:
    d = r.get("domain_category", "unknown")
    domains[d] = domains.get(d, 0) + 1
for d, n in domains.items():
    print(f"   {d}: {n} records")

# ── 3. Vertex AI ADC check ────────────────────────────────────────────────────
print("\n─── Vertex AI Authentication ─────────────────────────────────────────")
try:
    import vertexai
    vertexai.init(
        project=settings.VERTEX_AI_PROJECT_ID,
        location=settings.VERTEX_AI_REGION,
    )
    print(f"✓  vertexai.init() succeeded")
except Exception as e:
    print(f"✗  Vertex AI init failed: {e}")
    print("   → Run: gcloud auth application-default login")
    print("   → Run: gcloud auth application-default set-quota-project", settings.VERTEX_AI_PROJECT_ID)
    sys.exit(1)

# ── 4. Embedding model check ──────────────────────────────────────────────────
print("\n─── Embedding Model ──────────────────────────────────────────────────")
try:
    from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
    t0 = time.time()
    model = TextEmbeddingModel.from_pretrained(settings.EMBEDDING_MODEL)
    test_input = [TextEmbeddingInput(text="test query for financial inclusion", task_type="RETRIEVAL_QUERY")]
    result = model.get_embeddings(test_input)
    dims = len(result[0].values)
    elapsed = round((time.time() - t0) * 1000)
    print(f"✓  {settings.EMBEDDING_MODEL} loaded — {dims}-dim vectors ({elapsed}ms)")
except Exception as e:
    print(f"✗  Embedding model failed: {e}")
    print("   → Make sure aiplatform.googleapis.com is enabled:")
    print(f"     gcloud services enable aiplatform.googleapis.com --project={settings.VERTEX_AI_PROJECT_ID}")
    sys.exit(1)

# ── 5. Build or load embeddings cache ────────────────────────────────────────
print("\n─── Embeddings Cache ─────────────────────────────────────────────────")
cache_path = settings.RAG_EMBEDDINGS_CACHE_PATH
corpus_embeddings = []

if os.path.exists(cache_path):
    with open(cache_path, encoding="utf-8") as f:
        corpus_embeddings = json.load(f)
    if len(corpus_embeddings) == len(records):
        print(f"✓  Cache loaded ({len(corpus_embeddings)} vectors from {cache_path})")
    else:
        print(f"⚠  Cache size mismatch ({len(corpus_embeddings)} vs {len(records)} records) — rebuilding")
        corpus_embeddings = []

if not corpus_embeddings:
    print(f"   Building embeddings for {len(records)} records…")
    texts = [
        " | ".join(filter(None, [r.get("domain_category",""), r.get("subdomain",""), r.get("user_query","")]))
        for r in records
    ]
    t0 = time.time()
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = [TextEmbeddingInput(text=t, task_type="RETRIEVAL_DOCUMENT") for t in batch]
        results = model.get_embeddings(inputs)
        corpus_embeddings.extend([r.values for r in results])
        print(f"   {min(i+batch_size, len(texts))}/{len(texts)} embedded")
    elapsed = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(corpus_embeddings, f)
    print(f"✓  Cache built and saved → {cache_path} ({elapsed}s)")

# ── 6. Query test ─────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--query", default="I received a suspicious UPI payment request asking for my PIN")
parser.add_argument("--top-k", type=int, default=3)
args, _ = parser.parse_known_args()

print(f"\n─── Retrieval Test ───────────────────────────────────────────────────")
print(f"   Query: \"{args.query}\"")
print(f"   Top-K: {args.top_k}")

import math

def cosine(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot/(na*nb) if na and nb else 0.0

t0 = time.time()
q_input = [TextEmbeddingInput(text=args.query, task_type="RETRIEVAL_QUERY")]
q_vec = model.get_embeddings(q_input)[0].values
elapsed_embed = round((time.time()-t0)*1000)

scores = [(cosine(q_vec, doc_vec), i) for i, doc_vec in enumerate(corpus_embeddings)]
scores.sort(reverse=True)
elapsed_total = round((time.time()-t0)*1000)

print(f"   Embed: {elapsed_embed}ms  |  Search: {elapsed_total}ms\n")

for rank, (score, idx) in enumerate(scores[:args.top_k], 1):
    r = records[idx]
    print(f"  [{rank}] score={score:.4f}  |  {r.get('domain_category','')} > {r.get('subdomain','')}")
    print(f"       Query: {r.get('user_query','')[:90]}…")
    guidance = r.get('answer_guidance','')[:120]
    print(f"       Guidance: {guidance}…")
    print()

print("─── All checks passed ✓ ─────────────────────────────────────────────\n")
