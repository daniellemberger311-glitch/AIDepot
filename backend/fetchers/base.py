import time
import functools
import logging
from typing import Optional
from sqlalchemy.orm import Session
from backend.cache import store as cache_store

logger = logging.getLogger(__name__)


def with_retry(max_attempts: int = 3, base_delay: float = 1.5):
    """Dekorator: wiederholt bei Netzwerkfehlern mit exponentiellem Backoff."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_attempts:
                        logger.error("Fetcher %s fehlgeschlagen nach %d Versuchen: %s", fn.__name__, max_attempts, exc)
                        raise
                    wait = base_delay * (2 ** (attempt - 1))
                    logger.warning("Versuch %d/%d fehlgeschlagen (%s) – warte %.1fs", attempt, max_attempts, exc, wait)
                    time.sleep(wait)
        return wrapper
    return decorator


class BaseFetcher:
    """Abstrakte Basisklasse für alle Datenquellen-Adapter.

    Bietet: Cache-Lookup/-Speicherung, Retry, Quota-Tracking.
    """

    SOURCE_NAME: str = "base"
    DEFAULT_TTL: int = 3600  # 1 Stunde Standard

    def __init__(self, db: Session):
        self.db = db

    def _cache_get(self, key: str) -> Optional[dict]:
        return cache_store.get(key, self.db)

    def _cache_set(self, key: str, data: dict, ttl: int) -> None:
        cache_store.set(key, data, ttl, self.SOURCE_NAME, self.db)

    def _make_key(self, data_type: str, ticker: str) -> str:
        return f"{self.SOURCE_NAME}:{data_type}:{ticker}"
