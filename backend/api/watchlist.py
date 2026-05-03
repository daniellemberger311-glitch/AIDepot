"""GET /api/watchlist – Watchlist mit Zone-Filter, Sortierung und optionalem Breakdown."""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.database import get_db
from backend.models import DailyScore, Stock, ScoreBreakdown, OptionsRecommendation
from backend.schemas import StockScoreOut
from backend.api._helpers import build_score_out

router = APIRouter()


def _latest_score_date(db: Session) -> Optional[str]:
    return db.execute(
        select(DailyScore.score_date).order_by(DailyScore.score_date.desc()).limit(1)
    ).scalar_one_or_none()


@router.get("", response_model=list[StockScoreOut], summary="Watchlist abrufen")
def get_watchlist(
    zone:      Optional[int] = Query(None, ge=1, le=4, description="Zone 1–4 filtern"),
    sort:      str           = Query("total_score", description="total_score | delta_7d | delta_1d | ticker"),
    limit:     int           = Query(200, ge=1, le=1000),
    date:      Optional[str] = Query(None, description="Score-Datum YYYY-MM-DD, Standard: letzter Tag"),
    breakdown: bool          = Query(False, description="Score-Breakdown einschließen"),
    db: Session = Depends(get_db),
):
    """
    Alle gescannten Aktien mit ihrem neuesten Tages-Score.

    - `zone=1`  → nur Zone-1-Aktien (≥ 76 Punkte)
    - `sort=delta_7d` → nach 7-Tage-Delta absteigend sortieren
    - `breakdown=true` → Score-Aufschlüsselung pro Kriterium einschließen
    """
    if date is None:
        date = _latest_score_date(db)
        if date is None:
            return []

    sort_map = {
        "total_score": DailyScore.total_score.desc(),
        "delta_7d":    DailyScore.delta_7d.desc(),
        "delta_1d":    DailyScore.delta_1d.desc(),
        "ticker":      DailyScore.ticker.asc(),
    }

    stmt = (
        select(DailyScore, Stock.name, Stock.sector)
        .join(Stock, Stock.ticker == DailyScore.ticker, isouter=True)
        .where(DailyScore.score_date == date)
    )
    if zone is not None:
        stmt = stmt.where(DailyScore.zone == zone)
    stmt = stmt.order_by(sort_map.get(sort, DailyScore.total_score.desc())).limit(limit)

    rows = db.execute(stmt).all()
    results = []
    for ds, name, sector in rows:
        bd = None
        if breakdown:
            bd = db.execute(
                select(ScoreBreakdown)
                .where(ScoreBreakdown.ticker == ds.ticker, ScoreBreakdown.score_date == date)
            ).scalar_one_or_none()
        rec = None
        if ds.zone == 1:
            rec = db.execute(
                select(OptionsRecommendation)
                .where(OptionsRecommendation.ticker == ds.ticker, OptionsRecommendation.rec_date == date)
            ).scalar_one_or_none()
        results.append(build_score_out(ds, name, sector, bd, rec))

    return results


@router.get("/zones/summary", summary="Zone-Zusammenfassung")
def get_zone_summary(
    date: Optional[str] = Query(None, description="Score-Datum YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Anzahl Aktien pro Zone für das angegebene Datum."""
    if date is None:
        date = _latest_score_date(db)
        if date is None:
            return {"date": None, "zones": {}}

    rows = db.execute(
        select(DailyScore.zone, DailyScore.ticker)
        .where(DailyScore.score_date == date)
    ).all()

    zones: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
    for zone, _ in rows:
        zones[zone] = zones.get(zone, 0) + 1

    return {
        "date":  date,
        "total": len(rows),
        "zones": zones,
    }
