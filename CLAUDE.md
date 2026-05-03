# AIDepot – Projektdokumentation für Claude

Dieses Dokument wird in jeder Claude-Code-Session automatisch geladen und gibt Kontext über das Projekt.

## Was ist AIDepot?

Persönliche, lokal betriebene Single-User-Anwendung zur Analyse von US-Aktien und Optionsscheinen.  
Ziel: Aktien im Pre-Breakout-Aufbau (VCP-Muster) frühzeitig erkennen und Optionsschein-Positionen bis zum Exit begleiten.

## Tech-Stack

| Schicht | Technologie |
|---------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, APScheduler |
| Datenbank | SQLite (`./data/aidepot.db`) |
| Frontend | React 18, TypeScript, Vite, TanStack Query, Tailwind CSS, Recharts |
| Benachrichtigungen | Telegram Bot (kostenlos) |
| Daten | yfinance, Finnhub, Alpha Vantage, StockTwits, ApeWisdom, Marketaux, SimFin |

## Verzeichnisstruktur

```
AIDepot/
├── CLAUDE.md              ← Diese Datei (immer geladen)
├── docs/                  ← Detaillierte Dokumentation
│   ├── ARCHITECTURE.md
│   ├── SCORING.md
│   ├── API.md
│   ├── RATE_LIMITS.md
│   └── SETUP.md
├── TODO.md                ← Offene Aufgaben & Fortschritt
├── .env.example           ← API-Keys Template
├── backend/
│   ├── main.py            ← FastAPI-Einstiegspunkt (Port 8000)
│   ├── config.py          ← Pydantic BaseSettings (.env)
│   ├── database.py        ← SQLite-Engine + Session
│   ├── models.py          ← SQLAlchemy ORM-Modelle
│   ├── schemas.py         ← Pydantic Request/Response-Typen
│   ├── api/               ← REST-Endpunkte
│   ├── fetchers/          ← Datenquellen-Adapter
│   ├── scoring/           ← 3-Ebenen-Scoring-Engine
│   ├── scheduler/         ← APScheduler (06:00 UTC täglich)
│   ├── notifications/     ← Telegram-Bot
│   ├── cache/             ← TTL-Cache (In-Memory + SQLite)
│   ├── universe/          ← ~850 Ticker-Universum
│   └── backtesting/       ← Historische Signal-Simulation
├── frontend/              ← Vite + React + TypeScript (Port 5173)
└── scripts/
    ├── init_db.py         ← DB initialisieren (einmalig ausführen)
    ├── backfill_scores.py ← 30-Tage-Historie generieren
    └── test_fetchers.py   ← API-Verbindungen testen
```

## Starten (Entwicklung)

```bash
# Backend
cd AIDepot
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env  # API-Keys eintragen
python scripts/init_db.py
uvicorn backend.main:app --reload --port 8000

# Frontend (neues Terminal)
cd frontend
npm install
npm run dev
```

Swagger-UI: http://localhost:8000/docs  
App: http://localhost:5173

## Zwei Workflows

**Workflow A – Scanner (06:00 UTC täglich)**
- Scannt ~850 US-Aktien (S&P 500 + NASDAQ 100 + Russell 2000 + persönliche Liste + Trending)
- 3-Ebenen-Scoring: Fundamental (40%) + Technisch (35%) + Sentiment (25%)
- 4-Zonen-Watchlist: Zone 1 (≥76) → Zone 2 (≥61) → Zone 3 (≥41) → Zone 4 (<41)
- Bei Zone 1: automatische Optionsschein-Empfehlung

**Workflow B – Bestandsbeobachtung (täglich nach Scan)**
- Täglich neu bewertet: Score-Entwicklung, KO-Abstand, Restlaufzeit, Sentiment
- 4 Exit-Signaltypen mit Telegram-Benachrichtigung
- P&L-Berechnung und Trade-Archivierung

## Wichtige Konventionen

- **Git-Branch:** `claude/stock-options-analyzer-umA6s`
- **Sprache:** Kommentare und Commits auf Deutsch; Code-Identifiers auf Englisch
- **Keine Auth:** Single-User, localhost only
- **Kein Cloud-Zwang:** Alles lokal, SQLite, kein Docker erforderlich
- **Rate-Limits:** Alpha Vantage (25/Tag) + Finnhub (60/Min) beachten → `backend/cache/store.py`

## Datenbank

```bash
# Schema neu initialisieren
python scripts/init_db.py

# Direkt inspizieren
sqlite3 data/aidepot.db ".tables"
sqlite3 data/aidepot.db "SELECT * FROM configuration;"
```

## API-Keys (kostenlos)

| Dienst | Anmeldung |
|--------|-----------|
| Finnhub | finnhub.io → Free Tier |
| Alpha Vantage | alphavantage.co → Free Key |
| Marketaux | marketaux.com → Free Tier |
| SimFin | simfin.com → Personal Free |
| StockTwits | Kein Key nötig |
| ApeWisdom | Kein Key nötig |
| yfinance | Kein Key nötig |
| Telegram Bot | @BotFather → /newbot |
