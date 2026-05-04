#!/usr/bin/env bash
# AIDepot – Update-Script
# Zieht den neuesten Stand von GitHub, baut das Frontend neu
# und startet den Dienst neu.
#
# Aufruf: bash update.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo "==> AIDepot Update gestartet"

echo "--- Git: neuesten Stand holen ---"
git pull origin main

echo "--- Python: Pakete aktualisieren ---"
.venv/bin/pip install -q -r backend/requirements.txt

echo "--- Frontend: bauen ---"
cd frontend
npm install --silent
npm run build
cd ..

echo "--- Dienst neu starten ---"
sudo systemctl restart aidepot

echo "--- Status prüfen ---"
sudo systemctl status aidepot --no-pager

echo "==> Update abgeschlossen"
