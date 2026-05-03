"""GET /api/history – Trade-Archiv und Signalqualitäts-Statistiken."""
import json
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.database import get_db
from backend.models import Transaction, Position, SignalQuality, Stock
from backend.schemas import TransactionOut, SignalQualityOut

router = APIRouter()


@router.get("/trades", response_model=list[TransactionOut], summary="Trade-Archiv")
def get_trade_history(
    ticker:  Optional[str] = Query(None, description="Nach Ticker filtern"),
    limit:   int           = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Alle abgeschlossenen Verkaufs-Transaktionen mit P&L-Daten."""
    stmt = (
        select(Transaction)
        .where(Transaction.tx_type == "SELL")
        .order_by(Transaction.tx_date.desc())
        .limit(limit)
    )
    if ticker:
        stmt = stmt.where(Transaction.ticker == ticker.upper())
    txs = db.execute(stmt).scalars().all()
    return [
        TransactionOut(
            id          = t.id,
            position_id = t.position_id,
            ticker      = t.ticker,
            tx_type     = t.tx_type,
            quantity    = t.quantity,
            price       = t.price,
            tx_date     = t.tx_date,
            score_at_tx = t.score_at_tx,
            pnl_abs     = t.pnl_abs,
            pnl_pct     = t.pnl_pct,
            hold_days   = t.hold_days,
            notes       = t.notes,
        )
        for t in txs
    ]


@router.get("/signal-quality", response_model=list[SignalQualityOut], summary="Signalqualität")
def get_signal_quality(db: Session = Depends(get_db)):
    """
    Trefferquote und Ø-P&L pro Signaltyp (aus signal_quality-Tabelle).
    Werden beim Schließen einer Position automatisch befüllt.
    """
    rows = db.execute(select(SignalQuality)).scalars().all()
    if not rows:
        return []

    # Aggregieren nach Signaltyp (JSON-Array in signal_types)
    stats: dict[str, dict] = {}
    for sq in rows:
        try:
            sig_types = json.loads(sq.signal_types or "[]")
        except (json.JSONDecodeError, TypeError):
            sig_types = []
        for stype in (sig_types or ["UNBEKANNT"]):
            if stype not in stats:
                stats[stype] = {"total": 0, "profitable": 0, "pnl_sum": 0.0}
            stats[stype]["total"] += 1
            if sq.profitable:
                stats[stype]["profitable"] += 1
            stats[stype]["pnl_sum"] += sq.pnl_pct or 0.0

    return [
        SignalQualityOut(
            signal_type   = stype,
            total_trades  = d["total"],
            profitable    = d["profitable"],
            win_rate_pct  = round(d["profitable"] / d["total"] * 100, 1),
            avg_pnl_pct   = round(d["pnl_sum"] / d["total"], 2),
        )
        for stype, d in sorted(stats.items())
    ]


@router.get("/summary", summary="P&L-Gesamtübersicht")
def get_history_summary(db: Session = Depends(get_db)):
    """Aggregierte Kennzahlen: Trades gesamt, Trefferquote, Ø-Haltedauer, Ø-P&L."""
    sell_txs = db.execute(
        select(Transaction).where(Transaction.tx_type == "SELL")
    ).scalars().all()

    if not sell_txs:
        return {
            "total_trades":    0,
            "profitable":      0,
            "win_rate_pct":    None,
            "avg_pnl_pct":     None,
            "avg_hold_days":   None,
            "total_pnl_abs":   0.0,
        }

    profitable   = sum(1 for t in sell_txs if (t.pnl_pct or 0) > 0)
    pnl_values   = [t.pnl_pct for t in sell_txs if t.pnl_pct is not None]
    hold_values  = [t.hold_days for t in sell_txs if t.hold_days is not None]
    total_pnl    = sum(t.pnl_abs or 0 for t in sell_txs)
    n            = len(sell_txs)

    return {
        "total_trades":  n,
        "profitable":    profitable,
        "win_rate_pct":  round(profitable / n * 100, 1),
        "avg_pnl_pct":   round(sum(pnl_values) / len(pnl_values), 2) if pnl_values else None,
        "avg_hold_days": round(sum(hold_values) / len(hold_values), 1) if hold_values else None,
        "total_pnl_abs": round(total_pnl, 2),
    }
