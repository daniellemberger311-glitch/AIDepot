"""StockTwits-Fetcher: Bullish/Bearish-Ratio und Trending Tickers.
Kein API-Key erforderlich. Inoffizielle Public-API – freiwillig drosseln.
"""
import logging
import time
import requests
from sqlalchemy.orm import Session
from backend.fetchers.base import BaseFetcher, with_retry

logger = logging.getLogger(__name__)

SENTIMENT_TTL = 3600   # 1 Stunde
TRENDING_TTL  = 3600


class StockTwitsFetcher(BaseFetcher):
    SOURCE_NAME = "stocktwits"
    BASE_URL = "https://api.stocktwits.com/api/2"
    _last_call: float = 0.0

    def _throttle(self, min_gap: float = 2.0) -> None:
        """Mindestabstand zwischen Anfragen einhalten (inoffizielle API)."""
        elapsed = time.time() - StockTwitsFetcher._last_call
        if elapsed < min_gap:
            time.sleep(min_gap - elapsed)
        StockTwitsFetcher._last_call = time.time()

    def get_sentiment_ratio(self, ticker: str) -> dict:
        """Bullish/Bearish-Ratio für einen Ticker. Gecacht 1 Stunde."""
        key = self._make_key("sentiment", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        self._throttle()
        data = self._fetch_sentiment(ticker)
        self._cache_set(key, data, SENTIMENT_TTL)
        return data

    @with_retry()
    def _fetch_sentiment(self, ticker: str) -> dict:
        default = {"bullish_count": 0, "bearish_count": 0, "bullish_ratio": 0.5, "total": 0}
        try:
            resp = requests.get(
                f"{self.BASE_URL}/streams/symbol/{ticker}.json",
                timeout=10,
                headers={"User-Agent": "AIDepot/1.0"},
            )
            if resp.status_code == 429:
                logger.warning("StockTwits Rate-Limit für %s", ticker)
                return default
            resp.raise_for_status()
            data = resp.json()
            symbol_info = data.get("symbol", {})
            bullish = symbol_info.get("watchlist_count", 0)
            sentiment_data = {m.get("entities", {}).get("sentiment", {}).get("basic", "") for m in data.get("messages", [])}
            b_count = sum(1 for s in sentiment_data if s == "Bullish")
            be_count = sum(1 for s in sentiment_data if s == "Bearish")
            total = b_count + be_count
            ratio = b_count / total if total > 0 else 0.5
            return {
                "bullish_count": b_count,
                "bearish_count": be_count,
                "bullish_ratio": round(ratio, 3),
                "total": total,
            }
        except Exception as exc:
            logger.debug("StockTwits Sentiment für %s fehlgeschlagen: %s", ticker, exc)
            return default

    def get_trending_tickers(self) -> list[str]:
        """Aktuelle Trending-Ticker. Gecacht 1 Stunde."""
        key = "stocktwits:trending:global"
        cached = self._cache_get(key)
        if cached:
            return cached.get("tickers", [])

        self._throttle()
        tickers = self._fetch_trending()
        self._cache_set(key, {"tickers": tickers}, TRENDING_TTL)
        return tickers

    @with_retry()
    def _fetch_trending(self) -> list[str]:
        try:
            resp = requests.get(
                f"{self.BASE_URL}/trending/symbols.json",
                timeout=10,
                headers={"User-Agent": "AIDepot/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            return [s["symbol"] for s in data.get("symbols", [])]
        except Exception as exc:
            logger.warning("StockTwits Trending fehlgeschlagen: %s", exc)
            return []
