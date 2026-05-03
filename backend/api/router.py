"""Zentraler API-Router: sammelt alle Sub-Router.

Phase 3 wird die vollständigen Endpunkte implementieren.
Bereits aktiv: /api/logs (Fehlerprotokoll)
"""
from fastapi import APIRouter

from backend.api.logs import router as logs_router

router = APIRouter()

router.include_router(logs_router, prefix="/logs", tags=["Logs"])

# Platzhalter für Phase-3-Router (werden hier eingebunden):
# from backend.api.watchlist  import router as watchlist_router
# from backend.api.signals    import router as signals_router
# from backend.api.portfolio  import router as portfolio_router
# from backend.api.dashboard  import router as dashboard_router
# from backend.api.history    import router as history_router
# from backend.api.scan       import router as scan_router
# from backend.api.config     import router as config_router
# from backend.api.universe   import router as universe_router
