"""Historische Rohdaten für Backtesting.

Liefert:
  - OHLCV-Tagesdaten inkl. Lookback-Puffer für Indikatoren (200 Handelstage)
  - Fundamentals (KGV, Umsatzwachstum, FCF, D/E) aus yfinance quarterly data
  - SPY-Referenzdaten für relative Stärke
  - Sentiment: immer neutral (12,5/25) – historische Daten nicht verfügbar

Caching: alle Abrufe werden im In-Memory-Cache gehalten (TTL 4h),
damit mehrere Backtests desselben Tickers keine doppelten Downloads verursachen.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Lookback in Handelstagen vor from_date für Indikator-Berechnung
_INDICATOR_LOOKBACK_DAYS = 252  # 1 Handelsjahr

# Einfacher Modul-Level-Cache: key → (timestamp, data)
_cache: dict[str, tuple[datetime, object]] = {}
_CACHE_TTL_SECONDS = 4 * 3600


def _cached(key: str, fn):
    """Einfacher TTL-Cache ohne Abhängigkeit von cache/store.py."""
    now = datetime.utcnow()
    if key in _cache:
        ts, data = _cache[key]
        if (now - ts).total_seconds() < _CACHE_TTL_SECONDS:
            return data
    result = fn()
    _cache[key] = (now, result)
    return result


# ── OHLCV ────────────────────────────────────────────────────────────────────

def get_ohlcv(ticker: str, from_date: str, to_date: str) -> pd.DataFrame:
    """
    Tägliche OHLCV-Daten für den angegebenen Zeitraum + Lookback-Puffer.

    Gibt DataFrame mit DatetimeIndex und Spalten:
      Open, High, Low, Close, Volume
    Sortiert aufsteigend (älteste zuerst).
    """
    # Lookback-Puffer: Handelstage ≈ Kalendertage × 1,4
    cal_lookback = int(_INDICATOR_LOOKBACK_DAYS * 1.4)
    fetch_from = (
        datetime.strptime(from_date, "%Y-%m-%d") - timedelta(days=cal_lookback)
    ).strftime("%Y-%m-%d")

    cache_key = f"ohlcv:{ticker}:{fetch_from}:{to_date}"

    def _fetch():
        logger.debug("yfinance OHLCV: %s %s→%s", ticker, fetch_from, to_date)
        raw = yf.download(
            ticker,
            start=fetch_from,
            end=to_date,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if raw.empty:
            logger.warning("Keine OHLCV-Daten für %s", ticker)
            return pd.DataFrame()

        # MultiIndex entfernen falls vorhanden
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        raw.index = pd.to_datetime(raw.index)
        raw = raw[["Open", "High", "Low", "Close", "Volume"]].sort_index()
        raw = raw[raw["Close"] > 0].dropna(subset=["Close"])
        return raw

    return _cached(cache_key, _fetch)


def get_spy_ohlcv(from_date: str, to_date: str) -> pd.DataFrame:
    """SPY als Benchmark für relative Stärke."""
    return get_ohlcv("SPY", from_date, to_date)


# ── Fundamentals ─────────────────────────────────────────────────────────────

def get_fundamentals(ticker: str) -> dict:
    """
    Statische Fundamentaldaten aus yfinance.
    Für Backtesting gilt: Quartalswerte werden auf alle Tage im Quartal angewendet
    (Point-in-time-Approximation – ausreichend für Signal-Zeitstrahl-Analyse).

    Rückgabe-Dict:
      pe_ratio, sector, revenue_growth_yoy, fcf_positive, fcf_growing,
      debt_equity, eps_beats (0–3), earnings_dates (list[str])
    """
    cache_key = f"fundamentals:{ticker}"

    def _fetch():
        logger.debug("yfinance Fundamentals: %s", ticker)
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            sector   = info.get("sector", "")
            de_ratio = info.get("debtToEquity")
            if de_ratio:
                de_ratio = de_ratio / 100  # yfinance liefert in %

            # Umsatzwachstum aus Quartalsumsatz
            rev_growth = _estimate_revenue_growth(t)

            # FCF
            fcf_pos, fcf_grow = _estimate_fcf(t)

            # EPS-Beat-Streak (0–3 Quartale)
            eps_beats = _estimate_eps_beats(info)

            fcf_latest, fcf_prev = _get_fcf_values(t)

            return {
                "pe_ratio":           pe_ratio,
                "sector":             sector,
                "revenue_growth_yoy": rev_growth,
                "fcf_latest":         fcf_latest,
                "fcf_prev":           fcf_prev,
                "debt_equity":        de_ratio,
                "eps_history":        _build_eps_history(info),
            }
        except Exception as exc:
            logger.warning("Fundamentals für %s fehlgeschlagen: %s", ticker, exc)
            return {}

    return _cached(cache_key, _fetch)


def _estimate_revenue_growth(ticker_obj) -> Optional[float]:
    """Umsatzwachstum YoY aus quarterly_financials."""
    try:
        qf = ticker_obj.quarterly_financials
        if qf is None or qf.empty:
            return None
        rev_row = None
        for lbl in ("Total Revenue", "Revenue", "Net Revenue"):
            if lbl in qf.index:
                rev_row = qf.loc[lbl]
                break
        if rev_row is None or len(rev_row) < 5:
            return None
        # Letztes Quartal vs. gleiches Quartal Vorjahr
        latest = float(rev_row.iloc[0])
        prev   = float(rev_row.iloc[4])
        if prev and prev != 0:
            return (latest - prev) / abs(prev)
    except Exception:
        pass
    return None


def _get_fcf_values(ticker_obj) -> tuple[Optional[float], Optional[float]]:
    """FCF letztes Quartal + Vorquartal aus cash flow statement."""
    try:
        cf = ticker_obj.quarterly_cashflow
        if cf is None or cf.empty:
            return None, None
        fcf_row = None
        for lbl in ("Free Cash Flow", "FreeCashFlow"):
            if lbl in cf.index:
                fcf_row = cf.loc[lbl]
                break
        if fcf_row is None or len(fcf_row) < 1:
            return None, None
        latest = float(fcf_row.iloc[0])
        prev   = float(fcf_row.iloc[1]) if len(fcf_row) >= 2 else None
        return latest, prev
    except Exception:
        return None, None


def _build_eps_history(info: dict) -> list[dict]:
    """
    Approximierte EPS-Beat-Historie für score_eps_beat_streak().
    yfinance liefert keine direkte Beat-Historie → einfache Schätzung:
    1 Beat wenn trailing EPS > forward EPS * 0.95.
    """
    eps     = info.get("trailingEps")
    eps_fwd = info.get("epsForward")
    if eps and eps_fwd and eps > eps_fwd * 0.95:
        return [{"beat": True}, {"beat": True}]   # 2 Quartale positiv
    return [{"beat": False}]                        # neutral


# ── Handelstage ermitteln ─────────────────────────────────────────────────────

def get_trading_days(df_ohlcv: pd.DataFrame, from_date: str, to_date: str) -> list[str]:
    """
    Gibt alle Handelstage im Zielzeitraum zurück (Index aus OHLCV gefiltert).
    Nur Tage, für die auch OHLCV-Daten existieren (kein Wochenende, keine Feiertage).
    """
    from_dt = pd.Timestamp(from_date)
    to_dt   = pd.Timestamp(to_date)
    mask    = (df_ohlcv.index >= from_dt) & (df_ohlcv.index <= to_dt)
    return [d.strftime("%Y-%m-%d") for d in df_ohlcv.index[mask]]
