# AIDepot – Entwicklungs-Roadmap

Zuletzt aktualisiert: 2025-05-03  
Branch: `claude/stock-options-analyzer-umA6s`

---

## Übersicht

```
Phase 1 │ Backend-Fundament     │ ~25% fertig   │ Aktiv
Phase 2 │ Scoring-Engine        │ 0%            │ Als nächstes
Phase 3 │ API + Automatisierung │ 0%            │ Folgt auf Phase 2
Phase 4 │ Backtesting-Modul     │ 0%            │ Nach Phase 3
Phase 5 │ Frontend              │ 0%            │ Parallel zu Phase 3/4
```

**Meilenstein „Erster lauffähiger Scan":** Ende Phase 3  
**Meilenstein „Vollständige App":** Ende Phase 5

---

## Phase 1 – Backend-Fundament

**Ziel:** Alle Datenquellen angebunden, Datenbank läuft, Backend startet fehlerfrei.

### ✅ Bereits erledigt

| Datei | Beschreibung |
|-------|-------------|
| `backend/config.py` | Pydantic BaseSettings, liest `.env` |
| `backend/database.py` | SQLite-Engine, Session-Factory, `init_db()` |
| `backend/models.py` | 13 SQLAlchemy ORM-Modelle |
| `backend/schemas.py` | Alle Pydantic Request/Response-Typen |
| `backend/main.py` | FastAPI-App, CORS, Lifespan |
| `backend/cache/store.py` | TTL-Cache (In-Memory + SQLite) |
| `backend/fetchers/base.py` | BaseFetcher: Cache-Lookup, Retry-Dekorator |
| `backend/fetchers/yfinance_fetcher.py` | OHLCV, Fundamentals, Earnings, Insider |
| `backend/fetchers/stocktwits_fetcher.py` | Bullish-Ratio, Trending Tickers |
| `backend/fetchers/apewisdom_fetcher.py` | Reddit-Mentions |
| `backend/fetchers/finnhub_fetcher.py` | News-Sentiment, Insider, Earnings, Analyst-Ratings |
| `scripts/init_db.py` | DB-Initialisierung mit Startkonfiguration |

### ⏳ Noch offen

| Schritt | Datei | Aufwand | Priorität |
|---------|-------|---------|-----------|
| 1.1 | `backend/fetchers/alphavantage_fetcher.py` | Klein | Mittel – 25/Tag-Limit beachten |
| 1.2 | `backend/fetchers/marketaux_fetcher.py` | Klein | Mittel |
| 1.3 | `backend/fetchers/simfin_fetcher.py` | Klein | Mittel |
| 1.4 | `backend/universe/loader.py` | Mittel | Hoch – wird von Scheduler benötigt |
| 1.5 | `scripts/test_fetchers.py` | Klein | Smoke-Test vor Phase 2 |

**Abschluss-Kriterium:** `python scripts/test_fetchers.py AAPL` zeigt Daten aus allen Quellen ohne Fehler.

---

## Phase 2 – Scoring-Engine

**Ziel:** Jeder Ticker erhält täglich einen validen Score 0–100 mit vollständiger Aufschlüsselung.  
**Abhängigkeit:** Phase 1 vollständig abgeschlossen.

### Schritte (in dieser Reihenfolge)

| Schritt | Datei | Beschreibung | Aufwand |
|---------|-------|-------------|---------|
| 2.1 | `backend/scoring/fundamental.py` | 7 Kriterien, max. 40 Punkte | Mittel |
| 2.2 | `backend/scoring/technical.py` | VCP + 6 Indikatoren, max. 35 Punkte | Groß |
| 2.3 | `backend/scoring/sentiment.py` | 4 Kriterien + Unterdrückungslogik, max. 25 Punkte | Mittel |
| 2.4 | `backend/scoring/delta.py` | Δ1T, Δ7T, Δ30T aus `score_history` | Klein |
| 2.5 | `backend/scoring/options.py` | OS-Parameter-Ableitung (nur Zone 1) | Klein |
| 2.6 | `backend/scoring/orchestrator.py` | Hauptkoordinator, schreibt in DB | Mittel |

### Scoring-Logik im Detail

**Ebene 1 – Fundamental (max. 40 Punkte)**

| Kriterium | Punkte | Formel |
|-----------|--------|--------|
| KGV vs. Sektorschnitt | 0–8 | <0,75x → 8; <1,0x → 6; <1,25x → 4; >1,5x → 0 |
| EPS-Beat-Streak | 0–6 | +2 pro Beat, max. 3 Quartale |
| Umsatzwachstum YoY | 0–6 | >20% → 6; 10–20% → 4; 0–10% → 2; negativ → 0 |
| FCF positiv + wachsend | 0–5 | FCF > 0 → 2; YoY gewachsen → +3 |
| Verschuldungsgrad D/E | 0–5 | <0,5 → 5; 0,5–1,0 → 3; 1,0–2,0 → 1; >2,0 → 0 |
| Insider-Käufe netto (90T) | 0–5 | ≥3 Käufe → 5; 1–2 → 3; neutral → 1; Verkäufe → 0 |
| Earnings-Nähe | 0–5 | 7–14 Tage → 5; 3–7 Tage → 3; >14 Tage → 1 |

**Ebene 2 – Technisch (max. 35 Punkte)**

| Kriterium | Punkte | Formel |
|-----------|--------|--------|
| VCP-Muster | 0–10 | 3 Kontraktionen → 10; 2 → 7; 1 + Vol↓ → 4 |
| Volumen-Kontraktion | 0–5 | 3W-Ø < 80% des 10W-Ø → 5; <90% → 3 |
| Preis-Nähe zu Widerstand | 0–5 | <3% → 5; 3–7% → 3; >10% → 0 |
| RSI 55–70 | 0–5 | 55–70 → 5; 50–55 od. 70–75 → 3; sonst 0 |
| Relative Stärke vs. SPY | 0–4 | RS > 1,1 (20T) → 4; 1,0–1,1 → 2; <1,0 → 0 |
| MACD-Signal | 0–3 | Histogramm positiv + steigend → 3; flach → 1 |
| Bollinger-Squeeze | 0–3 | BB-Breite < 20. Perzentil (52W) → 3 |

**VCP-Erkennung (Kern des technischen Scores):**
- Swing-Hochs der letzten 20 Wochen identifizieren
- Jede Korrektur kleiner als vorherige (Verhältnis < 0,85)
- Volumen in Down-Wochen sinkt progressiv
- Kurs innerhalb 10% des 52-Wochen-Hochs
- Implementierung: `ta`-Bibliothek + manuelle Pivot-Berechnung auf yfinance-OHLCV

**Ebene 3 – Sentiment (max. 25 Punkte)**

| Kriterium | Punkte | Formel |
|-----------|--------|--------|
| News-Sentiment | 0–8 | Ø Finnhub + Marketaux: >0,6 → 8; 0,3–0,6 → 5; 0–0,3 → 2; negativ → 0 |
| StockTwits Bullish-Ratio | 0–7 | >65% → 7; 55–65% → 5; 45–55% → 3; <45% → 0 |
| Reddit-Momentum | 0–5 | +50% vs. 7T-Ø → 5; +20–50% → 3; flach → 1 |
| Analysten-Delta | 0–5 | ≥2 Netto-Upgrades → 5; 1 → 3; neutral → 1; Downgrade → 0 |

**Unterdrückungsregel:**  
Wenn L1 + L2 > 50 UND L3 < 5 → Score auf max. 74 gedeckelt (kein Zone-1-Eintrag).

**Abschluss-Kriterium:** `orchestrator.score_ticker("AAPL")` schreibt valide Zeile in `daily_scores` + `score_history` + `score_breakdown`.

---

## Phase 3 – API-Endpunkte & Automatisierung

**Ziel:** Backend vollständig nutzbar, täglicher Scan läuft automatisch, Telegram-Nachrichten kommen an.  
**Abhängigkeit:** Phase 2 abgeschlossen.

### API-Endpunkte

| Schritt | Datei | Endpunkte |
|---------|-------|----------|
| 3.1 | `backend/api/router.py` | Alle Router zusammenführen |
| 3.2 | `backend/api/watchlist.py` | `GET /api/watchlist` |
| 3.3 | `backend/api/signals.py` | `GET /api/signals/{ticker}` |
| 3.4 | `backend/api/portfolio.py` | CRUD Positionen, Exit-Signale |
| 3.5 | `backend/api/dashboard.py` | `GET /api/dashboard` |
| 3.6 | `backend/api/history.py` | Trades, Signalqualität |
| 3.7 | `backend/api/scan.py` | Manueller Scan-Trigger |
| 3.8 | `backend/api/config.py` | Konfiguration lesen/schreiben |
| 3.9 | `backend/api/universe.py` | Universum verwalten |

### Automatisierung

| Schritt | Datei | Beschreibung |
|---------|-------|-------------|
| 3.10 | `backend/scheduler/priority_queue.py` | Priorisierte Scan-Reihenfolge (Tier 0–4) |
| 3.11 | `backend/scheduler/jobs.py` | APScheduler: 06:00 UTC Scan + Portfolio-Monitor |
| 3.12 | `backend/notifications/telegram.py` | Bot-Sender + alle Nachrichten-Templates |

### Notification-Templates

```
📈 ZONEN-WECHSEL: {ticker} Z{alt}→Z{neu}  Score: {score} | Δ7T: +{x}
⚡ KATALYSATOR: {ticker}  Score +{x} an einem Tag → {score}
🔨 AUFBAU: {ticker}  7-Tage-Trend steigt seit {n} Tagen  Δ7T: +{x}
⚠️ EXIT: {ticker} [{signal_typ}]  Score: {alt}→{neu} | KO-Abstand: {pct}%
📊 TAGES-ZUSAMMENFASSUNG  Top-5 Zone 1 + {n} Exit-Warnungen
```

**Abschluss-Kriterium:**
1. `curl -X POST localhost:8000/api/scan/trigger` startet Scan
2. Watchlist unter `GET /api/watchlist` zeigt Ergebnisse
3. Telegram-Nachricht kommt nach Scan an

---

## Phase 4 – Backtesting-Modul

**Ziel:** Nutzer gibt Ticker + Zeitraum ein, sieht wann welche Signale aufgetreten wären.  
**Abhängigkeit:** Phase 2 (Scoring-Engine) abgeschlossen.

### Schritte

| Schritt | Datei | Beschreibung |
|---------|-------|-------------|
| 4.1 | `backend/backtesting/historical_data.py` | OHLCV + Fundamentals für Vergangenheit laden |
| 4.2 | `backend/backtesting/engine.py` | Score für jeden historischen Tag berechnen |
| 4.3 | `backend/backtesting/signal_mapper.py` | Signal-Events auf Zeitstrahl projizieren |
| 4.4 | `backend/api/backtest.py` | `POST /api/backtest` Endpunkt |

### Einschränkungen

- **Sentiment historisch nicht verfügbar** → neutraler Wert 12,5/25 für alle Vergangenheitsdaten
- **Kein Transaktions-Simulator** → nur Signal-Zeitstrahl, keine automatische P&L
- **Alpha-Vantage-Limit** nicht betroffen (nur yfinance + `ta`)

### Darstellung im Frontend (Phase 5)

```
[Ticker]  [Von]  [Bis]  [Berechnen]

Kurs-Chart ─────────────────────────────────────────────
  📈Z3→Z2    ⚡Δ1T+18    📈Z2→Z1    🔨7T-Trend
    ↓           ↓           ↓           ↓
Score-Verlauf 0–100 (Zonen als farbige Hintergrundbänder)
Signal-Zeitstrahl mit Icons pro Event-Typ
```

**Abschluss-Kriterium:** `POST /api/backtest { "ticker": "NVDA", "from_date": "2024-01-01", "to_date": "2025-05-01" }` gibt valide Score-Zeitreihe + Signal-Events zurück.

---

## Phase 5 – Frontend

**Ziel:** Vollständige React-App mit allen 6 Seiten.  
**Abhängigkeit:** Phase 3 API-Endpunkte abgeschlossen (kann parallel entwickelt werden).

### Schritt 5.1 – Scaffolding & Konfiguration

```bash
cd AIDepot
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install @tanstack/react-query react-router-dom recharts axios \
            tailwindcss @tailwindcss/vite date-fns \
            react-hook-form zod lucide-react
```

**Konfiguration:**
- `vite.config.ts`: Proxy `/api/**` → `localhost:8000`
- Tailwind initialisieren
- React Router v6 einrichten

### Schritt 5.2 – Gemeinsame Komponenten

| Komponente | Beschreibung |
|-----------|-------------|
| `ScoreBadge` | Farbige Pille 0–100 (rot/gelb/grün nach Zone) |
| `DeltaBadge` | ±Delta mit ▲/▼-Pfeil und Farbe |
| `ZoneBadge` | Z1/Z2/Z3/Z4-Tag |
| `MiniChart` | Recharts-Sparkline für Score-Verlauf |
| `DataTable` | Sortierbare Tabelle (wiederverwendbar) |
| `Layout` + `Sidebar` + `TopBar` | App-Shell |

### Schritt 5.3 – Seiten

| Seite | Route | Hauptinhalt |
|-------|-------|-------------|
| Dashboard | `/` | P&L-Zusammenfassung, Top-5-Signale, Exit-Warnungen |
| Watchlist | `/watchlist` | 4-Zonen-Tabelle, sortiert nach Δ7T |
| Signal-Detail | `/signal/:ticker` | Score-Aufschlüsselung, 30T-Chart, OS-Empfehlung |
| Portfolio | `/portfolio` | Positionen, Status HALTEN/BEOBACHTEN/EXIT, Kauf/Verkauf |
| Trade-Historie | `/history` | Archiv, P&L-Statistik, Trefferquote pro Signaltyp |
| Backtesting | `/backtest` | Ticker+Zeitraum eingeben, Signal-Zeitstrahl anzeigen |

### Schritt 5.4 – State-Management

**TanStack Query v5** für Server-State (Polling alle 60 Sek. für Portfolio/Dashboard).  
**useState/useReducer** nur für UI-State (Filter, Modal offen/geschlossen).  
Kein Redux – Single-User-App, minimal state needed.

**Abschluss-Kriterium:** Alle 6 Seiten laden echte Daten, Portfolio-CRUD funktioniert, Backtesting-Chart wird gerendert.

---

## Abhängigkeitsgraph

```
Phase 1 (Fetcher + DB)
    │
    ▼
Phase 2 (Scoring-Engine)  ─────────────────────┐
    │                                           │
    ▼                                           │
Phase 3 (API + Scheduler)    Phase 4 (Backtest)─┤
    │                                           │
    └──────────────────────────────────────────▼
                                         Phase 5 (Frontend)
```

Phase 4 und Phase 5 können **parallel** zu Phase 3 entwickelt werden, sobald Phase 2 abgeschlossen ist.

---

## Zeitschätzung (grob)

| Phase | Aufwand | Kumulativ |
|-------|---------|-----------|
| Phase 1 Rest (3 Fetcher + Universe) | ~2h | ~2h |
| Phase 2 (Scoring-Engine) | ~4h | ~6h |
| Phase 3 (API + Scheduler + Telegram) | ~4h | ~10h |
| Phase 4 (Backtesting) | ~2h | ~12h |
| Phase 5 (Frontend) | ~6h | ~18h |

---

## Nächster konkreter Schritt

**→ Phase 1 abschließen:**

1. `backend/fetchers/alphavantage_fetcher.py` – kleiner Fetcher, 25/Tag-Limit beachten
2. `backend/fetchers/marketaux_fetcher.py` – News + Sentiment
3. `backend/fetchers/simfin_fetcher.py` – Fundamentaldaten
4. `backend/universe/loader.py` – S&P 500, NASDAQ 100, Russell 2000 als Liste laden
5. `scripts/test_fetchers.py` – Smoke-Test aller 8 Quellen

Dann direkt in Phase 2 (Scoring-Engine) starten.
