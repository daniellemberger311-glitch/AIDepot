# Architektur-Übersicht

Zuletzt aktualisiert: 2026-05-04

---

## System-Diagramm

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React, gebaut)                        │
│  Dashboard │ Watchlist │ Signal-Detail │ Portfolio │ Config + Logs   │
│            Browser → http://<IP>:8000                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────────────┐
│                      BACKEND (FastAPI, Port 8000)                    │
│                                                                      │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ /watchlist │  │ /signals   │  │ /portfolio  │  │ /backtest   │  │
│  │ /dashboard │  │ /history   │  │ /scan       │  │ /config     │  │
│  └─────┬──────┘  └─────┬──────┘  └──────┬──────┘  └──────┬──────┘  │
│        └───────────────┴─────────────┬──┘                 │         │
│                                      │                     │         │
│  ┌───────────────────────────────────▼─────────────────────▼──────┐  │
│  │                      SCORING ENGINE                             │  │
│  │  L1 Fundamental (40%)  – 7 Kriterien, max. 40 Pkt.             │  │
│  │  L2 Technisch   (35%)  – VCP-Kern + 6 Indikatoren, max. 35 Pkt.│  │
│  │  L3 Sentiment   (25%)  – 4 Quellen + Unterdrückungsregel        │  │
│  │  Delta: Δ1T / Δ7T / Δ30T | Options-Empfehlung (Zone 1)         │  │
│  └─────────────────────────────┬───────────────────────────────────┘  │
│                                │                                      │
│  ┌─────────────────────────────▼────────────────────────────────┐    │
│  │                   FETCHER-SCHICHT (8 Adapter)                 │    │
│  │  yfinance │ Finnhub │ AlphaVantage │ Marketaux │ SimFin       │    │
│  │  StockTwits │ ApeWisdom │ Wikipedia                           │    │
│  │  BaseFetcher: Cache-Check → API-Call → Cache-Set              │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────────┐    │
│  │ APScheduler  │  │ Cache (SQLite   │  │ Telegram-Bot          │    │
│  │ 06:00 UTC    │  │ + In-Memory)    │  │ (optional)            │    │
│  └──────────────┘  └─────────────────┘  └──────────────────────┘    │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │ MemoryLogHandler → GET/DELETE /api/logs (Ringpuffer 1000)  │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │ StaticFiles → frontend/dist/ (gebautes React-Bundle)       │      │
│  │ SPA-Fallback → index.html für alle unbekannten Pfade        │      │
│  └────────────────────────────────────────────────────────────┘      │
└───────────────────────────────────────────────────────────────────────┘
                               │
                   ┌───────────▼──────────┐
                   │  SQLite-Datenbank     │
                   │  data/aidepot.db      │
                   │  Migrationen: Alembic │
                   └──────────────────────┘

        systemd ─────── aidepot.service (Restart=on-failure)
                ─────── aidepot-backup.timer (täglich 03:00 UTC)
```

---

## Zwei Workflows

### Workflow A – Täglicher Scanner (06:00 UTC)

```
1. Prioritätswarteschlange bauen:
   Tier 0: Offene Positionen (~5–20)  → täglich, alle APIs
   Tier 1: Zone 1+2 (~150)           → täglich, alle APIs (AV nur Top 10)
   Tier 2: Zone 3 (~200)             → täglich, yfinance + StockTwits + ApeWisdom
   Tier 3: Zone 4 Rotation (200/Tag) → nur yfinance + ta-Bibliothek
2. Pro Ticker: Fetchers → Scoring → Δ berechnen → Zone zuweisen
3. close_price + currency aus yfinance speichern
4. Optionsschein-Empfehlung bei Zone 1
5. Notifications: Zonenwechsel, Δ-Spikes, 7T-Trends
```

### Workflow B – Bestandsbeobachtung (06:30 UTC, nach Scan)

```
1. Alle offenen Positionen laden
2. Pro Position:
   - Score heute vs. Kaufzeitpunkt
   - KO-Abstand berechnen
   - Restlaufzeit prüfen
   - Sentiment-Status prüfen
3. Exit-Signale generieren (4 Typen: Score-Drop, KO, Restlaufzeit, Sentiment)
4. Kritische Signale → Telegram sofort
5. Signal-Qualitäts-Update (Trades > 30 Tage alt)
```

---

## Schichtenmodell

| Schicht | Verantwortung | Dateien |
|---------|---------------|---------|
| Präsentation | React UI, Routing | `frontend/src/pages/`, `frontend/src/components/` |
| API | REST-Endpunkte, Validierung (Pydantic) | `backend/api/` |
| Domäne | Scoring, Signale, Options-Logik | `backend/scoring/` |
| Datenzugriff | Fetcher, TTL-Cache | `backend/fetchers/`, `backend/cache/` |
| Infrastruktur | DB, Scheduler, Telegram, Logs | `backend/database.py`, `backend/scheduler/`, `backend/notifications/`, `backend/log_handler.py` |
| Tests | Scoring-Engine Unit-Tests | `tests/scoring/`, `tests/test_orchestrator.py` |

---

## Datenfluss (Scoring)

```
yfinance OHLCV (4h gecacht) ────────────────────────────────────┐
                                                                  │
    ▼                                                            │
technical.py                                                     │
  → VCP-Score (20W Wochenchart, Swing-Highs, Kontraktion)       │
  → RSI (ta, 14T), MACD (ta), Bollinger (ta)                    │
  → Volumen-Kontraktion (3W vs. 10W)                            │
  → Relative Stärke vs. SPY (20T)                               │
  → Preis vs. 52W-Hoch                                          │
                                                                  │
Finnhub + SimFin (24h gecacht) ──────────────────────────────────┤
    │                                                             │
    ▼                                                             │
fundamental.py                                                   │
  → KGV vs. Sektorschnitt                                       │
  → EPS-Beat-Streak, Umsatzwachstum                             │
  → FCF positiv/wachsend, D/E-Ratio                             │
  → Insider-Netto (90T), Earnings-Nähe                          │
                                                                  │
StockTwits + ApeWisdom + Finnhub News + Marketaux (1–2h gecacht) │
    │                                                             │
    ▼                                                             │
sentiment.py                                                     │
  → News-Sentiment (Ø Finnhub + Marketaux)                      │
  → StockTwits Bullish-Ratio                                    │
  → Reddit-Mention-Momentum (ApeWisdom)                         │
  → Analysten-Delta (Netto-Upgrades 30T)                        │
  → Unterdrückungscheck (L1+L2 > 50 und L3 < 5 → max. 74)      │
                                                                  │
                          ◄──────────────────────────────────────┘
    ▼
orchestrator.py
  → Gewichtete Summe → Score 0–100 → Zone 1–4
  → close_price + currency aus yfinance-Metadaten
    │
    ▼
delta.py → Δ1T / Δ7T / Δ30T aus score_history
    │
    ▼
options.py → Hebel / Laufzeit / KO-Abstand / Entry / SL (nur Zone 1, ATR-basiert)
    │
    ▼
SQLite:
  daily_scores        ← Hauptergebnis inkl. close_price, currency
  score_history       ← Zeitreihe für Δ-Berechnung + 30T-Chart
  score_breakdown     ← Alle 18 Einzelkriterien
  options_recommendations ← OS-Empfehlung
```

---

## Produktions-Setup

```
Linux-PC (headless, Heimnetz)
  │
  ├── systemd: aidepot.service
  │     uvicorn backend.main:app --host 0.0.0.0 --port 8000
  │     → FastAPI serviert /api/... und frontend/dist/ über Port 8000
  │     → APScheduler läuft im selben Prozess
  │
  ├── systemd: aidepot-backup.timer (03:00 UTC täglich)
  │     → sqlite3 ".backup '/path/data/backups/aidepot_YYYYMMDD.db'"
  │     → 7 rotierende Kopien
  │
  └── update.sh (manuell bei Bedarf)
        git pull → pip → pytest → alembic upgrade → npm build → restart
```

---

## Datenbank-Schema (13 Tabellen)

| Tabelle | Inhalt |
|---------|--------|
| `stocks` | Stammdaten (ticker, name, sector, industry, exchange) |
| `daily_scores` | Letzter Score-Stand je Ticker (close_price, currency) |
| `score_history` | Zeitreihe aller Scores (für Charts + Δ-Berechnung) |
| `score_breakdown` | 18 Einzelkriterien je Scoring-Lauf |
| `watchlist` | Aktive Zone-1/2-Einträge |
| `options_recommendations` | OS-Empfehlungen je Zone-1-Signal |
| `positions` | Portfolio-Positionen (offen + geschlossen) |
| `transactions` | Kauf-/Verkauf-Buchungen |
| `exit_signals` | Generierte Exit-Warnungen |
| `notifications_log` | Versendete Telegram-Nachrichten |
| `signal_quality` | Aggregierte Trefferquoten je Signaltyp |
| `api_cache` | TTL-Cache für alle Fetcher-Ergebnisse |
| `configuration` | App-Einstellungen (Key-Value-Store) |
