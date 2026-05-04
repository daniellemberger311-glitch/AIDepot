# AIDepot – Projektdokumentation für Claude

Diese Datei wird in jeder Claude-Code-Session automatisch geladen.

## Was ist AIDepot?

Persönliche, lokal betriebene Single-User-App zur Analyse von US-Aktien und Optionsscheinen.  
Ziel: Aktien im Pre-Breakout-Aufbau (VCP-Muster wie ASTS, SNDK, NVDA) frühzeitig erkennen und Optionsschein-Positionen täglich bis zum Exit begleiten.

## Aktueller Entwicklungsstand

**Phase 1 ✅ | Phase 2 ✅ | Phase 3 ✅ | Phase 4 ✅ | Phase 5 ✅ | Phase 6 ✅ – App ist produktionsreif**

| Modul | Status |
|-------|--------|
| Projektstruktur, .env, .gitignore | ✅ fertig |
| `backend/config.py` | ✅ fertig |
| `backend/database.py` + `models.py` | ✅ fertig |
| `backend/schemas.py` + `main.py` (serviert auch Frontend) | ✅ fertig |
| `backend/cache/store.py` | ✅ fertig |
| `backend/log_handler.py` + `backend/api/logs.py` | ✅ fertig |
| Fetcher: alle 8 + Key-Rotation AV | ✅ fertig |
| Scoring-Engine: 6 Module + Orchestrator | ✅ fertig |
| API-Endpunkte: 40+ Routen (watchlist, signals, portfolio, dashboard, history, scan, config, universe, backtest) | ✅ fertig |
| Scheduler (APScheduler 06:00 UTC) + Telegram-Bot | ✅ fertig |
| Backtesting-Modul | ✅ fertig |
| Frontend (React + Vite, 7 Seiten) | ✅ fertig |
| Alembic-Migrationen (`migrations/`) | ✅ fertig |
| systemd-Service + Backup-Timer | ✅ fertig |
| Unit-Tests Scoring-Engine (`tests/`) | ✅ fertig – 133 Tests |
| `update.sh` (Einzeiler-Deployment) | ✅ fertig |
| Responsive UI (Mobile Bottom-Nav + Desktop Sidebar) | ✅ fertig |

Detaillierter Fortschritt → `TODO.md`  
Entwicklungs-Roadmap → `docs/ROADMAP.md`

## Tech-Stack

| Schicht | Technologie |
|---------|-------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, APScheduler |
| Datenbank | SQLite (`./data/aidepot.db`) + Alembic-Migrationen |
| Frontend | React 18, TypeScript, Vite, TanStack Query v5, Tailwind CSS v4, Recharts |
| Produktion | systemd-Service, FastAPI serviert gebautes Frontend (ein Prozess, ein Port: 8000) |
| Tests | pytest, 133 Unit-Tests für die Scoring-Engine |
| Benachrichtigungen | Telegram Bot (python-telegram-bot, optional) |

## Verzeichnisstruktur

```
AIDepot/
├── CLAUDE.md              ← Diese Datei (automatisch geladen)
├── TODO.md                ← Fortschritt & erledigte Aufgaben
├── README.md              ← Installationsanleitung
├── conftest.py            ← pytest sys.path-Konfiguration
├── alembic.ini            ← Alembic-Konfiguration
├── update.sh              ← Einzeiler-Deployment (git pull → tests → alembic → build → restart)
├── aidepot.service        ← systemd-Service-Unit (Auto-Start, 0.0.0.0:8000)
├── aidepot-backup.service ← systemd-Backup-Service
├── aidepot-backup.timer   ← systemd-Timer (täglich 03:00 UTC)
├── docs/
│   ├── ROADMAP.md         ← Alle Phasen abgeschlossen
│   ├── ARCHITECTURE.md    ← System-Diagramm, Datenfluss
│   ├── SCORING.md         ← 3-Ebenen-Scoring mit Punktetabellen
│   ├── API.md             ← REST-Endpunkte Referenz (alle ✅)
│   ├── RATE_LIMITS.md     ← Strategie für 850 Aktien mit Free-Tier-APIs
│   └── SETUP.md           ← Einrichtungsanleitung + Heimnetz/Produktion
├── migrations/            ← Alembic-Versionsmigration
│   ├── env.py
│   └── versions/
│       ├── 0001_initial.py              ← Alle 13 Tabellen
│       └── 0002_close_price_currency.py ← Kurspreise + Währung
├── tests/                 ← pytest Unit-Tests
│   ├── scoring/
│   │   ├── test_fundamental.py  ← 40 Tests, alle 7 L1-Kriterien
│   │   ├── test_sentiment.py    ← 41 Tests, L3 + Unterdrückungsregel
│   │   └── test_technical.py    ← 35 Tests, L2 mit synthetischen DataFrames
│   └── test_orchestrator.py     ← 17 Tests, Zonengrenzen
├── .env                   ← API-Keys (gitignored)
├── .env.example           ← API-Keys Template
├── backend/
│   ├── main.py            ← FastAPI-Einstiegspunkt (Port 8000, serviert auch frontend/dist/)
│   ├── config.py          ← Pydantic BaseSettings (.env)
│   ├── database.py        ← SQLite-Engine + Session
│   ├── log_handler.py     ← MemoryLogHandler (Ringpuffer 1000 Einträge)
│   ├── models.py          ← SQLAlchemy ORM-Modelle (13 Tabellen)
│   ├── schemas.py         ← Pydantic Request/Response-Typen
│   ├── api/
│   │   ├── router.py      ← Zentraler Router
│   │   ├── logs.py        ← GET/DELETE /api/logs
│   │   ├── watchlist.py   ← GET /api/watchlist + /zones/summary
│   │   ├── signals.py     ← GET /api/signals/{ticker} + /history
│   │   ├── portfolio.py   ← CRUD Positionen + Exit-Signale
│   │   ├── dashboard.py   ← GET /api/dashboard
│   │   ├── history.py     ← Trade-Archiv + Signalqualität
│   │   ├── scan.py        ← POST /api/scan/trigger|cancel|ticker/{t}; GET /status
│   │   ├── config.py      ← GET/PUT /api/config + /status + /scan-schedule
│   │   └── universe.py    ← Ticker-CRUD + Suche + Refresh
│   ├── fetchers/          ← 8 Datenquellen-Adapter
│   ├── scoring/           ← 3-Ebenen-Scoring-Engine
│   │   ├── fundamental.py ← L1: 7 Kriterien, max. 40 Pkt.
│   │   ├── technical.py   ← L2: VCP + 6 Indikatoren, max. 35 Pkt.
│   │   ├── sentiment.py   ← L3: 4 Kriterien + Unterdrückung, max. 25 Pkt.
│   │   ├── delta.py       ← Δ1T / Δ7T / Δ30T
│   │   ├── options.py     ← OS-Parameter-Ableitung (nur Zone 1)
│   │   └── orchestrator.py← Hauptkoordinator, schreibt in 4 DB-Tabellen
│   ├── scheduler/         ← APScheduler tägl. 06:00 UTC
│   │   ├── jobs.py        ← Scan + Exit-Check + Notifications + Wartung
│   │   └── priority_queue.py ← Tier-0→3-Reihenfolge + Zone-4-Rotation
│   ├── notifications/     ← Telegram-Bot
│   │   └── telegram.py    ← 5 Nachrichtentypen + Dispatcher
│   ├── cache/             ← TTL-Cache (In-Memory + SQLite)
│   ├── universe/          ← ~850 Ticker-Universum
│   └── backtesting/       ← Historische Signal-Simulation
│       ├── historical_data.py
│       ├── engine.py
│       └── signal_mapper.py
├── frontend/              ← Vite + React + TypeScript
│   └── dist/              ← Gebautes Frontend (von FastAPI serviert)
└── scripts/
    ├── init_db.py         ← DB initialisieren (einmalig)
    ├── backup.sh          ← SQLite-Backup (täglich via systemd-Timer)
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

## Starten

**Entwicklung (zwei Prozesse):**
```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python scripts/init_db.py
uvicorn backend.main:app --reload --port 8000

# Frontend (separates Terminal)
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

**Produktion / Heimnetz (ein Prozess):**
```bash
# Frontend einmalig bauen
cd frontend && npm run build && cd ..

# Backend startet auf 0.0.0.0:8000 und serviert auch das gebaute Frontend
uvicorn backend.main:app --host 0.0.0.0 --port 8000
# → http://<Linux-IP>:8000  (von Allen Geräten im Heimnetz erreichbar)
```

**Automatisch via systemd:**
```bash
sudo cp aidepot.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now aidepot
```

## Tests & Updates

```bash
# Tests lokal ausführen
python -m pytest tests/ -q --tb=short   # 133 Tests

# Update (Produktion): git pull → tests → alembic → npm build → service restart
bash update.sh
```

## Wichtige Konventionen

- **Git-Branch:** Feature-Branches nach Bedarf; Merges auf `main`
- **Sprache:** Kommentare, Commits, Docs auf Deutsch; Code-Identifiers auf Englisch
- **Keine Auth:** Single-User, localhost/Heimnetz only, kein Cloud-Zwang
- **Rate-Limits immer beachten:** Alpha Vantage (50/Tag mit 2 Keys, je 25), Finnhub (60/Min) – Details in `docs/RATE_LIMITS.md`
- **Cache prüfen vor jedem API-Call:** `backend/cache/store.py`
- **DAX-Ticker (.DE):** StockTwits/ApeWisdom liefern keine DE-Daten → Sentiment = neutral (12,5/25)
- **DB-Schema ändern:** Immer Alembic-Migration erstellen (`alembic revision --autogenerate -m "Beschreibung"`), nie direkt in `models.py` ohne Migration

## API-Keys

| Dienst | Variable | Limit | Status |
|--------|----------|-------|--------|
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | 25/Tag | ✅ konfiguriert |
| Alpha Vantage 2 | `ALPHA_VANTAGE_API_KEY_2` | +25/Tag (Rotation) | ✅ konfiguriert |
| Finnhub | `FINNHUB_API_KEY` | 60/Min | ✅ konfiguriert |
| Marketaux | `MARKETAUX_API_KEY` | 100 News/Tag | ✅ konfiguriert |
| SimFin | `SIMFIN_API_KEY` | unbegrenzt | ✅ konfiguriert |
| Telegram | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | kostenlos | ✅ konfiguriert + Bot als Admin im Kanal |

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
