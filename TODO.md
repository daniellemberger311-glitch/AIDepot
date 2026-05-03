# AIDepot – Offene Aufgaben & Fortschritt

Zuletzt aktualisiert: 2026-05-03

---

## Aktueller Stand

**Phase:** 3 – API-Endpunkte + Scheduler (Phase 2 abgeschlossen ✅)  
**Branch:** `claude/stock-options-analyzer-umA6s`  
**Gesamtfortschritt:** ~60 %

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

## ✅ Phase 2 – Scoring-Engine (abgeschlossen)

- [x] `backend/scoring/fundamental.py` – 7 Kriterien, max. 40 Punkte
- [x] `backend/scoring/technical.py` – VCP + 6 Indikatoren (ta-Bibliothek), max. 35 Punkte
- [x] `backend/scoring/sentiment.py` – 4 Kriterien + Unterdrückungslogik, max. 25 Punkte
- [x] `backend/scoring/delta.py` – Δ1T, Δ7T, Δ30T aus score_history
- [x] `backend/scoring/options.py` – OS-Parameter-Ableitung (Hebel, Laufzeit, KO, Entry, SL)
- [x] `backend/scoring/orchestrator.py` – Hauptkoordinator, schreibt in alle 4 Tabellen

**Abschluss-Kriterium ✅:** `orchestrator.score_ticker("AAPL")` gibt Score 39/100 (Zone 4) zurück und hat daily_scores, score_history, score_breakdown, watchlist korrekt befüllt.

Test-Ergebnis (ohne Finnhub/SimFin/Marketaux-Keys, nur yfinance + AV):
- L1 Fundamental: 15/40 | L2 Technical: 17/35 | L3 Sentiment: 7/25
- VCP: 4 Pkt (1 Kontraktion), RSI in Zone: 5 Pkt, MACD positiv+steigend: 3 Pkt

---

## 📋 Spätere Phasen

### Phase 3 – API + Scheduler + Konfigurationsmodul (als nächstes)
- [ ] `backend/api/watchlist.py` – GET /api/watchlist?zone=&sort=
- [ ] `backend/api/signals.py` – GET /api/signals/{ticker}
- [ ] `backend/api/portfolio.py` – CRUD Positionen + Transaktionen
- [ ] `backend/api/dashboard.py` – GET /api/dashboard
- [ ] `backend/api/history.py` – GET /api/history/trades + signal-quality
- [ ] `backend/api/scan.py` – POST /api/scan/trigger (manueller Scan)
- [ ] `backend/api/config.py` – GET/PUT /api/config (Gewichtungen, Zonen-Grenzen, Alerts)
- [ ] `backend/api/universe.py` – POST/DELETE /api/universe/ticker (manuell hinzufügen/entfernen)
- [ ] `backend/scheduler/jobs.py` – APScheduler 06:00 UTC + Quota-Reset + Tier-Rotation
- [ ] `backend/scheduler/priority_queue.py` – Tier-Priorisierung (Zone 0 → 1 → 2 → 3/4)
- [ ] `backend/notifications/telegram.py` – alle 4 Benachrichtigungstypen

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
