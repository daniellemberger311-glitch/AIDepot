# AIDepot – Projektdokumentation für Claude

Diese Datei wird in jeder Claude-Code-Session automatisch geladen.

## Was ist AIDepot?

Persönliche, lokal betriebene Single-User-App zur Analyse von US-Aktien und Optionsscheinen.  
Ziel: Aktien im Pre-Breakout-Aufbau (VCP-Muster wie ASTS, SNDK, NVDA) frühzeitig erkennen und Optionsschein-Positionen täglich bis zum Exit begleiten.

## Aktueller Entwicklungsstand

**Phase 1 ✅ abgeschlossen | Phase 2 ✅ abgeschlossen | Phase 3 ✅ abgeschlossen | Phase 4 – Backtesting (als nächstes)**

| Modul | Status |
|-------|--------|
| Projektstruktur, .env, .gitignore | ✅ fertig |
| `backend/config.py` | ✅ fertig |
| `backend/database.py` + `models.py` | ✅ fertig |
| `backend/schemas.py` + `main.py` | ✅ fertig |
| `backend/cache/store.py` | ✅ fertig |
| `backend/log_handler.py` + `backend/api/logs.py` | ✅ fertig |
| Fetcher: alle 8 + Key-Rotation AV | ✅ fertig |
| Scoring-Engine: 6 Module + Orchestrator | ✅ fertig |
| API-Endpunkte: 35 Routen (watchlist, signals, portfolio, dashboard, history, scan, config, universe) | ✅ fertig |
| Scheduler (APScheduler 06:00 UTC) + Telegram-Bot | ✅ fertig |
| Backtesting-Modul | ⏳ offen – Phase 4 |
| Frontend (React + Vite) | ⏳ offen – Phase 5 |

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
│   ├── SCORING.md         ← 3-Ebenen-Scoring mit Punktetabellen (implementiert)
│   ├── API.md             ← REST-Endpunkte Referenz (✅ = fertig, ⏳ = Phase 3)
│   ├── RATE_LIMITS.md     ← Strategie für 850 Aktien mit Free-Tier-APIs
│   └── SETUP.md           ← Einrichtungsanleitung + API-Key-Status
├── .env                   ← API-Keys (gitignored, alle 4 Keys konfiguriert)
├── .env.example           ← API-Keys Template
├── backend/
│   ├── main.py            ← FastAPI-Einstiegspunkt (Port 8000)
│   ├── config.py          ← Pydantic BaseSettings (.env)
│   ├── database.py        ← SQLite-Engine + Session
│   ├── log_handler.py     ← MemoryLogHandler (Ringpuffer 1000 Einträge)
│   ├── models.py          ← SQLAlchemy ORM-Modelle (13 Tabellen)
│   ├── schemas.py         ← Pydantic Request/Response-Typen
│   ├── api/               ← 35 REST-Endpunkte (✅ Phase 3 abgeschlossen)
│   │   ├── router.py      ← Zentraler Router
│   │   ├── logs.py        ← GET /api/logs
│   │   ├── watchlist.py   ← GET /api/watchlist
│   │   ├── signals.py     ← GET /api/signals/{ticker}
│   │   ├── portfolio.py   ← CRUD Positionen + Exit-Signale
│   │   ├── dashboard.py   ← GET /api/dashboard
│   │   ├── history.py     ← Trade-Archiv + Signalqualität
│   │   ├── scan.py        ← POST /api/scan/trigger
│   │   ├── config.py      ← GET/PUT /api/config + Status
│   │   └── universe.py    ← Ticker-CRUD + Suche + Refresh
│   ├── fetchers/          ← 8 Datenquellen-Adapter (✅)
│   ├── scoring/           ← 3-Ebenen-Scoring-Engine (✅)
│   │   ├── fundamental.py ← L1: 7 Kriterien, max. 40 Pkt.
│   │   ├── technical.py   ← L2: VCP + 6 Indikatoren, max. 35 Pkt.
│   │   ├── sentiment.py   ← L3: 4 Kriterien + Unterdrückung, max. 25 Pkt.
│   │   ├── delta.py       ← Δ1T / Δ7T / Δ30T
│   │   ├── options.py     ← OS-Parameter-Ableitung (nur Zone 1)
│   │   └── orchestrator.py← Hauptkoordinator, schreibt in 4 DB-Tabellen
│   ├── scheduler/         ← APScheduler tägl. 06:00 UTC (✅)
│   │   ├── jobs.py        ← Scan + Exit-Check + Notifications + Wartung
│   │   └── priority_queue.py ← Tier-0→3-Reihenfolge + Zone-4-Rotation
│   ├── notifications/     ← Telegram-Bot (✅)
│   │   └── telegram.py    ← 5 Nachrichtentypen + Dispatcher
│   ├── cache/             ← TTL-Cache (In-Memory + SQLite)
│   ├── universe/          ← ~850 Ticker-Universum
│   └── backtesting/       ← Historische Signal-Simulation – Phase 4 ⏳
├── frontend/              ← Vite + React + TypeScript (Port 5173) – Phase 5
└── scripts/
    ├── init_db.py         ← DB initialisieren (einmalig)
    ├── backfill_scores.py ← 30-Tage-Historie für Charts
    └── test_fetchers.py   ← API-Verbindungen testen
```

## Zwei Workflows

**Workflow A – Scanner (06:00 UTC täglich)**
- ~850 US-Aktien scannen (S&P 500 + NASDAQ 100 + Russell 2000 + DAX 40 + persönliche Liste)
- 3-Ebenen-Scoring: Fundamental (40%) + Technisch (35%) + Sentiment (25%) → Score 0–100
- 4-Zonen-Watchlist: Zone 1 (≥76) → Zone 2 (≥61) → Zone 3 (≥41) → Zone 4 (<41)
- Zone 1: Optionsschein-Empfehlung (Richtung, Hebel-Range, Laufzeit, KO-Abstand, Entry, SL)

**Workflow B – Bestandsbeobachtung (täglich nach Scan)**
- Score-Entwicklung, KO-Abstand, Restlaufzeit, Sentiment täglich neu bewertet
- 4 Exit-Signaltypen → Telegram-Benachrichtigung
- P&L-Berechnung bei Verkauf, Trade-Archivierung, Signalqualitäts-Tracking

## Starten (Entwicklung)

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
# .env ist bereits konfiguriert (alle API-Keys eingetragen)
python scripts/init_db.py
uvicorn backend.main:app --reload --port 8000

# Frontend (nach Phase-5-Fertigstellung)
cd frontend && npm install && npm run dev
```

Swagger-UI: http://localhost:8000/docs  
Log-Übersicht: http://localhost:8000/api/logs?level=ERROR

## Wichtige Konventionen

- **Git-Branch:** `main` (direkte Entwicklung, kein Feature-Branch außer explizit angewiesen)
- **Sprache:** Kommentare, Commits, Docs auf Deutsch; Code-Identifiers auf Englisch
- **Keine Auth:** Single-User, localhost only, kein Cloud-Zwang
- **Rate-Limits immer beachten:** Alpha Vantage (50/Tag mit 2 Keys, je 25), Finnhub (60/Min) – Details in `docs/RATE_LIMITS.md`
- **Cache prüfen vor jedem API-Call:** `backend/cache/store.py`
- **DAX-Ticker (.DE):** StockTwits/ApeWisdom liefern keine DE-Daten → Sentiment = neutral (12,5/25)

## API-Keys (alle konfiguriert)

| Dienst | Variable | Limit | Status |
|--------|----------|-------|--------|
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | 25/Tag | ✅ |
| Alpha Vantage 2 | `ALPHA_VANTAGE_API_KEY_2` | +25/Tag (Rotation) | ✅ |
| Finnhub | `FINNHUB_API_KEY` | 60/Min | ✅ |
| Marketaux | `MARKETAUX_API_KEY` | 100 News/Tag | ✅ |
| SimFin | `SIMFIN_API_KEY` | unbegrenzt | ✅ |
| Telegram | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | kostenlos | ⏳ noch nicht eingerichtet |

## Scoring-Kurzreferenz

| Ebene | Gewichtung | Max. Punkte | Datenquellen |
|-------|-----------|------------|--------------|
| Fundamental | 40% | 40 | yfinance, SimFin (inkl. Bilanz), Finnhub |
| Technisch | 35% | 35 | yfinance OHLCV + `ta`-Bibliothek (RSI, MACD, BB, ATR) |
| Sentiment | 25% | 25 | Finnhub, Marketaux, StockTwits, ApeWisdom |

Zone 1 (≥76) → Optionsschein-Empfehlung  
Zone 2 (61–75) → VCP aktiv, beobachten  
Zone 3 (41–60) → Auf dem Radar  
Zone 4 (<41) → Universum

**Unterdrückungsregel:** L1+L2 > 50 UND L3 < 5 → Score gedeckelt auf 74 (kein Zone-1-Eintrag)

## Datenbank direkt inspizieren

```bash
python -c "
import sqlite3; con = sqlite3.connect('data/aidepot.db')
for row in con.execute('SELECT ticker, total_score, zone FROM daily_scores ORDER BY total_score DESC LIMIT 10'): print(row)
"
```
