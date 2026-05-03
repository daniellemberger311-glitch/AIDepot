# Setup-Anleitung

## Voraussetzungen

- Python 3.11 oder höher
- Node.js 20 oder höher
- Git

## Schritt 1: Repository klonen & Branch wechseln

```bash
git clone <repo-url> AIDepot
cd AIDepot
git checkout claude/stock-options-analyzer-umA6s
```

## Schritt 2: Backend einrichten

```bash
# Virtuelle Umgebung anlegen
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r backend/requirements.txt

# Umgebungsvariablen konfigurieren
cp .env.example .env
# .env öffnen und API-Keys eintragen (siehe Abschnitt "API-Keys")

# Datenbank initialisieren (einmalig)
mkdir -p data
python scripts/init_db.py
```

## Schritt 3: Frontend einrichten

```bash
cd frontend
npm install
cd ..
```

## Schritt 4: Starten

**Terminal 1 – Backend:**
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 – Frontend:**
```bash
cd frontend
npm run dev
```

**App öffnen:** http://localhost:5173  
**API-Docs:** http://localhost:8000/docs

## API-Keys Status

| Dienst | Variable | Limit | Status |
|--------|----------|-------|--------|
| Alpha Vantage (Key 1) | `ALPHA_VANTAGE_API_KEY` | 25 Calls/Tag, 5/Min | ✅ konfiguriert |
| Alpha Vantage (Key 2) | `ALPHA_VANTAGE_API_KEY_2` | +25 Calls/Tag (Rotation) | ✅ konfiguriert |
| Finnhub | `FINNHUB_API_KEY` | 60 Calls/Min | ✅ konfiguriert |
| Marketaux | `MARKETAUX_API_KEY` | 100 News/Tag | ✅ konfiguriert |
| SimFin | `SIMFIN_API_KEY` | unbegrenzt (privat) | ✅ konfiguriert |
| Telegram Bot | `TELEGRAM_BOT_TOKEN` | kostenlos | ⏳ noch nicht eingerichtet |
| Telegram Chat-ID | `TELEGRAM_CHAT_ID` | – | ⏳ noch nicht eingerichtet |

Alle Keys sind in `.env` hinterlegt (`.gitignore`d – niemals einchecken).

## API-Keys beschaffen

### Finnhub (60 Calls/Min)
1. https://finnhub.io → "Get free API key"
2. Key in `.env`: `FINNHUB_API_KEY=...`

### Alpha Vantage (25 Calls/Tag)
1. https://www.alphavantage.co/support/#api-key
2. Key in `.env`: `ALPHA_VANTAGE_API_KEY=...`

### Marketaux (100 News/Tag)
1. https://www.marketaux.com → Free Plan
2. Key in `.env`: `MARKETAUX_API_KEY=...`

### SimFin (unbegrenzt, privat)
1. https://simfin.com → Free Account
2. Key in `.env`: `SIMFIN_API_KEY=...`

### Telegram-Bot

1. Telegram öffnen → @BotFather suchen
2. `/newbot` senden → Name wählen → Token erhalten
3. Token in `.env`: `TELEGRAM_BOT_TOKEN=...`
4. Bot anschreiben (einmal Nachricht senden)
5. Chat-ID herausfinden:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   → `"chat": {"id": 123456789}` → das ist die Chat-ID
6. In `.env`: `TELEGRAM_CHAT_ID=123456789`

## Erster Scan (manuell)

Nach dem Setup direkt einen ersten Scan auslösen:

```bash
# Option A: Via API
curl -X POST http://localhost:8000/api/scan/trigger

# Option B: Python direkt
python -c "
import asyncio
from backend.scheduler.jobs import run_daily_scan
asyncio.run(run_daily_scan())
"
```

## Verbindungen testen

```bash
python scripts/test_fetchers.py AAPL
```

Ausgabe sollte zeigen:
- yfinance: ✅ OHLCV-Daten geladen
- Finnhub: ✅ Sentiment erhalten (wenn Key gesetzt)
- StockTwits: ✅ Bullish-Ratio erhalten
- ApeWisdom: ✅ Reddit-Mentions erhalten

## Täglichen Scan automatisieren

Der APScheduler läuft automatisch wenn `uvicorn` läuft.  
Um sicherzustellen, dass der Scan auch bei Systemneustart läuft:

**Linux (systemd-Service, optional):**
```ini
# /etc/systemd/system/aidepot.service
[Unit]
Description=AIDepot Backend
After=network.target

[Service]
User=<dein-user>
WorkingDirectory=/path/to/AIDepot
ExecStart=/path/to/AIDepot/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable aidepot
systemctl start aidepot
```

## Häufige Probleme

**Problem:** `ModuleNotFoundError: No module named 'backend'`  
**Lösung:** Aus dem `AIDepot`-Stammverzeichnis starten, nicht aus `backend/`

**Problem:** `sqlite3.OperationalError: no such table`  
**Lösung:** `python scripts/init_db.py` erneut ausführen

**Problem:** Finnhub gibt 429 zurück  
**Lösung:** Rate-Limit erreicht; `backend/cache/store.py` cached Ergebnisse – nach 1 Minute Pause wird automatisch weitergescannt

**Problem:** yfinance gibt leere DataFrames zurück  
**Lösung:** Ticker-Symbol prüfen (US-Format: "AAPL", nicht "AAPL.US"); bei Wochenenden gibt es keine Kurse
