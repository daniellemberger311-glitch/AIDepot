"""Optionsschein-Empfehlung: Parameter-Ableitung für Zone-1-Aktien.

Ableitungsregeln:
  Richtung:    CALL bei steigendem Δ7T (Standard); PUT nur bei explizit negativem Δ7T
  Hebel:       ATR/Kurs < 2% → 5–6x; 2–3% → 5–7x; > 3% → 6–8x
  Laufzeit:    8 Wochen Basis; +2 Wochen wenn Earnings ≤ 6 Wochen entfernt
  KO-Abstand:  max(12%, 3 × ATR%)
  Einstieg:    ~2% über aktuellem Kurs (Breakout-Signal)
  Stop-Loss:   Letztes lokales Tief (20 Tage OHLCV)
"""
import logging
import pandas as pd
import ta
from sqlalchemy.orm import Session

from backend.fetchers.yfinance_fetcher import YFinanceFetcher

logger = logging.getLogger(__name__)


def _compute_atr_pct(df: pd.DataFrame) -> float:
    """ATR (14 Tage) als Prozent des aktuellen Kurses. Fallback: 2.0%."""
    if len(df) < 15:
        return 0.02
    try:
        atr_ind = ta.volatility.AverageTrueRange(
            high=df["High"].ffill(),
            low=df["Low"].ffill(),
            close=df["Close"].ffill(),
            window=14,
        )
        atr = float(atr_ind.average_true_range().dropna().iloc[-1])
        price = float(df["Close"].iloc[-1])
        if price <= 0:
            return 0.02
        return atr / price
    except Exception as exc:
        logger.debug("ATR-Berechnung fehlgeschlagen: %s", exc)
        return 0.02


def _last_pivot_low(df: pd.DataFrame, lookback: int = 20) -> float | None:
    """Letztes lokales Tief der letzten N Handelstage (Stop-Loss-Basis)."""
    if len(df) < lookback:
        return None
    recent = df.tail(lookback)
    lows   = recent["Low"].values.astype(float)
    pivot  = None
    for i in range(1, len(lows) - 1):
        if lows[i] < lows[i - 1] and lows[i] <= lows[i + 1]:
            pivot = lows[i]  # Letztes lokales Tief überschreibt vorherige
    return float(pivot) if pivot is not None else None


def _ensure_daily_index(df: pd.DataFrame) -> pd.DataFrame:
    """Sicherstellt, dass der DataFrame keine Date-Spalte als Index-Wert hat."""
    df = df.copy()
    if "Date" in df.columns:
        df = df.set_index("Date")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df


def derive_options_params(
    ticker: str,
    total_score: float,
    delta_7d: float | None,
    days_to_earnings: int | None,
    db: Session,
) -> dict:
    """
    Leitet Optionsschein-Parameter für Zone-1-Aktien ab.
    Gibt ein vollständiges Parameter-Dict zurück (leer bei Datenfehler).
    """
    yf_f = YFinanceFetcher(db)
    df_raw = yf_f.get_ohlcv(ticker, period="3mo", interval="1d")

    if df_raw.empty:
        logger.warning("options.py: Keine OHLCV-Daten für %s", ticker)
        return {}

    df = _ensure_daily_index(df_raw)

    current_price = float(df["Close"].iloc[-1])
    if current_price <= 0:
        return {}

    atr_pct   = _compute_atr_pct(df)
    pivot_low = _last_pivot_low(df)

    # Hebel-Empfehlung: höhere Volatilität → höherer Hebel
    if atr_pct < 0.02:
        leverage_min, leverage_max = 5, 6
    elif atr_pct < 0.03:
        leverage_min, leverage_max = 5, 7
    else:
        leverage_min, leverage_max = 6, 8

    # Laufzeit: 8 Wochen Basis, +2 wenn Earnings innerhalb 6 Wochen
    duration_weeks = 8
    if days_to_earnings is not None and 0 < days_to_earnings <= 42:
        duration_weeks += 2

    # KO-Abstand: max(12%, 3 × ATR%)
    ko_distance_pct = max(0.12, 3.0 * atr_pct)

    # Einstiegs-Trigger: ~2% über aktuellem Kurs (Breakout-Bestätigung)
    entry_trigger = round(current_price * 1.02, 4)

    # Stop-Loss: letztes Pivot-Tief oder 5%-Fallback
    stop_loss = round(pivot_low, 4) if pivot_low else round(current_price * 0.95, 4)

    # Richtung: PUT nur wenn Δ7T explizit negativ (sehr ungewöhnlich für Zone 1)
    direction = "PUT" if (delta_7d is not None and delta_7d < -5) else "CALL"

    params = {
        "direction":       direction,
        "leverage_min":    float(leverage_min),
        "leverage_max":    float(leverage_max),
        "duration_weeks":  duration_weeks,
        "ko_distance_pct": round(ko_distance_pct * 100, 1),   # Als Prozentzahl, z.B. 12.5
        "entry_trigger":   entry_trigger,
        "stop_loss":       stop_loss,
        "base_price":      round(current_price, 4),
        "atr_pct":         round(atr_pct * 100, 2),            # Als Prozentzahl, z.B. 1.85
    }

    logger.debug("Options %s: %s Hebel %d–%dx Laufzeit %dW KO %.1f%% Entry %.2f SL %.2f",
                 ticker, direction, leverage_min, leverage_max, duration_weeks,
                 ko_distance_pct * 100, entry_trigger, stop_loss)
    return params
