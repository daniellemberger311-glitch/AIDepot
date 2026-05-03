# Architektur-Übersicht

## System-Diagramm

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  Dashboard │ Watchlist │ Signal-Detail │ Portfolio │ Backtest   │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP / JSON (localhost:8000)
┌─────────────────────▼───────────────────────────────────────────┐
│                    BACKEND (FastAPI)                             │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ /watchlist│  │/signals  │  │/portfolio │  │  /backtest   │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  │
│       └─────────────┴──────────┬────┘                │          │
│                                 │                     │          │
│  ┌──────────────────────────────▼─────────────────────▼───────┐ │
│  │                   SCORING ENGINE                            │ │
│  │  Ebene 1: Fundamental (40%)                                 │ │
│  │  Ebene 2: Technisch    (35%) – VCP-Kern                     │ │
│  │  Ebene 3: Sentiment    (25%) + Unterdrückungslogik          │ │
│  │  Delta-Berechnung: Δ1T / Δ7T / Δ30T                        │ │
│  └─────────────────────────┬───────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │                    FETCHER-SCHICHT                        │   │
│  │  yfinance │ Finnhub │ AlphaVantage │ StockTwits │ ...    │   │
│  │  BaseFetcher: Cache-Check → API-Call → Cache-Set          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │  APScheduler │  │  Cache (SQLite)  │  │  Telegram-Bot   │  │
│  │  06:00 UTC   │  │  + In-Memory    │  │  Notifications  │  │
│  └──────────────┘  └─────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   SQLite-Datenbank  │
                    │   data/aidepot.db   │
                    └────────────────────┘
```

## Zwei Workflows

### Workflow A – Täglicher Scanner (06:00 UTC)

```
1. StockTwits Trending → Universe aktualisieren
2. Prioritätswarteschlange bauen:
   Tier 0: Offene Positionen (immer)
   Tier 1: Zone-1-Aktien
   Tier 2: Zone-2-Aktien
   Tier 3: Zone-3-Aktien
   Tier 4: Zone-4-Rotation (200/Tag)
3. Pro Ticker: Fetchers → Scoring → Δ berechnen → Zone zuweisen
4. Notifications: Zonenwechsel, Δ-Spikes, 7T-Trends
5. Optionsschein-Empfehlung bei Zone 1
```

### Workflow B – Bestandsbeobachtung (nach Scan)

```
1. Alle offenen Positionen laden
2. Pro Position:
   - Score heute vs. Kaufzeitpunkt
   - KO-Abstand berechnen
   - Restlaufzeit prüfen
   - Sentiment-Status prüfen
3. Exit-Signale generieren (4 Typen)
4. 🔴 Kritische Signale → Telegram sofort
5. Signal-Qualitäts-Update (Trades > 30 Tage alt)
```

## Schichtenmodell

| Schicht | Verantwortung | Dateien |
|---------|---------------|---------|
| Präsentation | React UI, Routing | `frontend/src/pages/` |
| API | REST-Endpunkte, Validierung | `backend/api/` |
| Domäne | Scoring, Signale, Options-Logik | `backend/scoring/` |
| Datenzugriff | Fetcher, Cache | `backend/fetchers/`, `backend/cache/` |
| Infrastruktur | DB, Scheduler, Telegram | `backend/database.py`, `backend/scheduler/` |

## Datenfluss (Scoring)

```
yfinance OHLCV (4h gecacht)
    │
    ▼
technical.py → VCP-Score + RSI + MACD + Bollinger + ATR + RS
    │
Finnhub / SimFin (24h gecacht)
    │
    ▼
fundamental.py → KGV + EPS + FCF + Insider + Earnings-Nähe
    │
StockTwits / ApeWisdom / Finnhub News (2h gecacht)
    │
    ▼
sentiment.py → News + Ratio + Reddit + Analyst-Delta
    │           → Unterdrückungscheck
    ▼
orchestrator.py → Gewichtete Summe → Score 0–100 → Zone
    │
    ▼
delta.py → Δ1T / Δ7T / Δ30T aus score_history
    │
    ▼
options.py → Hebel / Laufzeit / KO-Abstand / Entry / SL (nur Zone 1)
    │
    ▼
SQLite: daily_scores + score_history + score_breakdown + options_recommendations
```
