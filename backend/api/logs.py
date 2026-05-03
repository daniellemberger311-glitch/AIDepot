"""API-Endpunkt: GET /api/logs – App-Log-Übersicht mit Fehlerfilter."""
from fastapi import APIRouter, Query
from typing import Optional

from backend.log_handler import memory_handler

router = APIRouter()


@router.get("", summary="Log-Einträge abrufen")
def get_logs(
    level:  Optional[str] = Query(None,  description="Mindest-Level: DEBUG | INFO | WARNING | ERROR | CRITICAL"),
    module: Optional[str] = Query(None,  description="Logger-Namenfilter (Teilstring), z.B. 'scoring'"),
    limit:  int           = Query(200,   ge=1, le=1000, description="Max. Anzahl Einträge"),
    since:  Optional[str] = Query(None,  description="ISO-Timestamp – nur Einträge ab diesem Zeitpunkt"),
):
    """
    Gibt gepufferte Log-Einträge zurück (neueste zuerst).

    Beispiele:
    - Nur Fehler:          GET /api/logs?level=ERROR
    - Scoring-Probleme:    GET /api/logs?level=WARNING&module=scoring
    - Letzte 50 Einträge:  GET /api/logs?limit=50
    """
    entries = memory_handler.get_entries(level=level, module=module, limit=limit, since=since)
    return {
        "total_returned": len(entries),
        "error_count":    memory_handler.error_count(),
        "warning_count":  memory_handler.warning_count(),
        "entries":        entries,
    }


@router.get("/summary", summary="Log-Zusammenfassung")
def get_log_summary():
    """Schnellübersicht: nur Fehler- und Warnzähler + letzte 10 Fehler."""
    errors = memory_handler.get_entries(level="ERROR", limit=10)
    return {
        "error_count":   memory_handler.error_count(),
        "warning_count": memory_handler.warning_count(),
        "recent_errors": errors,
    }


@router.delete("", summary="Log-Puffer leeren")
def clear_logs():
    """Löscht alle gepufferten Log-Einträge aus dem RAM."""
    memory_handler.clear()
    return {"message": "Log-Puffer geleert"}
