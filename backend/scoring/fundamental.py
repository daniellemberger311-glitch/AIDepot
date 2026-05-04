"""Scoring-Ebene 1: Fundamentalanalyse (max. 40 Punkte).

Kriterien:
  1. KGV vs. Sektorschnitt       – max. 8 Pkt.
  2. EPS-Überraschungs-Streak    – max. 6 Pkt.
  3. Umsatzwachstum YoY          – max. 6 Pkt.
  4. Free Cashflow                – max. 5 Pkt.
  5. Verschuldungsgrad (D/E)      – max. 5 Pkt.
  6. Insider-Käufe netto (90T)   – max. 5 Pkt.
  7. Earnings-Nähe (Katalysator) – max. 5 Pkt.
"""
import logging
from sqlalchemy.orm import Session

from backend.fetchers.yfinance_fetcher import YFinanceFetcher
from backend.fetchers.simfin_fetcher import SimFinFetcher
from backend.fetchers.finnhub_fetcher import FinnhubFetcher

logger = logging.getLogger(__name__)

# Typische Trailing-KGV-Durchschnitte je Sektor (Stand 2024/2025)
SECTOR_PE_AVERAGES: dict[str, float] = {
    "Technology":             28.0,
    "Healthcare":             22.0,
    "Financial Services":     14.0,
    "Consumer Cyclical":      20.0,
    "Consumer Defensive":     20.0,
    "Industrials":            20.0,
    "Basic Materials":        15.0,
    "Energy":                 12.0,
    "Utilities":              18.0,
    "Real Estate":            35.0,
    "Communication Services": 20.0,
}
_DEFAULT_SECTOR_PE = 20.0


def _sector_pe(sector: str) -> float:
    return SECTOR_PE_AVERAGES.get(sector, _DEFAULT_SECTOR_PE)


# ── Einzelne Kriterien ──────────────────────────────────────────────────────

def score_pe_vs_sector(pe_ratio: float | None, sector: str) -> float:
    """KGV vs. Sektorschnitt – max. 8 Pkt."""
    if pe_ratio is None or pe_ratio <= 0:
        return 2.0  # neutral bei fehlenden Daten
    if not sector or sector not in SECTOR_PE_AVERAGES:
        return 2.0  # neutral wenn Sektor unbekannt – kein Vergleich möglich
    avg = _sector_pe(sector)
    ratio = pe_ratio / avg
    if ratio < 0.75:
        return 8.0
    if ratio < 1.0:
        return 6.0
    if ratio < 1.25:
        return 4.0
    if ratio < 1.5:
        return 2.0
    return 0.0


def score_eps_beat_streak(eps_history: list[dict]) -> float:
    """EPS-Überraschungs-Streak – max. 6 Pkt. (+2 pro aufeinanderfolgendem Beat)."""
    streak = 0
    for q in (eps_history or [])[:3]:
        if q.get("beat"):
            streak += 1
        else:
            break  # Streak endet beim ersten Nicht-Beat
    return float(min(streak * 2, 6))


def score_revenue_growth(growth_rate: float | None) -> float:
    """Umsatzwachstum YoY – max. 6 Pkt."""
    if growth_rate is None:
        return 2.0  # neutral
    if growth_rate > 0.20:
        return 6.0
    if growth_rate > 0.10:
        return 4.0
    if growth_rate >= 0.0:
        return 2.0
    return 0.0


def score_fcf(fcf: float | None, fcf_prev: float | None) -> float:
    """FCF positiv und wachsend – max. 5 Pkt."""
    if fcf is None:
        return 1.0  # neutral bei fehlenden Daten (wie andere Kriterien)
    pts = 0.0
    if fcf > 0:
        pts += 2.0
        if fcf_prev is not None and fcf > fcf_prev:
            pts += 3.0
    return pts


def score_debt_equity(de_ratio: float | None) -> float:
    """Verschuldungsgrad (D/E) – max. 5 Pkt.
    yfinance liefert de_ratio als Prozent-Wert (50 = 0,5x D/E).
    """
    if de_ratio is None:
        return 2.0  # neutral
    # Normalisieren: yfinance gibt Werte wie 50.0 (= 50% = 0.5x D/E)
    de = de_ratio / 100.0 if de_ratio > 10 else de_ratio
    if de < 0.5:
        return 5.0
    if de < 1.0:
        return 3.0
    if de < 2.0:
        return 1.0
    return 0.0


def score_insider_net(buy_count: int, sell_count: int) -> float:
    """Insider-Käufe netto (90 Tage) – max. 5 Pkt."""
    net = buy_count - sell_count
    if net >= 3:
        return 5.0
    if net >= 1:
        return 3.0
    if net == 0:
        return 1.0
    return 0.0  # Netto-Verkäufe


def score_earnings_proximity(days_to_earnings: int | None) -> float:
    """Earnings-Nähe als Katalysator – max. 5 Pkt."""
    if days_to_earnings is None:
        return 1.0  # kein Termin bekannt
    if 7 <= days_to_earnings <= 14:
        return 5.0
    if 3 <= days_to_earnings < 7:
        return 3.0
    return 1.0  # > 14 Tage oder < 3 Tage (schon kurz davor / eingepreist)


# ── Aggregator ──────────────────────────────────────────────────────────────

def compute_fundamental_score(ticker: str, db: Session) -> tuple[float, dict]:
    """
    Berechnet den Fundamental-Score (max. 40 Punkte).
    Gibt (total_score, breakdown_dict) zurück.
    """
    yf_f = YFinanceFetcher(db)
    sf_f = SimFinFetcher(db)
    fh_f = FinnhubFetcher(db)

    fundamentals = yf_f.get_fundamentals(ticker)
    earnings     = yf_f.get_earnings_calendar(ticker)
    simfin       = sf_f.get_fundamentals(ticker)

    # Insider: Finnhub bevorzugt, yfinance als Fallback
    fh_insider = fh_f.get_insider_transactions(ticker)
    if fh_insider.get("buy_count", 0) == 0 and fh_insider.get("sell_count", 0) == 0:
        insider = yf_f.get_insider_summary(ticker)
    else:
        insider = fh_insider

    # EPS-Beats: Finnhub bevorzugt, yfinance-Fallback
    fh_eps = fh_f.get_earnings_surprises(ticker)
    eps_history = fh_eps if fh_eps else earnings.get("eps_history", [])

    # Umsatzwachstum: SimFin bevorzugt, yfinance als Fallback
    rev      = simfin.get("revenue")
    rev_prev = simfin.get("revenue_prev_year")
    if rev and rev_prev and rev_prev > 0:
        growth_rate = (rev - rev_prev) / rev_prev
    else:
        growth_rate = fundamentals.get("revenue_growth")  # yfinance YoY als Dezimalzahl

    # Free Cashflow: SimFin bevorzugt, yfinance als Fallback
    fcf      = simfin.get("free_cashflow") or fundamentals.get("free_cashflow")
    fcf_prev = simfin.get("fcf_prev_year")

    pe_ratio = fundamentals.get("pe_ratio")
    sector   = fundamentals.get("sector", "")
    de_ratio = fundamentals.get("debt_to_equity")

    # ── Teilscores ──────────────────────────────────────────────────────────
    s_pe       = score_pe_vs_sector(pe_ratio, sector)
    s_eps      = score_eps_beat_streak(eps_history)
    s_rev      = score_revenue_growth(growth_rate)
    s_fcf      = score_fcf(fcf, fcf_prev)
    s_de       = score_debt_equity(de_ratio)
    s_insider  = score_insider_net(insider.get("buy_count", 0), insider.get("sell_count", 0))
    s_earnings = score_earnings_proximity(earnings.get("days_to_earnings"))

    total = s_pe + s_eps + s_rev + s_fcf + s_de + s_insider + s_earnings

    breakdown = {
        "pe_vs_sector":         s_pe,
        "eps_beat_streak":      s_eps,
        "revenue_growth":       s_rev,
        "fcf_score":            s_fcf,
        "debt_equity":          s_de,
        "insider_net":          s_insider,
        "earnings_proximity":   s_earnings,
        # Metadaten für Orchestrator und Diagnose
        "_pe_ratio":            pe_ratio,
        "_sector":              sector,
        "_growth_rate":         growth_rate,
        "_days_earn":           earnings.get("days_to_earnings"),
        "_next_earnings_date":  earnings.get("next_earnings_date"),
    }

    logger.debug("Fundamental %s: %.1f/40 – KGV=%.1f EPS=%.0f Rev=%.0f FCF=%.0f DE=%.0f Ins=%.0f Earn=%.0f",
                 ticker, total, s_pe, s_eps, s_rev, s_fcf, s_de, s_insider, s_earnings)
    return round(total, 1), breakdown
