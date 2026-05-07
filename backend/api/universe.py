"""Universe-Endpunkte: Ticker-Verwaltung, Suche und Aktualisierung.

Routen:
  GET    /api/universe            – alle Ticker (aktiv + optional inaktiv)
  POST   /api/universe/add        – Ticker manuell hinzufügen
  DELETE /api/universe/{ticker}   – Ticker deaktivieren
  GET    /api/universe/search     – Reserve-Suche (is_active=0)
  POST   /api/universe/refresh    – Wikipedia + AV LISTING_STATUS aktualisieren
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, update

from backend.database import get_db
from backend.models import Stock

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class UniverseTickerOut(BaseModel):
    ticker:          str
    name:            Optional[str]
    sector:          Optional[str]
    industry:        Optional[str]
    exchange:        Optional[str]
    universe_source: Optional[str]
    is_active:       bool
    added_at:        Optional[str]


class UniverseAddIn(BaseModel):
    ticker: str
    name:   Optional[str] = None


# ── Endpunkte ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[UniverseTickerOut], summary="Alle Ticker")
def list_universe(
    active_only: bool          = Query(True,  description="Nur aktive Ticker"),
    source:      Optional[str] = Query(None,  description="Quelle: SP500 | NASDAQ100 | RUSSELL200 | WATCHLIST | MANUAL"),
    limit:       int           = Query(1000,  ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Liste aller Ticker im Universum, optional nach Quelle gefiltert."""
    stmt = select(Stock).order_by(Stock.universe_source, Stock.ticker)
    if active_only:
        stmt = stmt.where(Stock.is_active == 1)
    if source:
        stmt = stmt.where(Stock.universe_source == source.upper())
    stocks = db.execute(stmt.limit(limit)).scalars().all()
    return [
        UniverseTickerOut(
            ticker          = s.ticker,
            name            = s.name,
            sector          = s.sector,
            industry        = s.industry,
            exchange        = s.exchange,
            universe_source = s.universe_source,
            is_active       = bool(s.is_active),
            added_at        = s.added_at,
        )
        for s in stocks
    ]


@router.get("/stats", summary="Universum-Statistiken")
def get_universe_stats(db: Session = Depends(get_db)):
    """Anzahl Ticker pro Quelle (aktiv / inaktiv)."""
    rows = db.execute(
        select(Stock.universe_source, Stock.is_active, func.count(Stock.ticker))
        .group_by(Stock.universe_source, Stock.is_active)
        .order_by(Stock.universe_source)
    ).all()

    stats: dict[str, dict] = {}
    total_active = 0
    for source, is_active, count in rows:
        src = source or "UNBEKANNT"
        if src not in stats:
            stats[src] = {"active": 0, "inactive": 0}
        if is_active:
            stats[src]["active"] += count
            total_active += count
        else:
            stats[src]["inactive"] += count

    return {"total_active": total_active, "by_source": stats}


@router.get("/search", response_model=list[UniverseTickerOut], summary="Reserve-Suche")
def search_universe(
    q:     str = Query(..., min_length=1, description="Ticker oder Name (Teilstring)"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Suche in der Reserve-Datenbank (is_active=0).
    Nützlich um inaktive Ticker zu finden und zu aktivieren.
    """
    q = q.upper()
    stocks = db.execute(
        select(Stock)
        .where(
            Stock.is_active == 0,
            or_(
                Stock.ticker.contains(q),
                Stock.name.ilike(f"%{q}%"),
            ),
        )
        .order_by(Stock.ticker)
        .limit(limit)
    ).scalars().all()
    return [
        UniverseTickerOut(
            ticker          = s.ticker,
            name            = s.name,
            sector          = s.sector,
            industry        = s.industry,
            exchange        = s.exchange,
            universe_source = s.universe_source,
            is_active       = bool(s.is_active),
            added_at        = s.added_at,
        )
        for s in stocks
    ]


@router.post("/add", response_model=UniverseTickerOut, status_code=201, summary="Ticker hinzufügen")
def add_ticker(payload: UniverseAddIn, db: Session = Depends(get_db)):
    """
    Ticker manuell zum aktiven Universum hinzufügen (universe_source = WATCHLIST).
    Falls der Ticker bereits inaktiv vorhanden ist, wird er reaktiviert.
    """
    ticker = payload.ticker.upper().strip()
    existing = db.get(Stock, ticker)

    if existing:
        if existing.is_active:
            raise HTTPException(400, f"{ticker} ist bereits aktiv im Universum")
        existing.is_active       = 1
        existing.universe_source = "WATCHLIST"
        existing.name            = payload.name or existing.name
        existing.added_at        = datetime.utcnow().isoformat()
        db.commit()
        db.refresh(existing)
        logger.info("Ticker %s reaktiviert (WATCHLIST)", ticker)
        return UniverseTickerOut(
            ticker=existing.ticker, name=existing.name, sector=existing.sector,
            industry=existing.industry, exchange=existing.exchange,
            universe_source=existing.universe_source, is_active=True,
            added_at=existing.added_at,
        )

    stock = Stock(
        ticker          = ticker,
        name            = payload.name,
        universe_source = "WATCHLIST",
        is_active       = 1,
        added_at        = datetime.utcnow().isoformat(),
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    logger.info("Ticker %s neu hinzugefügt (WATCHLIST)", ticker)
    return UniverseTickerOut(
        ticker=stock.ticker, name=stock.name, sector=stock.sector,
        industry=stock.industry, exchange=stock.exchange,
        universe_source=stock.universe_source, is_active=True,
        added_at=stock.added_at,
    )


@router.delete("/{ticker}", status_code=204, summary="Ticker deaktivieren")
def deactivate_ticker(ticker: str, db: Session = Depends(get_db)):
    """
    Ticker aus dem aktiven Scan-Zyklus entfernen (is_active = 0).
    Historische Scores bleiben erhalten.
    """
    stock = db.get(Stock, ticker.upper())
    if stock is None:
        raise HTTPException(404, f"Ticker {ticker.upper()} nicht gefunden")
    if not stock.is_active:
        raise HTTPException(400, f"{ticker.upper()} ist bereits inaktiv")
    stock.is_active = 0
    db.commit()
    logger.info("Ticker %s deaktiviert", ticker.upper())


@router.post("/activate-all", summary="Alle inaktiven Ticker aktivieren")
def activate_all_tickers(db: Session = Depends(get_db)):
    """Setzt is_active=1 für alle Ticker in der stocks-Tabelle."""
    result = db.execute(update(Stock).where(Stock.is_active == 0).values(is_active=1))
    db.commit()
    count = result.rowcount
    total = db.query(Stock).filter(Stock.is_active == 1).count()
    logger.info("%d inaktive Ticker aktiviert – gesamt aktiv: %d", count, total)
    return {"activated": count, "total_active": total}


@router.post("/refresh", summary="Universum aktualisieren")
def refresh_universe(db: Session = Depends(get_db)):
    """
    Wikipedia-Listen (S&P 500 + NASDAQ 100) und AV LISTING_STATUS aktualisieren.
    Dauert ~10–30 Sekunden (Netzwerkabruf).
    """
    from backend.universe.loader import refresh_universe as _refresh

    try:
        result = _refresh(db)
        return {
            "success":      True,
            "added":        result.get("added", 0),
            "updated":      result.get("updated", 0),
            "total_active": result.get("total_active", 0),
            "message":      f"{result.get('added', 0)} neue Ticker, {result.get('updated', 0)} aktualisiert",
        }
    except Exception as exc:
        logger.error("Universe-Refresh fehlgeschlagen: %s", exc)
        raise HTTPException(500, f"Refresh fehlgeschlagen: {exc}")
