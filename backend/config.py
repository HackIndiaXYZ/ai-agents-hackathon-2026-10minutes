"""
config.py — Centralised settings for the entire backend.

All environment variables, model names, and tunable thresholds live here.
No agent should hard-code any of these values — always import from this module.

Authentication: all Google/GCP calls use Application Default Credentials (ADC).
No API keys are required for Gemini or embeddings — run once:
    gcloud auth application-default login
    gcloud config set project YOUR_PROJECT_ID
"""

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # ─── Google Search (optional — web search is skipped when these are empty) ─
    GOOGLE_SEARCH_API_KEY: str = ""
    GOOGLE_SEARCH_ENGINE_ID: str = ""

    # ─── Infrastructure ───────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ─── GCP / Vertex AI ─────────────────────────────────────────────────────
    # Required: the GCP project where Vertex AI APIs are enabled.
    VERTEX_AI_PROJECT_ID: str
    VERTEX_AI_REGION: str = "us-central1"
    # Optional: GCS bucket for storing the dataset and embeddings in GCP.
    GCS_BUCKET_NAME: str = ""

    # ─── Model routing (Vertex AI model names) ────────────────────────────────
    # gemini-2.5-pro  → complex reasoning agents (supervisor, context, reasoning)
    # gemini-2.5-flash → fast lightweight agents (language, clarification, …)
    PRO_MODEL: str = "gemini-2.5-pro"
    FLASH_MODEL: str = "gemini-2.5-flash"

    # ─── Embeddings ───────────────────────────────────────────────────────────
    # text-multilingual-embedding-002 supports 100+ languages including all
    # Indian languages — no separate API key, uses ADC.
    EMBEDDING_MODEL: str = "text-multilingual-embedding-002"

    # ─── RAG ─────────────────────────────────────────────────────────────────
    RAG_JSONL_PATH: str = "data/financial_fraud_qa.jsonl"
    RAG_EMBEDDINGS_CACHE_PATH: str = "data/rag_embeddings_cache.json"
    # Vertex AI Vector Search — leave empty to use local cosine-similarity fallback.
    # Populate after running: python scripts/build_rag_index.py --create-index
    VECTOR_SEARCH_INDEX_ENDPOINT_ID: str = ""
    VECTOR_SEARCH_DEPLOYED_INDEX_ID: str = ""
    RAG_TOP_K: int = 5

    # ─── Onboarding ───────────────────────────────────────────────────────────
    ONBOARDING_MAX_QUESTIONS: int = 15
    ONBOARDING_MIN_QUESTIONS: int = 12

    # ─── Thresholds ───────────────────────────────────────────────────────────
    CLARIFICATION_CONFIDENCE_THRESHOLD: float = 0.70

    WEB_SEARCH_TRIGGER_TYPES: List[str] = [
        "market_price",
        "deadline",
        "news",
        "recent_update",
    ]

    MAX_CLARIFICATION_TURNS: int = 2
    MARKET_PRICE_MAX_AGE_DAYS: int = 7
    DEADLINE_MAX_AGE_DAYS: int = 30
    MAX_SUB_QUERIES: int = 4

    # ─── BGE-M3 / Qdrant RAG pipeline ────────────────────────────────────────
    # Local Qdrant instance (docker run -p 6333:6333 qdrant/qdrant)
    QDRANT_URL:          str = "http://localhost:6333"
    QDRANT_COLLECTION:   str = "sahayak_fraud_qa"
    BGE_MODEL_NAME:      str = "BAAI/bge-m3"
    BGE_RERANKER_NAME:   str = "BAAI/bge-reranker-v2-m3"

    # ─── Adaptive data loop ──────────────────────────────────────────────────
    # Anonymised, AI-formatted user interactions are appended here (staging).
    # Promote into Qdrant with: python rag/ingest_bge.py --path <this file>
    ADAPTIVE_DATASET_PATH: str = "data/adaptive_dataset.jsonl"

    # ─── Session / profile TTLs (seconds) ────────────────────────────────────
    SESSION_TTL_SECONDS: int = 86_400        # 24 hours
    PROFILE_TTL_SECONDS: int = 604_800       # 7 days

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# ─── Singleton — import this everywhere ──────────────────────────────────────
settings = Settings()
