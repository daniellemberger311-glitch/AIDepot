# AIDepot – Entwicklungs-Roadmap

Zuletzt aktualisiert: 2026-05-04

---

## Übersicht

```
Phase 1 │ Backend-Fundament              │ 100% ✅  │ Abgeschlossen
Phase 2 │ Scoring-Engine                 │ 100% ✅  │ Abgeschlossen
Phase 3 │ API + Scheduler + Notifications│ 100% ✅  │ Abgeschlossen
Phase 4 │ Backtesting-Modul              │ 100% ✅  │ Abgeschlossen
Phase 5 │ Frontend (7 Seiten)            │ 100% ✅  │ Abgeschlossen
Phase 6 │ Produktion + Qualitätssicherung│ 100% ✅  │ Abgeschlossen
```

**App ist vollständig und produktionsreif.**

---

## Phase 1 – Backend-Fundament ✅

Alle Fetcher, Datenbank, Cache, Universum-Loader fertig.  
Universum: ~850 aktive Ticker (S&P 500 + NASDAQ 100 + Russell 2000 + DAX 40 + persönliche Liste).

---

## Phase 2 – Scoring-Engine ✅

Jeder Ticker erhält täglich einen validen Score 0–100 mit vollständiger Aufschlüsselung.

### Scoring-Logik

**Ebene 1 – Fundamental (max. 40 Punkte)**

| Kriterium | Punkte | Logik |
|-----------|--------|-------|
| KGV vs. Sektorschnitt | 0–8 | <0,75x → 8; <1,0x → 6; <1,25x → 4; >1,5x → 0 |
| EPS-Beat-Streak | 0–6 | +2 pro Beat, max. 3 Quartale |
| Umsatzwachstum YoY | 0–6 | >20% → 6; 10–20% → 4; 0–10% → 2; negativ → 0 |
| FCF positiv + wachsend | 0–5 | FCF > 0 → 2; YoY gewachsen → +3 |
| Verschuldungsgrad D/E | 0–5 | <0,5 → 5; 0,5–1,0 → 3; 1,0–2,0 → 1; >2,0 → 0 |
| Insider-Käufe netto (90T) | 0–5 | ≥3 Käufe → 5; 1–2 → 3; neutral → 1; Verkäufe → 0 |
| Earnings-Nähe | 0–5 | 7–14 Tage → 5; 3–7 Tage → 3; >14 Tage → 1 |

**Ebene 2 – Technisch (max. 35 Punkte)**

| Kriterium | Punkte | Logik |
|-----------|--------|-------|
| VCP-Muster | 0–10 | 3 Kontraktionen → 10; 2 → 7; 1 + Vol↓ → 4 |
| Volumen-Kontraktion | 0–5 | 3W-Ø < 80% des 10W-Ø → 5; <90% → 3 |
| Preis-Nähe zu Widerstand | 0–5 | <3% → 5; 3–7% → 3; >10% → 0 |
| RSI 55–70 | 0–5 | 55–70 → 5; 50–55 od. 70–75 → 3; sonst 0 |
| Relative Stärke vs. SPY | 0–4 | RS > 1,1 (20T) → 4; 1,0–1,1 → 2; <1,0 → 0 |
| MACD-Signal | 0–3 | Histogramm positiv + steigend → 3; flach → 1 |
| Bollinger-Squeeze | 0–3 | BB-Breite < 20. Perzentil (52W) → 3 |

**Ebene 3 – Sentiment (max. 25 Punkte)**

| Kriterium | Punkte | Logik |
|-----------|--------|-------|
| News-Sentiment | 0–8 | Ø Finnhub + Marketaux: >0,6 → 8; 0,3–0,6 → 5; 0–0,3 → 2; negativ → 0 |
| StockTwits Bullish-Ratio | 0–7 | >65% → 7; 55–65% → 5; 45–55% → 3; <45% → 0 |
| Reddit-Momentum | 0–5 | +50% vs. 24h → 5; +20–50% → 3; flach → 1 |
| Analysten-Delta | 0–5 | ≥2 Netto-Upgrades → 5; 1 → 3; neutral → 1; Downgrade → 0 |

**Unterdrückungsregel:** Wenn L1+L2 > 50 UND L3 < 5 → Score max. 74 (kein Zone-1-Eintrag).

---

## Phase 3 – API + Scheduler + Notifications ✅

**40+ REST-Endpunkte** – vollständig implementiert.

**Scheduler-Jobs (APScheduler):**

| Zeitpunkt | Job |
|-----------|-----|
| 06:00 UTC täglich | Täglicher Scan (Tier 0→3, Zone-4-Rotation) |
| 06:30 UTC täglich | Exit-Signal-Check aller offenen Positionen |
| 07:00 UTC täglich | Telegram-Benachrichtigungen |
| 02:00 UTC sonntags | Wikipedia-Refresh + Cache-Bereinigung |

**Scan-Tiers:**

```
Tier 0  Offene Positionen (~5–20)     → täglich, alle APIs
Tier 1  Zone 1+2 (~150)              → täglich, alle APIs (AV nur Top 10)
Tier 2  Zone 3 (~200)                → täglich, yfinance + StockTwits + ApeWisdom
Tier 3  Zone 4 (~500+, 200/Tag)      → rotierend, nur yfinance + ta-Bibliothek
```

**Telegram-Nachrichtentypen:**
- Zone-Wechsel (Z3→Z2, Z2→Z1)
- Δ1T-Spike (> +15 an einem Tag)
- 7T-Aufbau-Trend (3 aufeinanderfolgende Anstiege)
- Exit-Warnung (Score-Drop, KO-Abstand, Restlaufzeit, Sentiment)
- Tages-Zusammenfassung (Top-5 + Exit-Zähler)

---

## Phase 4 – Backtesting-Modul ✅

Ticker + Zeitraum eingeben → sehen, wann welche Signale aufgetreten wären.

**Komponenten:**
- `historical_data.py` – OHLCV + Fundamentals via yfinance (4h gecacht)
- `engine.py` – tägliche Score-Berechnung aus OHLCV-Slices
- `signal_mapper.py` – Event-Erkennung: `ZONE_CHANGE`, `ZONE1_ENTRY`, `DELTA_SPIKE`, `STREAK_7D`
- `POST /api/backtest` – synchron für kurze Zeiträume

**Einschränkungen:**
- Sentiment: immer neutral 12,5/25 (historische Daten nicht verfügbar)
- Kein P&L-Simulator (nur Signal-Zeitstrahl)

---

## Phase 5 – Frontend (7 Seiten) ✅

**Stack:** Vite 6 + React 18 + TypeScript + TanStack Query v5 + React Router v6 + Recharts + Tailwind CSS v4

| Seite | Route | Besonderheiten |
|-------|-------|---------------|
| Dashboard | `/` | Scan-Steuerung, Abbrechen-Button, Fehler-Banner, letzter Scan in Sidebar |
| Watchlist | `/watchlist` | Zone-Tabs mit Zählern, sortierbar, Kurs mit Währung |
| Signal-Detail | `/signal/:ticker` | L1/L2/L3-Breakdown, 30T-Recharts-Chart, OS-Empfehlung, Rescan |
| Portfolio | `/portfolio` | Positionen-CRUD, Schließen-Modal, Exit-Signal-Anzeige |
| Trade-Historie | `/history` | Trade-Archiv, P&L-Statistik, Trefferquote |
| Backtesting | `/backtest` | Duales ComposedChart (Kurs + Score), Ereignistabelle |
| Konfiguration | `/config` | 6 Tabs: Universum, API-Status, Gewichtungen, Scan-Config, Alerts, Logs |

**Währungsformatierung:** `$` für USD, `€` für EUR, `£` für GBP, `CODE` für andere – aus yfinance-Metadaten.

---

## Phase 6 – Produktion + Qualitätssicherung ✅

### Einzelner Dienst (FastAPI serviert Frontend)

Das gebaute React-Bundle (`frontend/dist/`) wird von FastAPI via `StaticFiles` ausgeliefert.  
→ Kein Node.js in Produktion. Ein Port (8000). Eine `uvicorn`-Instanz.

### systemd-Integration

```
aidepot.service       → Auto-Start, Restart=on-failure, 0.0.0.0:8000
aidepot-backup.service → SQLite-safe Backup (sqlite3 .backup)
aidepot-backup.timer  → täglich 03:00 UTC, 7 rotierende Kopien
```

### Alembic-Migrationen

Schema-Änderungen werden ohne Datenverlust eingespielt:

```bash
alembic revision --autogenerate -m "Beschreibung"
alembic upgrade head
```

`render_as_batch=True` in `migrations/env.py` für SQLite-kompatible ALTER TABLE.

**Migrationen:**
- `0001_initial.py` – alle 13 Tabellen und Indizes
- `0002_close_price_currency.py` – `close_price` + `currency` Spalten in `daily_scores`

### update.sh

```bash
git pull origin main
.venv/bin/pip install -q -r backend/requirements.txt
.venv/bin/python -m pytest tests/ -q --tb=short || exit 1   ← bricht bei Fehler ab
.venv/bin/alembic upgrade head
cd frontend && npm install --silent && npm run build && cd ..
sudo systemctl restart aidepot
```

### Unit-Tests (133 Tests, alle grün)

| Datei | Tests | Inhalt |
|-------|-------|--------|
| `tests/scoring/test_fundamental.py` | 40 | Alle 7 L1-Kriterien inkl. Grenzwerte |
| `tests/scoring/test_sentiment.py` | 41 | L3-Kriterien + Unterdrückungsregel |
| `tests/scoring/test_technical.py` | 35 | L2 mit synthetischen DataFrames |
| `tests/test_orchestrator.py` | 17 | Zonengrenzen (76/61/41) |

---

## Abhängigkeitsgraph

```
Phase 1 (Fetcher + DB + Universe) ✅
    │
    ▼
Phase 2 (Scoring-Engine) ✅ ──────────────────────┐
    │                                              │
    ▼                                              │
Phase 3 (API + Scheduler + Config) ✅    Phase 4 (Backtest) ✅
    │                                              │
    └──────────────────────────────────────────────▼
                                       Phase 5 (Frontend) ✅
                                                   │
                                                   ▼
                                       Phase 6 (Produktion) ✅
```
