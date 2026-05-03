# AIDepot – Offene Aufgaben & Fortschritt

Zuletzt aktualisiert: 2025-05-03

---

## Aktueller Stand

**Phase:** 1 – MVP (Backend-Fundament)  
**Branch:** `claude/stock-options-analyzer-umA6s`  
**Fortschritt:** ~30% (Grundstruktur + DB + Backend-Kern fertig)

---

## ✅ Erledigt

- [x] Projektstruktur & Verzeichnisse angelegt
- [x] `.gitignore`, `.env.example`
- [x] `backend/requirements.txt`
- [x] `backend/config.py` (Pydantic BaseSettings)
- [x] `backend/database.py` (SQLite-Engine, Session, init_db)
- [x] `backend/models.py` (alle SQLAlchemy ORM-Modelle)
- [x] `backend/schemas.py` (alle Pydantic Request/Response-Typen)
- [x] `backend/main.py` (FastAPI-App, CORS, Lifespan)
- [x] `backend/cache/store.py` (TTL-Cache, In-Memory + SQLite)
- [x] `scripts/init_db.py`
- [x] `CLAUDE.md` (Projekt-Kontext für jede Session)
- [x] `docs/ARCHITECTURE.md`
- [x] `docs/SCORING.md`
- [x] `docs/API.md`
- [x] `docs/RATE_LIMITS.md`
- [x] `docs/SETUP.md`

---

## 🔄 In Arbeit

- [ ] `backend/fetchers/base.py` – BaseFetcher mit Cache + Retry
- [ ] `backend/fetchers/yfinance_fetcher.py` – OHLCV, Fundamentals
- [ ] `backend/fetchers/stocktwits_fetcher.py` – Bullish-Ratio, Trending
- [ ] `backend/fetchers/apewisdom_fetcher.py` – Reddit-Mentions

---

## 📋 Offen

### Phase 1 – MVP Scanner + Watchlist
- [ ] `backend/fetchers/finnhub_fetcher.py` – News, Insider, Earnings
- [ ] `backend/fetchers/alphavantage_fetcher.py` – technische Indikatoren
- [ ] `backend/fetchers/marketaux_fetcher.py` – News + Sentiment
- [ ] `backend/fetchers/simfin_fetcher.py` – KGV, EPS, FCF
- [ ] `backend/scoring/fundamental.py` – Ebene 1 (max. 40 Punkte)
- [ ] `backend/scoring/technical.py` – Ebene 2 mit VCP (max. 35 Punkte)
- [ ] `backend/scoring/sentiment.py` – Ebene 3 + Unterdrückung (max. 25 Punkte)
- [ ] `backend/scoring/delta.py` – Δ1T, Δ7T, Δ30T
- [ ] `backend/scoring/options.py` – OS-Parameter-Ableitung
- [ ] `backend/scoring/orchestrator.py` – Gesamtkoordinator

### Phase 1 – API-Endpunkte
- [ ] `backend/api/router.py`
- [ ] `backend/api/watchlist.py`
- [ ] `backend/api/signals.py`
- [ ] `backend/api/portfolio.py`
- [ ] `backend/api/dashboard.py`
- [ ] `backend/api/history.py`
- [ ] `backend/api/scan.py`
- [ ] `backend/api/config.py`
- [ ] `backend/api/universe.py`

### Phase 2 – Automatisierung + Notifications
- [ ] `backend/universe/loader.py` – ~850 Ticker-Universum
- [ ] `backend/scheduler/priority_queue.py` – Scan-Reihenfolge
- [ ] `backend/scheduler/jobs.py` – APScheduler 06:00 UTC
- [ ] `backend/notifications/telegram.py` – Bot + Templates

### Phase 3 – Backtesting
- [ ] `backend/backtesting/historical_data.py`
- [ ] `backend/backtesting/engine.py`
- [ ] `backend/backtesting/signal_mapper.py`
- [ ] `backend/api/backtest.py`

### Phase 4 – Frontend
- [ ] Vite + React + TypeScript Projekt anlegen
- [ ] Tailwind CSS + Routing konfigurieren
- [ ] `frontend/src/types/index.ts`
- [ ] `frontend/src/api/` – alle API-Clients
- [ ] Seite: Dashboard
- [ ] Seite: Watchlist (4-Zonen-Tabelle)
- [ ] Seite: Signal-Detail (Score-Aufschlüsselung + Chart + OS-Empfehlung)
- [ ] Seite: Portfolio (Positionen + Exit-Signale)
- [ ] Seite: Trade-Historie (P&L + Signalqualität)
- [ ] Seite: Backtesting

### Phase 5 – Lerneffekt & Qualität
- [ ] `signal_quality`-Tabelle automatisch befüllen
- [ ] Trefferquote pro Signaltyp anzeigen
- [ ] Gewichtungsanpassung via UI

---

## Bekannte Einschränkungen

| Einschränkung | Details |
|---------------|---------|
| Alpha Vantage 25/Tag | Nur als Ergänzung nutzen; `ta`-Bibliothek ist primär |
| Optionsschein-Stammdaten | Kein Free-API → ISIN + KO manuell eingeben |
| Historisches Sentiment | Für Backtesting nicht verfügbar → neutraler Wert 12,5/25 |
| yfinance inoffiziell | Könnte brechen; hinter Abstraktionsschicht isoliert |

---

## Nächster Schritt

Fetcher-Implementierung: `backend/fetchers/base.py` → `yfinance_fetcher.py` → `stocktwits_fetcher.py`

Danach: Scoring-Engine bauen (nutzt die Fetcher direkt).
