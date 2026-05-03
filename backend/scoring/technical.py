"""Scoring-Ebene 2: Technische Analyse (max. 35 Punkte).

Kriterien:
  1. VCP-Muster               – max. 10 Pkt.
  2. Volumen-Kontraktion      – max.  5 Pkt.
  3. Preis-Nähe zu Widerstand – max.  5 Pkt.
  4. RSI 55–70                – max.  5 Pkt.
  5. Relative Stärke vs. SPY  – max.  4 Pkt.
  6. MACD-Signal (ta-Lib)     – max.  3 Pkt.
  7. Bollinger-Squeeze        – max.  3 Pkt.
"""
import logging
import pandas as pd
import ta
from sqlalchemy.orm import Session

from backend.fetchers.yfinance_fetcher import YFinanceFetcher

logger = logging.getLogger(__name__)


# ── Hilfsfunktionen ─────────────────────────────────────────────────────────

def _to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resampling täglich → wöchentlich (W-FRI)."""
    df = df.copy()
    if "Date" in df.columns:
        df = df.set_index("Date")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    # Nur benötigte Spalten mit passenden Aggregationen
    agg = {}
    if "Open" in df.columns:
        agg["Open"] = "first"
    if "High" in df.columns:
        agg["High"] = "max"
    if "Low" in df.columns:
        agg["Low"] = "min"
    if "Close" in df.columns:
        agg["Close"] = "last"
    if "Volume" in df.columns:
        agg["Volume"] = "sum"
    return df.resample("W-FRI").agg(agg).dropna(subset=["Close"])


def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    """Stellt sicher, dass der DataFrame einen DatetimeIndex hat."""
    df = df.copy()
    if "Date" in df.columns:
        df = df.set_index("Date")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df


# ── VCP-Erkennung ────────────────────────────────────────────────────────────

def _detect_vcp(df_weekly: pd.DataFrame) -> tuple[int, bool]:
    """
    VCP (Volatility Contraction Pattern) nach Minervini erkennen.
    Returns (num_contractions, volume_confirms).
    """
    if len(df_weekly) < 8:
        return 0, False

    w = df_weekly.tail(20)

    # 52W-Hoch aus verfügbaren Daten
    high_52w = float(df_weekly.tail(52)["High"].max()) if len(df_weekly) >= 52 else float(df_weekly["High"].max())
    current  = float(w["Close"].iloc[-1])

    # Pflichtbedingung: Kurs innerhalb 10% des 52W-Hochs
    if current < high_52w * 0.90:
        return 0, False

    highs = w["High"].values.astype(float)
    lows  = w["Low"].values.astype(float)
    vols  = w["Volume"].values.astype(float)
    n     = len(highs)

    # Lokale Swing-Hochs (jedes Hoch >= beide Nachbarn)
    swing_highs: list[tuple[int, float]] = []
    for i in range(1, n - 1):
        if highs[i] >= highs[i - 1] and highs[i] >= highs[i + 1]:
            swing_highs.append((i, highs[i]))

    if len(swing_highs) < 2:
        return 0, False

    # Pullback-Tiefe und Volumen vom Swing-Hoch zum nächsten Tief
    pullbacks: list[float] = []
    vol_in_pullbacks: list[float] = []

    for sh_idx, sh_price in swing_highs:
        if sh_idx + 1 >= n:
            continue
        # Kleinstes Tief in einem Fenster von bis zu 6 Wochen nach dem Hoch
        end = min(sh_idx + 7, n)
        slice_lows = lows[sh_idx + 1:end]
        if len(slice_lows) == 0:
            continue
        min_low_idx = int(slice_lows.argmin())
        min_low_val = float(slice_lows[min_low_idx])

        depth = (sh_price - min_low_val) / sh_price
        if depth <= 0:
            continue

        abs_end = sh_idx + 1 + min_low_idx + 1
        avg_vol = float(vols[sh_idx:abs_end].mean())
        pullbacks.append(depth)
        vol_in_pullbacks.append(avg_vol)

    if len(pullbacks) < 2:
        return 0, False

    # Kontraktionen zählen: jede Tiefe < 85% der vorherigen
    contractions = 0
    vol_contracting_count = 0

    for i in range(1, len(pullbacks)):
        if pullbacks[i] < pullbacks[i - 1] * 0.85:
            contractions += 1
        if vol_in_pullbacks[i] < vol_in_pullbacks[i - 1]:
            vol_contracting_count += 1

    volume_confirms = vol_contracting_count >= max(1, (len(pullbacks) - 1) // 2)
    return contractions, volume_confirms


def score_vcp(df_weekly: pd.DataFrame) -> float:
    """VCP-Score – max. 10 Pkt."""
    if df_weekly.empty:
        return 0.0
    contractions, vol_ok = _detect_vcp(df_weekly)
    if contractions >= 3:
        return 10.0
    if contractions == 2:
        return 7.0
    if contractions == 1 and vol_ok:
        return 4.0
    return 0.0


# ── Volumen-Kontraktion ──────────────────────────────────────────────────────

def score_volume_contraction(df_weekly: pd.DataFrame) -> float:
    """
    3W-Ø-Volumen vs. 10W-Ø-Volumen.
    < 80% → 5 Pkt.; < 90% → 3 Pkt.; sonst 0.
    """
    if len(df_weekly) < 5:
        return 0.0
    w       = df_weekly.tail(10)
    avg_3w  = float(w["Volume"].tail(3).mean())
    avg_10w = float(w["Volume"].mean())
    if avg_10w == 0:
        return 0.0
    ratio = avg_3w / avg_10w
    if ratio < 0.80:
        return 5.0
    if ratio < 0.90:
        return 3.0
    return 0.0


# ── Preis-Nähe zu Widerstand ─────────────────────────────────────────────────

def score_price_vs_resistance(df: pd.DataFrame, high_52w: float | None) -> float:
    """
    Abstand Kurs zu Pivot/52W-Hoch.
    < 3% → 5; 3–7% → 3; 7–10% → 1; > 10% → 0.
    """
    if df.empty:
        return 0.0
    current    = float(df["Close"].iloc[-1])
    resistance = high_52w if (high_52w and high_52w > 0) else float(df["High"].max())
    if resistance <= 0 or current <= 0:
        return 0.0
    distance = (resistance - current) / resistance
    if distance < 0.03:
        return 5.0
    if distance < 0.07:
        return 3.0
    if distance < 0.10:
        return 1.0
    return 0.0


# ── RSI 55–70 ────────────────────────────────────────────────────────────────

def score_rsi(df: pd.DataFrame) -> tuple[float, float | None]:
    """RSI-Zonen-Score – max. 5 Pkt. Gibt (score, rsi_wert) zurück."""
    if len(df) < 20:
        return 0.0, None
    try:
        close = df["Close"].ffill().dropna()
        rsi_series = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        rsi_val    = rsi_series.dropna()
        if rsi_val.empty:
            return 0.0, None
        rsi = float(rsi_val.iloc[-1])
        if 55 <= rsi <= 70:
            return 5.0, rsi
        if (50 <= rsi < 55) or (70 < rsi <= 75):
            return 3.0, rsi
        return 0.0, rsi
    except Exception as exc:
        logger.debug("RSI-Berechnung fehlgeschlagen: %s", exc)
        return 0.0, None


# ── Relative Stärke vs. SPY ──────────────────────────────────────────────────

def score_relative_strength(df: pd.DataFrame, df_spy: pd.DataFrame) -> float:
    """RS über 20 Handelstage vs. SPY – max. 4 Pkt."""
    if len(df) < 21 or len(df_spy) < 21:
        return 0.0
    try:
        close_t = df["Close"].ffill()
        close_s = df_spy["Close"].ffill()
        ticker_ret = float(close_t.iloc[-1]) / float(close_t.iloc[-21])
        spy_ret    = float(close_s.iloc[-1]) / float(close_s.iloc[-21])
        if spy_ret == 0:
            return 0.0
        rs = ticker_ret / spy_ret
        if rs > 1.1:
            return 4.0
        if rs >= 1.0:
            return 2.0
        return 0.0
    except Exception as exc:
        logger.debug("RS-Berechnung fehlgeschlagen: %s", exc)
        return 0.0


# ── MACD-Signal ──────────────────────────────────────────────────────────────

def score_macd(df: pd.DataFrame) -> float:
    """MACD-Histogramm via ta-Bibliothek – max. 3 Pkt."""
    if len(df) < 35:
        return 0.0
    try:
        close = df["Close"].ffill().dropna()
        macd  = ta.trend.MACD(close=close)
        hist  = macd.macd_diff().dropna()
        if len(hist) < 2:
            return 0.0
        last = float(hist.iloc[-1])
        prev = float(hist.iloc[-2])
        if last > 0 and last > prev:
            return 3.0
        if last > 0:
            return 1.0
        return 0.0
    except Exception as exc:
        logger.debug("MACD-Berechnung fehlgeschlagen: %s", exc)
        return 0.0


# ── Bollinger-Squeeze ────────────────────────────────────────────────────────

def score_bollinger_squeeze(df: pd.DataFrame) -> float:
    """
    BB-Breite < 20. Perzentil der letzten ~52 Wochen (252 Handelstage).
    Indikator für komprimierte Volatilität vor Ausbruch.
    """
    window_days = min(len(df), 252)
    if window_days < 50:
        return 0.0
    try:
        close = df["Close"].ffill().dropna()
        bb    = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        width = bb.bollinger_wband().dropna()  # Relative Breite in %
        if len(width) < 20:
            return 0.0
        recent        = width.tail(window_days)
        current_width = float(recent.iloc[-1])
        pct_20        = float(recent.quantile(0.20))
        if current_width < pct_20:
            return 3.0
        return 0.0
    except Exception as exc:
        logger.debug("Bollinger-Squeeze fehlgeschlagen: %s", exc)
        return 0.0


# ── Aggregator ───────────────────────────────────────────────────────────────

def compute_technical_score(ticker: str, db: Session) -> tuple[float, dict]:
    """
    Berechnet den Technischen Score (max. 35 Punkte).
    Gibt (total_score, breakdown_dict) zurück.
    """
    yf_f = YFinanceFetcher(db)

    df_raw    = yf_f.get_ohlcv(ticker, period="1y", interval="1d")
    df_spy_raw = yf_f.get_spy_ohlcv(period="3mo")

    _zero = {
        "vcp_score":           0.0,
        "volume_contraction":  0.0,
        "price_vs_resistance": 0.0,
        "rsi_zone":            0.0,
        "relative_strength":   0.0,
        "macd_signal":         0.0,
        "bollinger_squeeze":   0.0,
    }

    if df_raw.empty:
        logger.warning("Technical %s: Keine OHLCV-Daten verfügbar", ticker)
        return 0.0, _zero

    # Einheitlichen DatetimeIndex sicherstellen
    df_daily = _ensure_datetime_index(df_raw)
    df_spy   = _ensure_datetime_index(df_spy_raw) if not df_spy_raw.empty else pd.DataFrame()

    df_weekly = _to_weekly(df_daily)

    # 52W-Hoch aus Fundamentals (als Widerstandsreferenz)
    fund     = yf_f.get_fundamentals(ticker)
    high_52w = fund.get("high_52w")

    s_vcp    = score_vcp(df_weekly)
    s_vol    = score_volume_contraction(df_weekly)
    s_price  = score_price_vs_resistance(df_daily, high_52w)
    s_rsi, _ = score_rsi(df_daily)
    s_rs     = score_relative_strength(df_daily, df_spy)
    s_macd   = score_macd(df_daily)
    s_boll   = score_bollinger_squeeze(df_daily)

    total = s_vcp + s_vol + s_price + s_rsi + s_rs + s_macd + s_boll

    breakdown = {
        "vcp_score":           s_vcp,
        "volume_contraction":  s_vol,
        "price_vs_resistance": s_price,
        "rsi_zone":            s_rsi,
        "relative_strength":   s_rs,
        "macd_signal":         s_macd,
        "bollinger_squeeze":   s_boll,
    }

    logger.debug("Technical %s: %.1f/35 – VCP=%.0f Vol=%.0f Res=%.0f RSI=%.0f RS=%.0f MACD=%.0f BB=%.0f",
                 ticker, total, s_vcp, s_vol, s_price, s_rsi, s_rs, s_macd, s_boll)
    return round(total, 1), breakdown
