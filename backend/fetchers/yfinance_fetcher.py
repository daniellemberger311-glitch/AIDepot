"""yfinance-Fetcher: OHLCV, Fundamentals, Earnings-Kalender.
Kein API-Key erforderlich. Gilt als unbegrenzt nutzbar (inoffiziell).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from backend.fetchers.base import BaseFetcher, with_retry

logger = logging.getLogger(__name__)

OHLCV_TTL   = 4 * 3600   # 4 Stunden
FUND_TTL    = 24 * 3600   # 24 Stunden
EARN_TTL    = 24 * 3600


class YFinanceFetcher(BaseFetcher):
    SOURCE_NAME = "yfinance"

    def get_ohlcv(self, ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        """OHLCV-Daten. Gecacht 4 Stunden."""
        key = self._make_key(f"ohlcv_{period}", ticker)
        cached = self._cache_get(key)
        if cached:
            return pd.DataFrame(cached)

        df = self._fetch_ohlcv(ticker, period, interval)
        if not df.empty:
            self._cache_set(key, df.reset_index().to_dict("records"), OHLCV_TTL)
        return df

    @with_retry()
    def _fetch_ohlcv(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval, auto_adjust=True)
        if df.empty:
            logger.warning("yfinance: leere OHLCV für %s", ticker)
        else:
            df.index = df.index.tz_localize(None)
        return df

    def get_fundamentals(self, ticker: str) -> dict:
        """KGV, Marktkapitalisierung, Sektor, Wachstum. Gecacht 24 Stunden."""
        key = self._make_key("fundamentals", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_fundamentals(ticker)
        self._cache_set(key, data, FUND_TTL)
        return data

    @with_retry()
    def _fetch_fundamentals(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        info = t.info or {}
        return {
            "pe_ratio":           info.get("trailingPE"),
            "forward_pe":         info.get("forwardPE"),
            "market_cap":         info.get("marketCap"),
            "sector":             info.get("sector", ""),
            "industry":           info.get("industry", ""),
            "name":               info.get("longName", ticker),
            "exchange":           info.get("exchange", ""),
            "revenue_growth":     info.get("revenueGrowth"),       # YoY
            "earnings_growth":    info.get("earningsGrowth"),
            "debt_to_equity":     info.get("debtToEquity"),
            "free_cashflow":      info.get("freeCashflow"),
            "operating_cashflow": info.get("operatingCashflow"),
            "price":              info.get("currentPrice") or info.get("regularMarketPrice"),
            "high_52w":           info.get("fiftyTwoWeekHigh"),
            "low_52w":            info.get("fiftyTwoWeekLow"),
            "avg_volume_50d":     info.get("averageVolume"),
            "recommendation":     info.get("recommendationKey", ""),
        }

    def get_earnings_calendar(self, ticker: str) -> dict:
        """Nächster Earnings-Termin + letzte 4 Quartale EPS. Gecacht 24 Stunden."""
        key = self._make_key("earnings", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_earnings(ticker)
        self._cache_set(key, data, EARN_TTL)
        return data

    @with_retry()
    def _fetch_earnings(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        cal = {}

        # Nächster Earnings-Termin
        try:
            ec = t.earnings_dates
            if ec is not None and not ec.empty:
                future = ec[ec.index > datetime.now()]
                if not future.empty:
                    next_date = future.index[-1]
                    cal["next_earnings_date"] = str(next_date.date())
                    cal["days_to_earnings"] = (next_date.date() - datetime.now().date()).days
                else:
                    cal["next_earnings_date"] = None
                    cal["days_to_earnings"] = None
        except Exception:
            cal["next_earnings_date"] = None
            cal["days_to_earnings"] = None

        # Letzte 4 Quartale EPS
        try:
            hist = t.quarterly_earnings
            beats = []
            if hist is not None and not hist.empty:
                for _, row in hist.head(4).iterrows():
                    actual   = row.get("Reported EPS") or row.get("actual")
                    estimate = row.get("EPS Estimate")  or row.get("estimate")
                    if actual is not None and estimate is not None:
                        beats.append({
                            "actual":   float(actual),
                            "estimate": float(estimate),
                            "beat":     float(actual) > float(estimate),
                        })
            cal["eps_history"] = beats
        except Exception:
            cal["eps_history"] = []

        return cal

    def get_insider_summary(self, ticker: str) -> dict:
        """Insider-Transaktionen (90 Tage). Gecacht 24 Stunden. yfinance-Fallback."""
        key = self._make_key("insider", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_insider(ticker)
        self._cache_set(key, data, FUND_TTL)
        return data

    @with_retry()
    def _fetch_insider(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        result = {"buy_count": 0, "sell_count": 0, "net_buys": 0}
        try:
            it = t.insider_transactions
            if it is None or it.empty:
                return result
            cutoff = datetime.now() - timedelta(days=90)
            recent = it[pd.to_datetime(it["Start Date"]) > cutoff]
            buys  = len(recent[recent["Transaction"].str.contains("Purchase|Buy", case=False, na=False)])
            sells = len(recent[recent["Transaction"].str.contains("Sale|Sell", case=False, na=False)])
            result = {"buy_count": buys, "sell_count": sells, "net_buys": buys - sells}
        except Exception as exc:
            logger.debug("yfinance insider für %s fehlgeschlagen: %s", ticker, exc)
        return result

    def get_spy_ohlcv(self, period: str = "3mo") -> pd.DataFrame:
        """SPY-Kursdaten als Benchmark für Relative-Stärke-Berechnung."""
        return self.get_ohlcv("SPY", period=period)
