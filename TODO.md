# AIDepot – Offene Aufgaben & Fortschritt

Zuletzt aktualisiert: 2026-05-03

---

## Aktueller Stand

**Phase:** 4 – Backtesting (Phase 3 abgeschlossen ✅)  
**Branch:** `main`  
**Gesamtfortschritt:** ~75 %

---

## ✅ Phase 1 – Backend-Fundament (abgeschlossen)

- Projektstruktur, `.env`, `.gitignore`
- `backend/config.py`, `database.py`, `models.py` (13 Tabellen)
- `backend/schemas.py`, `main.py`, `cache/store.py`
- Alle 8 Fetcher inkl. AV-Key-Rotation
- `backend/universe/loader.py` – 703 aktive Ticker + 6.243 Reserve
- `scripts/init_db.py`, `scripts/test_fetchers.py`

---

## ✅ Phase 2 – Scoring-Engine (abgeschlossen)

- `backend/scoring/fundamental.py` – L1: 7 Kriterien, max. 40 Pkt.
- `backend/scoring/technical.py` – L2: VCP + 6 Indikatoren, max. 35 Pkt.
- `backend/scoring/sentiment.py` – L3: 4 Kriterien + Unterdrückungsregel, max. 25 Pkt.
- `backend/scoring/delta.py` – Δ1T / Δ7T / Δ30T
- `backend/scoring/options.py` – OS-Parameter (nur Zone 1)
- `backend/scoring/orchestrator.py` – Hauptkoordinator, schreibt in 4 DB-Tabellen

---

## ✅ Phase 3 – API + Scheduler + Notifications (abgeschlossen)

**35 REST-Endpunkte:**
- `GET /api/watchlist` – Zone-Filter, Sortierung, Breakdown
- `GET /api/signals/{ticker}` – vollständiges Signal + OS-Empfehlung
- `GET /api/signals/{ticker}/history` – Score-Verlauf
- `GET/POST/PUT/DELETE /api/portfolio` – CRUD Positionen + Exit-Signale + P&L
- `GET /api/dashboard` – Tagesübersicht
- `GET /api/history/trades` + `/signal-quality` + `/summary`
- `POST /api/scan/trigger` – Background-Task, `GET /api/scan/status`
- `GET/PUT /api/config` – Einstellungen, `GET /api/config/status` – API-Key-Status
- `GET/POST/DELETE /api/universe` – Ticker-CRUD + Reserve-Suche + Refresh

**Scheduler (APScheduler):**
- 06:00 UTC – Täglicher Scan (Tier 0→3 + Zone-4-Rotation)
- 06:30 UTC – Exit-Signal-Check aller offenen Positionen
- 07:00 UTC – Telegram-Benachrichtigungen
- So 02:00 UTC – Wikipedia-Refresh + Cache-Bereinigung

**Notifications:** Code fertig, Telegram noch nicht konfiguriert (⏳ BOT_TOKEN + CHAT_ID fehlen noch in .env)

---

## ✅ Phase 4 – Backtesting-Modul (abgeschlossen)

- [x] `backend/backtesting/historical_data.py` – OHLCV + Fundamentals (yfinance, TTL-Cache 4h)
- [x] `backend/backtesting/engine.py` – tägliche Score-Berechnung aus OHLCV-Slices
- [x] `backend/backtesting/signal_mapper.py` – ZONE_CHANGE, ZONE1_ENTRY, DELTA_SPIKE, STREAK_7D
- [x] `backend/api/backtest.py` – `POST /api/backtest`, `GET /api/backtest/status/{ticker}`, `DELETE /api/backtest/cache/{ticker}`
- [x] Router eingebunden → 40 Routen gesamt

**Einschränkungen:**
- Sentiment: immer neutral 12,5/25 (historisch nicht verfügbar)
- Zeiträume ≤ 1 Jahr: synchron; > 1 Jahr: Background-Job (max. 5 Jahre)
- EPS-Beat-Streak: vereinfachte Schätzung aus yfinance (keine echte Beat-Historie)

---

## 📋 Phase 5 – Frontend (7 Seiten, als nächstes)

- [ ] Vite + React + TypeScript scaffolden (`frontend/`)
- [ ] Dashboard (`/`) – P&L, Top-5 Zone 1, Exit-Warnungen
- [ ] Watchlist (`/watchlist`) – 4-Zonen-Tabelle, sortiert nach Δ7T
- [ ] Signal-Detail (`/signal/:ticker`) – Score-Aufschlüsselung, 30T-Chart, OS-Empfehlung
- [ ] Portfolio (`/portfolio`) – Positionen, HALTEN/BEOBACHTEN/EXIT, Kauf/Verkauf
- [ ] Trade-Historie (`/history`) – Archiv, P&L-Statistik, Trefferquote
- [ ] Backtesting (`/backtest`) – Ticker + Zeitraum, Signal-Zeitstrahl
- [ ] Konfiguration (`/config`) – 5 Tabs: Universum, API-Status, Gewichtungen, Scan, Alerts

---

## Bekannte Einschränkungen

| Einschränkung | Details |
|---------------|---------|
| AV MACD ist Premium | ta-Bibliothek berechnet MACD aus yfinance-OHLCV (kein Verlust) |
| Ticker-Listen Stand Q1 2025 | `POST /api/universe/refresh` oder wöchentl. Scheduler hält aktuell |
| Optionsschein-Stammdaten | Kein Free-API → ISIN + KO manuell eintragen |
| Historisches Sentiment | Für Backtesting: neutral 12,5/25 |
| Unrealized P&L | Warrant-Preis nicht via API → manuell oder via Scan nachgetragen |
| Telegram | BOT_TOKEN + CHAT_ID noch nicht in .env eingetragen |
