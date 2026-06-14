"""
memory/session_store.py — Redis read/write helpers for session state.

All Redis interactions for the graph go through this module.
Key naming conventions:
  session:{session_id}       → JSON blob of full AgentState  (TTL 24h)
  profile:{session_id}       → JSON blob of user_profile     (TTL 7d)
  feedback:{session_id}      → Redis List of feedback records
  all_feedback               → Redis List of all feedback records (for batch analysis)
"""

import json
import redis
from typing import Any, Dict, Optional
from config import settings


# ─── Connection pool (lazy singleton) ────────────────────────────────────────
_client: Optional[redis.Redis] = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _client


# ─── Session helpers ──────────────────────────────────────────────────────────

def load_session(session_id: str) -> Dict[str, Any]:
    """
    Returns the full session dict from Redis.
    Returns an empty dict if the session does not exist yet.
    """
    client = _get_client()
    raw = client.get(f"session:{session_id}")
    if raw is None:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def save_session(session_id: str, state: Dict[str, Any]) -> None:
    """
    Saves the full AgentState to Redis with a 24-hour TTL.
    The state dict is serialised to JSON.
    """
    client = _get_client()
    client.setex(
        f"session:{session_id}",
        settings.SESSION_TTL_SECONDS,
        json.dumps(state, default=str),
    )


# ─── Profile helpers ──────────────────────────────────────────────────────────

def load_profile(session_id: str) -> Dict[str, Any]:
    """
    Returns the user_profile sub-dict from Redis.
    Profile TTL is 7 days — it outlives the session.
    Returns an empty dict if no profile exists.
    """
    client = _get_client()
    raw = client.get(f"profile:{session_id}")
    if raw is None:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def save_profile(session_id: str, profile: Dict[str, Any]) -> None:
    """
    Saves only the user_profile sub-dict with a 7-day TTL.
    Use this whenever context_agent updates the profile.
    """
    client = _get_client()
    client.setex(
        f"profile:{session_id}",
        settings.PROFILE_TTL_SECONDS,
        json.dumps(profile, default=str),
    )


# ─── Feedback helpers ─────────────────────────────────────────────────────────

def append_feedback(session_id: str, record: Dict[str, Any]) -> None:
    """
    Appends a feedback record to two Redis lists:
      - feedback:{session_id}  (per-session list)
      - all_feedback           (global list for batch analysis)
    """
    client = _get_client()
    serialised = json.dumps(record, default=str)
    client.rpush(f"feedback:{session_id}", serialised)
    client.rpush("all_feedback", serialised)


def get_feedback(session_id: str) -> list:
    """
    Returns all feedback records for this session as a list of dicts.
    """
    client = _get_client()
    raw_list = client.lrange(f"feedback:{session_id}", 0, -1)
    result = []
    for raw in raw_list:
        try:
            result.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return result


def update_feedback_rating(session_id: str, turn_number: int, rating: str) -> bool:
    """
    Finds the feedback record matching turn_number for this session and
    updates its rating field. Returns True if a record was found and updated.
    """
    client = _get_client()
    raw_list = client.lrange(f"feedback:{session_id}", 0, -1)
    for idx, raw in enumerate(raw_list):
        try:
            record = json.loads(raw)
            if record.get("turn_number") == turn_number:
                record["rating"] = rating
                client.lset(f"feedback:{session_id}", idx, json.dumps(record, default=str))
                return True
        except (json.JSONDecodeError, redis.ResponseError):
            pass
    return False


def health_check() -> bool:
    """Ping Redis. Returns True if reachable."""
    try:
        return _get_client().ping()
    except Exception:
        return False


# ─── Generic key/value cache (used by the i18n translation cache) ─────────────

def cache_get(key: str) -> Optional[str]:
    try:
        return _get_client().get(key)
    except Exception:
        return None


def cache_set(key: str, value: str, ttl: int = 2_592_000) -> None:
    """Cache a string value (default TTL 30 days)."""
    try:
        _get_client().setex(key, ttl, value)
    except Exception:
        pass


# ─── Interaction event log (adaptive data loop) ───────────────────────────────
# Raw, low-PII interaction events are queued here, then harvested by the
# adaptive dataset builder into an anonymised staging JSONL.

def log_interaction_event(event: Dict[str, Any]) -> None:
    try:
        client = _get_client()
        client.rpush("interactions:raw", json.dumps(event, default=str))
        client.ltrim("interactions:raw", -5000, -1)  # cap the queue
    except Exception:
        pass


def peek_interaction_events() -> list:
    """Return all currently-queued raw events without removing them."""
    try:
        raw = _get_client().lrange("interactions:raw", 0, -1)
    except Exception:
        return []
    out = []
    for r in raw:
        try:
            out.append(json.loads(r))
        except json.JSONDecodeError:
            pass
    return out


def drop_interaction_events(n: int) -> None:
    """Remove the first n events (those already harvested)."""
    if n <= 0:
        return
    try:
        _get_client().ltrim("interactions:raw", n, -1)
    except Exception:
        pass


def count_interaction_events() -> int:
    try:
        return int(_get_client().llen("interactions:raw"))
    except Exception:
        return 0


# ─── User profile (by profile_id, separate from session) ─────────────────────

def save_user_profile(profile_id: str, profile: Dict[str, Any]) -> None:
    client = _get_client()
    client.setex(
        f"userprofile:{profile_id}",
        settings.PROFILE_TTL_SECONDS,
        json.dumps(profile, default=str),
    )


def load_user_profile(profile_id: str) -> Dict[str, Any]:
    client = _get_client()
    raw = client.get(f"userprofile:{profile_id}")
    if raw is None:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def list_user_profiles() -> list:
    """Return all stored user profile IDs (for the UI profile selector)."""
    client = _get_client()
    keys = client.keys("userprofile:*")
    profiles = []
    for key in keys:
        raw = client.get(key)
        if raw:
            try:
                p = json.loads(raw)
                profiles.append(p)
            except json.JSONDecodeError:
                pass
    return profiles


# ─── Knowledge graph helpers ──────────────────────────────────────────────────

def save_knowledge_graph(profile_id: str, kg: Dict[str, Any]) -> None:
    client = _get_client()
    client.setex(
        f"kg:{profile_id}",
        settings.PROFILE_TTL_SECONDS,
        json.dumps(kg, default=str),
    )


def load_knowledge_graph(profile_id: str) -> Dict[str, Any]:
    client = _get_client()
    raw = client.get(f"kg:{profile_id}")
    if raw is None:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# ─── Knowledge graph history (for the Literacy Progress Dashboard) ─────────────

def append_kg_snapshot(profile_id: str, kg: Dict[str, Any], trigger: str = "") -> None:
    """
    Record a lightweight point-in-time snapshot of the user's scores so we can
    chart real literacy progress over time. Stored as a capped Redis list under
    kg_history:{profile_id}. Only scores are kept — not the full KG — to stay small.
    """
    from datetime import datetime, timezone

    client = _get_client()
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_score": kg.get("overall_score", 0.0),
        "domain_scores": {
            d: data.get("score", 0.0) for d, data in (kg.get("domains", {}) or {}).items()
        },
        "literacy_level": kg.get("literacy_level", "beginner"),
        "chat_interactions": kg.get("chat_interactions", 0),
        "trigger": trigger,
    }
    key = f"kg_history:{profile_id}"
    client.rpush(key, json.dumps(snapshot, default=str))
    client.ltrim(key, -50, -1)  # keep last 50 snapshots
    client.expire(key, settings.PROFILE_TTL_SECONDS)


def get_kg_history(profile_id: str) -> list:
    """Return the list of stored KG snapshots (oldest first)."""
    client = _get_client()
    raw_list = client.lrange(f"kg_history:{profile_id}", 0, -1)
    out = []
    for raw in raw_list:
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return out
