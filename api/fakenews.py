from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
import json
import time

from rss_collector import collect_latest_factchecks

FAKE_NEWS_CACHE_TTL_SECONDS = 600
FAKE_NEWS_MAX_LIMIT = 60
FAKE_NEWS_DEFAULT_LIMIT = 20
FAKE_NEWS_RECENT_DAYS = 7

_fake_news_cache = {
    "timestamp": 0.0,
    "items": [],
}


def _parse_feed_datetime(raw_value):
    if not raw_value:
        return None
    try:
        dt = parsedate_to_datetime(raw_value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _format_date_label(dt_utc):
    if not dt_utc:
        return "Data non disponibile"
    return dt_utc.strftime("%d %b %Y")


def _classify_type(text):
    haystack = (text or "").lower()
    if any(word in haystack for word in ("deepfake", "ai generated", "voice clone", "synthetic")):
        return "deepfake"
    if any(word in haystack for word in ("old video", "old photo", "ricicl", "years old", "201", "200")):
        return "old"
    if any(word in haystack for word in ("percent", "%", "statistic", "dato", "numer")):
        return "numbers"
    if any(word in haystack for word in ("quote", "citazione")):
        return "quote"
    return "misinfo"


def _icon_for_type(item_type):
    if item_type == "deepfake":
        return "🤖", "icon-deepfake"
    if item_type == "old":
        return "📅", "icon-old"
    if item_type == "numbers":
        return "📊", "icon-numbers"
    if item_type == "quote":
        return "💬", "icon-quote"
    return "📡", "icon-misinfo"


def _normalize_article(article, idx):
    title = (article.get("title") or "").strip()
    summary = (article.get("summary") or "").strip()
    source = article.get("source") or "Fonte RSS"
    link = article.get("link") or ""
    credibility = int(article.get("credibility") or 70)
    published_raw = article.get("published") or ""
    published_dt = _parse_feed_datetime(published_raw)
    item_type = _classify_type(f"{title} {summary}")
    icon, icon_class = _icon_for_type(item_type)

    signals = [
        {"color": "amber", "text": "Caso individuato tramite monitoraggio RSS multi-fonte."},
        {"color": "blue", "text": f"Fonte: {source} (credibilita {credibility}/100)."},
    ]
    if link:
        signals.append({"color": "red", "text": "Verifica sempre il contenuto completo prima di condividere."})

    return {
        "id": idx,
        "type": item_type,
        "icon": icon,
        "iconClass": icon_class,
        "date": _format_date_label(published_dt),
        "publishedAt": published_dt.isoformat() if published_dt else "",
        "virality": f"Fonte {source}",
        "claim": title or "Titolo non disponibile",
        "claimHighlight": "",
        "verdictShort": "SEGNALAZIONE RECENTE — Richiede verifica",
        "summaryShort": summary[:280] if summary else "Apri la fonte per leggere il contenuto completo.",
        "signals": signals,
        "sources": [
            {"icon": "↗", "name": source, "action": "apri articolo originale"},
        ],
        "verdictFull": (
            "Questo elemento arriva dal feed RSS in tempo reale e contiene termini tipici di "
            "disinformazione/fact-check. Non e un verdetto automatico finale: usa la pagina di verifica "
            "per analisi completa multi-fonte."
        ),
        "link": link,
        "source": source,
        "credibility": credibility,
    }


def _collect_live_fake_news(limit):
    raw_articles = collect_latest_factchecks(
        max_per_feed=25,
        max_results=max(limit * 2, 30),
    )

    filtered = []
    seen = set()
    for article in raw_articles:
        title = (article.get("title") or "").strip()
        link = (article.get("link") or "").strip()
        key = link or title.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        filtered.append(article)

    normalized = [_normalize_article(article, idx) for idx, article in enumerate(filtered, 1)]

    cutoff = datetime.now(timezone.utc) - timedelta(days=FAKE_NEWS_RECENT_DAYS)
    fresh_only = []
    for item in normalized:
        published_at = item.get("publishedAt")
        try:
            dt = datetime.fromisoformat(published_at) if published_at else None
        except Exception:
            dt = None
        if dt and dt >= cutoff:
            fresh_only.append(item)

    if fresh_only:
        normalized = fresh_only

    normalized.sort(
        key=lambda item: item.get("publishedAt") or "1970-01-01T00:00:00+00:00",
        reverse=True,
    )
    return normalized[:limit]


def get_fake_news_items(limit, force_refresh=False):
    now = time.time()
    cache_age = now - _fake_news_cache["timestamp"]
    cache_has_enough = len(_fake_news_cache["items"]) >= limit
    cache_valid = cache_age <= FAKE_NEWS_CACHE_TTL_SECONDS

    if not force_refresh and cache_valid and cache_has_enough:
        return _fake_news_cache["items"][:limit], True

    items = _collect_live_fake_news(limit)
    _fake_news_cache["items"] = items
    _fake_news_cache["timestamp"] = now
    return items, False


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query or "")

        limit = FAKE_NEWS_DEFAULT_LIMIT
        refresh = False

        if "limit" in query and query["limit"]:
            try:
                requested = int(query["limit"][0])
                limit = max(1, min(requested, FAKE_NEWS_MAX_LIMIT))
            except (TypeError, ValueError):
                pass

        if "refresh" in query and query["refresh"]:
            refresh = query["refresh"][0].strip().lower() in {"1", "true", "yes"}

        try:
            items, cache_hit = get_fake_news_items(limit=limit, force_refresh=refresh)
            self._send_json(200, {
                "ok": True,
                "items": items,
                "count": len(items),
                "cache_hit": cache_hit,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})