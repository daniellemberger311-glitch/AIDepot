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
            params_base = {"ticker": ticker, "period": "TTM", "fyear": "latest"}

            # Gewinn- und Verlustrechnung
            r_income = requests.get(
                f"{self.BASE_URL}/companies/statements/compact",
                params={**params_base, "statements": "PL"},
                headers=self._headers(), timeout=15,
            )
            r_income.raise_for_status()

            # Cashflow-Statement
            r_cf = requests.get(
                f"{self.BASE_URL}/companies/statements/compact",
                params={**params_base, "statements": "CF"},
                headers=self._headers(), timeout=15,
            )
            r_cf.raise_for_status()

            # Bilanz (für D/E-Ratio und Verschuldungsgrad)
            r_bs = requests.get(
                f"{self.BASE_URL}/companies/statements/compact",
                params={**params_base, "statements": "BS"},
                headers=self._headers(), timeout=15,
            )
            r_bs.raise_for_status()

            result = dict(default)
            result.update(self._parse_income(r_income.json()))
            result.update(self._parse_cashflow(r_cf.json()))
            result.update(self._parse_balance_sheet(r_bs.json()))
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

    def _parse_balance_sheet(self, data: dict) -> dict:
        """D/E-Ratio aus SimFin-Balance-Sheet extrahieren."""
        result = {}
        try:
            rows = data[0].get("statements", [{}])[0].get("data", [])
            cols = data[0].get("statements", [{}])[0].get("columns", [])
            if not rows or not cols:
                return result
            row = dict(zip(cols, rows[-1]))
            # Gesamtschulden: Long-Term Debt + Short-Term Debt
            lt_debt = row.get("Long Term Debt") or row.get("Long-Term Debt") or 0
            st_debt = row.get("Short Term Debt") or row.get("Short-Term Debt") or 0
            equity  = row.get("Total Equity") or row.get("Shareholders' Equity")
            total_debt = float(lt_debt or 0) + float(st_debt or 0)
            if equity and float(equity) > 0:
                result["debt_to_equity"] = round(total_debt / float(equity), 4)
        except Exception as exc:
            logger.debug("SimFin BS-Parse: %s", exc)
        return result
