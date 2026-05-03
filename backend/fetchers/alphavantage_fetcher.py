"""Alpha-Vantage-Fetcher: Technische Indikatoren und News-Sentiment.
Free Tier: NUR 25 Calls/Tag – extrem sparsam einsetzen!
Primär als Ergänzung zu yfinance+ta, nicht als Hauptquelle.
"""
import logging
import requests
from datetime import datetime
from sqlalchemy.orm import Session

from backend.config import settings
from backend.fetchers.base import BaseFetcher, with_retry
from backend.models import Configuration

logger = logging.getLogger(__name__)

RSI_TTL       = 4 * 3600
MACD_TTL      = 4 * 3600
NEWS_TTL      = 2 * 3600
QUOTA_KEY     = "av_calls_today"
QUOTA_RESET   = "av_quota_date"


class AlphaVantageFetcher(BaseFetcher):
    SOURCE_NAME = "alphavantage"
    BASE_URL = "https://www.alphavantage.co/query"

    def _quota_remaining(self) -> int:
        """Verbleibende Calls heute prüfen und ggf. Tageszähler zurücksetzen."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        date_row = self.db.get(Configuration, QUOTA_RESET)
        count_row = self.db.get(Configuration, QUOTA_KEY)

        if not date_row or date_row.value != today:
            for key, val in [(QUOTA_RESET, today), (QUOTA_KEY, "0")]:
                row = self.db.get(Configuration, key)
                if row:
                    row.value = val
                else:
                    from backend.models import Configuration as C
                    self.db.add(C(key=key, value=val))
            self.db.commit()
            return settings.alpha_vantage_calls_per_day

        used = int(count_row.value) if count_row else 0
        return max(0, settings.alpha_vantage_calls_per_day - used)

    def _increment_quota(self) -> None:
        row = self.db.get(Configuration, QUOTA_KEY)
        if row:
            row.value = str(int(row.value) + 1)
            self.db.commit()

    def _get(self, params: dict) -> dict:
        if not settings.alpha_vantage_api_key:
            return {}
        if self._quota_remaining() <= 0:
            logger.warning("Alpha Vantage Tageslimit erreicht – überspringe Call")
            return {}
        params["apikey"] = settings.alpha_vantage_api_key
        resp = requests.get(self.BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        self._increment_quota()
        return resp.json()

    def get_rsi(self, ticker: str, interval: str = "daily", period: int = 14) -> dict:
        """RSI über Alpha Vantage. Gecacht 4 Stunden. Quota-geschützt."""
        key = self._make_key(f"rsi_{interval}", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_rsi(ticker, interval, period)
        if data:
            self._cache_set(key, data, RSI_TTL)
        return data

    @with_retry(max_attempts=2)
    def _fetch_rsi(self, ticker: str, interval: str, period: int) -> dict:
        r = self._get({"function": "RSI", "symbol": ticker,
                       "interval": interval, "time_period": period,
                       "series_type": "close"})
        meta = r.get("Technical Analysis: RSI", {})
        if not meta:
            return {}
        latest_date = sorted(meta.keys())[-1]
        return {"date": latest_date, "rsi": float(meta[latest_date]["RSI"])}

    def get_macd(self, ticker: str, interval: str = "daily") -> dict:
        """MACD über Alpha Vantage. Gecacht 4 Stunden."""
        key = self._make_key(f"macd_{interval}", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_macd(ticker, interval)
        if data:
            self._cache_set(key, data, MACD_TTL)
        return data

    @with_retry(max_attempts=2)
    def _fetch_macd(self, ticker: str, interval: str) -> dict:
        r = self._get({"function": "MACD", "symbol": ticker,
                       "interval": interval, "series_type": "close"})
        meta = r.get("Technical Analysis: MACD", {})
        if not meta:
            return {}
        latest_date = sorted(meta.keys())[-1]
        row = meta[latest_date]
        return {
            "date":      latest_date,
            "macd":      float(row["MACD"]),
            "signal":    float(row["MACD_Signal"]),
            "histogram": float(row["MACD_Hist"]),
        }

    def get_news_sentiment(self, ticker: str) -> dict:
        """News-Sentiment über Alpha Vantage (Fallback). Gecacht 2 Stunden."""
        key = self._make_key("news_sentiment", ticker)
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
