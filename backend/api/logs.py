"""API-Endpunkt: GET /api/logs – App-Log-Übersicht mit Fehlerfilter."""
import re
from fastapi import APIRouter, Query
from typing import Optional

from backend.log_handler import memory_handler, LOG_FILE

router = APIRouter()

_LEVEL_ORDER = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
_LOG_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(?P<level>\w+)\s+(?P<logger>\S+)\s+–\s+(?P<message>.+)$"
)


def _read_file_logs(level: Optional[str], module: Optional[str], limit: int) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    level_no = _LEVEL_ORDER.get(level.upper(), 0) if level else 0
    entries: list[dict] = []
    try:
        with LOG_FILE.open(encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        for line in reversed(lines):
            m = _LOG_LINE_RE.match(line.rstrip())
            if not m:
                continue
            lvl = m.group("level")
            if _LEVEL_ORDER.get(lvl, 0) < level_no:
                continue
            if module and module.lower() not in m.group("logger").lower():
                continue
            entries.append({
                "timestamp": m.group("ts").replace(" ", "T") + "+00:00",
                "level":     lvl,
                "logger":    m.group("logger"),
                "message":   m.group("message"),
            })
            if len(entries) >= limit:
                break
    except Exception:
        pass
    return entries


@router.get("", summary="Log-Einträge abrufen")
def get_logs(
    level:  Optional[str] = Query(None,  description="Mindest-Level: DEBUG | INFO | WARNING | ERROR | CRITICAL"),
    module: Optional[str] = Query(None,  description="Logger-Namenfilter (Teilstring), z.B. 'scoring'"),
    limit:  int           = Query(500,   ge=1, le=2000, description="Max. Anzahl Einträge"),
    since:  Optional[str] = Query(None,  description="ISO-Timestamp – nur Einträge ab diesem Zeitpunkt"),
    source: str           = Query("memory", description="'memory' (RAM-Puffer) oder 'file' (persistente Log-Datei)"),
):
    """
    Gibt gepufferte Log-Einträge zurück (neueste zuerst).

    - source=memory  → RAM-Puffer (wird bei Neustart geleert, default)
    - source=file    → persistente Log-Datei data/aidepot.log (Scan-Logs bleiben erhalten)

    Beispiele:
    - Scan-Logs von heute: GET /api/logs?source=file&module=scoring&limit=500
    - Nur Fehler:          GET /api/logs?level=ERROR&source=file
    """
    if source == "file":
        entries = _read_file_logs(level=level, module=module, limit=limit)
    else:
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
