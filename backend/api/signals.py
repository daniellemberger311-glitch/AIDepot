"""GET /api/signals/{ticker} – Vollständiges Signal-Detail inkl. Score-Verlauf."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.database import get_db
from backend.models import DailyScore, Stock, ScoreBreakdown, OptionsRecommendation, ScoreHistory
from backend.schemas import StockScoreOut, ScoreHistoryPoint
from backend.api._helpers import build_score_out

router = APIRouter()


@router.get("/{ticker}", response_model=StockScoreOut, summary="Signal-Detail")
def get_signal(
    ticker: str,
    date:   Optional[str] = Query(None, description="Score-Datum YYYY-MM-DD, Standard: letzter Tag"),
    db: Session = Depends(get_db),
):
    """
    Vollständiges Signal für einen Ticker: Score-Aufschlüsselung + Optionsschein-Empfehlung.

    Wirft 404 wenn der Ticker noch nicht gescannt wurde.
    """
    ticker = ticker.upper()

    if date is None:
        date = db.execute(
            select(DailyScore.score_date)
            .where(DailyScore.ticker == ticker)
            .order_by(DailyScore.score_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        if date is None:
            raise HTTPException(404, f"Keine Scores für {ticker} gefunden")

    ds = db.execute(
        select(DailyScore)
        .where(DailyScore.ticker == ticker, DailyScore.score_date == date)
    ).scalar_one_or_none()
    if ds is None:
        raise HTTPException(404, f"Kein Score für {ticker} am {date}")

    stock = db.get(Stock, ticker)
    bd    = db.execute(
        select(ScoreBreakdown)
        .where(ScoreBreakdown.ticker == ticker, ScoreBreakdown.score_date == date)
    ).scalar_one_or_none()
    rec   = db.execute(
        select(OptionsRecommendation)
        .where(
            OptionsRecommendation.ticker == ticker,
            OptionsRecommendation.rec_date == date,
            OptionsRecommendation.is_active == 1,
        )
    ).scalar_one_or_none()

    return build_score_out(
        ds,
        stock.name   if stock else None,
        stock.sector if stock else None,
        bd,
        rec,
    )


@router.get("/{ticker}/history", response_model=list[ScoreHistoryPoint], summary="Score-Verlauf")
def get_signal_history(
    ticker: str,
    days:   int = Query(30, ge=1, le=365, description="Anzahl Tage"),
    db: Session = Depends(get_db),
):
    """Score-Verlauf der letzten N Tage (für Chart)."""
    ticker = ticker.upper()
    rows = db.execute(
        select(ScoreHistory)
        .where(ScoreHistory.ticker == ticker)
        .order_by(ScoreHistory.score_date.desc())
        .limit(days)
    ).scalars().all()
    if not rows:
        raise HTTPException(404, f"Kein Score-Verlauf für {ticker}")
    return [
        ScoreHistoryPoint(score_date=r.score_date, total_score=r.total_score, zone=r.zone)
        for r in reversed(rows)
    ]
