import json
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from backend.models import ApiCache


_memory: dict[str, tuple[any, float]] = {}


def get(cache_key: str, db: Session) -> Optional[dict]:
    """Zuerst In-Memory, dann SQLite-Cache prüfen."""
    if cache_key in _memory:
        data, expires = _memory[cache_key]
        if time.time() < expires:
            return data
        del _memory[cache_key]

    row = db.get(ApiCache, cache_key)
    if row and row.expires_at > datetime.utcnow().isoformat():
        data = json.loads(row.data_json)
        _memory[cache_key] = (data, time.time() + 60)
        return data
    return None


def set(cache_key: str, data: dict, ttl_seconds: int, source: str, db: Session) -> None:
    """In-Memory + SQLite speichern."""
    expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
    _memory[cache_key] = (data, time.time() + ttl_seconds)

    row = db.get(ApiCache, cache_key)
    if row:
        row.data_json = json.dumps(data)
        row.expires_at = expires_at
        row.cached_at = datetime.utcnow().isoformat()
    else:
        db.add(ApiCache(
            cache_key=cache_key,
            data_json=json.dumps(data),
            source=source,
            ttl_seconds=ttl_seconds,
            cached_at=datetime.utcnow().isoformat(),
            expires_at=expires_at,
        ))
    db.commit()


def cleanup_expired(db: Session) -> int:
    """Abgelaufene Cache-Einträge löschen, Anzahl zurückgeben."""
    now = datetime.utcnow().isoformat()
    deleted = db.query(ApiCache).filter(ApiCache.expires_at < now).delete()
    db.commit()
    return deleted
