"""Erstellt alle Datenbanktabellen und befüllt die Startkonfiguration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import init_db

if __name__ == "__main__":
    print("Initialisiere Datenbank …")
    init_db()
    print("Fertig. Datenbank bereit.")
