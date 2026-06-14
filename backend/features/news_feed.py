"""
features/news_feed.py — Live fraud-alert feed from Google News RSS.

Google News exposes a public RSS endpoint that needs no API key and returns
real, current headlines. We query it for financial-fraud news scoped to the
user's state, parse the RSS, then (optionally) use Gemini to tag each item with
a scam category + a one-line prevention tip.

Nothing here is hardcoded — every alert is a live news item with a real source
link and publish date. If Gemini enrichment fails, the raw real headlines are
still returned.
"""

import sys
import os
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any
from xml.etree import ElementTree as ET
from urllib.parse import quote_plus

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import httpx

from utils.logger import logger

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"

# Core fraud query; state is appended when provided. `when:30d` keeps it recent.
_BASE_QUERY = (
    '("UPI fraud" OR "online scam" OR "cyber fraud" OR "financial fraud" OR '
    '"digital arrest" OR "OTP fraud" OR "loan app scam") India when:30d'
)


def _clean_title(raw_title: str) -> Dict[str, str]:
    """Google News titles are 'Headline - Publisher'. Split them."""
    title = html.unescape(raw_title or "").strip()
    publisher = ""
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        if len(parts) == 2 and len(parts[1]) < 60:
            title, publisher = parts[0].strip(), parts[1].strip()
    return {"title": title, "publisher": publisher}


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _parse_pubdate(date_str: str) -> Dict[str, str]:
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days_ago = (datetime.now(timezone.utc) - dt).days
        return {
            "iso": dt.isoformat(),
            "relative": "today" if days_ago <= 0 else f"{days_ago}d ago",
        }
    except Exception:
        return {"iso": "", "relative": ""}


def fetch_raw_alerts(state: str = "", limit: int = 12) -> List[Dict[str, Any]]:
    """Fetch and parse live fraud-news items from Google News RSS."""
    query = _BASE_QUERY
    if state and state.lower() not in ("india", "other", ""):
        # Inject the state name so results skew regional.
        query = query.replace("India when:30d", f'"{state}" India when:30d')

    url = _GOOGLE_NEWS_RSS.format(q=quote_plus(query))

    try:
        resp = httpx.get(
            url,
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0 (SahayakAI FraudAlertBot)"},
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.error(f"[news_feed] RSS fetch failed: {exc}")
        return []

    items: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(resp.content)
        for item in root.iter("item"):
            title_raw = item.findtext("title", "")
            link = item.findtext("link", "")
            pub = item.findtext("pubDate", "")
            desc = item.findtext("description", "")
            source_el = item.find("source")
            source_name = source_el.text if source_el is not None else ""

            parsed_title = _clean_title(title_raw)
            date_info = _parse_pubdate(pub)

            items.append({
                "title": parsed_title["title"],
                "publisher": source_name or parsed_title["publisher"],
                "link": link,
                "snippet": _strip_html(desc)[:240],
                "published_iso": date_info["iso"],
                "published_relative": date_info["relative"],
            })
            if len(items) >= limit:
                break
    except Exception as exc:
        logger.error(f"[news_feed] RSS parse failed: {exc}")
        return []

    return items


def _enrich_with_gemini(items: List[Dict[str, Any]], state: str, language: str = "English") -> List[Dict[str, Any]]:
    """
    Single batched Gemini pass: tag each real headline with a scam category and
    a short prevention tip. Falls back to the raw items if Gemini is unavailable.
    """
    if not items:
        return items

    try:
        from features.gemini_grounded import generate_grounded

        headlines = "\n".join(f"{i+1}. {it['title']}" for i, it in enumerate(items))
        prompt = f"""You are a fraud-awareness analyst for rural India. Below are real news
headlines about financial fraud{f' relevant to {state}' if state else ''}.

For EACH numbered headline, output a JSON object with:
  - "index": the headline number
  - "scam_type": a short category in {language} (e.g. "UPI fraud", "Digital arrest", "Loan app scam", "OTP theft", "KYC fraud", "Investment scam")
  - "who_is_targeted": one short phrase in {language} on who is at risk
  - "prevention_tip": ONE practical sentence in {language} on how to stay safe

Headlines:
{headlines}

Return ONLY a JSON array of these objects, no prose."""

        result = generate_grounded(prompt, temperature=0.1, want_json=True, use_grounding=False)
        enrich = result.get("json")
        if isinstance(enrich, list):
            by_index = {}
            for e in enrich:
                try:
                    by_index[int(e.get("index"))] = e
                except Exception:
                    continue
            for i, it in enumerate(items, 1):
                e = by_index.get(i, {})
                it["scam_type"] = e.get("scam_type", "Financial fraud")
                it["who_is_targeted"] = e.get("who_is_targeted", "")
                it["prevention_tip"] = e.get("prevention_tip", "")
        return items
    except Exception as exc:
        logger.warning(f"[news_feed] enrichment skipped: {exc}")
        return items


def get_fraud_alerts(state: str = "", limit: int = 10, enrich: bool = True, language: str = "English") -> Dict[str, Any]:
    """
    Public entry point: live fraud alerts for a state, optionally AI-enriched.

    Returns {state, count, alerts, helplines, source}.
    """
    items = fetch_raw_alerts(state=state, limit=limit)
    if enrich and items:
        items = _enrich_with_gemini(items, state, language=language)

    return {
        "state": state or "All India",
        "count": len(items),
        "alerts": items,
        # Real, official national helplines (stable public facts, not fabricated data)
        "helplines": [
            {"label": "Cyber Crime Helpline", "value": "1930"},
            {"label": "Report online", "value": "https://cybercrime.gov.in"},
            {"label": "UIDAI / Aadhaar", "value": "1947"},
        ],
        "source": "Google News RSS (live)",
    }
