"""POST /api/scan/trigger – Manueller Scan-Trigger mit Background-Task.

Scan-Status wird in einem Modul-Level-Dict gehalten (Single-User, kein Redis nötig).
Der Scheduler ruft dieselbe run_scan()-Funktion auf.
"""
import logging
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.database import get_db, SessionLocal
from backend.models import Stock

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Gemeinsamer Scan-Status ──────────────────────────────────────────────────
# Wird von API und Scheduler gelesen/geschrieben.
scan_state: dict = {
    "running":           False,
    "started_at":        None,
    "progress":          0,
    "total":             0,
    "current_ticker":    None,
    "last_completed":    None,
    "last_duration_sec": None,
    "error":             None,
    "tickers_done":      [],
    "tickers_failed":    [],
    "cancelled":         False,
}


def run_scan(ticker_list: Optional[list[str]] = None) -> None:
    """
    Vollständigen Scan für alle (oder angegebene) Ticker ausführen.
    Blockiert – in einem Thread oder via BackgroundTasks aufrufen.
    """
    from backend.scheduler.priority_queue import build_scan_queue

    if scan_state["running"]:
        logger.warning("Scan bereits aktiv – überspringe Doppel-Start")
        return

    scan_state.update({
        "running":        True,
        "started_at":     datetime.utcnow().isoformat(),
        "progress":       0,
        "current_ticker": None,
        "error":          None,
        "tickers_done":   [],
        "tickers_failed": [],
        "cancelled":      False,
    })

    start_ts = time.monotonic()

    try:
        with SessionLocal() as db:
            tickers = ticker_list or build_scan_queue(db)
            scan_state["total"] = len(tickers)
            logger.info("Scan gestartet: %d Ticker", len(tickers))

            from backend.scoring.orchestrator import score_ticker_safe
            for i, ticker in enumerate(tickers):
                if scan_state["cancelled"]:
                    logger.info("Scan manuell abgebrochen nach %d/%d Tickern", i, len(tickers))
                    scan_state["error"] = f"Manuell abgebrochen nach {i} von {len(tickers)} Tickern"
                    break
                scan_state["current_ticker"] = ticker
                result = score_ticker_safe(ticker, db)
                scan_state["progress"] = i + 1
                if result:
                    scan_state["tickers_done"].append(ticker)
                else:
                    scan_state["tickers_failed"].append(ticker)

    except Exception as exc:
        scan_state["error"] = str(exc)
        logger.error("Scan abgebrochen: %s", exc)
    finally:
        duration = round(time.monotonic() - start_ts, 1)
        scan_state.update({
            "running":           False,
            "last_completed":    datetime.utcnow().isoformat(),
            "last_duration_sec": duration,
            "current_ticker":    None,
        })
        logger.info(
            "Scan abgeschlossen: %d/%d Ticker in %.0fs (%d Fehler)",
            len(scan_state["tickers_done"]),
            scan_state["total"],
            duration,
            len(scan_state["tickers_failed"]),
        )


# ── Endpunkte ────────────────────────────────────────────────────────────────

@router.post("/trigger", status_code=202, summary="Scan manuell starten")
def trigger_scan(
    background_tasks: BackgroundTasks,
    tickers: Optional[list[str]] = None,
):
    """
    Startet einen vollständigen Scan im Hintergrund.
    Gibt sofort zurück (HTTP 202). Status über GET /api/scan/status abrufen.

    Optional: `tickers`-Liste für Einzel-Ticker-Tests übergeben.
    """
    if scan_state["running"]:
        return {
            "message":  "Scan läuft bereits",
            "started_at": scan_state["started_at"],
            "progress": scan_state["progress"],
            "total":    scan_state["total"],
        }

    background_tasks.add_task(run_scan, tickers)
    return {
        "message":    "Scan gestartet",
        "started_at": datetime.utcnow().isoformat(),
    }


@router.get("/status", summary="Scan-Status")
def get_scan_status():
    """Aktueller Scan-Fortschritt und letzter Abschluss-Zeitpunkt."""
    return {
        "running":           scan_state["running"],
        "started_at":        scan_state["started_at"],
        "progress":          scan_state["progress"],
        "total":             scan_state["total"],
        "current_ticker":    scan_state["current_ticker"],
        "last_completed":    scan_state["last_completed"],
        "last_duration_sec": scan_state["last_duration_sec"],
        "error":             scan_state["error"],
        "tickers_failed":    scan_state["tickers_failed"],
    }


@router.post("/cancel", summary="Laufenden Scan abbrechen")
def cancel_scan():
    """Setzt ein Abbruch-Flag – der aktuelle Ticker wird noch abgeschlossen."""
    if not scan_state["running"]:
        return {"message": "Kein Scan aktiv"}
    scan_state["cancelled"] = True
    return {"message": "Abbruch angefordert – aktueller Ticker wird noch fertig"}


@router.post("/ticker/{ticker}", summary="Einzelnen Ticker scannen")
def scan_single_ticker(ticker: str, db: Session = Depends(get_db)):
    """Einen einzelnen Ticker sofort (synchron) scannen. Nützlich zum Testen."""
    from backend.scoring.orchestrator import score_ticker_safe
    result = score_ticker_safe(ticker.upper(), db)
    if result is None:
        return {"success": False, "ticker": ticker.upper(), "error": "Scoring fehlgeschlagen – Details im Log"}
    return {
        "success":     True,
        "ticker":      result["ticker"],
        "score_date":  result["score_date"],
        "total_score": result["total_score"],
        "zone":        result["zone"],
        "l1":          result["l1"],
        "l2":          result["l2"],
        "l3":          result["l3"],
    }
