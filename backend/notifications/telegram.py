"""Telegram-Benachrichtigungen: Bot-Sender + alle 5 Nachrichtentypen.

Typen:
  ZONE_CHANGE   – Ticker wechselt Zone
  DELTA_SPIKE   – Score steigt um ≥ alert_delta_1d an einem Tag
  STREAK_7D     – 7-Tage-Aufwärtstrend
  EXIT          – Exit-Signal für offene Position
  DAILY_SUMMARY – Tages-Zusammenfassung nach Scan
"""
import logging
import asyncio
from datetime import datetime
from typing import Optional

from backend.config import settings
from backend.database import SessionLocal

logger = logging.getLogger(__name__)


# ── Bot-Sender ────────────────────────────────────────────────────────────────

def _send_message(text: str) -> bool:
    """Synchrone Telegram-Nachricht senden. Gibt True bei Erfolg zurück."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.debug("Telegram nicht konfiguriert – Nachricht übersprungen")
        return False

    try:
        import telegram  # python-telegram-bot
        bot = telegram.Bot(token=settings.telegram_bot_token)
        asyncio.get_event_loop().run_until_complete(
            bot.send_message(
                chat_id    = settings.telegram_chat_id,
                text       = text,
                parse_mode = "HTML",
            )
        )
        return True
    except Exception as exc:
        logger.error("Telegram-Fehler: %s", exc)
        return False


def _log_notification(channel: str, notif_type: str, ticker: Optional[str],
                       message: str, success: bool, error: Optional[str] = None) -> None:
    """Gesendete Nachricht in notifications_log schreiben."""
    try:
        from backend.models import NotificationLog
        with SessionLocal() as db:
            db.add(NotificationLog(
                channel           = channel,
                notification_type = notif_type,
                ticker            = ticker,
                message_text      = message[:4000],
                sent_at           = datetime.utcnow().isoformat(),
                success           = int(success),
                error_detail      = error,
            ))
            db.commit()
    except Exception as exc:
        logger.error("Notification-Log fehlgeschlagen: %s", exc)


# ── Nachrichtentypen ──────────────────────────────────────────────────────────

def notify_zone_change(ticker: str, old_zone: int, new_zone: int, score: float, delta_7d: Optional[float]) -> None:
    """Zonenänderung – z. B. Zone 3 → Zone 2."""
    direction = "📈" if new_zone < old_zone else "📉"
    delta_str = f" | Δ7T: {delta_7d:+.1f}" if delta_7d is not None else ""
    msg = (
        f"{direction} <b>ZONEN-WECHSEL: {ticker}</b>\n"
        f"Z{old_zone} → Z{new_zone}  |  Score: <b>{score:.0f}</b>{delta_str}"
    )
    success = _send_message(msg)
    _log_notification("TELEGRAM", "ZONE_CHANGE", ticker, msg, success)


def notify_delta_spike(ticker: str, score: float, delta_1d: float, zone: int) -> None:
    """Starker Tages-Score-Anstieg."""
    msg = (
        f"⚡ <b>KATALYSATOR: {ticker}</b>\n"
        f"Score +{delta_1d:.1f} an einem Tag → <b>{score:.0f}</b>  |  Zone {zone}"
    )
    success = _send_message(msg)
    _log_notification("TELEGRAM", "DELTA_SPIKE", ticker, msg, success)


def notify_streak_7d(ticker: str, score: float, delta_7d: float, streak_days: int) -> None:
    """7-Tage-Aufwärtstrend hält an."""
    msg = (
        f"🔨 <b>AUFBAU: {ticker}</b>\n"
        f"7-Tage-Trend steigt seit {streak_days} Tagen  |  Δ7T: <b>{delta_7d:+.1f}</b>  |  Score: {score:.0f}"
    )
    success = _send_message(msg)
    _log_notification("TELEGRAM", "STREAK_7D", ticker, msg, success)


def notify_exit_signal(
    ticker:      str,
    signal_type: str,
    severity:    str,
    message:     str,
    current_pnl: Optional[float],
) -> None:
    """Exit-Warnung für eine offene Position."""
    icon = "🔴" if severity == "RED" else "🟡"
    pnl_str = f"  |  P&L: {current_pnl:+.1f}%" if current_pnl is not None else ""
    msg = (
        f"{icon} <b>EXIT: {ticker}</b> [{signal_type}]\n"
        f"{message}{pnl_str}"
    )
    success = _send_message(msg)
    _log_notification("TELEGRAM", "EXIT", ticker, msg, success)


def send_daily_summary() -> None:
    """
    Tages-Zusammenfassung nach dem Scan:
    - Top-5 Zone-1-Ticker
    - Anzahl Exit-Warnungen
    - Scan-Statistik
    """
    from sqlalchemy import select, func
    from backend.models import DailyScore, ExitSignal, Position, Stock

    try:
        with SessionLocal() as db:
            latest_date = db.execute(
                select(DailyScore.score_date).order_by(DailyScore.score_date.desc()).limit(1)
            ).scalar_one_or_none()
            if not latest_date:
                return

            # Zone-Verteilung
            zones = {z: 0 for z in range(1, 5)}
            for zone, count in db.execute(
                select(DailyScore.zone, func.count(DailyScore.id))
                .where(DailyScore.score_date == latest_date)
                .group_by(DailyScore.zone)
            ).all():
                zones[zone] = count

            # Top-5 Zone 1
            top5 = db.execute(
                select(DailyScore, Stock.name)
                .join(Stock, Stock.ticker == DailyScore.ticker, isouter=True)
                .where(DailyScore.score_date == latest_date, DailyScore.zone == 1)
                .order_by(DailyScore.total_score.desc())
                .limit(5)
            ).all()

            # Offene Exit-Warnungen
            exit_count = db.execute(
                select(func.count(ExitSignal.id))
                .join(Position, Position.id == ExitSignal.position_id)
                .where(ExitSignal.is_acknowledged == 0, Position.is_open == 1)
            ).scalar_one() or 0

            # Nachricht aufbauen
            total = sum(zones.values())
            top5_lines = "\n".join(
                f"  {i+1}. <b>{ds.ticker}</b> {ds.total_score:.0f} Pkt"
                + (f" ({name})" if name else "")
                for i, (ds, name) in enumerate(top5)
            ) or "  – (noch kein Scan heute)"

            exit_line = f"⚠️ {exit_count} offene Exit-Warnungen" if exit_count else "✅ Keine Exit-Warnungen"

            msg = (
                f"📊 <b>TAGES-ZUSAMMENFASSUNG</b> ({latest_date})\n\n"
                f"Gescannte Aktien: {total}\n"
                f"Zone 1 (≥76): {zones[1]} | Zone 2: {zones[2]} | Zone 3: {zones[3]} | Zone 4: {zones[4]}\n\n"
                f"<b>Top-5 Zone 1:</b>\n{top5_lines}\n\n"
                f"{exit_line}"
            )

            success = _send_message(msg)
            _log_notification("TELEGRAM", "DAILY_SUMMARY", None, msg, success)

    except Exception as exc:
        logger.error("Tages-Zusammenfassung fehlgeschlagen: %s", exc)


def send_test_message() -> bool:
    """Test-Nachricht senden (für Konfigurations-Check)."""
    msg = (
        f"✅ <b>AIDepot – Verbindungstest</b>\n"
        f"Telegram ist korrekt konfiguriert.\n"
        f"Zeit: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    success = _send_message(msg)
    _log_notification("TELEGRAM", "TEST", None, msg, success)
    return success


# ── Benachrichtigungs-Dispatcher ──────────────────────────────────────────────

def dispatch_scan_notifications(db) -> None:
    """
    Nach jedem Scan aufrufen: erkennt Zonenänderungen, Spikes und Streaks
    und sendet die entsprechenden Telegram-Nachrichten.
    """
    from sqlalchemy import select, text
    from backend.models import DailyScore, ScoreHistory

    alert_delta_1d = float(
        db.execute(text("SELECT value FROM configuration WHERE key='alert_delta_1d'")).scalar_one_or_none() or 15
    )
    streak_days_threshold = 3

    latest_date = db.execute(
        select(DailyScore.score_date).order_by(DailyScore.score_date.desc()).limit(1)
    ).scalar_one_or_none()
    if not latest_date:
        return

    today_scores = db.execute(
        select(DailyScore).where(DailyScore.score_date == latest_date)
    ).scalars().all()

    for ds in today_scores:
        # Zonenänderung: Vergleich mit vorherigem Score-Tag
        prev = db.execute(
            select(ScoreHistory)
            .where(ScoreHistory.ticker == ds.ticker, ScoreHistory.score_date < latest_date)
            .order_by(ScoreHistory.score_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        if prev and prev.zone != ds.zone:
            notify_zone_change(ds.ticker, prev.zone, ds.zone, ds.total_score, ds.delta_7d)

        # Delta-Spike
        if ds.delta_1d is not None and abs(ds.delta_1d) >= alert_delta_1d:
            notify_delta_spike(ds.ticker, ds.total_score, ds.delta_1d, ds.zone)

        # 7-Tage-Aufwärtstrend (≥ streak_days_threshold aufeinanderfolgende positive Δ1T)
        if ds.delta_7d is not None and ds.delta_7d > 0:
            history = db.execute(
                select(ScoreHistory)
                .where(ScoreHistory.ticker == ds.ticker)
                .order_by(ScoreHistory.score_date.desc())
                .limit(streak_days_threshold + 1)
            ).scalars().all()
            if len(history) >= streak_days_threshold:
                scores = [h.total_score for h in history]
                if all(scores[i] > scores[i+1] for i in range(len(scores)-1)):
                    notify_streak_7d(ds.ticker, ds.total_score, ds.delta_7d, len(history))
