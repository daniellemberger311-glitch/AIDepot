# AIDepot

Persönliche, lokal betriebene App zur Analyse von US-Aktien und Optionsscheinen.  
Erkennt Aktien im Pre-Breakout-Aufbau (VCP-Muster) frühzeitig und begleitet Optionsschein-Positionen täglich bis zum Exit.

**Stack:** Python 3.11 · FastAPI · SQLite · React 18 · TypeScript · Vite · Tailwind CSS

---

## Funktionsübersicht

- **Scanner** – täglich ~850 US-Aktien mit 3-Ebenen-Scoring (Fundamental · Technisch · Sentiment)
- **4-Zonen-Watchlist** – Zone 1 (≥76) bis Zone 4 (<41), mit automatischer Optionsschein-Empfehlung für Zone 1
- **Portfolio-Tracking** – offene Positionen mit KO-Abstand, Restlaufzeit und Exit-Signalen
- **Backtesting** – historische Score-Simulation für beliebige Ticker und Zeiträume
- **Telegram-Benachrichtigungen** – Zonenwechsel, Δ-Spikes, Exit-Signale (optional)

---

## Voraussetzungen

| Software | Mindestversion | Download |
|----------|---------------|----------|
| Python | 3.11 | https://python.org |
| Node.js | 18 | https://nodejs.org |
| Git | beliebig | https://git-scm.com |

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/daniellemberger311-glitch/aidepot.git
cd aidepot
```

### 2. Python-Umgebung einrichten

```bash
# Virtuelle Umgebung erstellen
python -m venv .venv

# Aktivieren – Mac/Linux:
source .venv/bin/activate
# Aktivieren – Windows:
.venv\Scripts\activate

# Pakete installieren
pip install -r backend/requirements.txt
```

### 3. API-Keys eintragen

```bash
cp .env.example .env
```

Datei `.env` im Texteditor öffnen und die Keys eintragen:

| Variable | Dienst | Limit (Free) | Registrierung |
|----------|--------|-------------|---------------|
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage | 25 Req/Tag | https://alphavantage.co |
| `ALPHA_VANTAGE_API_KEY_2` | Alpha Vantage (2. Key) | +25 Req/Tag | zweiter kostenloser Account |
| `FINNHUB_API_KEY` | Finnhub | 60 Req/Min | https://finnhub.io |
| `MARKETAUX_API_KEY` | Marketaux | 100 News/Tag | https://marketaux.com |
| `SIMFIN_API_KEY` | SimFin | unbegrenzt | https://simfin.com |
| `TELEGRAM_BOT_TOKEN` | Telegram | kostenlos | optional – siehe unten |
| `TELEGRAM_CHAT_ID` | Telegram | – | optional – siehe unten |

> Alle 5 Daten-API-Keys sind kostenlos erhältlich. Ohne Telegram funktioniert die App vollständig – Benachrichtigungen werden dann nur nicht versendet.

### 4. Datenbank initialisieren

```bash
python scripts/init_db.py
```

Erstellt `data/aidepot.db` mit allen Tabellen und lädt das Ticker-Universum (~850 Aktien).

### 5. API-Verbindungen testen (optional)

```bash
python scripts/test_fetchers.py
```

### 6. Frontend-Pakete installieren

```bash
cd frontend
npm install
cd ..
```

---

## Starten

Zwei Terminals öffnen:

**Terminal 1 – Backend**
```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 – Frontend**
```bash
cd frontend
npm run dev
```

App aufrufen: **http://localhost:5173**  
Swagger-API-Doku: http://localhost:8000/docs

---

## Erster Scan

Nach dem Start auf dem Dashboard oben rechts **„Scan starten"** klicken.  
Der Scanner durchläuft eine erste Auswahl an Aktien und befüllt die Watchlist.  
Dauer: ca. 5–15 Minuten (abhängig von Rate-Limits der Free-APIs).

Der automatische Tagesscan läuft täglich um **06:00 UTC**.

---

## Telegram einrichten (optional)

1. In Telegram `@BotFather` anschreiben → `/newbot` → Token kopieren → in `.env` als `TELEGRAM_BOT_TOKEN` eintragen
2. Den Bot einmal selbst anschreiben (beliebige Nachricht)
3. Token-URL aufrufen: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. `"chat": {"id": ...}` aus der Antwort kopieren → in `.env` als `TELEGRAM_CHAT_ID` eintragen

---

## Projektstruktur

```
AIDepot/
├── backend/
│   ├── main.py              # FastAPI-App (Port 8000)
│   ├── api/                 # 40 REST-Endpunkte
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
├── scripts/
│   ├── init_db.py           # DB einmalig initialisieren
│   └── test_fetchers.py     # API-Keys testen
├── data/                    # SQLite-Datenbank (wird angelegt)
├── .env.example             # API-Keys Vorlage
└── docs/                    # Technische Dokumentation
```

---

## Seiten

| URL | Beschreibung |
|-----|-------------|
| `/` | Dashboard – KPIs, Top-Signale, Exit-Warnungen |
| `/watchlist` | 4-Zonen-Tabelle aller Aktien, sortierbar |
| `/signal/:ticker` | Score-Aufschlüsselung, 30-Tage-Chart, OS-Empfehlung |
| `/portfolio` | Offene Positionen, Kauf/Verkauf, Exit-Signale |
| `/history` | Trade-Archiv, P&L-Statistik, Signalqualität |
| `/backtest` | Historische Score-Simulation mit Chart |
| `/config` | Universum, API-Status, Gewichtungen, Scan-Einstellungen |
