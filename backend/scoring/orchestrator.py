"""Scoring-Orchestrator: Koordiniert alle 3 Ebenen und schreibt in die DB.

Ablauf für jeden Ticker:
  1. Fundamental-Score (L1, max. 40 Pkt.)
  2. Technischer Score (L2, max. 35 Pkt.)
  3. Sentiment-Score  (L3, max. 25 Pkt.)
  4. Unterdrückungsregel (L1+L2 > 50 und L3 < 5 → max. 74)
  5. Zone bestimmen (1/2/3/4)
  6. Deltas berechnen (Δ1T, Δ7T, Δ30T)
  7. Optionsschein-Empfehlung (nur Zone 1)
  8. DB-Schreiboperationen (daily_scores, score_history, score_breakdown, watchlist)
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.scoring.fundamental import compute_fundamental_score
from backend.scoring.technical   import compute_technical_score
from backend.scoring.sentiment   import compute_sentiment_score, apply_suppression_rule
from backend.scoring.delta       import compute_deltas
from backend.scoring.options     import derive_options_params
from backend.models import (
    DailyScore, ScoreHistory, ScoreBreakdown, WatchlistEntry,
    OptionsRecommendation, Stock,
)
from backend.fetchers.yfinance_fetcher import YFinanceFetcher

logger = logging.getLogger(__name__)


# ── Hilfsfunktionen ─────────────────────────────────────────────────────────

def _assign_zone(score: float) -> int:
    if score >= 76:
        return 1
    if score >= 61:
        return 2
    if score >= 41:
        return 3
    return 4


def _strongest_signal(l1_bd: dict, l2_bd: dict, l3_bd: dict) -> str:
    """Kriterium mit dem höchsten Verhältnis (erreicht/max) bestimmen."""
    candidates = {
        "VCP":        (l2_bd.get("vcp_score", 0),          10),
        "Breakout":   (l2_bd.get("price_vs_resistance", 0), 5),
        "EPS-Streak": (l1_bd.get("eps_beat_streak", 0),     6),
        "Umsatz":     (l1_bd.get("revenue_growth", 0),      6),
        "Sentiment":  (l3_bd.get("news_sentiment", 0),      8),
        "Insider":    (l1_bd.get("insider_net", 0),         5),
        "RS":         (l2_bd.get("relative_strength", 0),   4),
        "Bollinger":  (l2_bd.get("bollinger_squeeze", 0),   3),
    }
    best_name, best_ratio = "–", 0.0
    for name, (val, max_val) in candidates.items():
        if max_val > 0:
            ratio = val / max_val
            if ratio > best_ratio:
                best_ratio, best_name = ratio, name
    return best_name


def _upsert(model_class, filter_kwargs: dict, update_kwargs: dict, db: Session) -> None:
    """Generischer Upsert: Zeile aktualisieren oder neu anlegen."""
    stmt = select(model_class)
    for k, v in filter_kwargs.items():
        stmt = stmt.where(getattr(model_class, k) == v)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        for k, v in update_kwargs.items():
            setattr(existing, k, v)
    else:
        db.add(model_class(**filter_kwargs, **update_kwargs))


def _update_watchlist(ticker: str, new_zone: int, db: Session) -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    entry = db.get(WatchlistEntry, ticker)
    if entry:
        if entry.current_zone != new_zone and not entry.manual_override:
            entry.previous_zone = entry.current_zone
            entry.current_zone  = new_zone
            entry.zone_since    = today
        entry.updated_at = datetime.utcnow().isoformat()
    else:
        db.add(WatchlistEntry(
            ticker=ticker, current_zone=new_zone,
            previous_zone=None, zone_since=today,
        ))


def _save_options_rec(
    ticker: str, score_date: str, params: dict, total_score: float, db: Session
) -> None:
    """Speichert Optionsschein-Empfehlung (nur wenn noch nicht vorhanden)."""
    if not params:
        return
    existing = db.execute(
        select(OptionsRecommendation)
        .where(OptionsRecommendation.ticker == ticker)
        .where(OptionsRecommendation.rec_date == score_date)
    ).scalar_one_or_none()
    if existing:
        return  # Heute bereits gespeichert
    db.add(OptionsRecommendation(
        ticker          = ticker,
        rec_date        = score_date,
        direction       = params.get("direction", "CALL"),
        leverage_min    = params.get("leverage_min"),
        leverage_max    = params.get("leverage_max"),
        duration_weeks  = params.get("duration_weeks"),
        ko_distance_pct = params.get("ko_distance_pct"),
        entry_trigger   = params.get("entry_trigger"),
        stop_loss       = params.get("stop_loss"),
        base_price_at_rec = params.get("base_price"),
        atr_at_rec      = params.get("atr_pct"),
        score_at_rec    = total_score,
    ))


# ── Hauptfunktion ────────────────────────────────────────────────────────────

def score_ticker(
    ticker: str,
    db: Session,
    score_date: Optional[str] = None,
) -> dict:
    """
    Vollständigen Score für einen Ticker berechnen und in DB schreiben.
    Gibt das Ergebnis-Dict zurück.

    Abschluss-Kriterium Phase 2:
        score_ticker("AAPL", db) schreibt validen Score in alle 4 Tabellen.
    """
    if score_date is None:
        score_date = datetime.utcnow().strftime("%Y-%m-%d")

    logger.info("Scoring %s am %s ...", ticker, score_date)

    # Sicherstellen, dass der Ticker in der stocks-Tabelle existiert
    stock = db.get(Stock, ticker)
    if not stock:
        logger.info("Ticker %s nicht in DB – lege Eintrag an", ticker)
        db.add(Stock(ticker=ticker, universe_source="MANUAL", is_active=1))
        db.flush()

    # ── Scoring ─────────────────────────────────────────────────────────────
    try:
        l1_score, l1_bd = compute_fundamental_score(ticker, db)
    except Exception as exc:
        logger.error("L1 (Fundamental) für %s fehlgeschlagen: %s", ticker, exc)
        l1_score, l1_bd = 0.0, {}

    try:
        l2_score, l2_bd = compute_technical_score(ticker, db)
    except Exception as exc:
        logger.error("L2 (Technical) für %s fehlgeschlagen: %s", ticker, exc)
        l2_score, l2_bd = 0.0, {}

    try:
        l3_score, l3_bd = compute_sentiment_score(ticker, db)
    except Exception as exc:
        logger.error("L3 (Sentiment) für %s fehlgeschlagen: %s", ticker, exc)
        l3_score, l3_bd = 0.0, {}

    # ── Aggregation ──────────────────────────────────────────────────────────
    total_score, suppressed = apply_suppression_rule(l1_score, l2_score, l3_score)
    zone                    = _assign_zone(total_score)
    deltas                  = compute_deltas(ticker, total_score, score_date, db)
    strongest               = _strongest_signal(l1_bd, l2_bd, l3_bd)

    days_earn         = l1_bd.get("_days_earn")
    next_earnings_str = l1_bd.get("_next_earnings_date")

    # Kurs + Währung aus Cache (kein extra API-Call, bereits in L1 abgerufen)
    try:
        yf_info    = YFinanceFetcher(db).get_fundamentals(ticker)
        close_price = yf_info.get("price")
        currency    = yf_info.get("currency") or "USD"
    except Exception:
        close_price, currency = None, "USD"

    # ── DB-Daten vorbereiten ─────────────────────────────────────────────────
    daily_data = {
        "total_score":      total_score,
        "l1_fundamentals":  l1_score,
        "l2_technicals":    l2_score,
        "l3_sentiment":     l3_score,
        "zone":             zone,
        "delta_1d":         deltas.get("delta_1d"),
        "delta_7d":         deltas.get("delta_7d"),
        "delta_30d":        deltas.get("delta_30d"),
        "strongest_signal": strongest,
        "next_catalyst":    next_earnings_str,
        "catalyst_days":    days_earn,
        "close_price":      close_price,
        "currency":         currency,
    }

    breakdown_data = {
        # L1
        "pe_vs_sector":        l1_bd.get("pe_vs_sector",       0.0),
        "eps_beat_streak":     l1_bd.get("eps_beat_streak",    0.0),
        "revenue_growth":      l1_bd.get("revenue_growth",     0.0),
        "fcf_score":           l1_bd.get("fcf_score",          0.0),
        "debt_equity":         l1_bd.get("debt_equity",        0.0),
        "insider_net":         l1_bd.get("insider_net",        0.0),
        "earnings_proximity":  l1_bd.get("earnings_proximity", 0.0),
        # L2
        "vcp_score":           l2_bd.get("vcp_score",           0.0),
        "volume_contraction":  l2_bd.get("volume_contraction",  0.0),
        "price_vs_resistance": l2_bd.get("price_vs_resistance", 0.0),
        "rsi_zone":            l2_bd.get("rsi_zone",            0.0),
        "relative_strength":   l2_bd.get("relative_strength",  0.0),
        "macd_signal":         l2_bd.get("macd_signal",         0.0),
        "bollinger_squeeze":   l2_bd.get("bollinger_squeeze",  0.0),
        # L3
        "news_sentiment":      l3_bd.get("news_sentiment",     0.0),
        "stocktwits_ratio":    l3_bd.get("stocktwits_ratio",   0.0),
        "reddit_momentum":     l3_bd.get("reddit_momentum",    0.0),
        "analyst_delta":       l3_bd.get("analyst_delta",      0.0),
        "sentiment_suppressed": int(suppressed),
    }

    # ── DB-Schreiboperationen ────────────────────────────────────────────────
    try:
        _upsert(DailyScore,    {"ticker": ticker, "score_date": score_date}, daily_data,     db)
        _upsert(ScoreHistory,  {"ticker": ticker, "score_date": score_date},
                {"total_score": total_score, "zone": zone},                                  db)
        _upsert(ScoreBreakdown, {"ticker": ticker, "score_date": score_date}, breakdown_data, db)
        _update_watchlist(ticker, zone, db)

        # Optionsschein-Empfehlung nur für Zone 1
        if zone == 1:
            yf_earn = YFinanceFetcher(db).get_earnings_calendar(ticker)
            opts = derive_options_params(
                ticker=ticker,
                total_score=total_score,
                delta_7d=deltas.get("delta_7d"),
                days_to_earnings=yf_earn.get("days_to_earnings"),
                db=db,
            )
            _save_options_rec(ticker, score_date, opts, total_score, db)

        db.commit()

    except Exception as exc:
        db.rollback()
        logger.error("DB-Fehler beim Speichern von %s: %s", ticker, exc)
        raise

    logger.info(
        "Score %s: %.1f (L1=%.1f L2=%.1f L3=%.1f%s) Zone %d Δ7T=%s",
        ticker, total_score, l1_score, l2_score, l3_score,
        " UNTERDRÜCKT" if suppressed else "",
        zone,
        f"{deltas['delta_7d']:+.1f}" if deltas.get("delta_7d") is not None else "n/a",
    )

    return {
        "ticker":      ticker,
        "score_date":  score_date,
        "total_score": total_score,
        "l1":          l1_score,
        "l2":          l2_score,
        "l3":          l3_score,
        "zone":        zone,
        "suppressed":  suppressed,
        "deltas":      deltas,
        "strongest":   strongest,
        "breakdown":   breakdown_data,
    }


def score_ticker_safe(
    ticker: str,
    db: Session,
    score_date: Optional[str] = None,
) -> Optional[dict]:
    """score_ticker mit vollständiger Fehlerabfangung (für Batch-Scans)."""
    try:
        return score_ticker(ticker, db, score_date)
    except Exception as exc:
        logger.error("score_ticker_safe(%s) fehlgeschlagen: %s", ticker, exc)
        return None
