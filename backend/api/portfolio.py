"""Portfolio-Endpunkte: Positionen anlegen, verwalten und schließen.

Routen:
  GET    /api/portfolio              – offene Positionen
  POST   /api/portfolio              – neue Position anlegen
  GET    /api/portfolio/{id}         – Positionsdetail
  PUT    /api/portfolio/{id}/close   – Position schließen (SELL-Transaktion)
  DELETE /api/portfolio/{id}         – Position löschen
  POST   /api/portfolio/{id}/check-exits – Exit-Signale für eine Position prüfen
  PUT    /api/portfolio/signals/{signal_id}/acknowledge – Signal quittieren
"""
import logging
from datetime import datetime, date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, text

from backend.database import get_db
from backend.models import Position, Transaction, ExitSignal, DailyScore, Stock
from backend.schemas import (
    PositionCreate, PositionClose, PositionOut, TransactionOut, ExitSignalOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _get_config_float(key: str, default: float, db: Session) -> float:
    row = db.execute(text("SELECT value FROM configuration WHERE key = :k"), {"k": key}).scalar_one_or_none()
    try:
        return float(row) if row is not None else default
    except ValueError:
        return default


def _days_to_expiry(expiry_date: Optional[str]) -> Optional[int]:
    if not expiry_date:
        return None
    try:
        exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        return max(0, (exp - date_type.today()).days)
    except ValueError:
        return None


def _ko_distance_pct(ko_level: Optional[float], underlying_price: Optional[float]) -> Optional[float]:
    if ko_level and underlying_price and underlying_price > 0:
        return round(abs(underlying_price - ko_level) / underlying_price * 100, 2)
    return None


def _position_status(exit_signals: list[ExitSignal]) -> str:
    open_sigs = [s for s in exit_signals if not s.is_acknowledged]
    if any(s.severity == "RED" for s in open_sigs):
        return "EXIT"
    if any(s.severity == "YELLOW" for s in open_sigs):
        return "BEOBACHTEN"
    return "HALTEN"


def _enrich_position(pos: Position, db: Session) -> PositionOut:
    """Position mit Live-Daten aus DailyScore anreichern."""
    latest_ds = db.execute(
        select(DailyScore)
        .where(DailyScore.ticker == pos.ticker)
        .order_by(DailyScore.score_date.desc())
        .limit(1)
    ).scalar_one_or_none()

    stock = db.get(Stock, pos.ticker)

    current_score = latest_ds.total_score if latest_ds else None
    current_zone  = latest_ds.zone        if latest_ds else None

    # Underlying-Preis aus dem letzten Score-Tag nicht direkt verfügbar →
    # ko_distance und unrealized_pnl werden durch täglichen Scan aktualisiert
    days_exp = _days_to_expiry(pos.expiry_date)

    exit_sigs = db.execute(
        select(ExitSignal)
        .where(ExitSignal.position_id == pos.id)
        .order_by(ExitSignal.signal_date.desc())
    ).scalars().all()

    sig_out = [
        ExitSignalOut(
            id               = s.id,
            position_id      = s.position_id,
            ticker           = s.ticker,
            signal_type      = s.signal_type,
            severity         = s.severity,
            trigger_value    = s.trigger_value,
            message          = s.message,
            recommendation   = s.recommendation,
            current_pnl_pct  = s.current_pnl_pct,
            is_acknowledged  = bool(s.is_acknowledged),
            signal_date      = s.signal_date,
        )
        for s in exit_sigs
    ]

    return PositionOut(
        id                  = pos.id,
        ticker              = pos.ticker,
        name                = stock.name if stock else None,
        product_type        = pos.product_type,
        direction           = pos.direction,
        isin                = pos.isin,
        quantity            = pos.quantity,
        entry_price         = pos.entry_price,
        entry_date          = pos.entry_date,
        entry_score         = pos.entry_score,
        entry_zone          = pos.entry_zone,
        ko_level            = pos.ko_level,
        expiry_date         = pos.expiry_date,
        leverage            = pos.leverage,
        underlying_at_entry = pos.underlying_at_entry,
        is_open             = bool(pos.is_open),
        current_score       = current_score,
        current_zone        = current_zone,
        days_to_expiry      = days_exp,
        status              = _position_status(exit_sigs) if pos.is_open else "GESCHLOSSEN",
        exit_signals        = sig_out,
    )


def _generate_exit_signals(pos: Position, ds: Optional[DailyScore], db: Session) -> list[ExitSignal]:
    """Exit-Signale für eine Position prüfen und neue in DB schreiben."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    new_signals: list[ExitSignal] = []

    exit_score_drop  = _get_config_float("exit_score_drop",  15.0, db)
    exit_ko_distance = _get_config_float("exit_ko_distance",  8.0, db)
    exit_expiry_weeks = int(_get_config_float("exit_expiry_weeks", 3, db))
    exit_bull_ratio  = _get_config_float("exit_bull_ratio",  35.0, db)

    def _already_today(signal_type: str) -> bool:
        existing = db.execute(
            select(ExitSignal)
            .where(
                ExitSignal.position_id == pos.id,
                ExitSignal.signal_type == signal_type,
                ExitSignal.signal_date == today,
            )
        ).scalar_one_or_none()
        return existing is not None

    # 1) Score-Rückgang
    if ds and pos.entry_score and (pos.entry_score - ds.total_score) >= exit_score_drop:
        if not _already_today("SCORE_DROP"):
            drop = pos.entry_score - ds.total_score
            sig = ExitSignal(
                position_id   = pos.id,
                ticker        = pos.ticker,
                signal_type   = "SCORE_DROP",
                severity      = "RED" if drop >= exit_score_drop * 1.5 else "YELLOW",
                trigger_value = round(drop, 1),
                message       = f"Score fiel um {drop:.1f} Punkte (Einstieg: {pos.entry_score:.0f} → heute: {ds.total_score:.0f})",
                recommendation= "Position schließen oder stark reduzieren",
                signal_date   = today,
            )
            db.add(sig)
            new_signals.append(sig)

    # 2) Restlaufzeit
    days_exp = _days_to_expiry(pos.expiry_date)
    if days_exp is not None and days_exp <= exit_expiry_weeks * 7:
        if not _already_today("EXPIRY_RISK"):
            severity = "RED" if days_exp <= 7 else "YELLOW"
            sig = ExitSignal(
                position_id   = pos.id,
                ticker        = pos.ticker,
                signal_type   = "EXPIRY_RISK",
                severity      = severity,
                trigger_value = float(days_exp),
                message       = f"Nur noch {days_exp} Tage bis Ablauf",
                recommendation= "Zeitwertverfall beachten – Position schließen oder rollen",
                signal_date   = today,
            )
            db.add(sig)
            new_signals.append(sig)

    # 3) Sentiment-Einbruch (L3 < exit_bull_ratio-Schwelle übersetzt in Sentiment-Score)
    if ds and ds.l3_sentiment < (exit_bull_ratio / 100.0 * 25):
        if not _already_today("SENTIMENT_DROP"):
            sig = ExitSignal(
                position_id   = pos.id,
                ticker        = pos.ticker,
                signal_type   = "SENTIMENT_DROP",
                severity      = "YELLOW",
                trigger_value = round(ds.l3_sentiment, 1),
                message       = f"Sentiment-Score niedrig: {ds.l3_sentiment:.1f}/25",
                recommendation= "Sentiment-Entwicklung beobachten",
                signal_date   = today,
            )
            db.add(sig)
            new_signals.append(sig)

    if new_signals:
        db.commit()
    return new_signals


# ── Endpunkte ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[PositionOut], summary="Offene Positionen")
def list_positions(
    include_closed: bool = Query(False, description="Geschlossene Positionen einschließen"),
    db: Session = Depends(get_db),
):
    """Alle Positionen mit aktuellem Score und Exit-Signalen."""
    stmt = select(Position).order_by(Position.entry_date.desc())
    if not include_closed:
        stmt = stmt.where(Position.is_open == 1)
    positions = db.execute(stmt).scalars().all()
    return [_enrich_position(p, db) for p in positions]


@router.post("", response_model=PositionOut, status_code=201, summary="Position anlegen")
def create_position(payload: PositionCreate, db: Session = Depends(get_db)):
    """Neue Position anlegen. Legt automatisch eine BUY-Transaktion an."""
    ticker = payload.ticker.upper()

    # Letzten Score für Einstiegs-Metadaten holen
    latest_ds = db.execute(
        select(DailyScore)
        .where(DailyScore.ticker == ticker)
        .order_by(DailyScore.score_date.desc())
        .limit(1)
    ).scalar_one_or_none()

    pos = Position(
        ticker              = ticker,
        product_type        = payload.product_type,
        direction           = payload.direction,
        isin                = payload.isin,
        quantity            = payload.quantity,
        entry_price         = payload.entry_price,
        entry_date          = payload.entry_date,
        ko_level            = payload.ko_level,
        expiry_date         = payload.expiry_date,
        leverage            = payload.leverage,
        underlying_at_entry = payload.underlying_at_entry,
        entry_score         = latest_ds.total_score if latest_ds else None,
        entry_zone          = latest_ds.zone        if latest_ds else None,
        entry_delta_1d      = latest_ds.delta_1d    if latest_ds else None,
        entry_delta_7d      = latest_ds.delta_7d    if latest_ds else None,
        entry_delta_30d     = latest_ds.delta_30d   if latest_ds else None,
        is_open             = 1,
    )
    db.add(pos)
    db.flush()  # ID generieren

    tx = Transaction(
        position_id = pos.id,
        ticker      = ticker,
        tx_type     = "BUY",
        quantity    = payload.quantity,
        price       = payload.entry_price,
        tx_date     = payload.entry_date,
        score_at_tx = latest_ds.total_score if latest_ds else None,
        notes       = payload.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(pos)

    logger.info("Position %d angelegt: %s %s × %.4f @ %.4f", pos.id, ticker, payload.direction, payload.quantity, payload.entry_price)
    return _enrich_position(pos, db)


@router.get("/{position_id}", response_model=PositionOut, summary="Positionsdetail")
def get_position(position_id: int, db: Session = Depends(get_db)):
    pos = db.get(Position, position_id)
    if pos is None:
        raise HTTPException(404, f"Position {position_id} nicht gefunden")
    return _enrich_position(pos, db)


@router.put("/{position_id}/close", response_model=PositionOut, summary="Position schließen")
def close_position(position_id: int, payload: PositionClose, db: Session = Depends(get_db)):
    """
    Position schließen: SELL-Transaktion anlegen, P&L berechnen, is_open = 0 setzen.
    """
    pos = db.get(Position, position_id)
    if pos is None:
        raise HTTPException(404, f"Position {position_id} nicht gefunden")
    if not pos.is_open:
        raise HTTPException(400, "Position ist bereits geschlossen")

    hold_days = None
    try:
        entry_dt = datetime.strptime(pos.entry_date, "%Y-%m-%d")
        sell_dt  = datetime.strptime(payload.sell_date, "%Y-%m-%d")
        hold_days = (sell_dt - entry_dt).days
    except ValueError:
        pass

    pnl_abs = (payload.sell_price - pos.entry_price) * pos.quantity
    pnl_pct = (payload.sell_price - pos.entry_price) / pos.entry_price * 100 if pos.entry_price else None
    if pos.direction == "SHORT" and pnl_pct is not None:
        pnl_pct = -pnl_pct
        pnl_abs = -pnl_abs

    latest_ds = db.execute(
        select(DailyScore)
        .where(DailyScore.ticker == pos.ticker)
        .order_by(DailyScore.score_date.desc())
        .limit(1)
    ).scalar_one_or_none()

    tx = Transaction(
        position_id = pos.id,
        ticker      = pos.ticker,
        tx_type     = "SELL",
        quantity    = pos.quantity,
        price       = payload.sell_price,
        tx_date     = payload.sell_date,
        score_at_tx = latest_ds.total_score if latest_ds else None,
        pnl_abs     = round(pnl_abs, 4),
        pnl_pct     = round(pnl_pct, 2) if pnl_pct is not None else None,
        hold_days   = hold_days,
        notes       = payload.notes,
    )
    db.add(tx)

    pos.is_open = 0
    db.commit()
    db.refresh(pos)

    logger.info("Position %d geschlossen: %s P&L %.2f%%", pos.id, pos.ticker, pnl_pct or 0)
    return _enrich_position(pos, db)


@router.delete("/{position_id}", status_code=204, summary="Position löschen")
def delete_position(position_id: int, db: Session = Depends(get_db)):
    pos = db.get(Position, position_id)
    if pos is None:
        raise HTTPException(404, f"Position {position_id} nicht gefunden")
    db.delete(pos)
    db.commit()


@router.post("/{position_id}/check-exits", summary="Exit-Signale prüfen")
def check_exit_signals(position_id: int, db: Session = Depends(get_db)):
    """
    Exit-Bedingungen für eine Position prüfen und neue Signale schreiben.
    Wird auch täglich vom Scheduler aufgerufen.
    """
    pos = db.get(Position, position_id)
    if pos is None:
        raise HTTPException(404, f"Position {position_id} nicht gefunden")
    if not pos.is_open:
        return {"message": "Position geschlossen – kein Exit-Check notwendig", "new_signals": 0}

    latest_ds = db.execute(
        select(DailyScore)
        .where(DailyScore.ticker == pos.ticker)
        .order_by(DailyScore.score_date.desc())
        .limit(1)
    ).scalar_one_or_none()

    new_signals = _generate_exit_signals(pos, latest_ds, db)
    return {
        "position_id": position_id,
        "ticker":      pos.ticker,
        "new_signals": len(new_signals),
        "signals":     [s.signal_type for s in new_signals],
    }


@router.put("/signals/{signal_id}/acknowledge", summary="Exit-Signal quittieren")
def acknowledge_signal(signal_id: int, db: Session = Depends(get_db)):
    sig = db.get(ExitSignal, signal_id)
    if sig is None:
        raise HTTPException(404, f"Signal {signal_id} nicht gefunden")
    sig.is_acknowledged = 1
    db.commit()
    return {"signal_id": signal_id, "acknowledged": True}


@router.get("/{position_id}/transactions", response_model=list[TransactionOut], summary="Transaktionen")
def get_transactions(position_id: int, db: Session = Depends(get_db)):
    pos = db.get(Position, position_id)
    if pos is None:
        raise HTTPException(404, f"Position {position_id} nicht gefunden")
    txs = db.execute(
        select(Transaction)
        .where(Transaction.position_id == position_id)
        .order_by(Transaction.tx_date)
    ).scalars().all()
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
