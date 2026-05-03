# AIDepot – Offene Aufgaben & Fortschritt

Zuletzt aktualisiert: 2025-05-03

---

## Aktueller Stand

**Phase:** 2 – Scoring-Engine (Phase 1 abgeschlossen ✅)
**Branch:** `claude/stock-options-analyzer-umA6s`
**Gesamtfortschritt:** ~40 % (alle Fetcher + DB + Backend-Kern + Universe fertig)

---

## ✅ Phase 1 – Backend-Fundament (abgeschlossen)

### Infrastruktur & Konfiguration
- [x] Projektstruktur mit allen Verzeichnissen
- [x] `.gitignore`, `.env.example`
- [x] `backend/requirements.txt` (inkl. `pydantic-settings`)
- [x] `backend/config.py` – Pydantic BaseSettings

### Datenbank
- [x] `backend/database.py` – SQLite-Engine, init_db()
- [x] `backend/models.py` – 13 SQLAlchemy ORM-Modelle
- [x] `scripts/init_db.py`

### Backend-Kern
- [x] `backend/schemas.py` – alle Pydantic-Typen
- [x] `backend/main.py` – FastAPI-App, CORS
- [x] `backend/cache/store.py` – TTL-Cache

### Fetcher (alle 8 fertig ✅)
- [x] `backend/fetchers/base.py`
- [x] `backend/fetchers/yfinance_fetcher.py`
- [x] `backend/fetchers/stocktwits_fetcher.py`
- [x] `backend/fetchers/apewisdom_fetcher.py`
- [x] `backend/fetchers/finnhub_fetcher.py`
- [x] `backend/fetchers/alphavantage_fetcher.py`
- [x] `backend/fetchers/marketaux_fetcher.py`
- [x] `backend/fetchers/simfin_fetcher.py`

### Universum
- [x] `backend/universe/loader.py` – 439 Ticker (SP500/NASDAQ100/RUSSELL200)

### Test
- [x] `scripts/test_fetchers.py` – alle 8 Quellen ✅ (Alpha Vantage: ⚠️ nur ohne Key)

### Dokumentation
- [x] `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/SCORING.md`
- [x] `docs/API.md`, `docs/RATE_LIMITS.md`, `docs/SETUP.md`, `docs/ROADMAP.md`

---

## 🔄 Phase 2 – Scoring-Engine (als nächstes)

- [ ] `backend/scoring/fundamental.py` – 7 Kriterien, max. 40 Punkte
- [ ] `backend/scoring/technical.py` – VCP + 6 Indikatoren, max. 35 Punkte
- [ ] `backend/scoring/sentiment.py` – 4 Kriterien + Unterdrückungslogik, max. 25 Punkte
- [ ] `backend/scoring/delta.py` – Δ1T, Δ7T, Δ30T
- [ ] `backend/scoring/options.py` – OS-Parameter-Ableitung
- [ ] `backend/scoring/orchestrator.py` – Hauptkoordinator, schreibt in DB

**Abschluss-Kriterium:** `orchestrator.score_ticker("AAPL")` schreibt validen Score in DB.

---

## 📋 Spätere Phasen

### Phase 3 – API + Automatisierung
- [ ] 9 API-Router (`watchlist`, `signals`, `portfolio`, `dashboard`, `history`, `scan`, `config`, `universe`, `backtest`)
- [ ] `backend/scheduler/jobs.py` – APScheduler 06:00 UTC
- [ ] `backend/scheduler/priority_queue.py`
- [ ] `backend/notifications/telegram.py`

### Phase 4 – Backtesting
- [ ] `backend/backtesting/` (3 Module + API-Endpunkt)

### Phase 5 – Frontend
- [ ] Vite + React + TypeScript scaffolden
- [ ] 6 Seiten: Dashboard, Watchlist, Signal-Detail, Portfolio, Trade-Historie, Backtest

---

## Bekannte Einschränkungen

| Einschränkung | Details |
|---------------|---------|
| Alpha Vantage 25/Tag | Primär `ta`-Bibliothek + yfinance; AV als Ergänzung |
| Optionsschein-Stammdaten | Kein Free-API → ISIN + KO manuell eintragen |
| Historisches Sentiment | Für Backtesting nicht verfügbar → neutral 12,5/25 |
| yfinance `earnings` deprecated | Warning unterdrücken oder auf `income_stmt` umstellen |
