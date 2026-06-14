"""
rag/embedder.py — Multilingual text embeddings via Vertex AI.

Uses text-multilingual-embedding-002 which supports 100+ languages,
making it suitable for all Indian languages in the dataset.

Authentication: Application Default Credentials (ADC).
Run once before starting the app:
    gcloud auth application-default login
    gcloud config set project YOUR_PROJECT_ID
"""

import sys
import os
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings


def _get_model():
    import vertexai
    from vertexai.language_models import TextEmbeddingModel

    vertexai.init(
        project=settings.VERTEX_AI_PROJECT_ID,
        location=settings.VERTEX_AI_REGION,
    )
    return TextEmbeddingModel.from_pretrained(settings.EMBEDDING_MODEL)


_model = None


def _model_instance():
    global _model
    if _model is None:
        _model = _get_model()
    return _model


def embed_documents(texts: List[str]) -> List[List[float]]:
    """Embed a batch of document chunks (indexing time, RETRIEVAL_DOCUMENT task)."""
    if not texts:
        return []
    from vertexai.language_models import TextEmbeddingInput

    model = _model_instance()
    inputs = [TextEmbeddingInput(text=t, task_type="RETRIEVAL_DOCUMENT") for t in texts]
    results = model.get_embeddings(inputs)
    return [r.values for r in results]


def embed_query(text: str) -> List[float]:
    """Embed a single user query (retrieval time, RETRIEVAL_QUERY task)."""
    from vertexai.language_models import TextEmbeddingInput

    model = _model_instance()
    inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_QUERY")]
    results = model.get_embeddings(inputs)
    return results[0].values if results else []
