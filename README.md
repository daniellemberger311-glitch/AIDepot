# AIDepot

Persönliche, lokal betriebene App zur Analyse von US-Aktien und Optionsscheinen.  
Erkennt Aktien im Pre-Breakout-Aufbau (VCP-Muster) frühzeitig und begleitet Optionsschein-Positionen täglich bis zum Exit.

**Stack:** Python 3.11 · FastAPI · SQLite · React 18 · TypeScript · Vite · Tailwind CSS

---

## Funktionsübersicht

- **Scanner** – täglich ~850 US-Aktien mit 3-Ebenen-Scoring (Fundamental · Technisch · Sentiment)
- **4-Zonen-Watchlist** – Zone 1 (≥76) bis Zone 4 (<41), mit automatischer Optionsschein-Empfehlung für Zone 1
- **Portfolio-Tracking** – offene Positionen mit KO-Abstand, Restlaufzeit, Kurs mit Währung und Exit-Signalen
- **Backtesting** – historische Score-Simulation für beliebige Ticker und Zeiträume
- **Log-Viewer** – In-App-Fehlerübersicht direkt in der Konfigurationsseite
- **Telegram-Benachrichtigungen** – Zonenwechsel, Δ-Spikes, Exit-Signale (optional)

---

## Voraussetzungen

| Software | Mindestversion |
|----------|---------------|
| Python | 3.11 |
| Node.js | 18 |
| Git | beliebig |

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/daniellemberger311-glitch/aidepot.git
cd aidepot
```

### 2. Python-Umgebung einrichten

```bash
python -m venv .venv

# Mac/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r backend/requirements.txt
```

### 3. API-Keys eintragen

```bash
cp .env.example .env
```

Datei `.env` öffnen und die Keys eintragen:

| Variable | Dienst | Limit (Free) | Registrierung |
|----------|--------|-------------|---------------|
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage | 25 Req/Tag | https://alphavantage.co |
| `ALPHA_VANTAGE_API_KEY_2` | Alpha Vantage (2. Key) | +25 Req/Tag | zweiter kostenloser Account |
| `FINNHUB_API_KEY` | Finnhub | 60 Req/Min | https://finnhub.io |
| `MARKETAUX_API_KEY` | Marketaux | 100 News/Tag | https://marketaux.com |
| `SIMFIN_API_KEY` | SimFin | unbegrenzt | https://simfin.com |
| `TELEGRAM_BOT_TOKEN` | Telegram | kostenlos | optional – siehe unten |
| `TELEGRAM_CHAT_ID` | Telegram | – | optional – siehe unten |

> Alle 5 Daten-APIs sind kostenlos. Ohne Telegram funktioniert die App vollständig.

### 4. Datenbank initialisieren

```bash
python scripts/init_db.py
```

Erstellt `data/aidepot.db` mit allen Tabellen und lädt das Ticker-Universum (~850 Aktien).

### 5. API-Verbindungen testen (optional)

```bash
python scripts/test_fetchers.py
```

### 6. Frontend bauen

```bash
cd frontend
npm install
npm run build
cd ..
```

---

## Starten

### Entwicklungsmodus (zwei Terminals)

**Terminal 1 – Backend:**
```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 – Frontend:**
```bash
cd frontend
npm run dev
```

App aufrufen: **http://localhost:5173**  
Swagger-API-Doku: http://localhost:8000/docs

### Produktionsmodus (ein Prozess)

Das gebaute Frontend (`frontend/dist/`) wird direkt von FastAPI serviert – kein Node.js nötig:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

App aufrufen: **http://localhost:8000** (oder `http://<IP>:8000` aus dem Heimnetz)

---

## Automatischer Start (Linux/systemd)

Damit die App beim Booten automatisch startet und nach Abstürzen neu startet:

```bash
# Pfad in aidepot.service anpassen (WorkingDirectory + User)
sudo cp aidepot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aidepot

# Status prüfen
sudo systemctl status aidepot
```

Erreichbar aus dem Heimnetz (Android, Windows, etc.) über `http://<Linux-PC-IP>:8000`.  
Die IP des Linux-PCs herausfinden: `ip addr show | grep "inet "`

---

## Updates einspielen

```bash
bash update.sh
```

Das Script führt automatisch aus: `git pull` → `pip install` → Tests → `alembic upgrade` → `npm build` → `systemctl restart`.  
Bricht bei fehlschlagenden Tests ab, bevor die Datenbank angefasst wird.

---

## Automatisches Backup

Die Datenbank wird täglich um 03:00 UTC gesichert (7 rotierende Kopien in `data/backups/`):

```bash
sudo cp aidepot-backup.service aidepot-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aidepot-backup.timer
```

Backup manuell auslösen: `bash scripts/backup.sh`

---

## Erster Scan

Nach dem Start auf dem Dashboard oben rechts **„Scan starten"** klicken.  
Dauer: ca. 5–15 Minuten (abhängig von den Rate-Limits der Free-APIs).

Der automatische Tagesscan läuft täglich um **06:00 UTC**.

---

## Telegram einrichten (optional)

1. In Telegram `@BotFather` anschreiben → `/newbot` → Token kopieren → `.env`: `TELEGRAM_BOT_TOKEN=...`
2. Den Bot einmal selbst anschreiben (beliebige Nachricht)
3. URL aufrufen: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. `"chat": {"id": ...}` aus der Antwort kopieren → `.env`: `TELEGRAM_CHAT_ID=...`

---

## Tests ausführen

```bash
python -m pytest tests/ -q --tb=short
```

133 Unit-Tests für die Scoring-Engine (L1 Fundamental, L2 Technisch, L3 Sentiment, Zonengrenzen).

---

## Projektstruktur

```
AIDepot/
├── backend/
│   ├── main.py              # FastAPI-App (Port 8000, serviert auch frontend/dist/)
│   ├── api/                 # 40+ REST-Endpunkte
│   ├── scoring/             # 3-Ebenen-Scoring-Engine
│   ├── fetchers/            # 8 Datenquellen-Adapter
│   ├── backtesting/         # Historische Simulation
│   ├── scheduler/           # APScheduler-Jobs
│   └── notifications/       # Telegram-Bot
├── frontend/
│   └── src/
│       ├── pages/           # 7 Seiten (Dashboard, Watchlist, …)
│       ├── components/      # Wiederverwendbare UI-Komponenten
│       └── api/client.ts    # Axios-API-Client
├── migrations/              # Alembic-Migrationen (DB-Schema-Änderungen)
├── tests/                   # pytest Unit-Tests (133 Tests)
├── scripts/
│   ├── init_db.py           # DB einmalig initialisieren
│   ├── backup.sh            # Manuelles Backup
│   └── test_fetchers.py     # API-Keys testen
├── update.sh                # Einzeiler-Deployment
├── aidepot.service          # systemd-Service-Unit
├── aidepot-backup.timer     # systemd-Backup-Timer
├── data/                    # SQLite-Datenbank (wird angelegt)
├── .env.example             # API-Keys Vorlage
└── docs/                    # Technische Dokumentation
```

---

## Seiten

| URL | Beschreibung |
|-----|-------------|
| `/` | Dashboard – KPIs, Top-Signale, Exit-Warnungen, Scan-Steuerung |
| `/watchlist` | 4-Zonen-Tabelle aller Aktien mit Kurs und Währung, sortierbar |
| `/signal/:ticker` | Score-Aufschlüsselung L1/L2/L3, 30-Tage-Chart, OS-Empfehlung |
| `/portfolio` | Offene Positionen, Kauf/Verkauf, Exit-Signale |
| `/history` | Trade-Archiv, P&L-Statistik, Signalqualität |
| `/backtest` | Historische Score-Simulation mit Kurs-/Score-Chart |
| `/config` | Universum, API-Status, Gewichtungen, Scan-Einstellungen, Logs |
