# API-Referenz

Basis-URL: `http://localhost:8000/api`  
Swagger-UI: `http://localhost:8000/docs`

---

## Dashboard

### `GET /api/dashboard`
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

### `GET /api/watchlist`
Alle Aktien nach Zone und Score.

**Query-Parameter:**
- `zone` (optional): 1, 2, 3 oder 4 – filtert nach Zone
- `sort` (optional): `delta_7d` (Standard), `score`, `delta_1d`
- `limit` (optional): Standard 50

**Response:** Liste von `StockScoreOut`-Objekten

---

## Signale

### `GET /api/signals/{ticker}`
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

### `GET /api/portfolio/positions`
Alle offenen Positionen mit aktuellem Status.

### `POST /api/portfolio/positions`
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

### `PATCH /api/portfolio/positions/{id}/close`
Position schließen und P&L berechnen.

**Body:**
```json
{
  "sell_price": 17.30,
  "sell_date": "2025-05-10"
}
```

### `GET /api/portfolio/exit-signals`
Alle offenen Exit-Signale (sortiert nach Priorität).

### `PATCH /api/portfolio/exit-signals/{id}/acknowledge`
Exit-Signal als gelesen markieren.

---

## Trade-Historie

### `GET /api/history/trades`
Alle abgeschlossenen Trades.

**Query-Parameter:**
- `limit` (optional): Standard 100

### `GET /api/history/signal-quality`
Trefferquote pro Signaltyp für den Lerneffekt.

---

## Scan

### `POST /api/scan/trigger`
Manuellen Scan starten (ohne auf 06:00 UTC zu warten).

**Query-Parameter:**
- `ticker` (optional): Nur diesen einen Ticker scannen

### `GET /api/scan/status`
Status des letzten Scans (Zeitstempel, Anzahl Ticker, Dauer).

---

## Konfiguration

### `GET /api/config`
Aktuelle Einstellungen laden.

### `PUT /api/config`
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

---

## Universum

### `GET /api/universe`
Alle Aktien im Universum mit Quellen.

### `POST /api/universe`
Aktie zur persönlichen Watchlist hinzufügen.

**Body:** `{ "ticker": "ASTS", "name": "AST SpaceMobile" }`

### `DELETE /api/universe/{ticker}`
Aktie aus persönlicher Watchlist entfernen.

---

## Backtesting

### `POST /api/backtest`
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
