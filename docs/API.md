# API-Referenz

Basis-URL: `http://localhost:8000/api`  
Swagger-UI: `http://localhost:8000/docs`

Alle Endpunkte sind implementiert ✅.

---

## Dashboard

### `GET /api/dashboard` ✅
Gesamtübersicht für die Startseite.

**Response:**
```json
{
  "total_pnl_abs": 1234.56,
  "total_pnl_pct": 18.4,
  "open_positions": 3,
  "top_signals": [...],
  "exit_alerts": [...]
}
```

---

## Watchlist

### `GET /api/watchlist` ✅
Alle Aktien nach Zone und Score.

**Query-Parameter:**
- `zone` (optional): 1, 2, 3 oder 4 – filtert nach Zone
- `sort` (optional): `total_score` (Standard), `delta_7d`, `delta_1d`, `ticker`
- `limit` (optional): Standard 200
- `breakdown` (optional): `true` – gibt Score-Breakdown-Felder mit zurück

**Response:** Liste von `StockScoreOut`-Objekten (inkl. `close_price`, `currency`)

### `GET /api/watchlist/zones/summary` ✅
Zonen-Zähler und Gesamt-Ticker-Anzahl.

**Response:**
```json
{
  "date": "2026-05-04",
  "total": 742,
  "zones": { "1": 12, "2": 45, "3": 183, "4": 502 }
}
```

---

## Signale

### `GET /api/signals/{ticker}` ✅
Vollständige Signal-Analyse für einen Ticker.

**Response:**
```json
{
  "ticker": "NVDA",
  "name": "NVIDIA Corporation",
  "sector": "Technology",
  "total_score": 82,
  "l1_fundamentals": 34.0,
  "l2_technicals": 28.0,
  "l3_sentiment": 20.0,
  "zone": 1,
  "delta_1d": 3.1,
  "delta_7d": 12.4,
  "delta_30d": 8.2,
  "close_price": 875.40,
  "currency": "USD",
  "strongest_signal": "VCP",
  "next_catalyst": "2026-05-21",
  "catalyst_days": 17,
  "score_date": "2026-05-04",
  "breakdown": { ... },
  "options_rec": {
    "direction": "CALL",
    "leverage_min": 5,
    "leverage_max": 6,
    "duration_weeks": 8,
    "ko_distance_pct": 13.5,
    "entry_trigger": 920.0,
    "stop_loss": 845.0,
    "base_price_at_rec": 875.40,
    "atr_at_rec": 18.2
  }
}
```

### `GET /api/signals/{ticker}/history` ✅
Score-Verlauf der letzten N Tage.

**Query-Parameter:**
- `days` (optional): Standard 30

**Response:** Liste von `{ score_date, total_score, zone }`

---

## Portfolio

### `GET /api/portfolio` ✅
Alle Positionen (offen und optional geschlossen).

**Query-Parameter:**
- `include_closed` (optional): `true` – gibt auch abgeschlossene Positionen zurück

### `POST /api/portfolio` ✅
Neue Position erfassen.

**Body:**
```json
{
  "ticker": "NVDA",
  "product_type": "WARRANT",
  "direction": "LONG",
  "isin": "DE000...",
  "quantity": 100,
  "entry_price": 12.50,
  "entry_date": "2026-04-15",
  "ko_level": 820.0,
  "expiry_date": "2026-07-18",
  "leverage": 6.0,
  "underlying_at_entry": 875.40,
  "notes": "VCP-Signal Zone 1"
}
```

### `GET /api/portfolio/{id}` ✅
Einzelne Position mit Exit-Signalen.

### `PUT /api/portfolio/{id}/close` ✅
Position schließen und P&L berechnen.

**Body:**
```json
{
  "sell_price": 17.30,
  "sell_date": "2026-05-10",
  "notes": "Kursziel erreicht"
}
```

### `DELETE /api/portfolio/{id}` ✅
Position löschen (ohne Trade-Eintrag).

### `POST /api/portfolio/{id}/check-exits` ✅
Exit-Signale für eine Position manuell prüfen.

### `GET /api/portfolio/{id}/transactions` ✅
Alle Transaktionen einer Position.

### `PUT /api/portfolio/signals/{id}/acknowledge` ✅
Exit-Signal als quittiert markieren.

---

## Trade-Historie

### `GET /api/history/trades` ✅
Alle abgeschlossenen Trades.

**Query-Parameter:**
- `ticker` (optional): Filtert nach Ticker
- `limit` (optional): Standard 100

### `GET /api/history/signal-quality` ✅
Trefferquote pro Signaltyp.

**Response:**
```json
[
  {
    "signal_type": "VCP",
    "total_trades": 14,
    "profitable": 10,
    "win_rate_pct": 71.4,
    "avg_pnl_pct": 18.3
  }
]
```

### `GET /api/history/summary` ✅
Gesamtstatistik aller Trades.

---

## Scan

### `POST /api/scan/trigger` ✅
Manuellen Vollscan starten (Background-Task).

**Response:** `{ "message": "Scan gestartet", "tickers": 842 }`

### `POST /api/scan/cancel` ✅
Laufenden Scan abbrechen. Der aktuelle Ticker wird noch fertig gescannt.

**Response:** `{ "message": "Abbruch angefordert – aktueller Ticker wird noch fertig" }`

### `POST /api/scan/ticker/{ticker}` ✅
Einzelnen Ticker sofort (synchron) rescannen.

### `GET /api/scan/status` ✅
Status des aktuellen oder letzten Scans.

**Response:**
```json
{
  "running": true,
  "started_at": "2026-05-04T06:00:05Z",
  "progress": 312,
  "total": 842,
  "current_ticker": "MSFT",
  "last_completed": "2026-05-03T06:28:11Z",
  "last_duration_sec": 1682,
  "error": null,
  "tickers_failed": []
}
```

---

## Konfiguration

### `GET /api/config` ✅
Aktuelle App-Einstellungen laden.

### `PUT /api/config` ✅
Einstellungen aktualisieren. Alle Felder optional.

**Body:**
```json
{
  "weight_fundamental": 40,
  "weight_technical": 35,
  "weight_sentiment": 25,
  "zone1_min_score": 76,
  "zone2_min_score": 61,
  "zone3_min_score": 41,
  "alert_delta_1d": 15,
  "exit_score_drop": 15,
  "exit_ko_distance": 8,
  "exit_expiry_weeks": 3,
  "exit_bull_ratio": 35
}
```

### `GET /api/config/status` ✅
API-Key-Status aller Dienste.

**Response:**
```json
{
  "yfinance":      { "status": "ok",      "note": "kein Key erforderlich" },
  "finnhub":       { "status": "ok",      "remaining_today": null },
  "alpha_vantage": { "status": "ok",      "remaining_today": 22, "key_2_active": false },
  "marketaux":     { "status": "ok" },
  "simfin":        { "status": "ok" },
  "stocktwits":    { "status": "ok",      "note": "kein Key erforderlich" },
  "apewisdom":     { "status": "ok",      "note": "kein Key erforderlich" },
  "telegram":      { "status": "missing", "note": "TELEGRAM_BOT_TOKEN nicht gesetzt" }
}
```

### `GET /api/config/scan-schedule` ✅
Scan-Zeitplan und Zone-4-Rotations-Status.

---

## Universum

### `GET /api/universe` ✅
Alle Ticker mit Metadaten.

**Query-Parameter:**
- `active_only` (optional): `true` – nur aktive Ticker
- `source` (optional): z. B. `SP500`, `NASDAQ100`, `WATCHLIST`

### `GET /api/universe/search?q={suchbegriff}` ✅
Ticker oder Firmenname in der Reserve-Datenbank suchen.

### `POST /api/universe/add` ✅
Ticker manuell hinzufügen.

**Body:** `{ "ticker": "ASTS", "name": "AST SpaceMobile" }`

### `DELETE /api/universe/{ticker}` ✅
Ticker deaktivieren (`is_active = false`). Historische Scores bleiben erhalten.

### `POST /api/universe/refresh` ✅
Universum aktualisieren (S&P 500 + NASDAQ 100 von Wikipedia, NYSE/NASDAQ-Reserve via AV).

**Response:** `{ "added": 3, "updated": 12, "total_active": 851 }`

---

## Logs

### `GET /api/logs` ✅
In-Memory-Logs der laufenden Backend-Instanz (Ringpuffer, max. 1000 Einträge).

**Query-Parameter:**
- `level` (optional): `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `module` (optional): Teilstring des Modulnamens (z. B. `alphavantage`)
- `limit` (optional): 1–1000, Standard 200

**Response:**
```json
{
  "total_returned": 42,
  "error_count": 2,
  "warning_count": 7,
  "entries": [
    {
      "timestamp": "2026-05-04T06:02:11.234Z",
      "level": "WARNING",
      "logger": "backend.fetchers.alphavantage_fetcher",
      "message": "Alpha Vantage Rate-Limit erreicht (Slot 1)"
    }
  ]
}
```

### `DELETE /api/logs` ✅
Log-Puffer leeren.

---

## Backtesting

### `POST /api/backtest` ✅
Historische Signal-Simulation für einen Ticker.

**Body:**
```json
{
  "ticker": "NVDA",
  "from_date": "2024-01-01",
  "to_date": "2025-05-04"
}
```

**Response:**
```json
{
  "ticker": "NVDA",
  "from_date": "2024-01-01",
  "to_date": "2025-05-04",
  "price_data": [
    { "date": "2024-01-02", "close": 495.22, "score": 58, "zone": 3, "delta_1d": null, "delta_7d": null }
  ],
  "signals": [
    {
      "date": "2024-01-15",
      "event_type": "ZONE_CHANGE",
      "from_zone": 3,
      "to_zone": 2,
      "score": 63,
      "description": "Zone 3 → Zone 2: Aufbau erkannt"
    }
  ],
  "total_signals": 12,
  "zone1_entries": 3,
  "summary": { ... }
}
```

---

## Fehler-Codes

| Code | Bedeutung |
|------|-----------|
| 200 | Erfolg |
| 404 | Ticker / Ressource nicht gefunden |
| 409 | Konflikt (z. B. Scan läuft bereits) |
| 422 | Validierungsfehler (Pydantic) |
| 500 | Interner Fehler (Details in Response-Body) |
