"""In-Memory-Log-Handler für die AIDepot-App.

Speichert die letzten MAX_ENTRIES Log-Einträge in einem Ringspeicher.
Wird beim App-Start in main.py an den Root-Logger angehängt.
Die Einträge sind über GET /api/logs abrufbar.
"""
import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock

MAX_ENTRIES = 1000


class _LogEntry:
    __slots__ = ("timestamp", "level", "logger", "message")

    def __init__(self, record: logging.LogRecord) -> None:
        self.timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        self.level     = record.levelname
        self.logger    = record.name
        self.message   = record.getMessage()
        if record.exc_info:
            self.message += "\n" + logging.Formatter().formatException(record.exc_info)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "level":     self.level,
            "logger":    self.logger,
            "message":   self.message,
        }


class MemoryLogHandler(logging.Handler):
    """Logging-Handler der Einträge im RAM puffert (thread-safe)."""

    def __init__(self) -> None:
        super().__init__()
        self._buffer: deque[_LogEntry] = deque(maxlen=MAX_ENTRIES)
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = _LogEntry(record)
            with self._lock:
                self._buffer.append(entry)
        except Exception:
            self.handleError(record)

    def get_entries(
        self,
        level: str | None = None,
        module: str | None = None,
        limit: int = 200,
        since: str | None = None,
    ) -> list[dict]:
        """
        Gefilterte Log-Einträge zurückgeben.
        level:  z.B. "ERROR", "WARNING", "INFO", "DEBUG"
        module: Teilstring des Logger-Namens, z.B. "scoring"
        limit:  max. Anzahl Einträge (neueste zuerst)
        since:  ISO-Timestamp – nur Einträge nach diesem Zeitpunkt
        """
        level_no = logging.getLevelName(level.upper()) if level else None

        with self._lock:
            entries = list(self._buffer)

        # Neueste zuerst
        entries.reverse()

        result = []
        for e in entries:
            if level_no is not None and logging.getLevelName(e.level) < level_no:
                continue
            if module and module.lower() not in e.logger.lower():
                continue
            if since and e.timestamp < since:
                continue
            result.append(e.to_dict())
            if len(result) >= limit:
                break

        return result

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def error_count(self) -> int:
        with self._lock:
            return sum(1 for e in self._buffer if e.level in ("ERROR", "CRITICAL"))

    def warning_count(self) -> int:
        with self._lock:
            return sum(1 for e in self._buffer if e.level == "WARNING")


# Modul-globale Instanz – wird in main.py registriert
memory_handler = MemoryLogHandler()
memory_handler.setLevel(logging.DEBUG)


def setup_logging(log_level: str = "INFO") -> None:
    """
    Root-Logger konfigurieren + MemoryLogHandler anhängen.
    Einmalig beim App-Start aufrufen.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Konsole (INFO und höher)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, MemoryLogHandler)
               for h in root.handlers):
        console = logging.StreamHandler()
        console.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s – %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root.addHandler(console)

    # Memory-Handler (alle Level)
    if memory_handler not in root.handlers:
        root.addHandler(memory_handler)
