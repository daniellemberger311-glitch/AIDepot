import sys
import os

# Sicherstellen, dass das Repo-Root im Python-Pfad liegt,
# damit 'from backend.scoring.xxx import ...' aus tests/ funktioniert.
sys.path.insert(0, os.path.dirname(__file__))
