"""Zentraler API-Router: sammelt alle Sub-Router.

Aktive Endpunkte:
  /api/logs       – Fehlerprotokoll (Phase 2)
  /api/watchlist  – Watchlist mit Zone-Filter
  /api/signals    – Signal-Detail + Score-Verlauf
  /api/portfolio  – Positionen CRUD + Exit-Signale
  /api/dashboard  – Tagesübersicht
  /api/history    – Trade-Archiv + Signalqualität
  /api/scan       – Manueller Scan-Trigger
  /api/config     – App-Konfiguration + API-Status
  /api/universe   – Ticker-Verwaltung + Suche
"""
from fastapi import APIRouter

from backend.api.logs       import router as logs_router
from backend.api.watchlist  import router as watchlist_router
from backend.api.signals    import router as signals_router
from backend.api.portfolio  import router as portfolio_router
from backend.api.dashboard  import router as dashboard_router
from backend.api.history    import router as history_router
from backend.api.scan       import router as scan_router
from backend.api.config     import router as config_router
from backend.api.universe   import router as universe_router

router = APIRouter()

router.include_router(logs_router,       prefix="/logs",      tags=["Logs"])
router.include_router(watchlist_router,  prefix="/watchlist", tags=["Watchlist"])
router.include_router(signals_router,    prefix="/signals",   tags=["Signale"])
router.include_router(portfolio_router,  prefix="/portfolio", tags=["Portfolio"])
router.include_router(dashboard_router,  prefix="/dashboard", tags=["Dashboard"])
router.include_router(history_router,    prefix="/history",   tags=["Historie"])
router.include_router(scan_router,       prefix="/scan",      tags=["Scan"])
router.include_router(config_router,     prefix="/config",    tags=["Konfiguration"])
router.include_router(universe_router,   prefix="/universe",  tags=["Universum"])
