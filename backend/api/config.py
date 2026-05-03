"""GET/PUT /api/config – App-Konfiguration und API-Key-Status.

Alle Einstellungen werden in der configuration-Tabelle (Key-Value-Store) gespeichert.
"""
import logging
from datetime import datetime, date as date_type
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, text

from backend.database import get_db
from backend.config import settings
from backend.schemas import ConfigOut, ConfigUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

# Alle bekannten Konfig-Schlüssel mit ihren Datentypen
_CONFIG_KEYS = {
    "weight_fundamental": int,
    "weight_technical":   int,
    "weight_sentiment":   int,
    "zone1_min_score":    int,
    "zone2_min_score":    int,
    "zone3_min_score":    int,
    "alert_delta_1d":     float,
    "exit_score_drop":    float,
    "exit_ko_distance":   float,
    "exit_expiry_weeks":  int,
    "exit_bull_ratio":    float,
    "scan_hour_utc":      int,
    "scan_minute_utc":    int,
    "zone4_daily_count":  int,
    "scan_rotation_idx":  int,
}


def _read_all(db: Session) -> dict:
    rows = db.execute(text("SELECT key, value FROM configuration")).fetchall()
    return {r[0]: r[1] for r in rows}


def _write(key: str, value, db: Session) -> None:
    db.execute(
        text(
            "INSERT INTO configuration(key, value, updated_at) VALUES(:k,:v,datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=:v, updated_at=datetime('now')"
        ),
        {"k": key, "v": str(value)},
    )


# ── Endpunkte ────────────────────────────────────────────────────────────────

@router.get("", response_model=ConfigOut, summary="Konfiguration lesen")
def get_config(db: Session = Depends(get_db)):
    """Alle App-Einstellungen als strukturiertes Objekt."""
    cfg = _read_all(db)

    def _get(key: str, default):
        raw = cfg.get(key)
        if raw is None:
            return default
        cast = _CONFIG_KEYS.get(key, str)
        try:
            return cast(raw)
        except (ValueError, TypeError):
            return default

    return ConfigOut(
        weight_fundamental  = _get("weight_fundamental", 40),
        weight_technical    = _get("weight_technical",   35),
        weight_sentiment    = _get("weight_sentiment",   25),
        zone1_min_score     = _get("zone1_min_score",    76),
        zone2_min_score     = _get("zone2_min_score",    61),
        zone3_min_score     = _get("zone3_min_score",    41),
        alert_delta_1d      = _get("alert_delta_1d",     15.0),
        exit_score_drop     = _get("exit_score_drop",    15.0),
        exit_ko_distance    = _get("exit_ko_distance",    8.0),
        exit_expiry_weeks   = _get("exit_expiry_weeks",   3),
        exit_bull_ratio     = _get("exit_bull_ratio",    35.0),
    )


@router.put("", response_model=ConfigOut, summary="Konfiguration aktualisieren")
def update_config(payload: ConfigUpdate, db: Session = Depends(get_db)):
    """
    Einzelne oder mehrere Einstellungen aktualisieren.
    Nur übergebene Felder werden geändert (PATCH-Semantik).

    Validierungen:
    - Scoring-Gewichtungen müssen zusammen 100 ergeben (wenn alle drei angegeben)
    - Zonen-Grenzen: zone1 > zone2 > zone3
    """
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "Keine Änderungen übergeben")

    # Gewichtungs-Validierung (nur wenn alle drei gesetzt)
    weight_keys = {"weight_fundamental", "weight_technical", "weight_sentiment"}
    if weight_keys.issubset(updates):
        total = updates["weight_fundamental"] + updates["weight_technical"] + updates["weight_sentiment"]
        if total != 100:
            raise HTTPException(400, f"Gewichtungen müssen zusammen 100 ergeben (aktuell: {total})")

    # Zonen-Reihenfolge prüfen (wenn alle drei angegeben)
    if all(k in updates for k in ("zone1_min_score", "zone2_min_score", "zone3_min_score")):
        if not (updates["zone1_min_score"] > updates["zone2_min_score"] > updates["zone3_min_score"]):
            raise HTTPException(400, "Zonen-Reihenfolge muss zone1 > zone2 > zone3 sein")

    for key, value in updates.items():
        if key in _CONFIG_KEYS:
            _write(key, value, db)

    db.commit()
    return get_config(db)


@router.get("/status", summary="API-Key-Status")
def get_api_status(db: Session = Depends(get_db)):
    """
    Zeigt den Status aller API-Dienste: ob der Key gesetzt ist,
    und für Alpha Vantage die verbleibende Tagesquota.
    """
    from sqlalchemy import text as sql_text

    def _key_status(key: str) -> dict:
        return {"status": "ok" if key else "missing"}

    # Alpha Vantage Quota aus Cache abschätzen
    av_quota = _estimate_av_quota(db)

    return {
        "yfinance":      {"status": "ok",   "note": "kein Key erforderlich"},
        "stocktwits":    {"status": "ok",   "note": "kein Key erforderlich"},
        "apewisdom":     {"status": "ok",   "note": "kein Key erforderlich"},
        "finnhub":       {
            "status": "ok" if settings.finnhub_api_key else "missing",
            "note":   "" if settings.finnhub_api_key else "FINNHUB_API_KEY nicht gesetzt – Sentiment eingeschränkt",
        },
        "alpha_vantage": {
            "status":          "ok" if settings.alpha_vantage_api_key else "missing",
            "key_2_active":    bool(settings.alpha_vantage_api_key_2),
            "remaining_today": av_quota,
        },
        "marketaux":     {
            "status": "ok" if settings.marketaux_api_key else "missing",
            "note":   "" if settings.marketaux_api_key else "MARKETAUX_API_KEY nicht gesetzt",
        },
        "simfin":        {
            "status": "ok" if settings.simfin_api_key else "missing",
            "note":   "" if settings.simfin_api_key else "SIMFIN_API_KEY nicht gesetzt – yfinance als Fallback",
        },
        "telegram":      {
            "status": "ok" if (settings.telegram_bot_token and settings.telegram_chat_id) else "missing",
            "note":   "" if (settings.telegram_bot_token and settings.telegram_chat_id) else "TELEGRAM_BOT_TOKEN oder TELEGRAM_CHAT_ID fehlt",
        },
    }


def _estimate_av_quota(db: Session) -> int:
    """Verbleibende AV-Quota heute aus api_cache-Einträgen schätzen."""
    today = date_type.today().isoformat()
    used = db.execute(
        text(
            "SELECT COUNT(*) FROM api_cache WHERE source LIKE 'alphavantage%' "
            "AND cached_at LIKE :today"
        ),
        {"today": f"{today}%"},
    ).scalar_one() or 0
    total_quota = settings.alpha_vantage_calls_per_day * (2 if settings.alpha_vantage_api_key_2 else 1)
    return max(0, total_quota - used)


@router.get("/scan-schedule", summary="Scan-Zeitplan")
def get_scan_schedule(db: Session = Depends(get_db)):
    """Nächste geplante Scan-Zeiten und Zone-4-Rotation."""
    from backend.api.scan import scan_state

    cfg_rows = db.execute(text("SELECT key, value FROM configuration WHERE key IN ('scan_hour_utc','scan_minute_utc','zone4_daily_count','scan_rotation_idx')")).fetchall()
    cfg = {r[0]: r[1] for r in cfg_rows}

    hour   = int(cfg.get("scan_hour_utc",   settings.scan_hour_utc))
    minute = int(cfg.get("scan_minute_utc", settings.scan_minute_utc))
    batch  = int(cfg.get("zone4_daily_count", 200))

    from backend.models import Stock, DailyScore
    from sqlalchemy import select as sa_select, func

    # Aktive Zone-4-Ticker zählen
    latest_date = db.execute(
        sa_select(DailyScore.score_date).order_by(DailyScore.score_date.desc()).limit(1)
    ).scalar_one_or_none()
    zone4_count = 0
    if latest_date:
        zone4_count = db.execute(
            sa_select(func.count(DailyScore.id))
            .where(DailyScore.score_date == latest_date, DailyScore.zone == 4)
        ).scalar_one() or 0

    cycle_days = max(1, round(zone4_count / batch, 1)) if batch else None

    return {
        "scan_time_utc":       f"{hour:02d}:{minute:02d}",
        "zone4_batch_size":    batch,
        "zone4_active_tickers": zone4_count,
        "zone4_cycle_days":    cycle_days,
        "last_scan_completed": scan_state["last_completed"],
        "last_duration_sec":   scan_state["last_duration_sec"],
        "scan_running":        scan_state["running"],
    }
