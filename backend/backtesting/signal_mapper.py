"""Signal-Mapper: erkennt Signal-Events aus historischen Score-Verläufen.

Event-Typen:
  ZONE_CHANGE  – Zonenänderung zwischen zwei aufeinanderfolgenden Tagen
  ZONE1_ENTRY  – Erstmaliger Eintritt in Zone 1 (nach ≥ 1 Tag außerhalb)
  DELTA_SPIKE  – Δ1T ≥ alert_delta_1d-Schwelle (positiv oder negativ)
  STREAK_7D    – 7 aufeinanderfolgende Tage mit positivem Δ1T

Alle Events haben ein Icon und eine Beschreibung für den Frontend-Zeitstrahl.
"""
import logging
from typing import Optional

from backend.schemas import BacktestDataPoint, BacktestSignalEvent

logger = logging.getLogger(__name__)

# Standard-Schwellenwerte (werden aus DB-Konfig überschrieben wenn vorhanden)
_DEFAULT_ALERT_DELTA_1D = 15.0
_STREAK_MIN_DAYS        = 7


def map_signals(
    data_points:   list[BacktestDataPoint],
    alert_delta_1d: float = _DEFAULT_ALERT_DELTA_1D,
) -> list[BacktestSignalEvent]:
    """
    Identifiziert alle Signal-Events aus einer geordneten Liste von BacktestDataPoints.
    Gibt Events chronologisch sortiert zurück.
    """
    if not data_points:
        return []

    events:        list[BacktestSignalEvent] = []
    streak_count:  int = 0
    in_zone1:      bool = False

    for i, dp in enumerate(data_points):
        prev = data_points[i - 1] if i > 0 else None

        # ── Zonenänderung ────────────────────────────────────────────────────
        if prev and prev.zone != dp.zone:
            direction = "📈" if dp.zone < prev.zone else "📉"
            events.append(BacktestSignalEvent(
                date        = dp.date,
                event_type  = "ZONE_CHANGE",
                from_zone   = prev.zone,
                to_zone     = dp.zone,
                score       = dp.score,
                delta_1d    = dp.delta_1d,
                delta_7d    = dp.delta_7d,
                description = f"{direction} Zone {prev.zone} → Zone {dp.zone}  |  Score: {dp.score:.0f}",
            ))

        # ── Zone-1-Eintritt (separates Event für Einstiegs-Markierung) ───────
        if dp.zone == 1 and not in_zone1:
            events.append(BacktestSignalEvent(
                date        = dp.date,
                event_type  = "ZONE1_ENTRY",
                from_zone   = prev.zone if prev else None,
                to_zone     = 1,
                score       = dp.score,
                delta_1d    = dp.delta_1d,
                delta_7d    = dp.delta_7d,
                description = f"🎯 Zone-1-Eintritt  |  Score: {dp.score:.0f}",
            ))
        in_zone1 = dp.zone == 1

        # ── Delta-Spike ──────────────────────────────────────────────────────
        if dp.delta_1d is not None and abs(dp.delta_1d) >= alert_delta_1d:
            sign = "+" if dp.delta_1d > 0 else ""
            events.append(BacktestSignalEvent(
                date        = dp.date,
                event_type  = "DELTA_SPIKE",
                from_zone   = None,
                to_zone     = dp.zone,
                score       = dp.score,
                delta_1d    = dp.delta_1d,
                delta_7d    = dp.delta_7d,
                description = f"⚡ Δ1T: {sign}{dp.delta_1d:.1f}  |  Score: {dp.score:.0f}",
            ))

        # ── 7-Tage-Aufwärtstrend ─────────────────────────────────────────────
        if dp.delta_1d is not None and dp.delta_1d > 0:
            streak_count += 1
        else:
            streak_count = 0

        if streak_count == _STREAK_MIN_DAYS:
            events.append(BacktestSignalEvent(
                date        = dp.date,
                event_type  = "STREAK_7D",
                from_zone   = None,
                to_zone     = dp.zone,
                score       = dp.score,
                delta_1d    = dp.delta_1d,
                delta_7d    = dp.delta_7d,
                description = f"🔨 7-Tage-Aufwärtstrend  |  Δ7T: {dp.delta_7d:+.1f}" if dp.delta_7d else "🔨 7-Tage-Aufwärtstrend",
            ))

    return events


def summarize(
    data_points: list[BacktestDataPoint],
    events:      list[BacktestSignalEvent],
) -> dict:
    """Kennzahlen-Zusammenfassung für das Backtest-Ergebnis."""
    if not data_points:
        return {
            "total_trading_days": 0,
            "total_signals":      0,
            "zone1_entries":      0,
            "zone1_days":         0,
            "zone1_days_pct":     0.0,
            "max_score":          None,
            "min_score":          None,
            "avg_score":          None,
            "delta_spikes":       0,
            "streaks_7d":         0,
            "zone_changes":       0,
        }

    scores      = [dp.score for dp in data_points]
    zone1_days  = sum(1 for dp in data_points if dp.zone == 1)
    n           = len(data_points)

    return {
        "total_trading_days": n,
        "total_signals":      len(events),
        "zone1_entries":      sum(1 for e in events if e.event_type == "ZONE1_ENTRY"),
        "zone1_days":         zone1_days,
        "zone1_days_pct":     round(zone1_days / n * 100, 1) if n else 0.0,
        "max_score":          round(max(scores), 1),
        "min_score":          round(min(scores), 1),
        "avg_score":          round(sum(scores) / n, 1),
        "delta_spikes":       sum(1 for e in events if e.event_type == "DELTA_SPIKE"),
        "streaks_7d":         sum(1 for e in events if e.event_type == "STREAK_7D"),
        "zone_changes":       sum(1 for e in events if e.event_type == "ZONE_CHANGE"),
    }
