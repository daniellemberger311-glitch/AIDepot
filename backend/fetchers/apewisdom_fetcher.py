"""ApeWisdom-Fetcher: Reddit-Erwähnungsranking (WSB, r/investing).
Kein API-Key erforderlich.
"""
import logging
import requests
from sqlalchemy.orm import Session
from backend.fetchers.base import BaseFetcher, with_retry

logger = logging.getLogger(__name__)

MENTIONS_TTL = 2 * 3600   # 2 Stunden


class ApeWisdomFetcher(BaseFetcher):
    SOURCE_NAME = "apewisdom"
    BASE_URL = "https://apewisdom.io/api/v1.0"

    def get_mentions(self, ticker: str) -> dict:
        """Reddit-Erwähnungen und 24h-Trend für einen Ticker. Gecacht 2 Stunden."""
        key = self._make_key("mentions", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_all_mentions()
        # Alle Ticker in einem Call cachen (API gibt Top-Liste zurück)
        for entry in data:
            t = entry.get("ticker", "")
            if t:
                entry_key = self._make_key("mentions", t)
                self._cache_set(entry_key, entry, MENTIONS_TTL)

        for entry in data:
            if entry.get("ticker") == ticker:
                return entry

        neutral = {"ticker": ticker, "mentions": 0, "mentions_24h_ago": 0, "rank": 9999}
        self._cache_set(key, neutral, MENTIONS_TTL)
        return neutral

    @with_retry()
    def _fetch_all_mentions(self) -> list[dict]:
        try:
            resp = requests.get(
                f"{self.BASE_URL}/filter/all-stocks/page/1",
                timeout=10,
                headers={"User-Agent": "AIDepot/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return [
                {
                    "ticker":           r.get("ticker", ""),
                    "name":             r.get("name", ""),
                    "mentions":         int(r.get("mentions", 0)),
                    "mentions_24h_ago": int(r.get("mentions_24h_ago", 0)),
                    "rank":             int(r.get("rank", 9999)),
                }
                for r in results
            ]
        except Exception as exc:
            logger.warning("ApeWisdom fehlgeschlagen: %s", exc)
            return []
