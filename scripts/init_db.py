"""Erstellt alle Datenbanktabellen und befüllt die Startkonfiguration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import init_db, SessionLocal
from backend.universe.loader import load_static_universe

if __name__ == "__main__":
    print("Initialisiere Datenbank …")
    init_db()
    print("Lade statisches Ticker-Universum …")
    db = SessionLocal()
    try:
        n = load_static_universe(db)
        print(f"{n} Ticker geladen.")
    finally:
        db.close()
    print("Fertig. Datenbank bereit.")
