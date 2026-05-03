# AIDepot – Offene Aufgaben & Fortschritt

Zuletzt aktualisiert: 2025-05-03

---

## Aktueller Stand

**Phase:** 2 – Scoring-Engine (Phase 1 abgeschlossen ✅)  
**Branch:** `claude/stock-options-analyzer-umA6s`  
**Gesamtfortschritt:** ~40 %

**Universum:** 703 aktive Ticker (SP500/NASDAQ100/RUSSELL200/Watchlist) + 6.243 Reserve (NYSE/NASDAQ via AV LISTING_STATUS, is_active=0)

---

## 🔑 Offene API-Keys (bevor der Live-Scan funktioniert)

| Dienst | Umgebungsvariable | Wo beantragen | Limit Free Tier | Status |
|--------|------------------|---------------|-----------------|--------|
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | alphavantage.co | 25/Tag, 5/Min | ✅ eingetragen |
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
  - Wikipedia-Fetch (funktioniert auf eigenem Rechner, wöchentliche Aktualisierung)
  - ⚠️ Listen sind Stand Q1 2025 – mit Wikipedia-Fetch auf eigenem Rechner aktualisierbar

### Test
- [x] `scripts/test_fetchers.py` – alle 8 Quellen ✅

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

### Phase 3 – API + Scheduler + Konfigurationsmodul
- [ ] API-Router: `watchlist`, `signals`, `portfolio`, `dashboard`, `history`, `scan`, `backtest`
- [ ] `backend/api/config.py` – vollständiges Konfigurationsmodul (siehe Roadmap)
- [ ] `backend/api/universe.py` – Universum-Verwaltung inkl. manueller Ticker-Eingabe
- [ ] `backend/scheduler/jobs.py` – APScheduler 06:00 UTC + Wochenplan-Rotation
- [ ] `backend/scheduler/priority_queue.py` – Tier-Rotation (Mindestfrequenz: wöchentlich)
- [ ] `backend/notifications/telegram.py`
- [ ] `backend/universe/loader.py` erweitern:
  - [ ] DAX 40 (.DE-Ticker) als optionale Quelle
  - [ ] S&P 400 Mid Cap (Wachstums-Aktien vor S&P-500-Aufnahme)
  - [ ] Scan-Rotation so konfigurieren, dass alle Aktien min. 1x/Woche gescannt werden

### Phase 4 – Backtesting
- [ ] `backend/backtesting/` (3 Module + API-Endpunkt)

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
