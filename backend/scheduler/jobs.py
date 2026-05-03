"""APScheduler-Jobs: Täglicher Scan (06:00 UTC) + wöchentliche Wartung (So 02:00 UTC).

Eingebunden in main.py via lifespan-Context-Manager.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import settings
from backend.database import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ── Job-Funktionen ────────────────────────────────────────────────────────────

def job_daily_scan() -> None:
    """Täglicher Hauptscan: alle Tiers in Prioritätsreihenfolge."""
    logger.info("=== Täglicher Scan gestartet (UTC %s) ===", datetime.utcnow().isoformat())
    from backend.api.scan import run_scan
    run_scan()


def job_check_exit_signals() -> None:
    """Exit-Signale für alle offenen Positionen nach dem Scan prüfen."""
    from backend.models import Position
    from backend.api.portfolio import _generate_exit_signals, _get_config_float
    from backend.models import DailyScore
    from sqlalchemy import select

    logger.info("Exit-Signal-Check gestartet")
    with SessionLocal() as db:
        open_positions = db.execute(
            select(Position).where(Position.is_open == 1)
        ).scalars().all()

        total_new = 0
        for pos in open_positions:
            latest_ds = db.execute(
                select(DailyScore)
                .where(DailyScore.ticker == pos.ticker)
                .order_by(DailyScore.score_date.desc())
                .limit(1)
            ).scalar_one_or_none()
            new_sigs = _generate_exit_signals(pos, latest_ds, db)
            total_new += len(new_sigs)

        logger.info("Exit-Signal-Check abgeschlossen: %d neue Signale für %d Positionen", total_new, len(open_positions))


def job_send_notifications() -> None:
    """Tages-Zusammenfassung und Exit-Alerts per Telegram versenden."""
    from backend.notifications.telegram import send_daily_summary
    send_daily_summary()


def job_weekly_maintenance() -> None:
    """Sonntags 02:00 UTC: Wikipedia-Refresh + Cache-Bereinigung."""
    logger.info("=== Wöchentliche Wartung gestartet ===")

    with SessionLocal() as db:
        # Cache bereinigen
        try:
            from sqlalchemy import text
            deleted = db.execute(
                text("DELETE FROM api_cache WHERE expires_at < datetime('now')")
            ).rowcount
            db.commit()
            logger.info("Cache bereinigt: %d abgelaufene Einträge gelöscht", deleted)
        except Exception as exc:
            logger.error("Cache-Bereinigung fehlgeschlagen: %s", exc)

        # Wikipedia-Listen aktualisieren (Internet erforderlich)
        try:
            from backend.universe.loader import refresh_universe
            result = refresh_universe(db)
            logger.info(
                "Universe-Refresh: %d neue, %d aktualisierte Ticker (gesamt aktiv: %d)",
                result.get("added", 0),
                result.get("updated", 0),
                result.get("total_active", 0),
            )
        except Exception as exc:
            logger.warning("Universe-Refresh fehlgeschlagen (kein Internet?): %s", exc)


# ── Scheduler-Lifecycle ───────────────────────────────────────────────────────

def start_scheduler() -> None:
    """APScheduler initialisieren und Jobs registrieren."""
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("Scheduler läuft bereits – überspringe Start")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")

    scan_hour   = settings.scan_hour_utc
    scan_minute = settings.scan_minute_utc

    # Täglicher Hauptscan
    _scheduler.add_job(
        job_daily_scan,
        CronTrigger(hour=scan_hour, minute=scan_minute, timezone="UTC"),
        id="daily_scan",
        replace_existing=True,
        misfire_grace_time=600,  # bis zu 10 Min Verzögerung tolerieren
    )

    # Exit-Signal-Check 30 Minuten nach Scan-Start (nach Abschluss des Scans)
    _scheduler.add_job(
        job_check_exit_signals,
        CronTrigger(hour=scan_hour, minute=(scan_minute + 30) % 60, timezone="UTC"),
        id="exit_signal_check",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Telegram-Benachrichtigung 1 Stunde nach Scan
    _scheduler.add_job(
        job_send_notifications,
        CronTrigger(hour=(scan_hour + 1) % 24, minute=scan_minute, timezone="UTC"),
        id="send_notifications",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Wöchentliche Wartung (Sonntag 02:00 UTC)
    _scheduler.add_job(
        job_weekly_maintenance,
        CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="UTC"),
        id="weekly_maintenance",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info(
        "Scheduler gestartet: tägl. Scan %02d:%02d UTC, wöchentl. Wartung So 02:00 UTC",
        scan_hour, scan_minute,
    )


def stop_scheduler() -> None:
    """Scheduler sauber beenden (in lifespan-Teardown aufrufen)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler gestoppt")


def get_scheduler_info() -> dict:
    """Status und nächste Ausführungszeiten aller Jobs."""
    if not _scheduler or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id":       job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return {"running": True, "jobs": jobs}
