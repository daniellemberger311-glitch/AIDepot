"""Alpha-Vantage-Fetcher: Technische Indikatoren und News-Sentiment.

Free-Tier-Limits (BEIDE müssen eingehalten werden!):
  - 25 Calls/Tag pro Key → mit 2 Keys effektiv 50 Calls/Tag
  - 5 Calls/Min → 13-Sekunden-Mindestabstand (prozessglobal)

Key-Rotation:
  Key 1 (ALPHA_VANTAGE_API_KEY) wird zuerst verwendet.
  Sobald Key 1 erschöpft ist, übernimmt Key 2 (ALPHA_VANTAGE_API_KEY_2).
  Beide Quoten werden separat in der DB verfolgt.
"""
import time
import logging
import requests
from datetime import datetime
from sqlalchemy.orm import Session

from backend.config import settings
from backend.fetchers.base import BaseFetcher, with_retry
from backend.models import Configuration

logger = logging.getLogger(__name__)

RSI_TTL  = 4 * 3600
MACD_TTL = 4 * 3600
NEWS_TTL = 2 * 3600

# Quota-Tracking-Konfiguration pro Key-Slot
_KEY_SLOTS = [
    {
        "key_attr":    "alpha_vantage_api_key",
        "quota_key":   "av_calls_today",
        "quota_reset": "av_quota_date",
    },
    {
        "key_attr":    "alpha_vantage_api_key_2",
        "quota_key":   "av_calls_today_2",
        "quota_reset": "av_quota_date_2",
    },
]

# 5 Calls/Minute = 1 Call alle 12 Sekunden → 13 s Puffer (prozessglobal)
_AV_MIN_INTERVAL: float = 13.0
_last_av_call_ts: float = 0.0


def _enforce_rate_limit() -> None:
    global _last_av_call_ts
    elapsed = time.monotonic() - _last_av_call_ts
    if elapsed < _AV_MIN_INTERVAL:
        wait = _AV_MIN_INTERVAL - elapsed
        logger.debug("Alpha Vantage Rate-Limit: warte %.1f s", wait)
        time.sleep(wait)
    _last_av_call_ts = time.monotonic()


class AlphaVantageFetcher(BaseFetcher):
    SOURCE_NAME = "alphavantage"
    BASE_URL    = "https://www.alphavantage.co/query"

    # ── Quota-Verwaltung pro Key-Slot ─────────────────────────────────────────

    def _quota_remaining(self, slot: dict) -> int:
        today     = datetime.utcnow().strftime("%Y-%m-%d")
        date_row  = self.db.get(Configuration, slot["quota_reset"])
        count_row = self.db.get(Configuration, slot["quota_key"])

        if not date_row or date_row.value != today:
            for k, v in [(slot["quota_reset"], today), (slot["quota_key"], "0")]:
                row = self.db.get(Configuration, k)
                if row:
                    row.value = v
                else:
                    self.db.add(Configuration(key=k, value=v))
            self.db.commit()
            return settings.alpha_vantage_calls_per_day

        used = int(count_row.value) if count_row else 0
        return max(0, settings.alpha_vantage_calls_per_day - used)

    def _consume_quota(self, slot: dict) -> None:
        row = self.db.get(Configuration, slot["quota_key"])
        if row:
            row.value = str(int(row.value) + 1)
            self.db.commit()

    def _active_slot(self) -> dict | None:
        """Ersten Key-Slot mit verbleibender Quota zurückgeben."""
        for slot in _KEY_SLOTS:
            api_key = getattr(settings, slot["key_attr"], "")
            if not api_key:
                continue
            if self._quota_remaining(slot) > 0:
                return slot
        return None

    # ── Interner API-Call ──────────────────────────────────────────────────────

    def _get(self, params: dict) -> dict:
        slot = self._active_slot()
        if slot is None:
            logger.warning(
                "Alpha Vantage: alle Keys erschöpft (je %d Calls/Tag)",
                settings.alpha_vantage_calls_per_day,
            )
            return {}

        _enforce_rate_limit()
        params["apikey"] = getattr(settings, slot["key_attr"])
        resp = requests.get(self.BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        self._consume_quota(slot)

        data = resp.json()
        if "Note" in data or "Information" in data:
            msg = data.get("Note") or data.get("Information", "")
            logger.warning("Alpha Vantage Rate-Limit-Antwort (Slot %s): %s",
                           slot["key_attr"], msg[:80])
            return {}
        return data

    # ── RSI ───────────────────────────────────────────────────────────────────

    def get_rsi(self, ticker: str, interval: str = "daily", period: int = 14) -> dict:
        """RSI-Wert für einen Ticker. Gecacht 4 Stunden. Quota-geschützt."""
        key    = self._make_key(f"rsi_{interval}_{period}", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached
        data = self._fetch_rsi(ticker, interval, period)
        if data:
            self._cache_set(key, data, RSI_TTL)
        return data

    @with_retry(max_attempts=2)
    def _fetch_rsi(self, ticker: str, interval: str, period: int) -> dict:
        r = self._get({
            "function":    "RSI",
            "symbol":      ticker,
            "interval":    interval,
            "time_period": period,
            "series_type": "close",
        })
        meta = r.get("Technical Analysis: RSI", {})
        if not meta:
            return {}
        latest = sorted(meta.keys())[-1]
        return {"date": latest, "rsi": float(meta[latest]["RSI"])}

    # ── MACD (nur Premium) ────────────────────────────────────────────────────
    # AV MACD ist Premium (2024/2025). Scoring-Engine nutzt ta-Bibliothek.
    # Bleibt als optionaler Validierungs-Call für künftige Premium-Keys.

    def get_macd(self, ticker: str, interval: str = "daily") -> dict:
        key    = self._make_key(f"macd_{interval}", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached
        data = self._fetch_macd(ticker, interval)
        if data:
            self._cache_set(key, data, MACD_TTL)
        return data

    @with_retry(max_attempts=2)
    def _fetch_macd(self, ticker: str, interval: str) -> dict:
        r = self._get({
            "function":    "MACD",
            "symbol":      ticker,
            "interval":    interval,
            "series_type": "close",
        })
        meta = r.get("Technical Analysis: MACD", {})
        if not meta:
            return {}
        latest = sorted(meta.keys())[-1]
        row = meta[latest]
        return {
            "date":      latest,
            "macd":      float(row["MACD"]),
            "signal":    float(row["MACD_Signal"]),
            "histogram": float(row["MACD_Hist"]),
        }

    # ── News-Sentiment (Fallback zu Finnhub/Marketaux) ────────────────────────

    def get_news_sentiment(self, ticker: str) -> dict:
        """AV News-Sentiment als Fallback. Gecacht 2 Stunden."""
        key    = self._make_key("news_sentiment", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached
        data = self._fetch_news(ticker)
        if data:
            self._cache_set(key, data, NEWS_TTL)
        return data

    @with_retry(max_attempts=2)
    def _fetch_news(self, ticker: str) -> dict:
        default = {"sentiment_score": 0.0, "articles_count": 0}
        r = self._get({"function": "NEWS_SENTIMENT", "tickers": ticker, "limit": "10"})
        feed = r.get("feed", [])
        if not feed:
            return default
        scores = []
        for article in feed:
            for ts in article.get("ticker_sentiment", []):
                if ts.get("ticker") == ticker:
                    try:
                        scores.append(float(ts.get("ticker_sentiment_score", 0)))
                    except (ValueError, TypeError):
                        pass
        if not scores:
            return default
        return {
            "sentiment_score": round(sum(scores) / len(scores), 4),
            "articles_count":  len(scores),
        }

    # ── Quota-Status (für /api/config/status) ────────────────────────────────

    def quota_status(self) -> dict:
        """Quota-Status beider Keys zurückgeben."""
        keys_info = []
        total_remaining = 0
        for slot in _KEY_SLOTS:
            api_key = getattr(settings, slot["key_attr"], "")
            if not api_key:
                continue
            remaining = self._quota_remaining(slot)
            total_remaining += remaining
            keys_info.append({"slot": slot["key_attr"], "remaining": remaining})
        return {
            "total_remaining":  total_remaining,
            "limit_per_day":    settings.alpha_vantage_calls_per_day,
            "keys":             keys_info,
            "min_interval_secs": _AV_MIN_INTERVAL,
        }
