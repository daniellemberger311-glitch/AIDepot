# AIDepot – Projektdokumentation für Claude

Diese Datei wird in jeder Claude-Code-Session automatisch geladen.

## Was ist AIDepot?

Persönliche, lokal betriebene Single-User-App zur Analyse von US-Aktien und Optionsscheinen.  
Ziel: Aktien im Pre-Breakout-Aufbau (VCP-Muster wie ASTS, SNDK, NVDA) frühzeitig erkennen und Optionsschein-Positionen täglich bis zum Exit begleiten.

## Aktueller Entwicklungsstand

**Phase 1 – Backend-Fundament (~25 % fertig)**

| Modul | Status |
|-------|--------|
| Projektstruktur, .env, .gitignore | ✅ fertig |
| `backend/config.py` | ✅ fertig |
| `backend/database.py` + `models.py` | ✅ fertig |
| `backend/schemas.py` + `main.py` | ✅ fertig |
| `backend/cache/store.py` | ✅ fertig |
| Fetcher: yfinance, StockTwits, ApeWisdom, Finnhub | ✅ fertig |
| Fetcher: Alpha Vantage, Marketaux, SimFin | ⏳ offen |
| Scoring-Engine (3 Ebenen + Orchestrator) | ⏳ offen |
| API-Endpunkte (9 Router) | ⏳ offen |
| Scheduler + Telegram | ⏳ offen |
| Backtesting-Modul | ⏳ offen |
| Frontend (React + Vite) | ⏳ offen |

Detaillierter Fortschritt → `TODO.md`  
Entwicklungs-Roadmap → `docs/ROADMAP.md`

## Tech-Stack

| Schicht | Technologie |
|---------|-------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, APScheduler |
| Datenbank | SQLite (`./data/aidepot.db`) |
| Frontend | React 18, TypeScript, Vite, TanStack Query v5, Tailwind CSS, Recharts |
| Benachrichtigungen | Telegram Bot (kostenlos, python-telegram-bot) |

## Verzeichnisstruktur

```
AIDepot/
├── CLAUDE.md              ← Diese Datei (automatisch geladen)
├── TODO.md                ← Offene Aufgaben & aktueller Fortschritt
├── docs/
│   ├── ROADMAP.md         ← Entwicklungs-Roadmap (Phasen 1–5)
│   ├── ARCHITECTURE.md    ← System-Diagramm, Datenfluss
│   ├── SCORING.md         ← 3-Ebenen-Scoring mit Punktetabellen
│   ├── API.md             ← REST-Endpunkte Referenz
│   ├── RATE_LIMITS.md     ← Strategie für 850 Aktien mit Free-Tier-APIs
│   └── SETUP.md           ← Einrichtungsanleitung
├── .env.example           ← API-Keys Template
├── backend/
│   ├── main.py            ← FastAPI-Einstiegspunkt (Port 8000)
│   ├── config.py          ← Pydantic BaseSettings (.env)
│   ← database.py          ← SQLite-Engine + Session
│   ├── models.py          ← SQLAlchemy ORM-Modelle (13 Tabellen)
│   ├── schemas.py         ← Pydantic Request/Response-Typen
│   ├── api/               ← REST-Endpunkte (9 Router)
│   ├── fetchers/          ← 8 Datenquellen-Adapter
│   ├── scoring/           ← 3-Ebenen-Scoring-Engine
│   ├── scheduler/         ← APScheduler (06:00 UTC täglich)
│   ├── notifications/     ← Telegram-Bot
│   ├── cache/             ← TTL-Cache (In-Memory + SQLite)
│   ├── universe/          ← ~850 Ticker-Universum
│   └── backtesting/       ← Historische Signal-Simulation
├── frontend/              ← Vite + React + TypeScript (Port 5173)
└── scripts/
    ├── init_db.py         ← DB initialisieren (einmalig)
    ├── backfill_scores.py ← 30-Tage-Historie für Charts
    └── test_fetchers.py   ← API-Verbindungen testen
```

## Zwei Workflows

**Workflow A – Scanner (06:00 UTC täglich)**
- ~850 US-Aktien scannen (S&P 500 + NASDAQ 100 + Russell 2000 + persönliche Liste + Trending)
- 3-Ebenen-Scoring: Fundamental (40%) + Technisch (35%) + Sentiment (25%) → Score 0–100
- 4-Zonen-Watchlist: Zone 1 (≥76) → Zone 2 (≥61) → Zone 3 (≥41) → Zone 4 (<41)
- Zone 1: Optionsschein-Empfehlung (Richtung, Hebel, Laufzeit, KO-Abstand, Entry, SL)

**Workflow B – Bestandsbeobachtung (täglich nach Scan)**
- Score-Entwicklung, KO-Abstand, Restlaufzeit, Sentiment täglich neu bewertet
- 4 Exit-Signaltypen → Telegram-Benachrichtigung
- P&L-Berechnung bei Verkauf, Trade-Archivierung, Signalqualitäts-Tracking

## Starten (Entwicklung)

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # API-Keys eintragen
python scripts/init_db.py
uvicorn backend.main:app --reload --port 8000

# Frontend (separates Terminal, nach Phase-4-Fertigstellung)
cd frontend && npm install && npm run dev
```

Swagger-UI: http://localhost:8000/docs

## Wichtige Konventionen

- **Git-Branch:** `claude/stock-options-analyzer-umA6s`
- **Sprache:** Kommentare, Commits, Docs auf Deutsch; Code-Identifiers auf Englisch
- **Keine Auth:** Single-User, localhost only, kein Cloud-Zwang
- **Rate-Limits immer beachten:** Alpha Vantage (25/Tag), Finnhub (60/Min) – Details in `docs/RATE_LIMITS.md`
- **Cache prüfen vor jedem API-Call:** `backend/cache/store.py`

## Scoring-Kurzreferenz

| Ebene | Gewichtung | Max. Punkte | Datenquellen |
|-------|-----------|------------|--------------|
| Fundamental | 40% | 40 | yfinance, SimFin, Finnhub |
| Technisch | 35% | 35 | yfinance OHLCV + `ta`-Bibliothek |
| Sentiment | 25% | 25 | Finnhub, StockTwits, ApeWisdom, Marketaux |

Zone 1 (≥76) → Optionsschein-Empfehlung  
Zone 2 (61–75) → VCP aktiv, beobachten  
Zone 3 (41–60) → Auf dem Radar  
Zone 4 (<41) → Universum

## Datenbank direkt inspizieren

```bash
sqlite3 data/aidepot.db ".tables"
sqlite3 data/aidepot.db "SELECT key, value FROM configuration;"
sqlite3 data/aidepot.db "SELECT ticker, total_score, zone FROM daily_scores ORDER BY total_score DESC LIMIT 10;"
```
