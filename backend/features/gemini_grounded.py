"""
features/gemini_grounded.py — Gemini (Vertex AI) with live Google Search grounding.

This is the single source of "real, current, cited" data for the scheme,
document, and complaint features. It calls Gemini with the Google Search
grounding tool so answers reflect current government rules — not the model's
training snapshot — and returns the web sources Gemini actually used.

No extra API keys: grounding rides on the same Vertex AI ADC the rest of the
backend already uses. If grounding is unavailable for any reason, it degrades
gracefully to an ungrounded call (still real model reasoning, just no live web).

Usage:
    from features.gemini_grounded import generate_grounded

    result = generate_grounded(
        "List current eligibility for PM Kisan in 2026 ...",
        temperature=0.2,
        want_json=True,
    )
    result["json"]      # parsed dict/list (when want_json and parse succeeds)
    result["text"]      # raw model text
    result["sources"]   # [{"title": ..., "uri": ...}, ...] from grounding
    result["grounded"]  # True if Google Search grounding was actually applied
"""

import json
import sys
import os
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from utils.logger import logger

# Vertex AI is initialised once (idempotent).
_initialised = False


def _ensure_init() -> None:
    global _initialised
    if not _initialised:
        import vertexai
        vertexai.init(
            project=settings.VERTEX_AI_PROJECT_ID,
            location=settings.VERTEX_AI_REGION,
        )
        _initialised = True


def _build_search_tool():
    """
    Return a Google Search grounding Tool, tolerant of SDK version differences.

    Newer Vertex SDKs expose `grounding.GoogleSearch()`; older ones use
    `grounding.GoogleSearchRetrieval()`. Try both; return None if neither works
    (caller then runs ungrounded).
    """
    try:
        from vertexai.generative_models import Tool, grounding
    except Exception:
        return None

    # Newer API: GoogleSearch (Gemini 2.x)
    try:
        return Tool.from_google_search_retrieval(grounding.GoogleSearch())
    except Exception:
        pass
    # Older API: GoogleSearchRetrieval
    try:
        return Tool.from_google_search_retrieval(grounding.GoogleSearchRetrieval())
    except Exception:
        pass
    return None


def _extract_sources(response) -> List[Dict[str, str]]:
    """Pull the real web sources Gemini grounded on out of grounding_metadata."""
    sources: List[Dict[str, str]] = []
    try:
        cand = response.candidates[0]
        gm = getattr(cand, "grounding_metadata", None)
        if not gm:
            return sources
        chunks = getattr(gm, "grounding_chunks", None) or []
        for ch in chunks:
            web = getattr(ch, "web", None)
            if web is None:
                continue
            uri = getattr(web, "uri", "") or ""
            title = getattr(web, "title", "") or uri
            if uri:
                sources.append({"title": title, "uri": uri})
    except Exception:
        pass
    # De-dupe by uri, preserve order
    seen = set()
    deduped = []
    for s in sources:
        if s["uri"] not in seen:
            seen.add(s["uri"])
            deduped.append(s)
    return deduped


def _strip_to_json(text: str) -> str:
    """Strip markdown fences and isolate the JSON body."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip()
    # If there's leading prose before the JSON, grab from first { or [
    for opener, closer in (("{", "}"), ("[", "]")):
        start = t.find(opener)
        end = t.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidate = t[start : end + 1]
            try:
                json.loads(candidate)
                return candidate
            except Exception:
                continue
    return t


def generate_grounded(
    prompt: str,
    temperature: float = 0.2,
    want_json: bool = False,
    model_name: Optional[str] = None,
    use_grounding: bool = True,
) -> Dict[str, Any]:
    """
    Generate content with Gemini, grounded on live Google Search.

    Returns a dict:
      {
        "text":     str,                 # model text
        "json":     Any | None,          # parsed JSON when want_json succeeds
        "sources":  [{"title","uri"}],   # live web sources used for grounding
        "grounded": bool,                # was grounding actually applied
        "error":    str | None,          # set if the call failed entirely
      }
    """
    result: Dict[str, Any] = {
        "text": "",
        "json": None,
        "sources": [],
        "grounded": False,
        "error": None,
    }

    try:
        _ensure_init()
        from vertexai.generative_models import GenerativeModel, GenerationConfig

        model = GenerativeModel(model_name or settings.FLASH_MODEL)
        gen_config = GenerationConfig(temperature=temperature)

        tools = None
        if use_grounding:
            tool = _build_search_tool()
            if tool is not None:
                tools = [tool]

        try:
            response = model.generate_content(
                prompt,
                generation_config=gen_config,
                tools=tools,
            )
            result["grounded"] = tools is not None
        except Exception as grounding_exc:
            # Grounding may be unavailable in some regions/projects — retry plain.
            logger.warning(f"[grounded] grounding call failed, retrying ungrounded: {grounding_exc}")
            response = model.generate_content(prompt, generation_config=gen_config)
            result["grounded"] = False

        text = (response.text or "").strip()
        result["text"] = text
        result["sources"] = _extract_sources(response)

        if want_json and text:
            try:
                result["json"] = json.loads(_strip_to_json(text))
            except Exception as parse_exc:
                logger.warning(f"[grounded] JSON parse failed: {parse_exc}")
                result["json"] = None

    except Exception as exc:
        logger.error(f"[grounded] generation failed: {exc}")
        result["error"] = str(exc)

    return result
