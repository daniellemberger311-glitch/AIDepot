"""Backtesting-Engine: berechnet tägliche Scores für einen historischen Zeitraum.

Architektur:
  1. Einmalig: OHLCV + SPY + Fundamentals laden (yfinance)
  2. Für jeden Handelstag im Zielzeitraum:
     a. OHLCV-Slice bis zu diesem Tag
     b. Technische Indikatoren aus Slice berechnen (direkte Funktionen aus scoring/technical.py)
     c. Fundamentals: statisch (Quartalswerte gelten pro Tag des Quartals)
     d. Sentiment: immer neutral = 12.5/25 (historische Daten nicht verfügbar)
     e. Total-Score + Zone berechnen
     f. Deltas aus den bisherigen Tages-Scores berechnen
  3. Rückgabe: list[BacktestDataPoint]

Einschränkungen:
  - Sentiment immer 12,5/25 (historisch nicht verfügbar)
  - Fundamental-Scores werden täglich gleich gewertet (Quartalsaktualisierung)
  - Earnings-Nähe-Kriterium entfällt (historische Earnings-Daten schwer verfügbar)
  - Insider-Transaktionen entfallen (kein historischer Free-Datenzugang)
"""
import logging
from typing import Optional

import pandas as pd

from backend.backtesting.historical_data import (
    get_ohlcv, get_spy_ohlcv, get_fundamentals, get_trading_days,
)
from backend.scoring.technical import (
    _to_weekly, _ensure_datetime_index,
    score_vcp, score_volume_contraction, score_price_vs_resistance,
    score_rsi, score_relative_strength, score_macd, score_bollinger_squeeze,
)
from backend.scoring.fundamental import (
    score_pe_vs_sector, score_eps_beat_streak, score_revenue_growth,
    score_fcf, score_debt_equity,
)
from backend.schemas import BacktestDataPoint

logger = logging.getLogger(__name__)

# Sentiment-Neutral-Wert (12,5/25 = 50 % der Maximalpunkte)
_SENTIMENT_NEUTRAL = 12.5

# Mindest-Lookback-Tage für sinnvolle Indikatoren
_MIN_LOOKBACK = 60


def _assign_zone(score: float) -> int:
    if score >= 76:
        return 1
    if score >= 61:
        return 2
    if score >= 41:
        return 3
    return 4


def _apply_suppression(l1: float, l2: float, l3: float) -> float:
    """Unterdrückungsregel: L1+L2 > 50 und L3 < 5 → max. 74."""
    total = l1 + l2 + l3
    if (l1 + l2) > 50 and l3 < 5:
        return min(total, 74.0)
    return total


# ── Fundamental-Score aus vorgeladenen Daten ─────────────────────────────────

def _compute_l1(fund: dict) -> float:
    """L1-Fundamental-Score aus pre-fetched fundamentals dict (max. 40 Pkt.)."""
    s_pe  = score_pe_vs_sector(fund.get("pe_ratio"), fund.get("sector", ""))
    s_eps = score_eps_beat_streak(fund.get("eps_history", []))
    s_rev = score_revenue_growth(fund.get("revenue_growth_yoy"))
    s_fcf = score_fcf(fund.get("fcf_latest"), fund.get("fcf_prev"))
    s_de  = score_debt_equity(fund.get("debt_equity"))
    # Insider-Käufe + Earnings-Nähe: neutral (historisch nicht verfügbar)
    s_ins  = 1.0
    s_earn = 1.0
    return round(s_pe + s_eps + s_rev + s_fcf + s_de + s_ins + s_earn, 1)


# ── Technischer Score aus OHLCV-Slice ────────────────────────────────────────

def _compute_l2(df_slice: pd.DataFrame, df_spy_slice: pd.DataFrame) -> float:
    """L2-Technischer Score aus tagesaktuellem OHLCV-Slice (max. 35 Pkt.)."""
    if df_slice.empty or len(df_slice) < _MIN_LOOKBACK:
        return 0.0

    df_daily  = _ensure_datetime_index(df_slice)
    df_weekly = _to_weekly(df_daily)
    df_spy    = _ensure_datetime_index(df_spy_slice) if not df_spy_slice.empty else pd.DataFrame()

    high_52w = float(df_daily["High"].tail(252).max()) if len(df_daily) >= 252 else float(df_daily["High"].max())

    s_vcp,       _  = score_vcp(df_weekly),              None
    s_vcp            = score_vcp(df_weekly)
    s_vol            = score_volume_contraction(df_weekly)
    s_price          = score_price_vs_resistance(df_daily, high_52w)
    s_rsi,       _  = score_rsi(df_daily)
    s_rs             = score_relative_strength(df_daily, df_spy)
    s_macd           = score_macd(df_daily)
    s_boll           = score_bollinger_squeeze(df_daily)

    return round(s_vcp + s_vol + s_price + s_rsi + s_rs + s_macd + s_boll, 1)


# ── Deltas berechnen ─────────────────────────────────────────────────────────

def _compute_deltas(scores: list[float], idx: int) -> tuple[Optional[float], Optional[float]]:
    """Δ1T und Δ7T aus bisheriger Score-Liste."""
    delta_1d = round(scores[idx] - scores[idx - 1], 1) if idx >= 1 else None
    delta_7d = round(scores[idx] - scores[idx - 7], 1) if idx >= 7 else None
    return delta_1d, delta_7d


# ── Haupt-Engine ─────────────────────────────────────────────────────────────

def run_backtest(ticker: str, from_date: str, to_date: str) -> list[BacktestDataPoint]:
    """
    Tägliche Scores für den angegebenen Zeitraum berechnen.

    Gibt eine nach Datum sortierte Liste von BacktestDataPoint zurück.
    Gibt [] zurück wenn keine OHLCV-Daten verfügbar.
    """
    logger.info("Backtest %s: %s → %s", ticker, from_date, to_date)

    # ── Rohdaten laden ───────────────────────────────────────────────────────
    df_all   = get_ohlcv(ticker, from_date, to_date)
    df_spy   = get_spy_ohlcv(from_date, to_date)
    fund     = get_fundamentals(ticker)

    if df_all.empty:
        logger.warning("Backtest %s: Keine OHLCV-Daten – abgebrochen", ticker)
        return []

    trading_days = get_trading_days(df_all, from_date, to_date)
    if not trading_days:
        return []

    logger.info("Backtest %s: %d Handelstage", ticker, len(trading_days))

    # ── L1 einmalig berechnen (statische Fundamentals) ───────────────────────
    l1_score = _compute_l1(fund)

    # ── Tagesweise iterieren ─────────────────────────────────────────────────
    daily_scores: list[float] = []
    data_points:  list[BacktestDataPoint] = []

    for i, day in enumerate(trading_days):
        day_ts = pd.Timestamp(day)

        # OHLCV bis einschließlich dieses Tages
        df_slice     = df_all[df_all.index <= day_ts]
        df_spy_slice = df_spy[df_spy.index <= day_ts] if not df_spy.empty else pd.DataFrame()

        if df_slice.empty:
            continue

        close = float(df_slice["Close"].iloc[-1])

        # L2 – Technisch
        try:
            l2_score = _compute_l2(df_slice, df_spy_slice)
        except Exception as exc:
            logger.debug("L2 für %s am %s fehlgeschlagen: %s", ticker, day, exc)
            l2_score = 0.0

        # L3 – Sentiment (immer neutral)
        l3_score = _SENTIMENT_NEUTRAL

        # Gesamt-Score
        total = _apply_suppression(l1_score, l2_score, l3_score)
        zone  = _assign_zone(total)

        daily_scores.append(total)
        delta_1d, delta_7d = _compute_deltas(daily_scores, i)

        data_points.append(BacktestDataPoint(
            date     = day,
            close    = round(close, 4),
            score    = round(total, 1),
            zone     = zone,
            delta_1d = delta_1d,
            delta_7d = delta_7d,
        ))

        if (i + 1) % 50 == 0:
            logger.debug("Backtest %s: %d/%d Tage", ticker, i + 1, len(trading_days))

    logger.info("Backtest %s abgeschlossen: %d Datenpunkte", ticker, len(data_points))
    return data_points
