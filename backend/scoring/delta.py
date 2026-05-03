"""Delta-Berechnung: Δ1T, Δ7T, Δ30T aus score_history."""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models import ScoreHistory

logger = logging.getLogger(__name__)


def _get_historical_score(ticker: str, days_ago: int, today: "datetime.date", db: Session) -> float | None:
    """Liest den Score von vor `days_ago` Tagen aus der score_history-Tabelle."""
    target_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    row = db.execute(
        select(ScoreHistory.total_score)
        .where(ScoreHistory.ticker == ticker)
        .where(ScoreHistory.score_date == target_date)
    ).scalar_one_or_none()
    return float(row) if row is not None else None


def compute_deltas(ticker: str, current_score: float, score_date: str, db: Session) -> dict:
    """
    Berechnet Δ1T, Δ7T, Δ30T anhand der score_history-Tabelle.
    Gibt {delta_1d, delta_7d, delta_30d} zurück.
    Fehlende Historieneinträge → None.
    """
    try:
        today = datetime.strptime(score_date, "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Ungültiges Datumsformat für Delta-Berechnung: %s", score_date)
        return {"delta_1d": None, "delta_7d": None, "delta_30d": None}

    score_1d  = _get_historical_score(ticker, 1,  today, db)
    score_7d  = _get_historical_score(ticker, 7,  today, db)
    score_30d = _get_historical_score(ticker, 30, today, db)

    return {
        "delta_1d":  round(current_score - score_1d,  1) if score_1d  is not None else None,
        "delta_7d":  round(current_score - score_7d,  1) if score_7d  is not None else None,
        "delta_30d": round(current_score - score_30d, 1) if score_30d is not None else None,
    }
