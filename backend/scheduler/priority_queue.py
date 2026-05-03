"""Scan-Prioritätswarteschlange: Tier-Reihenfolge + Zone-4-Rotation.

Tier 0 – Offene Positionen         → täglich zuerst, alle APIs
Tier 1 – Zone 1 + Zone 2           → täglich, alle APIs
Tier 2 – Zone 3                    → täglich, yfinance + ta + StockTwits
Tier 3 – Zone 4 rotierend          → zone4_batch_size Aktien/Tag (Standard: 200)

Der Rotation-Index wird in der configuration-Tabelle als scan_rotation_idx gespeichert
und beim nächsten Scan an der letzten Position fortgesetzt.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, text

from backend.models import Stock, DailyScore, Position

logger = logging.getLogger(__name__)


def _get_config_int(key: str, default: int, db: Session) -> int:
    row = db.execute(text("SELECT value FROM configuration WHERE key = :k"), {"k": key}).scalar_one_or_none()
    try:
        return int(row) if row is not None else default
    except (ValueError, TypeError):
        return default


def _set_config(key: str, value, db: Session) -> None:
    db.execute(
        text(
            "INSERT INTO configuration(key, value, updated_at) VALUES(:k,:v,datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=:v, updated_at=datetime('now')"
        ),
        {"k": key, "v": str(value)},
    )
    db.commit()


def build_scan_queue(db: Session) -> list[str]:
    """
    Gibt eine geordnete Ticker-Liste für den heutigen Scan zurück.

    Reihenfolge:
      1. Offene Positionen (Tier 0, dedupliziert)
      2. Zone 1 + Zone 2 (Tier 1)
      3. Zone 3 (Tier 2)
      4. Zone 4 – Rotation-Batch (Tier 3)
      5. Neue Ticker ohne bisherigen Score
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")

    latest_date = db.execute(
        select(DailyScore.score_date).order_by(DailyScore.score_date.desc()).limit(1)
    ).scalar_one_or_none()

    # ── Tier 0: offene Positionen ─────────────────────────────────────────────
    open_tickers: list[str] = list(dict.fromkeys(
        r[0] for r in db.execute(
            select(Position.ticker).where(Position.is_open == 1)
        ).all()
    ))

    if latest_date:
        # ── Tier 1: Zone 1+2 ─────────────────────────────────────────────────
        tier1 = [
            r[0] for r in db.execute(
                select(DailyScore.ticker)
                .where(DailyScore.score_date == latest_date, DailyScore.zone.in_([1, 2]))
                .order_by(DailyScore.total_score.desc())
            ).all()
        ]

        # ── Tier 2: Zone 3 ───────────────────────────────────────────────────
        tier2 = [
            r[0] for r in db.execute(
                select(DailyScore.ticker)
                .where(DailyScore.score_date == latest_date, DailyScore.zone == 3)
                .order_by(DailyScore.total_score.desc())
            ).all()
        ]

        # ── Tier 3: Zone 4 (Rotation) ────────────────────────────────────────
        all_zone4 = [
            r[0] for r in db.execute(
                select(DailyScore.ticker)
                .where(DailyScore.score_date == latest_date, DailyScore.zone == 4)
                .order_by(DailyScore.ticker)
            ).all()
        ]
    else:
        tier1, tier2, all_zone4 = [], [], []

    # Neue Ticker ohne Scores
    scored_tickers = set(
        r[0] for r in db.execute(select(DailyScore.ticker)).all()
    ) if latest_date else set()
    new_tickers = [
        r[0] for r in db.execute(
            select(Stock.ticker).where(Stock.is_active == 1)
        ).all()
        if r[0] not in scored_tickers
    ]

    # Zone-4-Rotation
    batch_size = _get_config_int("zone4_daily_count", 200, db)
    rot_idx    = _get_config_int("scan_rotation_idx", 0, db)

    if all_zone4:
        start      = rot_idx % len(all_zone4)
        zone4_batch = (all_zone4 + all_zone4)[start : start + batch_size]
        new_rot_idx = (rot_idx + batch_size) % len(all_zone4)
        _set_config("scan_rotation_idx", new_rot_idx, db)
        logger.info(
            "Zone-4-Rotation: Index %d → %d, Batch: %d/%d Ticker",
            rot_idx, new_rot_idx, len(zone4_batch), len(all_zone4),
        )
    else:
        zone4_batch = []

    # Finale Reihenfolge (Duplikate entfernen, Priorität erhalten)
    seen: set[str] = set()
    queue: list[str] = []
    for ticker in open_tickers + tier1 + tier2 + zone4_batch + new_tickers:
        if ticker not in seen:
            seen.add(ticker)
            queue.append(ticker)

    logger.info(
        "Scan-Queue: %d Ticker (T0=%d T1=%d T2=%d T3=%d Neu=%d)",
        len(queue), len(open_tickers), len(tier1), len(tier2), len(zone4_batch), len(new_tickers),
    )
    return queue
