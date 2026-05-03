"""SimFin-Fetcher: KGV, EPS, Free Cashflow, Verschuldungsgrad.
Kostenlos für private Nutzung, kein Rate-Limit.
Fällt bei fehlendem Key auf yfinance-Fundamentals zurück.
"""
import logging
import requests
from sqlalchemy.orm import Session

from backend.config import settings
from backend.fetchers.base import BaseFetcher, with_retry

logger = logging.getLogger(__name__)

FUND_TTL = 24 * 3600   # 24 Stunden – ändert sich höchstens quartalsweise


class SimFinFetcher(BaseFetcher):
    SOURCE_NAME = "simfin"
    BASE_URL = "https://backend.simfin.com/api/v3"

    def _headers(self) -> dict:
        return {"Authorization": f"api-key {settings.simfin_api_key}"}

    def get_fundamentals(self, ticker: str) -> dict:
        """KGV, EPS-Verlauf, FCF, Verschuldungsgrad. Gecacht 24 Stunden."""
        key = self._make_key("fundamentals", ticker)
        cached = self._cache_get(key)
        if cached:
            return cached

        data = self._fetch_fundamentals(ticker)
        self._cache_set(key, data, FUND_TTL)
        return data

    @with_retry()
    def _fetch_fundamentals(self, ticker: str) -> dict:
        default = {
            "pe_ratio": None, "eps_ttm": None,
            "free_cashflow": None, "fcf_prev_year": None,
            "debt_to_equity": None, "revenue": None, "revenue_prev_year": None,
        }
        if not settings.simfin_api_key:
            return default
        try:
            # Gewinn- und Verlustrechnung (TTM)
            r_income = requests.get(
                f"{self.BASE_URL}/companies/statements/compact",
                params={"ticker": ticker, "statements": "PL", "period": "TTM", "fyear": "latest"},
                headers=self._headers(),
                timeout=15,
            )
            r_income.raise_for_status()
            income = r_income.json()

            # Cashflow-Statement
            r_cf = requests.get(
                f"{self.BASE_URL}/companies/statements/compact",
                params={"ticker": ticker, "statements": "CF", "period": "TTM", "fyear": "latest"},
                headers=self._headers(),
                timeout=15,
            )
            r_cf.raise_for_status()
            cashflow = r_cf.json()

            result = dict(default)
            result.update(self._parse_income(income))
            result.update(self._parse_cashflow(cashflow))
            return result

        except Exception as exc:
            logger.debug("SimFin für %s: %s", ticker, exc)
            return default

    def _parse_income(self, data: dict) -> dict:
        """Relevante Kennzahlen aus SimFin-Income-Response extrahieren."""
        result = {}
        try:
            rows = data[0].get("statements", [{}])[0].get("data", [])
            cols = data[0].get("statements", [{}])[0].get("columns", [])
            if not rows or not cols:
                return result
            row = dict(zip(cols, rows[-1]))
            revenue = row.get("Revenue")
            net_income = row.get("Net Income")
            shares = row.get("Shares (Diluted)")
            result["revenue"] = float(revenue) if revenue else None
            if net_income and shares and float(shares) > 0:
                result["eps_ttm"] = round(float(net_income) / float(shares), 4)
            # Vorjahres-Umsatz für Wachstumsberechnung
            if len(rows) >= 2:
                prev = dict(zip(cols, rows[-2]))
                result["revenue_prev_year"] = float(prev.get("Revenue", 0) or 0)
        except Exception as exc:
            logger.debug("SimFin Income-Parse: %s", exc)
        return result

    def _parse_cashflow(self, data: dict) -> dict:
        """Free Cashflow aus SimFin-Cashflow-Response extrahieren."""
        result = {}
        try:
            rows = data[0].get("statements", [{}])[0].get("data", [])
            cols = data[0].get("statements", [{}])[0].get("columns", [])
            if not rows or not cols:
                return result
            row = dict(zip(cols, rows[-1]))
            fcf = row.get("Free Cash Flow") or row.get("Net Cash from Operations")
            result["free_cashflow"] = float(fcf) if fcf else None
            if len(rows) >= 2:
                prev = dict(zip(cols, rows[-2]))
                prev_fcf = prev.get("Free Cash Flow") or prev.get("Net Cash from Operations")
                result["fcf_prev_year"] = float(prev_fcf) if prev_fcf else None
        except Exception as exc:
            logger.debug("SimFin CF-Parse: %s", exc)
        return result
