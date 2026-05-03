"""POST /api/backtest – Historische Signal-Simulation für einen Ticker.

Für kurze Zeiträume (≤ 1 Jahr) läuft der Backtest synchron.
Für längere Zeiträume wird ein Background-Task gestartet und der Status
kann über GET /api/backtest/status/{ticker} abgerufen werden.

Maximaler Zeitraum: 5 Jahre (begrenzt durch yfinance-Datenverfügbarkeit
und Rechenzeit; ca. 5–15 Sekunden pro Jahr je nach Ticker).
"""
import logging
import time
from datetime import datetime, date as date_type
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.schemas import BacktestRequest, BacktestResult, BacktestDataPoint, BacktestSignalEvent
from backend.backtesting.engine import run_backtest
from backend.backtesting.signal_mapper import map_signals, summarize

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Backtest-Status (Modul-Level, analog zu scan_state) ──────────────────────
_backtest_jobs: dict[str, dict] = {}   # key: "{ticker}:{from}:{to}"

_MAX_SYNC_YEARS = 1     # Zeiträume ≤ 1 Jahr → synchron
_MAX_YEARS      = 5     # Absolutes Maximum


def _job_key(ticker: str, from_date: str, to_date: str) -> str:
    return f"{ticker}:{from_date}:{to_date}"


def _run_backtest_job(ticker: str, from_date: str, to_date: str, alert_delta_1d: float) -> None:
    """Hintergrund-Job: Backtest berechnen und Ergebnis in _backtest_jobs speichern."""
    key = _job_key(ticker, from_date, to_date)
    _backtest_jobs[key]["status"] = "running"
    _backtest_jobs[key]["started_at"] = datetime.utcnow().isoformat()

    start = time.monotonic()
    try:
        data_points = run_backtest(ticker, from_date, to_date)
        events      = map_signals(data_points, alert_delta_1d)
        summary     = summarize(data_points, events)

        _backtest_jobs[key].update({
            "status":       "done",
            "duration_sec": round(time.monotonic() - start, 1),
            "result": {
                "ticker":        ticker,
                "from_date":     from_date,
                "to_date":       to_date,
                "price_data":    [dp.model_dump() for dp in data_points],
                "signals":       [e.model_dump() for e in events],
                "total_signals": summary["total_signals"],
                "zone1_entries": summary["zone1_entries"],
                "summary":       summary,
            },
        })
    except Exception as exc:
        logger.error("Backtest-Job %s fehlgeschlagen: %s", key, exc)
        _backtest_jobs[key].update({
            "status":  "error",
            "error":   str(exc),
            "duration_sec": round(time.monotonic() - start, 1),
        })


def _get_alert_delta() -> float:
    """alert_delta_1d-Schwelle aus DB lesen (Fallback: 15)."""
    try:
        from backend.database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            val = db.execute(
                text("SELECT value FROM configuration WHERE key='alert_delta_1d'")
            ).scalar_one_or_none()
            return float(val) if val else 15.0
    except Exception:
        return 15.0


# ── Validierung ───────────────────────────────────────────────────────────────

def _validate_dates(from_date: str, to_date: str) -> None:
    try:
        fd = datetime.strptime(from_date, "%Y-%m-%d").date()
        td = datetime.strptime(to_date,   "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, f"Ungültiges Datumsformat: {exc}")

    if fd >= td:
        raise HTTPException(400, "from_date muss vor to_date liegen")
    if td > date_type.today():
        raise HTTPException(400, "to_date darf nicht in der Zukunft liegen")

    years = (td - fd).days / 365.25
    if years > _MAX_YEARS:
        raise HTTPException(400, f"Maximaler Zeitraum: {_MAX_YEARS} Jahre")


# ── Endpunkte ─────────────────────────────────────────────────────────────────

@router.post("", response_model=BacktestResult, summary="Backtest starten")
def start_backtest(
    payload:          BacktestRequest,
    background_tasks: BackgroundTasks,
):
    """
    Historische Signal-Simulation für einen Ticker.

    - Zeitraum ≤ 1 Jahr → synchron (Antwort direkt)
    - Zeitraum > 1 Jahr → Hintergrund-Job (HTTP 202 über separaten Endpunkt)

    **Hinweis:** Sentiment-Score ist historisch nicht verfügbar → immer 12,5/25 (neutral).
    """
    ticker    = payload.ticker.upper()
    from_date = payload.from_date
    to_date   = payload.to_date

    _validate_dates(from_date, to_date)

    years         = (datetime.strptime(to_date, "%Y-%m-%d") - datetime.strptime(from_date, "%Y-%m-%d")).days / 365.25
    alert_delta   = _get_alert_delta()

    # Kurze Zeiträume synchron berechnen
    if years <= _MAX_SYNC_YEARS:
        data_points = run_backtest(ticker, from_date, to_date)
        if not data_points:
            raise HTTPException(404, f"Keine Daten für {ticker} im Zeitraum {from_date}–{to_date}")
        events  = map_signals(data_points, alert_delta)
        summary = summarize(data_points, events)
        return BacktestResult(
            ticker        = ticker,
            from_date     = from_date,
            to_date       = to_date,
            price_data    = data_points,
            signals       = events,
            total_signals = summary["total_signals"],
            zone1_entries = summary["zone1_entries"],
        )

    # Längere Zeiträume als Hintergrund-Job
    key = _job_key(ticker, from_date, to_date)
    if key not in _backtest_jobs or _backtest_jobs[key].get("status") == "error":
        _backtest_jobs[key] = {"status": "queued", "result": None, "error": None}
        background_tasks.add_task(_run_backtest_job, ticker, from_date, to_date, alert_delta)

    status = _backtest_jobs[key]["status"]
    if status == "done":
        r = _backtest_jobs[key]["result"]
        return BacktestResult(
            ticker        = r["ticker"],
            from_date     = r["from_date"],
            to_date       = r["to_date"],
            price_data    = [BacktestDataPoint(**dp) for dp in r["price_data"]],
            signals       = [BacktestSignalEvent(**e) for e in r["signals"]],
            total_signals = r["total_signals"],
            zone1_entries = r["zone1_entries"],
        )

    raise HTTPException(
        202,
        detail={
            "message":  "Backtest läuft im Hintergrund",
            "status":   status,
            "job_key":  key,
            "check_at": f"/api/backtest/status/{ticker}?from_date={from_date}&to_date={to_date}",
        },
    )


@router.get("/status/{ticker}", summary="Backtest-Status")
def get_backtest_status(ticker: str, from_date: str, to_date: str):
    """Status eines laufenden oder abgeschlossenen Backtest-Jobs."""
    key = _job_key(ticker.upper(), from_date, to_date)
    if key not in _backtest_jobs:
        raise HTTPException(404, "Kein Backtest-Job für diese Parameter gefunden")

    job = _backtest_jobs[key]
    return {
        "ticker":       ticker.upper(),
        "from_date":    from_date,
        "to_date":      to_date,
        "status":       job["status"],
        "started_at":   job.get("started_at"),
        "duration_sec": job.get("duration_sec"),
        "error":        job.get("error"),
        "ready":        job["status"] == "done",
    }


@router.delete("/cache/{ticker}", summary="Backtest-Cache leeren")
def clear_backtest_cache(ticker: str):
    """Gecachte Backtest-Ergebnisse und OHLCV-Cache für einen Ticker löschen."""
    from backend.backtesting.historical_data import _cache

    removed_jobs = [k for k in list(_backtest_jobs) if k.startswith(ticker.upper() + ":")]
    for k in removed_jobs:
        del _backtest_jobs[k]

    removed_cache = [k for k in list(_cache) if ticker.upper() in k]
    for k in removed_cache:
        del _cache[k]

    return {
        "ticker":         ticker.upper(),
        "jobs_removed":   len(removed_jobs),
        "cache_removed":  len(removed_cache),
    }
