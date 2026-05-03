# AIDepot – Offene Aufgaben & Fortschritt

Zuletzt aktualisiert: 2025-05-03

---

## Aktueller Stand

**Phase:** 1 – Backend-Fundament  
**Branch:** `claude/stock-options-analyzer-umA6s`  
**Gesamtfortschritt:** ~25 % (Grundstruktur, DB, Backend-Kern, 4 von 8 Fetchern)

---

## ✅ Erledigt

### Infrastruktur & Konfiguration
- [x] Projektstruktur mit allen Verzeichnissen angelegt
- [x] `.gitignore`, `.env.example`
- [x] `backend/requirements.txt`
- [x] `backend/config.py` – Pydantic BaseSettings, liest `.env`

### Datenbank
- [x] `backend/database.py` – SQLite-Engine, SessionLocal, `init_db()`
- [x] `backend/models.py` – alle SQLAlchemy ORM-Modelle:
  - `Stock`, `DailyScore`, `ScoreHistory`, `ScoreBreakdown`
  - `WatchlistEntry`, `OptionsRecommendation`
  - `Position`, `Transaction`, `ExitSignal`
  - `NotificationLog`, `SignalQuality`, `ApiCache`, `Configuration`
- [x] `scripts/init_db.py` – Tabellen erstellen + Standardkonfiguration befüllen

### Backend-Kern
- [x] `backend/schemas.py` – alle Pydantic Request/Response-Typen
- [x] `backend/main.py` – FastAPI-App, CORS, Lifespan-Hook

### Cache
- [x] `backend/cache/store.py` – TTL-Cache (In-Memory + SQLite-Fallback)

### Fetcher (4 von 8)
- [x] `backend/fetchers/base.py` – BaseFetcher mit Cache-Lookup, Retry-Dekorator
- [x] `backend/fetchers/yfinance_fetcher.py` – OHLCV, Fundamentals, Earnings, Insider (kein Key)
- [x] `backend/fetchers/stocktwits_fetcher.py` – Bullish-Ratio, Trending Tickers (kein Key)
- [x] `backend/fetchers/apewisdom_fetcher.py` – Reddit-Mentions (kein Key)
- [x] `backend/fetchers/finnhub_fetcher.py` – News-Sentiment, Insider, Earnings, Analyst (60/Min)

### Dokumentation
- [x] `CLAUDE.md` – Projekt-Kontext (automatisch in jeder Session geladen)
- [x] `docs/ARCHITECTURE.md` – System-Diagramm, Workflows, Schichtenmodell
- [x] `docs/SCORING.md` – vollständiges Scoring-System mit Punktetabellen
- [x] `docs/API.md` – alle geplanten REST-Endpunkte
- [x] `docs/RATE_LIMITS.md` – Strategie für 850 Aktien mit Free-Tier-APIs
- [x] `docs/SETUP.md` – Schritt-für-Schritt-Einrichtungsanleitung
- [x] `docs/ROADMAP.md` – Entwicklungs-Roadmap (Phasen 1–5)

---

## 🔄 Nächste Schritte (Phase 1 – Rest)

### Fetcher (4 noch offen)
- [ ] `backend/fetchers/alphavantage_fetcher.py` – technische Indikatoren (25/Tag-Limit!)
- [ ] `backend/fetchers/marketaux_fetcher.py` – News + Sentiment (100/Tag)
- [ ] `backend/fetchers/simfin_fetcher.py` – KGV, EPS, FCF, Verschuldung

### Scoring-Engine
- [ ] `backend/scoring/fundamental.py` – Ebene 1: 7 Kriterien, max. 40 Punkte
- [ ] `backend/scoring/technical.py` – Ebene 2: VCP + 6 weitere, max. 35 Punkte
- [ ] `backend/scoring/sentiment.py` – Ebene 3 + Unterdrückungslogik, max. 25 Punkte
- [ ] `backend/scoring/delta.py` – Δ1T, Δ7T, Δ30T aus `score_history`
- [ ] `backend/scoring/options.py` – Optionsschein-Parameter-Ableitung
- [ ] `backend/scoring/orchestrator.py` – Hauptkoordinator aller 3 Ebenen

### Universum
- [ ] `backend/universe/loader.py` – S&P 500, NASDAQ 100, Russell 2000, persönliche Liste

### API-Endpunkte
- [ ] `backend/api/router.py`
- [ ] `backend/api/watchlist.py` – GET /api/watchlist
- [ ] `backend/api/signals.py` – GET /api/signals/{ticker}
- [ ] `backend/api/portfolio.py` – CRUD Positionen
- [ ] `backend/api/dashboard.py` – GET /api/dashboard
- [ ] `backend/api/history.py` – Trades + Signalqualität
- [ ] `backend/api/scan.py` – manueller Scan-Trigger
- [ ] `backend/api/config.py` – Konfiguration lesen/schreiben
- [ ] `backend/api/universe.py` – Universum verwalten

---

## 📋 Spätere Phasen

### Phase 2 – Automatisierung
- [ ] `backend/universe/loader.py` fertigstellen
- [ ] `backend/scheduler/priority_queue.py`
- [ ] `backend/scheduler/jobs.py` – APScheduler 06:00 UTC
- [ ] `backend/notifications/telegram.py`

### Phase 3 – Backtesting
- [ ] `backend/backtesting/historical_data.py`
- [ ] `backend/backtesting/engine.py`
- [ ] `backend/backtesting/signal_mapper.py`
- [ ] `backend/api/backtest.py`

### Phase 4 – Frontend
- [ ] Vite + React + TypeScript Projekt scaffolden
- [ ] Tailwind CSS konfigurieren
- [ ] TanStack Query + React Router
- [ ] 6 Seiten: Dashboard, Watchlist, Signal-Detail, Portfolio, Trade-Historie, Backtesting

### Phase 5 – Lerneffekt & Feintuning
- [ ] Signal-Qualitäts-Tracking automatisieren
- [ ] Trefferquote pro Signaltyp im UI
- [ ] Gewichtungsanpassung (40/35/25) via UI

---

## Bekannte Einschränkungen

| Einschränkung | Details |
|---------------|---------|
| Alpha Vantage 25/Tag | Primär `ta`-Bibliothek + yfinance; AV als Ergänzung |
| Optionsschein-Stammdaten | Kein Free-API → ISIN + KO manuell eintragen |
| Historisches Sentiment | Für Backtesting nicht verfügbar → neutral 12,5/25 |
| yfinance inoffiziell | Hinter Abstraktionsschicht isoliert, leicht austauschbar |
