"""
scripts/build_rag_index.py — One-time RAG index builder.

Usage:
    cd backend
    python scripts/build_rag_index.py [--jsonl PATH] [--upload-gcs] [--create-index]

Steps:
  1. Reads the JSONL dataset from RAG_JSONL_PATH (or --jsonl override).
  2. Embeds each record using the configured embedding model.
  3. Saves local embedding cache to RAG_EMBEDDINGS_CACHE_PATH.
  4. (Optional) Uploads JSONL + embeddings JSON to GCS (--upload-gcs).
  5. (Optional) Creates a Vertex AI Vector Search index + endpoint (--create-index).
     This step is slow (index build can take 30–60 min) and only needed once.

After running with --create-index, copy the printed endpoint/index IDs into .env:
    VECTOR_SEARCH_INDEX_ENDPOINT_ID=projects/.../locations/.../indexEndpoints/...
    VECTOR_SEARCH_DEPLOYED_INDEX_ID=sahayak_rag_v1
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from rag.embedder import embed_documents
from utils.logger import logger


DEPLOYED_INDEX_ID = "sahayak_rag_v1"


def load_jsonl(path: str):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_embed_texts(records):
    return [
        " | ".join(filter(None, [
            r.get("domain_category", ""),
            r.get("subdomain", ""),
            r.get("user_query", ""),
        ]))
        for r in records
    ]


def compute_and_cache_embeddings(records, cache_path: str):
    texts = build_embed_texts(records)
    print(f"Embedding {len(texts)} records…")

    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        all_embeddings.extend(embed_documents(batch))
        print(f"  {min(i + batch_size, len(texts))}/{len(texts)} embedded")

    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_embeddings, f)
    print(f"Cache saved → {cache_path}")
    return all_embeddings


def upload_to_gcs(local_jsonl_path: str, embeddings: list, bucket_name: str):
    from google.cloud import storage

    client = storage.Client(project=settings.VERTEX_AI_PROJECT_ID)
    bucket = client.bucket(bucket_name)

    # Upload original JSONL
    blob = bucket.blob("rag/financial_fraud_qa.jsonl")
    blob.upload_from_filename(local_jsonl_path)
    print(f"Uploaded {local_jsonl_path} → gs://{bucket_name}/rag/financial_fraud_qa.jsonl")

    # Upload embeddings as Vector Search batch format:
    # Each line: {"id": "0", "embedding": [...]}
    vs_jsonl = "\n".join(
        json.dumps({"id": str(i), "embedding": emb})
        for i, emb in enumerate(embeddings)
    )
    blob_emb = bucket.blob("rag/embeddings.json")
    blob_emb.upload_from_string(vs_jsonl, content_type="application/json")
    gcs_uri = f"gs://{bucket_name}/rag/"
    print(f"Uploaded embeddings → {gcs_uri}embeddings.json")
    return gcs_uri


def create_vector_search_index(gcs_uri: str, dimensions: int):
    from google.cloud import aiplatform

    aiplatform.init(
        project=settings.VERTEX_AI_PROJECT_ID,
        location=settings.VERTEX_AI_REGION,
    )

    print("Creating Vertex AI Vector Search index (this can take 30–60 min)…")
    index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name="sahayak-rag-index",
        contents_delta_uri=gcs_uri,
        dimensions=dimensions,
        approximate_neighbors_count=150,
        distance_measure_type="DOT_PRODUCT_DISTANCE",
    )
    print(f"Index created: {index.resource_name}")

    print("Creating index endpoint…")
    endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name="sahayak-rag-endpoint",
        public_endpoint_enabled=False,
    )
    print(f"Endpoint created: {endpoint.resource_name}")

    print("Deploying index to endpoint (this can take 10–20 min)…")
    endpoint.deploy_index(
        index=index,
        deployed_index_id=DEPLOYED_INDEX_ID,
    )
    print(f"Deployed. Set these in .env:")
    print(f"  VECTOR_SEARCH_INDEX_ENDPOINT_ID={endpoint.resource_name}")
    print(f"  VECTOR_SEARCH_DEPLOYED_INDEX_ID={DEPLOYED_INDEX_ID}")

    # Poll until ready
    while True:
        deployed = endpoint.deployed_indexes
        if any(d.id == DEPLOYED_INDEX_ID for d in deployed):
            break
        print("  Waiting for deployment…")
        time.sleep(30)
    print("Index deployed and ready.")


def main():
    parser = argparse.ArgumentParser(description="Build RAG index for Sahayak AI")
    parser.add_argument("--jsonl", default=settings.RAG_JSONL_PATH)
    parser.add_argument("--upload-gcs", action="store_true")
    parser.add_argument("--create-index", action="store_true")
    args = parser.parse_args()

    jsonl_path = args.jsonl
    if not os.path.exists(jsonl_path):
        sys.exit(f"JSONL not found: {jsonl_path}")

    records = load_jsonl(jsonl_path)
    print(f"Loaded {len(records)} records from {jsonl_path}")

    embeddings = compute_and_cache_embeddings(records, settings.RAG_EMBEDDINGS_CACHE_PATH)
    dimensions = len(embeddings[0]) if embeddings else 768

    if args.upload_gcs or args.create_index:
        if not settings.GCS_BUCKET_NAME or not settings.VERTEX_AI_PROJECT_ID:
            sys.exit("Set GCS_BUCKET_NAME and VERTEX_AI_PROJECT_ID in .env first.")

    gcs_uri = None
    if args.upload_gcs or args.create_index:
        gcs_uri = upload_to_gcs(jsonl_path, embeddings, settings.GCS_BUCKET_NAME)

    if args.create_index:
        create_vector_search_index(gcs_uri, dimensions)

    print("Done.")


if __name__ == "__main__":
    main()
