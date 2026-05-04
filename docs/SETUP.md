# Setup-Anleitung

Zuletzt aktualisiert: 2026-05-04

---

## Voraussetzungen

| Software | Mindestversion |
|----------|---------------|
| Python | 3.11 |
| Node.js | 18 |
| Git | beliebig |

---

## Schritt 1: Repository klonen

```bash
git clone https://github.com/daniellemberger311-glitch/aidepot.git
cd AIDepot
```

---

## Schritt 2: Backend einrichten

```bash
# Virtuelle Umgebung anlegen
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r backend/requirements.txt

# Umgebungsvariablen konfigurieren
cp .env.example .env
# .env öffnen und API-Keys eintragen (siehe Abschnitt "API-Keys beschaffen")

# Datenbank initialisieren (einmalig)
python scripts/init_db.py

# Alembic-Stand markieren (einmalig nach init_db)
alembic stamp head
```

---

## Schritt 3: Frontend bauen

```bash
cd frontend
npm install
npm run build   # Erstellt frontend/dist/ (wird von FastAPI serviert)
cd ..
```

---

## Schritt 4: Starten

### Entwicklung (Live-Reload, zwei Prozesse)

**Terminal 1 – Backend:**
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 – Frontend:**
```bash
cd frontend && npm run dev
```

- Frontend: **http://localhost:5173**
- Backend / Swagger: http://localhost:8000/docs

### Produktion (ein Prozess, Heimnetz-tauglich)

Das gebaute `frontend/dist/` wird von FastAPI direkt ausgeliefert – kein separater Node.js-Prozess:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- Erreichbar lokal: **http://localhost:8000**
- Erreichbar aus Heimnetz (Android, Windows, etc.): **http://\<Linux-IP\>:8000**

Linux-IP herausfinden:
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

---

## Schritt 5: Automatischer Start (Linux/systemd)

```bash
# aidepot.service editieren: WorkingDirectory und User auf eigene Pfade anpassen
nano aidepot.service

# Service installieren
sudo cp aidepot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aidepot

# Status prüfen
sudo systemctl status aidepot --no-pager
```

### Automatisches Backup

```bash
sudo cp aidepot-backup.service aidepot-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aidepot-backup.timer

# Timer-Status prüfen
sudo systemctl list-timers aidepot-backup.timer
```

---

## API-Keys Status

| Dienst | Variable | Limit | Status |
|--------|----------|-------|--------|
| Alpha Vantage (Key 1) | `ALPHA_VANTAGE_API_KEY` | 25 Calls/Tag | ✅ konfiguriert |
| Alpha Vantage (Key 2) | `ALPHA_VANTAGE_API_KEY_2` | +25 Calls/Tag (Rotation) | ✅ konfiguriert |
| Finnhub | `FINNHUB_API_KEY` | 60 Calls/Min | ✅ konfiguriert |
| Marketaux | `MARKETAUX_API_KEY` | 100 News/Tag | ✅ konfiguriert |
| SimFin | `SIMFIN_API_KEY` | unbegrenzt (privat) | ✅ konfiguriert |
| Telegram Bot | `TELEGRAM_BOT_TOKEN` | kostenlos | ⏳ noch nicht eingerichtet |
| Telegram Chat-ID | `TELEGRAM_CHAT_ID` | – | ⏳ noch nicht eingerichtet |

Keys sind in `.env` hinterlegt (`.gitignore`d – niemals einchecken).

---

## API-Keys beschaffen

### Finnhub (60 Calls/Min, kostenlos)
1. https://finnhub.io → „Get free API key"
2. Key in `.env`: `FINNHUB_API_KEY=...`

### Alpha Vantage (25 Calls/Tag pro Key, kostenlos)
1. https://www.alphavantage.co/support/#api-key
2. Key 1: `ALPHA_VANTAGE_API_KEY=...`
3. Zweiten kostenlosen Account anlegen → Key 2: `ALPHA_VANTAGE_API_KEY_2=...`

### Marketaux (100 News/Tag, kostenlos)
1. https://www.marketaux.com → Free Plan
2. Key in `.env`: `MARKETAUX_API_KEY=...`

### SimFin (unbegrenzt, kostenlos)
1. https://simfin.com → Free Account
2. Key in `.env`: `SIMFIN_API_KEY=...`

### Telegram-Bot (optional)
1. Telegram öffnen → `@BotFather` suchen → `/newbot` → Name wählen → Token erhalten
2. Token in `.env`: `TELEGRAM_BOT_TOKEN=...`
3. Bot einmal selbst anschreiben (beliebige Nachricht senden)
4. Chat-ID herausfinden:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   → `"chat": {"id": 123456789}` → das ist die Chat-ID
5. In `.env`: `TELEGRAM_CHAT_ID=123456789`

---

## Erster Scan

Nach dem Setup direkt einen ersten Scan auslösen – entweder über den **„Scan starten"**-Button auf dem Dashboard oder per API:

```bash
curl -X POST http://localhost:8000/api/scan/trigger
```

Fortschritt unter `GET /api/scan/status` oder live auf dem Dashboard.  
Dauer: ca. 15–30 Minuten für ~850 Aktien.

---

## API-Verbindungen testen

```bash
python scripts/test_fetchers.py AAPL
```

Erwartete Ausgabe:
- yfinance: ✅ OHLCV-Daten geladen
- Finnhub: ✅ Sentiment erhalten
- StockTwits: ✅ Bullish-Ratio erhalten
- ApeWisdom: ✅ Reddit-Mentions erhalten

---

## Updates einspielen

```bash
bash update.sh
```

Das Script führt automatisch aus:
1. `git pull origin main`
2. `pip install -r backend/requirements.txt`
3. `pytest tests/ -q --tb=short` → bricht bei Testfehlern ab
4. `alembic upgrade head` → DB-Migrationen
5. `npm install && npm run build`
6. `sudo systemctl restart aidepot`

---

## Datenbank-Migrationen

Neue Migration anlegen (bei Änderungen in `backend/models.py`):

```bash
source .venv/bin/activate
alembic revision --autogenerate -m "Kurze Beschreibung"
alembic upgrade head
```

Bestehende Datenbank auf den aktuellen Stand bringen (nach erstem `init_db.py`):

```bash
alembic stamp head
```

---

## Häufige Probleme

**Problem:** `ModuleNotFoundError: No module named 'backend'`  
**Lösung:** Aus dem `AIDepot`-Stammverzeichnis starten, nicht aus `backend/`

**Problem:** `sqlite3.OperationalError: no such table`  
**Lösung:** `python scripts/init_db.py` ausführen, danach `alembic stamp head`

**Problem:** Finnhub gibt 429 zurück  
**Lösung:** Rate-Limit erreicht; der Cache verhindert Wiederholungen – nach Ablauf der Cache-TTL wird automatisch weitergemacht

**Problem:** yfinance gibt leere DataFrames zurück  
**Lösung:** Ticker-Symbol prüfen (US-Format: `AAPL`, nicht `AAPL.US`); an Wochenenden keine Kurse

**Problem:** Frontend zeigt „Netzwerkfehler"  
**Lösung:** Backend läuft? `sudo systemctl status aidepot` prüfen; im Entwicklungsmodus Backend auf Port 8000 starten

**Problem:** `alembic: command not found`  
**Lösung:** Virtuelle Umgebung aktivieren: `source .venv/bin/activate`
