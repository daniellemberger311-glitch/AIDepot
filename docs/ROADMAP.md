# AIDepot – Entwicklungs-Roadmap

Zuletzt aktualisiert: 2026-05-03  
Branch: `claude/stock-options-analyzer-umA6s`

---

## Übersicht

```
Phase 1 │ Backend-Fundament       │ 100% ✅  │ Abgeschlossen
Phase 2 │ Scoring-Engine          │ 100% ✅  │ Abgeschlossen
Phase 3 │ API + Scheduler + Konfig│  15%     │ Aktiv – als nächstes
Phase 4 │ Backtesting-Modul       │   0%     │ Nach Phase 3
Phase 5 │ Frontend (7 Seiten)     │   0%     │ Parallel zu Phase 3/4
```

**Meilenstein „Erster lauffähiger Scan":** Ende Phase 3  
**Meilenstein „Vollständige App":** Ende Phase 5

---

## Phase 1 – Backend-Fundament ✅ ABGESCHLOSSEN

Alle Fetcher, Datenbank, Cache, Universum-Loader fertig.  
Universum: 703 aktive Ticker + 6.243 Reserve (NYSE/NASDAQ). Detailstatus → `TODO.md`.

---

## Phase 2 – Scoring-Engine ✅ ABGESCHLOSSEN

**Ergebnis:** Jeder Ticker erhält täglich einen validen Score 0–100 mit vollständiger Aufschlüsselung.  
Abschluss-Test: `score_ticker("AAPL")` → Score 39/100, Zone 4, alle 4 DB-Tabellen befüllt.

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
| MACD-Signal | 0–3 | Histogramm positiv + steigend → 3; flach → 1 (ta-Bibliothek) |
| Bollinger-Squeeze | 0–3 | BB-Breite < 20. Perzentil (52W) → 3 |

**Ebene 3 – Sentiment (max. 25 Punkte)**

| Kriterium | Punkte | Formel |
|-----------|--------|--------|
| News-Sentiment | 0–8 | Ø Finnhub + Marketaux: >0,6 → 8; 0,3–0,6 → 5; 0–0,3 → 2; negativ → 0 |
| StockTwits Bullish-Ratio | 0–7 | >65% → 7; 55–65% → 5; 45–55% → 3; <45% → 0 |
| Reddit-Momentum | 0–5 | +50% vs. 7T-Ø → 5; +20–50% → 3; flach → 1 |
| Analysten-Delta | 0–5 | ≥2 Netto-Upgrades → 5; 1 → 3; neutral → 1; Downgrade → 0 |

**Unterdrückungsregel:** Wenn L1+L2 > 50 UND L3 < 5 → Score max. 74 (kein Zone-1-Eintrag).

**Abschluss-Kriterium:** `orchestrator.score_ticker("AAPL")` schreibt valide Zeile in `daily_scores` + `score_history` + `score_breakdown`.

---

## Phase 3 – API-Endpunkte, Scheduler & Konfigurationsmodul

**Ziel:** Backend vollständig nutzbar, täglicher Scan läuft automatisch, Telegram-Nachrichten kommen an.  
**Abhängigkeit:** Phase 2 abgeschlossen ✅

### 3.1 – API-Endpunkte

| Schritt | Datei | Endpunkte | Status |
|---------|-------|----------|----|
| 3.0 | `backend/api/router.py` + `backend/api/logs.py` | Basis-Router + GET /api/logs | ✅ fertig |
| 3.2 | `backend/api/watchlist.py` | `GET /api/watchlist` | ⏳ offen |
| 3.3 | `backend/api/signals.py` | `GET /api/signals/{ticker}` | ⏳ offen |
| 3.4 | `backend/api/portfolio.py` | CRUD Positionen, Exit-Signale | ⏳ offen |
| 3.5 | `backend/api/dashboard.py` | `GET /api/dashboard` | ⏳ offen |
| 3.6 | `backend/api/history.py` | Trades, Signalqualität | ⏳ offen |
| 3.7 | `backend/api/scan.py` | Manueller Scan-Trigger | ⏳ offen |
| 3.8 | `backend/api/config.py` | GET/PUT /api/config + /api/config/status | ⏳ offen |
| 3.9 | `backend/api/universe.py` | Universe CRUD + Suche | ⏳ offen |

### 3.2 – Konfigurationsmodul (`backend/api/config.py` + `backend/api/universe.py`)

Das Konfigurationsmodul ist der zentrale Steuerungsbereich der App.

**`GET/PUT /api/config`** – App-Einstellungen:

| Bereich | Parameter | Standard |
|---------|-----------|---------|
| Scoring-Gewichtungen | `weight_fundamental`, `weight_technical`, `weight_sentiment` | 40 / 35 / 25 |
| Zonen-Grenzen | `zone1_min`, `zone2_min`, `zone3_min` | 76 / 61 / 41 |
| Alert-Schwellen | `alert_delta_1d`, `alert_streak_days` | 15 / 3 |
| Exit-Schwellen | `exit_score_drop`, `exit_ko_pct`, `exit_weeks_expiry`, `exit_bull_ratio` | 15 / 8 / 3 / 35 |
| Scan-Zeitplan | `scan_hour_utc`, `scan_minute_utc` | 6 / 0 |
| Rotation | `zone4_batch_size` (Aktien/Tag Zone 4) | 200 |
| Telegram | `telegram_bot_token`, `telegram_chat_id` | – |

**`GET /api/config/status`** – API-Key-Status (grün/rot pro Dienst):
```json
{
  "yfinance":       {"status": "ok",      "note": "kein Key erforderlich"},
  "stocktwits":     {"status": "ok",      "note": "kein Key erforderlich"},
  "apewisdom":      {"status": "ok",      "note": "kein Key erforderlich"},
  "finnhub":        {"status": "missing", "note": "FINNHUB_API_KEY nicht gesetzt"},
  "alpha_vantage":  {"status": "ok",      "remaining_today": 24},
  "marketaux":      {"status": "missing", "note": "MARKETAUX_API_KEY nicht gesetzt"},
  "simfin":         {"status": "missing", "note": "SIMFIN_API_KEY nicht gesetzt"},
  "telegram":       {"status": "missing", "note": "TELEGRAM_BOT_TOKEN nicht gesetzt"}
}
```

**`POST /api/universe/refresh`** – Universe aktualisieren:
- Ruft `load_from_wikipedia()` auf → holt aktuelle S&P 500 + NASDAQ 100 von Wikipedia
- Ruft `load_from_av_listing()` auf → aktualisiert NYSE/NASDAQ-Reserve (1 AV-Credit)
- Gibt zurück: `{added: int, updated: int, total_active: int}`

**`GET /api/universe`** – alle Ticker (aktiv + inaktiv, filterbar nach Quelle)

**`POST /api/universe/add`** – Ticker manuell hinzufügen:
```json
{"ticker": "ASTS", "name": "AST SpaceMobile"}
```
- Legt Ticker mit `universe_source = "WATCHLIST"` und `is_active = 1` an
- Wird automatisch in den regulären Scan-Zyklus aufgenommen
- Erscheint in allen Scan-Tiers wie ein normaler Ticker

**`DELETE /api/universe/{ticker}`** – Ticker deaktivieren (`is_active = 0`):
- Entfernt Ticker aus dem Scan-Zyklus
- Historische Scores bleiben erhalten

**`GET /api/universe/search?q=Tesla`** – Suche in der Reserve-Datenbank (is_active=0):
- Zeigt Treffer aus den 6.243 Reserve-Tickern
- Nutzer kann gefundene Ticker mit einem Klick aktivieren

### 3.3 – Universum-Erweiterung in `loader.py`

Zusätzliche Indizes die beim nächsten Loader-Update aufgenommen werden:

| Index | Ticker-Anzahl | Suffix | Bemerkung |
|-------|--------------|--------|-----------|
| S&P 400 Mid Cap | ~100 relevante | keine | Wachstums-Aktien vor S&P-500-Aufnahme |
| DAX 40 | 40 | `.DE` | Original-Spec: „ergänzend DAX"; yfinance unterstützt `.DE` |
| Dow Jones 30 | 30 | keine | Größtenteils in S&P 500 enthalten, Überschneidung prüfen |

**DAX-Hinweis:** Deutsche Aktien benötigen `.DE`-Suffix bei yfinance (z. B. `SAP.DE`, `SIE.DE`). Der Scorer muss EUR-Kurse akzeptieren; alle relativen Berechnungen (RSI, Momentum, VCP) funktionieren währungsunabhängig. Sentiment-Quellen (StockTwits, ApeWisdom) liefern für DAX-Werte kaum Daten → Sentiment-Score = neutral 12,5/25 für .DE-Ticker.

### 3.4 – Scan-Rotation & Mindestfrequenz

**Ziel: Jede aktive Aktie wird mindestens 1x pro Woche vollständig gescannt.**

```
Tier 0  Gehaltene Positionen (~5–20)   → täglich, alle APIs
Tier 1  Zone 1+2 (~150)               → täglich, alle APIs (AV nur Top 10)
Tier 2  Zone 3 (~200)                  → täglich, yfinance + StockTwits + ApeWisdom
Tier 3  Zone 4 + restliche Aktien      → rotierend, nur yfinance + ta
```

**Rotation Zone 4 (konfigurierbar, Standard: 200 Aktien/Tag):**

| Aktive Ticker Zone 4 | Batch/Tag | Wiederholungsintervall |
|----------------------|-----------|------------------------|
| ~400 (aktuell) | 200 | 2 Tage |
| ~600 (nach Erweiterung) | 200 | 3 Tage |
| ~1.000 (maximale Ausbaustufe) | 200 | 5 Tage |
| ~1.400 (absolute Grenze) | 200 | 7 Tage = wöchentlich |

**→ Mit `zone4_batch_size = 200` ist die wöchentliche Mindestfrequenz für bis zu ~1.400 Zone-4-Aktien garantiert.**

Bei Bedarf `zone4_batch_size` via Konfigurationsseite erhöhen (z. B. 300/Tag für kürzeres Intervall).

**Rotation-Index:** Wird täglich in der `configuration`-Tabelle als `scan_rotation_idx` gespeichert. Bei Neustart setzt der Scan nahtlos an der letzten Position fort.

**Wöchentliche Aufgaben (Scheduler, sonntags 02:00 UTC):**
- Wikipedia-Listen aktualisieren (neue Index-Zusammensetzung)
- AV LISTING_STATUS auffrischen (1 Credit)
- Abgelaufene API-Cache-Einträge löschen

### 3.5 – Automatisierung

| Schritt | Datei | Beschreibung |
|---------|-------|-------------|
| 3.9 | `backend/scheduler/priority_queue.py` | Tier-Reihenfolge + Rotations-Index |
| 3.10 | `backend/scheduler/jobs.py` | Tägl. 06:00 UTC + wöchentl. Sonntag 02:00 UTC |
| 3.11 | `backend/notifications/telegram.py` | Bot-Sender + Templates |

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
2. `GET /api/watchlist` gibt Ergebnisse zurück
3. `GET /api/config/status` zeigt API-Key-Statusübersicht
4. Telegram-Nachricht kommt nach Scan an

---

## Phase 4 – Backtesting-Modul

**Ziel:** Ticker + Zeitraum eingeben → sehen, wann welche Signale aufgetreten wären.  
**Abhängigkeit:** Phase 2 (Scoring-Engine) abgeschlossen.

| Schritt | Datei | Beschreibung |
|---------|-------|-------------|
| 4.1 | `backend/backtesting/historical_data.py` | OHLCV + Fundamentals für Vergangenheit |
| 4.2 | `backend/backtesting/engine.py` | Score für jeden historischen Tag berechnen |
| 4.3 | `backend/backtesting/signal_mapper.py` | Signal-Events auf Zeitstrahl projizieren |
| 4.4 | `backend/api/backtest.py` | `POST /api/backtest` Endpunkt |

**Einschränkungen:** Historisches Sentiment nicht verfügbar → neutral 12,5/25. Kein P&L-Simulator (nur Signal-Zeitstrahl).

**Darstellung:**
```
[Ticker]  [Von]  [Bis]  [Berechnen]

Kurs-Chart ─────────────────────────────────────────────
  📈Z3→Z2    ⚡Δ1T+18    📈Z2→Z1    🔨7T-Trend
    ↓           ↓           ↓           ↓
Score-Verlauf 0–100 (Zonen als farbige Hintergrundbänder)
Signal-Zeitstrahl mit Icons pro Event-Typ
```

---

## Phase 5 – Frontend (7 Seiten)

**Ziel:** Vollständige React-App mit allen Seiten.  
**Abhängigkeit:** Phase 3 API-Endpunkte abgeschlossen (kann parallel entwickelt werden).

### Setup

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install @tanstack/react-query react-router-dom recharts axios \
            tailwindcss @tailwindcss/vite date-fns \
            react-hook-form zod lucide-react
```

### Seiten

| Seite | Route | Hauptinhalt |
|-------|-------|-------------|
| Dashboard | `/` | P&L-Zusammenfassung, Top-5-Signale, Exit-Warnungen |
| Watchlist | `/watchlist` | 4-Zonen-Tabelle, sortiert nach Δ7T |
| Signal-Detail | `/signal/:ticker` | Score-Aufschlüsselung, 30T-Chart, OS-Empfehlung |
| Portfolio | `/portfolio` | Positionen, Status HALTEN/BEOBACHTEN/EXIT, Kauf/Verkauf |
| Trade-Historie | `/history` | Archiv, P&L-Statistik, Trefferquote pro Signaltyp |
| Backtesting | `/backtest` | Ticker+Zeitraum, Signal-Zeitstrahl |
| **Konfiguration** | `/config` | Alle Einstellungen (siehe unten) |

### Konfigurationsseite (7. Seite) – Tab-Struktur

**Tab 1 – Universum:**
- Suchfeld: Ticker eingeben oder aus Reserve suchen → „Hinzufügen"-Button
- Aktive Ticker-Liste mit Quelle + Datum hinzugefügt + Entfernen-Button
- **„Universum aktualisieren"-Button** → ruft `POST /api/universe/refresh` auf
  - Holt aktuelle S&P 500 + NASDAQ 100 von Wikipedia
  - Aktualisiert NYSE/NASDAQ-Reserve via AV LISTING_STATUS
  - Zeigt Fortschritt + Ergebnis (n neue Ticker hinzugefügt)
- Letztes Update-Datum der Index-Listen

**Tab 2 – API-Status:**
- Übersicht aller 8 Dienste: grüner Haken oder rotes Kreuz
- Bei fehlendem Key: direkter Hinweis auf `.env`-Variable
- Alpha Vantage: Tagesquota-Anzeige (z. B. „22 von 25 verbleibend")

**Tab 3 – Scoring-Gewichtungen:**
- Schieberegler: Fundamental / Technisch / Sentiment (Summe muss 100 ergeben)
- Tabellarische Übersicht der Punkteverteilung
- Zonen-Grenzen anpassen (76 / 61 / 41)

**Tab 4 – Scan-Konfiguration:**
- Scan-Uhrzeit (Standard: 06:00 UTC)
- Zone-4-Batch-Größe (Standard: 200 Aktien/Tag)
- Nächster Scan-Zeitpunkt + letzter Scan-Zeitpunkt
- Anzeige: „Zone 4 wird alle X Tage vollständig gescannt"

**Tab 5 – Alert-Schwellen:**
- Exit-Schwellen (Score-Drop, KO-Abstand, Restlaufzeit, Bullish-Ratio)
- Notification-Schwellen (Δ1T-Spike, 7T-Streak-Tage)
- Telegram-Token + Chat-ID (mit Test-Nachricht-Button)

---

## Abhängigkeitsgraph

```
Phase 1 (Fetcher + DB + Universe) ✅
    │
    ▼
Phase 2 (Scoring-Engine)  ─────────────────────┐
    │                                           │
    ▼                                           │
Phase 3 (API + Scheduler + Config)  Phase 4 (Backtest)
    │                                           │
    └──────────────────────────────────────────▼
                                         Phase 5 (Frontend, 7 Seiten)
```

Phase 4 und Phase 5 können **parallel** zu Phase 3 entwickelt werden.

---

## Zeitschätzung

| Phase | Aufwand |
|-------|---------|
| Phase 2 (Scoring-Engine) | ~4h |
| Phase 3 (API + Scheduler + Config-Modul) | ~5h |
| Phase 4 (Backtesting) | ~2h |
| Phase 5 (Frontend, 7 Seiten) | ~7h |
| **Gesamt ab jetzt** | **~18h** |

---

## Nächster Schritt

**→ Phase 2 starten:** `backend/scoring/fundamental.py` → `technical.py` → `sentiment.py` → `delta.py` → `options.py` → `orchestrator.py`
