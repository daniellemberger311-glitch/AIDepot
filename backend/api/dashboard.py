"""GET /api/dashboard – Tagesübersicht: P&L-Zusammenfassung, Top-Signale, Exit-Warnungen."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.database import get_db
from backend.models import DailyScore, Stock, Position, Transaction, ExitSignal, OptionsRecommendation, ScoreBreakdown
from backend.schemas import DashboardOut, StockScoreOut, ExitSignalOut
from backend.api._helpers import build_score_out

router = APIRouter()


@router.get("", response_model=DashboardOut, summary="Dashboard-Übersicht")
def get_dashboard(db: Session = Depends(get_db)):
    """
    Tagesübersicht:
    - Realisiertes Gesamt-P&L aller geschlossenen Positionen
    - Anzahl offener Positionen
    - Top-5 Zone-1-Signale des letzten Scan-Tages
    - Alle offenen (unquittierten) Exit-Warnungen
    """
    # ── P&L ──────────────────────────────────────────────────────────────────
    pnl_row = db.execute(
        select(func.sum(Transaction.pnl_abs), func.sum(Transaction.pnl_pct))
        .where(Transaction.tx_type == "SELL")
    ).one()
    total_pnl_abs = round(pnl_row[0] or 0.0, 2)
    total_pnl_pct = round(pnl_row[1] / max(1, db.execute(
        select(func.count(Transaction.id)).where(Transaction.tx_type == "SELL")
    ).scalar_one() or 1), 2) if pnl_row[1] else None

    # ── Offene Positionen ─────────────────────────────────────────────────────
    open_count = db.execute(
        select(func.count(Position.id)).where(Position.is_open == 1)
    ).scalar_one()

    # ── Letztes Score-Datum ───────────────────────────────────────────────────
    latest_date = db.execute(
        select(DailyScore.score_date).order_by(DailyScore.score_date.desc()).limit(1)
    ).scalar_one_or_none()

    # ── Top-5 Zone-1-Signale ─────────────────────────────────────────────────
    top_signals: list[StockScoreOut] = []
    if latest_date:
        rows = db.execute(
            select(DailyScore, Stock.name, Stock.sector)
            .join(Stock, Stock.ticker == DailyScore.ticker, isouter=True)
            .where(DailyScore.score_date == latest_date, DailyScore.zone == 1)
            .order_by(DailyScore.total_score.desc())
            .limit(5)
        ).all()
        for ds, name, sector in rows:
            rec = db.execute(
                select(OptionsRecommendation)
                .where(
                    OptionsRecommendation.ticker == ds.ticker,
                    OptionsRecommendation.rec_date == latest_date,
                    OptionsRecommendation.is_active == 1,
                )
            ).scalar_one_or_none()
            top_signals.append(build_score_out(ds, name, sector, opt_rec=rec))

    # ── Exit-Warnungen ────────────────────────────────────────────────────────
    exit_rows = db.execute(
        select(ExitSignal)
        .join(Position, Position.id == ExitSignal.position_id)
        .where(ExitSignal.is_acknowledged == 0, Position.is_open == 1)
        .order_by(ExitSignal.signal_date.desc())
    ).scalars().all()
    exit_alerts = [
        ExitSignalOut(
            id              = s.id,
            position_id     = s.position_id,
            ticker          = s.ticker,
            signal_type     = s.signal_type,
            severity        = s.severity,
            trigger_value   = s.trigger_value,
            message         = s.message,
            recommendation  = s.recommendation,
            current_pnl_pct = s.current_pnl_pct,
            is_acknowledged = bool(s.is_acknowledged),
            signal_date     = s.signal_date,
        )
        for s in exit_rows
    ]

    return DashboardOut(
        total_pnl_abs  = total_pnl_abs,
        total_pnl_pct  = total_pnl_pct,
        open_positions = open_count,
        top_signals    = top_signals,
        exit_alerts    = exit_alerts,
    )
