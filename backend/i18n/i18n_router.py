"""
i18n/i18n_router.py — UI translation endpoint.

POST /i18n/translate
  body: { "lang": "Hindi", "strings": ["Save Profile", "Find eligible schemes →", ...] }
  returns: { "lang": "Hindi", "translations": { "<source>": "<translated>", ... } }

Each (lang, source) translation is cached in Redis forever-ish (30d TTL), so a
given string is translated by Gemini at most once per language. English (and any
unknown source) passes through unchanged.
"""

import sys
import os
import json
import hashlib
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config import settings
from memory.session_store import cache_get, cache_set
from utils.logger import logger

router = APIRouter(prefix="/i18n", tags=["i18n"])

# Languages we treat as "no translation needed"
_PASSTHROUGH = {"english", "en", "", None}

_CACHE_VERSION = "v1"


class TranslateRequest(BaseModel):
    lang: str = Field(..., description="Target language name, e.g. 'Hindi'")
    strings: List[str] = Field(default_factory=list)


def _cache_key(lang: str, source: str) -> str:
    h = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
    return f"i18n:{_CACHE_VERSION}:{lang.lower()}:{h}"


def _gemini_translate_batch(lang: str, sources: List[str]) -> Dict[str, str]:
    """Translate a batch of UI strings in one Gemini call. Returns {source: translated}."""
    if not sources:
        return {}
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig

        vertexai.init(project=settings.VERTEX_AI_PROJECT_ID, location=settings.VERTEX_AI_REGION)
        model = GenerativeModel(settings.FLASH_MODEL)

        numbered = "\n".join(f"{i}\t{s}" for i, s in enumerate(sources))
        prompt = f"""Translate these UI strings for a financial-inclusion app into {lang}.

Return ONLY a JSON object mapping each index (as a string) to its {lang} translation.

Strict rules:
- Keep it natural and short — these are buttons, labels, and headings.
- Preserve any placeholders in curly braces EXACTLY, e.g. {{name}}, {{count}}.
- Preserve emojis and trailing arrows/symbols (→, ↻, ✓) exactly where they appear.
- Do NOT translate the brand name "Sahayak AI".
- Do NOT translate Indian scheme names or acronyms (PM Kisan, UPI, KCC, SCSS, Aadhaar, PAN, GST).
- If a string is already a proper noun or code, return it unchanged.

Strings (index<TAB>text):
{numbered}

Return JSON like {{"0": "...", "1": "..."}} with one entry per index."""

        resp = model.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0, response_mime_type="application/json"),
        )
        data = json.loads(resp.text)
        out: Dict[str, str] = {}
        for i, src in enumerate(sources):
            val = data.get(str(i))
            out[src] = val if isinstance(val, str) and val.strip() else src
        return out
    except Exception as exc:
        logger.error(f"[i18n] batch translate failed ({lang}): {exc}")
        # Fail open: return source strings unchanged so the UI still renders
        return {s: s for s in sources}


@router.post("/translate")
async def translate(req: TranslateRequest):
    lang = (req.lang or "").strip()
    uniq = list(dict.fromkeys(s for s in req.strings if isinstance(s, str) and s.strip()))

    # English / unknown → identity
    if lang.lower() in _PASSTHROUGH:
        return {"lang": lang, "translations": {s: s for s in uniq}}

    translations: Dict[str, str] = {}
    misses: List[str] = []

    # Serve cached translations first
    for s in uniq:
        cached = cache_get(_cache_key(lang, s))
        if cached is not None:
            translations[s] = cached
        else:
            misses.append(s)

    # Translate cache misses in one batch, then cache them
    if misses:
        fresh = _gemini_translate_batch(lang, misses)
        for src, tr in fresh.items():
            translations[src] = tr
            cache_set(_cache_key(lang, src), tr)

    logger.info(f"[i18n] {lang}: {len(uniq)} strings ({len(misses)} new)")
    return {"lang": lang, "translations": translations}


@router.get("/languages")
async def languages():
    """Languages offered in the UI switcher."""
    return {
        "languages": [
            "English", "Hindi", "Bengali", "Telugu", "Marathi", "Tamil",
            "Gujarati", "Kannada", "Malayalam", "Punjabi", "Odia", "Urdu",
        ]
    }
