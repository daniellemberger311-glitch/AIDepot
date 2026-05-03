"""Alpha-Vantage-Fetcher: Technische Indikatoren und News-Sentiment.

Free-Tier-Limits (BEIDE müssen eingehalten werden!):
  - 25 Calls/Tag  → Quota-Zähler in DB, Reset um Mitternacht UTC
  - 5 Calls/Min   → Modul-globaler Timestamp, 13-Sekunden-Abstand erzwungen

Einsatz-Strategie:
  Nur für Zone 1+2 und gehaltene Positionen verwenden.
  Zone 3+4 → ta-Bibliothek + yfinance (kein Limit).
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

RSI_TTL     = 4 * 3600
MACD_TTL    = 4 * 3600
NEWS_TTL    = 2 * 3600
QUOTA_KEY   = "av_calls_today"
QUOTA_RESET = "av_quota_date"

# 5 Calls/Minute = 1 Call alle 12 Sekunden → 13 s Abstand als Puffer
_AV_MIN_INTERVAL: float = 13.0
_last_av_call_ts: float = 0.0   # Modul-global, verhindert parallele Überläufe


def _enforce_rate_limit() -> None:
    """Wartet so lange, bis seit dem letzten AV-Call mindestens 13 Sekunden vergangen sind.
    Wird VOR jedem echten AV-API-Call aufgerufen.
    """
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

    # ── Quota-Verwaltung ───────────────────────────────────────────────────────

    def _quota_remaining(self) -> int:
        """Verbleibende Calls heute. Setzt Tageszähler zurück bei neuer UTC-Date."""
        today     = datetime.utcnow().strftime("%Y-%m-%d")
        date_row  = self.db.get(Configuration, QUOTA_RESET)
        count_row = self.db.get(Configuration, QUOTA_KEY)

        if not date_row or date_row.value != today:
            for key, val in [(QUOTA_RESET, today), (QUOTA_KEY, "0")]:
                row = self.db.get(Configuration, key)
                if row:
                    row.value = val
                else:
                    self.db.add(Configuration(key=key, value=val))
            self.db.commit()
            return settings.alpha_vantage_calls_per_day

        used = int(count_row.value) if count_row else 0
        return max(0, settings.alpha_vantage_calls_per_day - used)

    def _consume_quota(self) -> None:
        """Erhöht den Tageszähler um 1."""
        row = self.db.get(Configuration, QUOTA_KEY)
        if row:
            row.value = str(int(row.value) + 1)
            self.db.commit()

    # ── Interner API-Call ──────────────────────────────────────────────────────

    def _get(self, params: dict) -> dict:
        """Führt einen AV-Call aus. Prüft Tageslimit und 5/Min-Limit."""
        if not settings.alpha_vantage_api_key:
            logger.debug("Kein ALPHA_VANTAGE_API_KEY – überspringe")
            return {}
        if self._quota_remaining() <= 0:
            logger.warning("Alpha Vantage Tageslimit (%d) erreicht", settings.alpha_vantage_calls_per_day)
            return {}

        _enforce_rate_limit()   # ← 5-Calls/Minute-Schutz

        params["apikey"] = settings.alpha_vantage_api_key
        resp = requests.get(self.BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        self._consume_quota()

        data = resp.json()
        # AV gibt bei Rate-Limit-Überschreitung eine "Note" statt Fehlercode zurück
        if "Note" in data or "Information" in data:
            msg = data.get("Note") or data.get("Information", "")
            logger.warning("Alpha Vantage Rate-Limit-Antwort: %s", msg[:80])
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
    # Hinweis: AV MACD ist seit 2024/2025 ein Premium-Endpunkt.
    # Die Scoring-Engine nutzt daher ausschließlich die ta-Bibliothek + yfinance
    # für MACD-Berechnungen. Diese Methode dient als optionaler Validierungs-Call
    # falls ein Premium-Key vorhanden ist.

    def get_macd(self, ticker: str, interval: str = "daily") -> dict:
        """MACD via AV (nur Premium-Keys). Fallback: ta-Bibliothek in technical.py."""
        key    = self._make_key(f"macd_{interval}", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached
        data = self._fetch_macd(ticker, interval)
        if data:
            self._cache_set(key, data, MACD_TTL)
        return data  # Gibt {} zurück wenn Premium nicht verfügbar

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

    # ── News-Sentiment (Fallback) ──────────────────────────────────────────────

    def get_news_sentiment(self, ticker: str) -> dict:
        """AV News-Sentiment als Fallback zu Finnhub/Marketaux. Gecacht 2 Stunden."""
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

    # ── Quota-Status (für Diagnose) ────────────────────────────────────────────

    def quota_status(self) -> dict:
        """Gibt aktuellen Quota-Status zurück (für API-Endpoint /api/config)."""
        return {
            "remaining_today":   self._quota_remaining(),
            "limit_per_day":     settings.alpha_vantage_calls_per_day,
            "min_interval_secs": _AV_MIN_INTERVAL,
        }
