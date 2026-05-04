#!/usr/bin/env bash
# AIDepot – tägliches Datenbank-Backup
# Behält die letzten 7 Kopien, ältere werden automatisch gelöscht.
#
# Einrichtung: Pfad unten anpassen, dann:
#   chmod +x scripts/backup.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DB_FILE="$REPO_DIR/data/aidepot.db"
BACKUP_DIR="$REPO_DIR/data/backups"
KEEP=7

mkdir -p "$BACKUP_DIR"

if [[ ! -f "$DB_FILE" ]]; then
  echo "Datenbank nicht gefunden: $DB_FILE" >&2
  exit 1
fi

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
DEST="$BACKUP_DIR/aidepot_$TIMESTAMP.db"

# SQLite-Safe-Kopie (kein korruptes Backup bei laufendem Dienst)
sqlite3 "$DB_FILE" ".backup '$DEST'"

echo "Backup erstellt: $DEST"

# Alte Backups löschen (nur die letzten $KEEP behalten)
ls -t "$BACKUP_DIR"/aidepot_*.db 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm --
echo "Backups behalten: $(ls "$BACKUP_DIR"/aidepot_*.db | wc -l) / $KEEP"
