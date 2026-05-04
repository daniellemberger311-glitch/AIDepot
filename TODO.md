# AIDepot – Fortschritt & erledigte Aufgaben

Zuletzt aktualisiert: 2026-05-04

---

## Aktueller Stand

**Alle Phasen abgeschlossen. App ist produktionsreif.**

| Phase | Beschreibung | Status |
|-------|-------------|--------|
| Phase 1 | Backend-Fundament | ✅ 100% |
| Phase 2 | Scoring-Engine | ✅ 100% |
| Phase 3 | API + Scheduler + Notifications | ✅ 100% |
| Phase 4 | Backtesting-Modul | ✅ 100% |
| Phase 5 | Frontend (7 Seiten) | ✅ 100% |
| Phase 6 | Produktion + Qualitätssicherung | ✅ 100% |

---

## ✅ Phase 1 – Backend-Fundament

- Projektstruktur, `.env`, `.gitignore`
- `backend/config.py`, `database.py`, `models.py` (13 Tabellen)
- `backend/schemas.py`, `main.py`, `cache/store.py`
- Alle 8 Fetcher inkl. AV-Key-Rotation
- `backend/universe/loader.py` – ~850 aktive Ticker
- `scripts/init_db.py`, `scripts/test_fetchers.py`

---

## ✅ Phase 2 – Scoring-Engine

- `backend/scoring/fundamental.py` – L1: 7 Kriterien, max. 40 Pkt.
- `backend/scoring/technical.py` – L2: VCP + 6 Indikatoren, max. 35 Pkt.
- `backend/scoring/sentiment.py` – L3: 4 Kriterien + Unterdrückungsregel, max. 25 Pkt.
- `backend/scoring/delta.py` – Δ1T / Δ7T / Δ30T
- `backend/scoring/options.py` – OS-Parameter (nur Zone 1)
- `backend/scoring/orchestrator.py` – Hauptkoordinator, schreibt in 4 DB-Tabellen

---

## ✅ Phase 3 – API + Scheduler + Notifications

**API-Endpunkte (40+ Routen):**
- `GET /api/watchlist` – Zone-Filter, Sortierung, Breakdown
- `GET /api/watchlist/zones/summary` – Zonen-Zähler
- `GET /api/signals/{ticker}` + `/history` – vollständiges Signal + Score-Verlauf
- `GET/POST/PUT/DELETE /api/portfolio` – CRUD Positionen + Exit-Signale + P&L
- `GET /api/dashboard` – Tagesübersicht
- `GET /api/history/trades` + `/signal-quality` + `/summary`
- `POST /api/scan/trigger` – Background-Task
- `POST /api/scan/cancel` – laufenden Scan abbrechen
- `POST /api/scan/ticker/{ticker}` – Einzelticker rescannen
- `GET /api/scan/status` – Fortschritt, Fehler, letzter Scan
- `GET/PUT /api/config` – Einstellungen
- `GET /api/config/status` – API-Key-Status
- `GET /api/config/scan-schedule` – Scan-Zeitplan
- `GET/POST/DELETE /api/universe` – Ticker-CRUD + Suche + Refresh
- `GET/DELETE /api/logs` – In-Memory-Log-Ringpuffer
- `POST /api/backtest` – historische Signal-Simulation

**Scheduler (APScheduler):**
- 06:00 UTC – Täglicher Scan (Tier 0→3 + Zone-4-Rotation)
- 06:30 UTC – Exit-Signal-Check aller offenen Positionen
- 07:00 UTC – Telegram-Benachrichtigungen
- So 02:00 UTC – Wikipedia-Refresh + Cache-Bereinigung

**Notifications:** Code fertig. Telegram noch nicht konfiguriert (⏳ BOT_TOKEN + CHAT_ID fehlen).

---

## ✅ Phase 4 – Backtesting-Modul

- `backend/backtesting/historical_data.py` – OHLCV + Fundamentals (yfinance, TTL-Cache 4h)
- `backend/backtesting/engine.py` – tägliche Score-Berechnung aus OHLCV-Slices
- `backend/backtesting/signal_mapper.py` – ZONE_CHANGE, ZONE1_ENTRY, DELTA_SPIKE, STREAK_7D
- `backend/api/backtest.py` – `POST /api/backtest`
- Router eingebunden

**Einschränkungen:**
- Sentiment: immer neutral 12,5/25 (historisch nicht verfügbar)
- EPS-Beat-Streak: vereinfachte Schätzung aus yfinance

---

## ✅ Phase 5 – Frontend (7 Seiten)

**Stack:** Vite 6 + React 18 + TypeScript, TanStack Query v5, React Router DOM v6, Recharts, Tailwind CSS v4, lucide-react

- `src/api/client.ts` – Axios-Client, alle Endpunkte
- `src/types/api.ts` – TypeScript-Typen (spiegeln schemas.py)
- Komponenten: `Card`, `PageHeader`, `ZoneBadge`, `ScoreBar`, `DeltaBadge`, `SeverityBadge`
- `Layout.tsx` – Sidebar mit letztem Scan-Zeitstempel (immer sichtbar, rot bei Fehler)
- **Dashboard** (`/`) – 4 KPI-Karten, Top-5 Zone-1-Signale, Exit-Warnungen, Scan-Trigger, Abbrechen-Button, Fehler-Banner
- **Watchlist** (`/watchlist`) – Zone-Tabs mit Zählern, sortierbare Tabelle, Kurs mit Währung
- **Signal-Detail** (`/signal/:ticker`) – Score-Breakdown L1/L2/L3, 30T-Chart (Recharts), OS-Empfehlung, Rescan, Kurs mit Währung
- **Portfolio** (`/portfolio`) – Positionen-CRUD, Schließen-Modal, Exit-Signal-Anzeige
- **Trade-Historie** (`/history`) – Archiv, Signalqualität, P&L-Zusammenfassung
- **Backtesting** (`/backtest`) – Kurs-/Score-Chart (Recharts ComposedChart), Ereignistabelle, KPI-Karten
- **Konfiguration** (`/config`) – 6 Tabs: Universum, API-Status, Gewichtungen, Scan-Config, Alerts, **Logs**

---

## ✅ Phase 6 – Produktion + Qualitätssicherung

- **Einzelner Dienst:** FastAPI serviert gebautes Frontend (`frontend/dist/`) via `StaticFiles` – kein Node.js in Produktion, ein Port (8000)
- **Heimnetz-Zugriff:** `--host 0.0.0.0` → erreichbar von Android, Windows, etc. über `http://<Linux-IP>:8000`
- **systemd-Service** (`aidepot.service`): Auto-Start beim Booten, `Restart=on-failure`
- **Backup-System** (`scripts/backup.sh` + `aidepot-backup.service/timer`): täglich 03:00 UTC, 7 rotierende Kopien, SQLite-safe Backup ohne Downtime
- **Alembic-Migrationen** (`migrations/`): Schema-Änderungen ohne Datenverlust; `render_as_batch=True` für SQLite
  - `0001_initial.py` – alle 13 Tabellen
  - `0002_close_price_currency.py` – `close_price` + `currency` in `daily_scores`
- **update.sh**: Einzeiler-Deployment (git pull → pip → pytest → alembic upgrade → npm build → systemctl restart)
- **Aktienkurs + Währung:** `close_price` / `currency` aus yfinance in DB gespeichert, überall angezeigt (`$`, `€`, `£`)
- **Scan-Abbrechen:** `POST /api/scan/cancel` → In-Memory-Flag, aktueller Ticker wird sauber fertig
- **Scan-Fehler-Banner:** Auf dem Dashboard sichtbar wenn letzter Scan fehlschlug
- **Letzter Scan in Sidebar:** Immer im Layout sichtbar, rot bei Fehler
- **Log-Viewer (Config-Tab 6):** Level-Filter, Modul-Filter, Auto-Refresh, erweiterbare Stack-Traces
- **Unit-Tests:** 133 Tests für Scoring-Engine (alle grün)
  - `tests/scoring/test_fundamental.py` – 40 Tests, alle 7 L1-Kriterien
  - `tests/scoring/test_sentiment.py` – 41 Tests, L3-Kriterien + Unterdrückungsregel
  - `tests/scoring/test_technical.py` – 35 Tests, L2 mit synthetischen DataFrames
  - `tests/test_orchestrator.py` – 17 Tests, Zonengrenzen (76/61/41)

---

## Bekannte Einschränkungen

| Einschränkung | Details |
|---------------|---------|
| AV MACD ist Premium | ta-Bibliothek berechnet MACD aus yfinance-OHLCV (kein Scoring-Verlust) |
| Ticker-Listen Stand Q1 2025 | `POST /api/universe/refresh` oder Scheduler hält aktuell |
| Optionsschein-Stammdaten | Kein Free-API → ISIN + KO manuell eintragen |
| Historisches Sentiment | Für Backtesting: neutral 12,5/25 |
| Unrealized P&L | Warrant-Preis nicht via API → manuell eintragen |
| Telegram | BOT_TOKEN + CHAT_ID noch nicht in `.env` eingetragen |
| Scoring-Gewichtungen konfigurierbar | In Config-Seite einstellbar, aber Änderungen wirken erst ab nächstem Scan |

---

## Mögliche zukünftige Erweiterungen (kein konkreter Plan)

- Telegram-Benachrichtigungen einrichten (BOT_TOKEN + CHAT_ID)
- Marktkalender-Integration (Feiertage → Scan überspringen)
- Mobile PWA / Responsive-Optimierung für sehr kleine Screens
- Mehrfach-Portfolio (mehrere Nutzerprofile)
- Erweiterte Backtesting-Auswertung mit P&L-Simulation
