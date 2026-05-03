# AIDepot – Offene Aufgaben & Fortschritt

Zuletzt aktualisiert: 2026-05-03

---

## Aktueller Stand

**Phase:** 3 ✅ abgeschlossen – API + Scheduler + Notifications  
**Branch:** `claude/phase-3-development-TiEnW`  
**Gesamtfortschritt:** ~75 %

**Universum:** 703 aktive Ticker (SP500/NASDAQ100/RUSSELL200/Watchlist) + 6.243 Reserve (NYSE/NASDAQ via AV LISTING_STATUS, is_active=0)

---

## 🔑 Offene API-Keys (bevor der Live-Scan funktioniert)

| Dienst | Umgebungsvariable | Wo beantragen | Limit Free Tier | Status |
|--------|------------------|---------------|-----------------|--------|
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | alphavantage.co | 25/Tag, 5/Min | ✅ eingetragen |
| Alpha Vantage 2 | `ALPHA_VANTAGE_API_KEY_2` | alphavantage.co | +25/Tag (Rotation) | ✅ eingetragen |
| Finnhub | `FINNHUB_API_KEY` | finnhub.io/register | 60 Calls/Min | ⏳ fehlt noch |
| Marketaux | `MARKETAUX_API_KEY` | marketaux.com | 100 News/Tag | ⏳ fehlt noch |
| SimFin | `SIMFIN_API_KEY` | simfin.com/api | unbegrenzt (privat) | ⏳ fehlt noch |
| Telegram Bot | `TELEGRAM_BOT_TOKEN` | @BotFather in Telegram | kostenlos | ⏳ fehlt noch |
| Telegram Chat-ID | `TELEGRAM_CHAT_ID` | siehe SETUP.md | – | ⏳ fehlt noch |

**Ohne Finnhub:** News-Sentiment, Insider-Transaktionen und Analyst-Ratings liefern Null-Werte → Sentiment-Score = 12,5/25 (neutral). App läuft, aber Sentiment-Ebene unvollständig.  
**Ohne SimFin:** Fundamentals kommen von yfinance (weniger präzise, aber funktional).  
**Ohne Telegram:** Kein Push-Alert, aber App läuft vollständig.

---

## ✅ Phase 1 – Backend-Fundament (abgeschlossen)

### Infrastruktur & Konfiguration
- [x] Projektstruktur mit allen Verzeichnissen
- [x] `.gitignore`, `.env.example`
- [x] `backend/requirements.txt` (inkl. `pydantic-settings`, `apscheduler`, `python-telegram-bot`)
- [x] `backend/config.py` – Pydantic BaseSettings

### Datenbank
- [x] `backend/database.py` – SQLite-Engine, init_db()
- [x] `backend/models.py` – 13 SQLAlchemy ORM-Modelle
- [x] `scripts/init_db.py`

### Backend-Kern
- [x] `backend/schemas.py` – alle Pydantic-Typen
- [x] `backend/main.py` – FastAPI-App, CORS
- [x] `backend/cache/store.py` – TTL-Cache

### Fetcher (alle 8 ✅)
- [x] `backend/fetchers/base.py`
- [x] `backend/fetchers/yfinance_fetcher.py`
- [x] `backend/fetchers/stocktwits_fetcher.py`
- [x] `backend/fetchers/apewisdom_fetcher.py`
- [x] `backend/fetchers/finnhub_fetcher.py`
- [x] `backend/fetchers/alphavantage_fetcher.py` (RSI ✅, MACD ist AV-Premium → ta-Bibliothek)
- [x] `backend/fetchers/marketaux_fetcher.py`
- [x] `backend/fetchers/simfin_fetcher.py`

### Universum
- [x] `backend/universe/loader.py`
  - 703 aktive Ticker (SP500 ~470, NASDAQ100 27, RUSSELL200 198, WATCHLIST 8)
  - 6.243 Reserve-Ticker (NYSE/NASDAQ via AV LISTING_STATUS, deaktiviert)
  - `refresh_universe()` – kombiniert Wikipedia-Fetch + AV LISTING_STATUS

### Test
- [x] `scripts/test_fetchers.py` – alle 8 Quellen ✅

### Dokumentation
- [x] `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/SCORING.md`
- [x] `docs/API.md`, `docs/RATE_LIMITS.md`, `docs/SETUP.md`, `docs/ROADMAP.md`

---

## ✅ Phase 2 – Scoring-Engine (abgeschlossen)

- [x] `backend/scoring/fundamental.py` – 7 Kriterien, max. 40 Punkte
- [x] `backend/scoring/technical.py` – VCP + 6 Indikatoren (ta-Bibliothek), max. 35 Punkte
- [x] `backend/scoring/sentiment.py` – 4 Kriterien + Unterdrückungslogik, max. 25 Punkte
- [x] `backend/scoring/delta.py` – Δ1T, Δ7T, Δ30T aus score_history
- [x] `backend/scoring/options.py` – OS-Parameter-Ableitung (Hebel, Laufzeit, KO, Entry, SL)
- [x] `backend/scoring/orchestrator.py` – Hauptkoordinator, schreibt in alle 4 Tabellen

**Abschluss-Test:** `score_ticker("AAPL")` → Score 39/100, Zone 4, alle 4 DB-Tabellen befüllt ✅

---

## ✅ Phase 3 – API + Scheduler + Notifications (abgeschlossen)

### API-Endpunkte (35 Routen gesamt)

- [x] `backend/api/_helpers.py` – gemeinsame `build_score_out()`-Funktion
- [x] `backend/api/router.py` – zentraler Router, alle Sub-Router eingebunden
- [x] `backend/api/logs.py` – GET /api/logs (bereits Phase 2)
- [x] `backend/api/watchlist.py`
  - `GET /api/watchlist` – Zone-Filter, Sortierung, optionaler Breakdown
  - `GET /api/watchlist/zones/summary` – Anzahl Aktien pro Zone
- [x] `backend/api/signals.py`
  - `GET /api/signals/{ticker}` – vollständiges Signal inkl. OS-Empfehlung
  - `GET /api/signals/{ticker}/history` – Score-Verlauf (30T-Chart)
- [x] `backend/api/portfolio.py`
  - `GET /api/portfolio` – offene + optionale geschlossene Positionen
  - `POST /api/portfolio` – Position anlegen (BUY-Transaktion automatisch)
  - `GET /api/portfolio/{id}` – Positionsdetail mit Exit-Signalen
  - `PUT /api/portfolio/{id}/close` – schließen (SELL + P&L-Berechnung)
  - `DELETE /api/portfolio/{id}` – löschen
  - `POST /api/portfolio/{id}/check-exits` – Exit-Signale generieren
  - `PUT /api/portfolio/signals/{id}/acknowledge` – Signal quittieren
  - `GET /api/portfolio/{id}/transactions` – alle Transaktionen
- [x] `backend/api/dashboard.py`
  - `GET /api/dashboard` – P&L, offene Positionen, Top-5 Z1, Exit-Warnungen
- [x] `backend/api/history.py`
  - `GET /api/history/trades` – Trade-Archiv (SELL-Transaktionen)
  - `GET /api/history/signal-quality` – Trefferquote pro Signaltyp
  - `GET /api/history/summary` – aggregierte P&L-Kennzahlen
- [x] `backend/api/scan.py`
  - `POST /api/scan/trigger` – Scan als Background-Task starten (HTTP 202)
  - `GET /api/scan/status` – Fortschritt + letzter Abschluss
  - `POST /api/scan/ticker/{ticker}` – Einzel-Ticker synchron scannen
- [x] `backend/api/config.py`
  - `GET /api/config` – alle Einstellungen
  - `PUT /api/config` – PATCH-Semantik, Gewichtungs-Validierung
  - `GET /api/config/status` – API-Key-Status aller 8 Dienste
  - `GET /api/config/scan-schedule` – Scan-Zeitplan + Zone-4-Rotation-Info
- [x] `backend/api/universe.py`
  - `GET /api/universe` – alle Ticker (aktiv/inaktiv, nach Quelle filtern)
  - `GET /api/universe/stats` – Anzahl pro Quelle
  - `GET /api/universe/search` – Reserve-Suche (is_active=0)
  - `POST /api/universe/add` – Ticker manuell hinzufügen (WATCHLIST)
  - `DELETE /api/universe/{ticker}` – deaktivieren (Scores bleiben erhalten)
  - `POST /api/universe/refresh` – Wikipedia + AV LISTING_STATUS aktualisieren

### Scheduler
- [x] `backend/scheduler/priority_queue.py` – Tier-Reihenfolge + Zone-4-Rotation
- [x] `backend/scheduler/jobs.py`
  - `job_daily_scan()` – tägl. 06:00 UTC
  - `job_check_exit_signals()` – tägl. 06:30 UTC
  - `job_send_notifications()` – tägl. 07:00 UTC
  - `job_weekly_maintenance()` – So 02:00 UTC (Cache + Wikipedia-Refresh)

### Notifications
- [x] `backend/notifications/telegram.py`
  - `notify_zone_change()` – Zonenänderung
  - `notify_delta_spike()` – Δ1T-Spike ≥ alert_delta_1d
  - `notify_streak_7d()` – 7-Tage-Aufwärtstrend
  - `notify_exit_signal()` – EXIT-Warnung
  - `send_daily_summary()` – Tages-Zusammenfassung
  - `dispatch_scan_notifications()` – Post-Scan-Dispatcher
  - `send_test_message()` – Verbindungstest

**Abschluss-Kriterium ✅:**
1. `POST /api/scan/trigger` startet Scan (HTTP 202)
2. `GET /api/watchlist` liefert Ergebnisse
3. `GET /api/config/status` zeigt API-Key-Statusübersicht
4. Scheduler läuft (`GET /health` zeigt Scheduler-Info)

---

## 📋 Spätere Phasen

### Phase 4 – Backtesting
- [ ] `backend/backtesting/historical_data.py` – OHLCV + Fundamentals für Vergangenheit
- [ ] `backend/backtesting/engine.py` – Score für jeden historischen Tag berechnen
- [ ] `backend/backtesting/signal_mapper.py` – Signal-Events auf Zeitstrahl projizieren
- [ ] `backend/api/backtest.py` – `POST /api/backtest` Endpunkt

### Phase 5 – Frontend
- [ ] Vite + React + TypeScript scaffolden
- [ ] 7 Seiten: Dashboard, Watchlist, Signal-Detail, Portfolio, Trade-Historie, Backtest, **Konfiguration**
- [ ] Konfigurationsseite:
  - [ ] Universe-Refresh-Button (Wikipedia + AV LISTING_STATUS)
  - [ ] Manueller Ticker-Input (Suche + Hinzufügen)
  - [ ] API-Key-Status-Übersicht (grün/rot pro Dienst)
  - [ ] Scoring-Gewichtungen anpassen (40/35/25)
  - [ ] Scan-Zeitplan + Rotation-Größe konfigurieren
  - [ ] Alert-Schwellenwerte (Zone-Grenzen, Delta-Schwellen, Exit-Schwellen)

---

## Bekannte Einschränkungen

| Einschränkung | Details |
|---------------|---------|
| Alpha Vantage 25/Tag + 5/Min | RSI via AV (free), MACD via ta-Bibliothek |
| AV MACD ist Premium | Kein Verlust: ta-Bibliothek berechnet MACD aus yfinance-OHLCV |
| Ticker-Listen Stand Q1 2025 | Wikipedia-Fetch auf eigenem Rechner hält Listen aktuell |
| Optionsschein-Stammdaten | Kein Free-API → ISIN + KO manuell eintragen |
| Historisches Sentiment | Für Backtesting: neutral 12,5/25 |
| DAX-Ticker mit .DE-Suffix | Sonderbehandlung in yfinance erforderlich |
| Unrealized P&L | Warrant-Preis nicht via API verfügbar – muss manuell nachgetragen werden |
