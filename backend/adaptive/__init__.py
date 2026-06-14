"""
adaptive/ — Adaptive data loop.

Captures real user interactions (chat questions answered, document checklists
generated, complaint guides produced, scheme lookups), then summarises and
ANONYMISES them into the same JSONL schema as the source fraud-QA dataset and
appends them to a staging file. A human promotes the staging file into Qdrant
when ready — user data never enters the live RAG index automatically.

  logger.py          → log_interaction(): queue a raw, low-PII event in Redis
  dataset_builder.py → harvest(): Gemini-anonymise queued events → staging JSONL
  adaptive_router.py → /adaptive/* endpoints
"""
