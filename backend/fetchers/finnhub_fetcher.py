"""Finnhub-Fetcher: News-Sentiment, Insider-Trades, Earnings-Überraschungen, Analyst-Ratings.
Free Tier: 60 Calls/Minute. Quota-geschützt.
"""
import logging
import time
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.config import settings
from backend.fetchers.base import BaseFetcher, with_retry

logger = logging.getLogger(__name__)

SENTIMENT_TTL = 2 * 3600
INSIDER_TTL   = 24 * 3600
EARNINGS_TTL  = 24 * 3600
ANALYST_TTL   = 24 * 3600

_calls_this_minute: list[float] = []


def _rate_limit():
    """Sicherstellt max. 55 Calls/Min (5 Calls Puffer)."""
    global _calls_this_minute
    now = time.time()
    _calls_this_minute = [t for t in _calls_this_minute if now - t < 60]
    if len(_calls_this_minute) >= 55:
        wait = 60 - (now - _calls_this_minute[0]) + 0.1
        logger.debug("Finnhub Rate-Limit: warte %.1fs", wait)
        time.sleep(max(wait, 0))
    _calls_this_minute.append(time.time())


class FinnhubFetcher(BaseFetcher):
    SOURCE_NAME = "finnhub"
    BASE_URL = "https://finnhub.io/api/v1"

    def _get(self, endpoint: str, params: dict) -> dict | list:
        if not settings.finnhub_api_key:
            return {}
        _rate_limit()
        params["token"] = settings.finnhub_api_key
        resp = requests.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_news_sentiment(self, ticker: str) -> dict:
        """Aggregierter News-Sentiment-Score. Gecacht 2 Stunden."""
        key = self._make_key("sentiment", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_sentiment(ticker)
        self._cache_set(key, data, SENTIMENT_TTL)
        return data

    @with_retry()
    def _fetch_sentiment(self, ticker: str) -> dict:
        default = {"buzz_score": 0.5, "sentiment_score": 0.0, "articles_count": 0}
        if not settings.finnhub_api_key:
            return default
        try:
            r = self._get("news-sentiment", {"symbol": ticker})
            return {
                "buzz_score":      r.get("buzz", {}).get("buzz", 0.5),
                "sentiment_score": r.get("sentiment", {}).get("bullishPercent", 0.5) - 0.5,
                "articles_count":  r.get("buzz", {}).get("articlesInLastWeek", 0),
            }
        except Exception as exc:
            logger.debug("Finnhub Sentiment für %s: %s", ticker, exc)
            return default

    def get_insider_transactions(self, ticker: str) -> dict:
        """Insider-Transaktionen (letzte 90 Tage). Gecacht 24 Stunden."""
        key = self._make_key("insider", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_insider(ticker)
        self._cache_set(key, data, INSIDER_TTL)
        return data

    @with_retry()
    def _fetch_insider(self, ticker: str) -> dict:
        default = {"buy_count": 0, "sell_count": 0, "net_buys": 0}
        if not settings.finnhub_api_key:
            return default
        try:
            cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            today  = datetime.now().strftime("%Y-%m-%d")
            r = self._get("stock/insider-transactions", {"symbol": ticker, "from": cutoff, "to": today})
            txs = r.get("data", []) if isinstance(r, dict) else []
            buys  = sum(1 for t in txs if t.get("transactionCode") in ("P",))
            sells = sum(1 for t in txs if t.get("transactionCode") in ("S", "S-Auto"))
            return {"buy_count": buys, "sell_count": sells, "net_buys": buys - sells}
        except Exception as exc:
            logger.debug("Finnhub Insider für %s: %s", ticker, exc)
            return default

    def get_earnings_surprises(self, ticker: str, quarters: int = 4) -> list[dict]:
        """Letzte N Earnings mit actual vs. estimate EPS. Gecacht 24 Stunden."""
        key = self._make_key("earnings_surprises", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached.get("data", [])

        data = self._fetch_earnings_surprises(ticker, quarters)
        self._cache_set(key, {"data": data}, EARNINGS_TTL)
        return data

    @with_retry()
    def _fetch_earnings_surprises(self, ticker: str, quarters: int) -> list[dict]:
        if not settings.finnhub_api_key:
            return []
        try:
            r = self._get("stock/earnings", {"symbol": ticker})
            results = []
            for item in (r or [])[:quarters]:
                actual   = item.get("actual")
                estimate = item.get("estimate")
                if actual is not None:
                    results.append({
                        "period":   item.get("period", ""),
                        "actual":   float(actual),
                        "estimate": float(estimate) if estimate else None,
                        "beat":     float(actual) > float(estimate) if estimate else False,
                    })
            return results
        except Exception as exc:
            logger.debug("Finnhub Earnings für %s: %s", ticker, exc)
            return []

    def get_analyst_recommendations(self, ticker: str) -> dict:
        """Analysten-Empfehlungen (aktueller Monat und Vormonat). Gecacht 24 Stunden."""
        key = self._make_key("analyst", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_analyst(ticker)
        self._cache_set(key, data, ANALYST_TTL)
        return data

    @with_retry()
    def _fetch_analyst(self, ticker: str) -> dict:
        default = {"strong_buy": 0, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 0, "net_upgrade": 0}
        if not settings.finnhub_api_key:
            return default
        try:
            r = self._get("stock/recommendation", {"symbol": ticker})
            if not r:
                return default
            current = r[0] if r else {}
            prior   = r[1] if len(r) > 1 else {}
            net = (
                (current.get("strongBuy", 0) + current.get("buy", 0)) -
                (prior.get("strongBuy", 0) + prior.get("buy", 0))
            )
            return {
                "strong_buy":   current.get("strongBuy", 0),
                "buy":          current.get("buy", 0),
                "hold":         current.get("hold", 0),
                "sell":         current.get("sell", 0),
                "strong_sell":  current.get("strongSell", 0),
                "net_upgrade":  net,
            }
        except Exception as exc:
            logger.debug("Finnhub Analyst für %s: %s", ticker, exc)
            return default
