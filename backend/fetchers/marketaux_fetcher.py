"""Marketaux-Fetcher: News + Sentiment-Score.
Free Tier: 100 News-Artikel/Tag. Als Fallback zu Finnhub.
"""
import logging
import requests
from datetime import datetime
from sqlalchemy.orm import Session

from backend.config import settings
from backend.fetchers.base import BaseFetcher, with_retry
from backend.models import Configuration

logger = logging.getLogger(__name__)

NEWS_TTL    = 2 * 3600
QUOTA_KEY   = "marketaux_calls_today"
QUOTA_RESET = "marketaux_quota_date"


class MarketauxFetcher(BaseFetcher):
    SOURCE_NAME = "marketaux"
    BASE_URL = "https://api.marketaux.com/v1/news/all"

    def _quota_remaining(self) -> int:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        date_row  = self.db.get(Configuration, QUOTA_RESET)
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
            return settings.marketaux_calls_per_day

        used = int(count_row.value) if count_row else 0
        return max(0, settings.marketaux_calls_per_day - used)

    def _increment_quota(self) -> None:
        row = self.db.get(Configuration, QUOTA_KEY)
        if row:
            row.value = str(int(row.value) + 1)
            self.db.commit()

    def get_news_sentiment(self, ticker: str) -> dict:
        """News + Sentiment für einen Ticker. Gecacht 2 Stunden."""
        key = self._make_key("sentiment", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        if self._quota_remaining() <= 0:
            logger.warning("Marketaux Tageslimit erreicht – überspringe %s", ticker)
            return {"sentiment_score": 0.0, "articles_count": 0}

        data = self._fetch_sentiment(ticker)
        self._cache_set(key, data, NEWS_TTL)
        return data

    @with_retry(max_attempts=2)
    def _fetch_sentiment(self, ticker: str) -> dict:
        default = {"sentiment_score": 0.0, "articles_count": 0}
        if not settings.marketaux_api_key:
            return default
        try:
            resp = requests.get(
                self.BASE_URL,
                params={
                    "symbols":        ticker,
                    "filter_entities": "true",
                    "language":       "en",
                    "limit":          3,
                    "api_token":      settings.marketaux_api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            self._increment_quota()
            articles = resp.json().get("data", [])
            if not articles:
                return default
            scores = []
            for a in articles:
                for entity in a.get("entities", []):
                    if entity.get("symbol") == ticker:
                        s = entity.get("sentiment_score")
                        if s is not None:
                            scores.append(float(s))
            if not scores:
                return default
            return {
                "sentiment_score": round(sum(scores) / len(scores), 4),
                "articles_count":  len(articles),
            }
        except Exception as exc:
            logger.debug("Marketaux für %s: %s", ticker, exc)
            return default
