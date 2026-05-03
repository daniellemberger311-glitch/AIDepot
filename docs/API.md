# API-Referenz

Basis-URL: `http://localhost:8000/api`  
Swagger-UI: `http://localhost:8000/docs`

**Status-Legende:** ✅ implementiert | ⏳ Phase 3 | ⏳ Phase 4

---

## Dashboard

### `GET /api/dashboard` ⏳ Phase 3
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

### `GET /api/watchlist` ⏳ Phase 3
Alle Aktien nach Zone und Score.

**Query-Parameter:**
- `zone` (optional): 1, 2, 3 oder 4 – filtert nach Zone
- `sort` (optional): `delta_7d` (Standard), `score`, `delta_1d`
- `limit` (optional): Standard 50

**Response:** Liste von `StockScoreOut`-Objekten

---

## Signale

### `GET /api/signals/{ticker}` ⏳ Phase 3
Vollständige Signal-Analyse für einen Ticker.

**Response:**
```json
{
  "ticker": "NVDA",
  "total_score": 82,
  "zone": 1,
  "delta_1d": 3.1,
  "delta_7d": 12.4,
  "breakdown": { ... alle Unterkriterien ... },
  "history": [ { "score_date": "2025-04-01", "total_score": 70, "zone": 2 }, ... ],
  "options_rec": {
    "direction": "CALL",
    "leverage_min": 5,
    "leverage_max": 6,
    "duration_weeks": 8,
    "ko_distance_pct": 13.5,
    "entry_trigger": 920.0,
    "stop_loss": 845.0
  }
}
```

---

## Portfolio

### `GET /api/portfolio/positions` ⏳ Phase 3
Alle offenen Positionen mit aktuellem Status.

### `POST /api/portfolio/positions` ⏳ Phase 3
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
  "entry_date": "2025-04-15",
  "ko_level": 820.0,
  "expiry_date": "2025-07-18",
  "leverage": 6.0
}
```

### `PATCH /api/portfolio/positions/{id}/close` ⏳ Phase 3
Position schließen und P&L berechnen.

**Body:**
```json
{
  "sell_price": 17.30,
  "sell_date": "2025-05-10"
}
```

### `GET /api/portfolio/exit-signals` ⏳ Phase 3
Alle offenen Exit-Signale (sortiert nach Priorität).

### `PATCH /api/portfolio/exit-signals/{id}/acknowledge` ⏳ Phase 3
Exit-Signal als gelesen markieren.

---

## Trade-Historie

### `GET /api/history/trades` ⏳ Phase 3
Alle abgeschlossenen Trades.

**Query-Parameter:**
- `limit` (optional): Standard 100

### `GET /api/history/signal-quality` ⏳ Phase 4
Trefferquote pro Signaltyp für den Lerneffekt.

---

## Scan

### `POST /api/scan/trigger` ⏳ Phase 3
Manuellen Scan starten (ohne auf 06:00 UTC zu warten).

**Query-Parameter:**
- `ticker` (optional): Nur diesen einen Ticker scannen

### `GET /api/scan/status` ⏳ Phase 3
Status des letzten Scans (Zeitstempel, Anzahl Ticker, Dauer).

---

## Konfiguration

### `GET /api/config` ⏳ Phase 3
Aktuelle Einstellungen laden.

### `PUT /api/config` ⏳ Phase 3
Einstellungen aktualisieren (Gewichtungen, Schwellenwerte, Telegram).

**Body:** (alle Felder optional)
```json
{
  "weight_fundamental": 40,
  "weight_technical": 35,
  "weight_sentiment": 25,
  "zone1_min_score": 76,
  "exit_score_drop": 15.0,
  "exit_ko_distance": 8.0
}
```

### `GET /api/config/status` ⏳ Phase 3
Quota-Status aller APIs + letzter Scan-Zeitstempel.

**Response:**
```json
{
  "alpha_vantage": {
    "total_remaining": 38,
    "limit_per_day": 25,
    "keys": [
      { "slot": "alpha_vantage_api_key", "remaining": 18 },
      { "slot": "alpha_vantage_api_key_2", "remaining": 20 }
    ],
    "min_interval_secs": 13.0
  },
  "last_scan_at": "2026-05-03T06:02:11Z",
  "last_scan_tickers": 842
}
```

---

## Universum

### `GET /api/universe` ⏳ Phase 3
Alle Aktien im Universum mit Quellen.

### `GET /api/universe/search` ⏳ Phase 3
Ticker oder Name suchen.

**Query-Parameter:**
- `q`: Suchbegriff (Ticker oder Firmenname)
- `limit` (optional): Standard 20

### `POST /api/universe/add` ⏳ Phase 3
Aktie zur persönlichen Watchlist hinzufügen.

**Body:** `{ "ticker": "ASTS", "name": "AST SpaceMobile" }`

### `DELETE /api/universe/{ticker}` ⏳ Phase 3
Aktie aus persönlicher Watchlist entfernen.

### `POST /api/universe/refresh` ⏳ Phase 3
Universum neu laden (S&P 500, NASDAQ 100, Russell 2000, Trending von StockTwits).  
Dauert ~1–2 Minuten. Gibt die Anzahl neu hinzugefügter Ticker zurück.

---

## Logs

### `GET /api/logs` ✅
In-Memory-Logs der laufenden Backend-Instanz abrufen.

**Query-Parameter:**
- `level` (optional): `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `module` (optional): Teilstring des Modulnamens (z. B. `alphavantage`)
- `limit` (optional): 1–1000, Standard 200
- `since` (optional): ISO-Zeitstempel – nur Einträge nach diesem Zeitpunkt

**Response:**
```json
[
  {
    "timestamp": "2026-05-03T06:02:11.234Z",
    "level": "WARNING",
    "module": "backend.fetchers.alphavantage_fetcher",
    "message": "Alpha Vantage Rate-Limit-Antwort (Slot alpha_vantage_api_key): Thank you..."
  }
]
```

### `GET /api/logs/summary` ✅
Kompaktzusammenfassung: letzte 10 Fehler + Zähler.

**Response:**
```json
{
  "error_count": 2,
  "warning_count": 7,
  "last_errors": [
    {
      "timestamp": "2026-05-03T06:01:55.100Z",
      "level": "ERROR",
      "module": "backend.fetchers.finnhub_fetcher",
      "message": "Finnhub API timeout: AAPL"
    }
  ]
}
```

### `DELETE /api/logs` ✅
Log-Puffer leeren.

---

## Backtesting

### `POST /api/backtest` ⏳ Phase 3
Historische Signal-Simulation für einen Ticker.

**Body:**
```json
{
  "ticker": "NVDA",
  "from_date": "2024-01-01",
  "to_date": "2025-05-03"
}
```

**Response:**
```json
{
  "ticker": "NVDA",
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
  "zone1_entries": 3
}
```

---

## Fehler-Codes

| Code | Bedeutung |
|------|-----------|
| 200 | Erfolg |
| 404 | Ticker nicht gefunden |
| 422 | Validierungsfehler (Pydantic) |
| 500 | Interner Fehler (Details in Response) |
