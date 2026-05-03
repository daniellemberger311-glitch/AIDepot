# Rate-Limit-Strategie

## Überblick: Limits aller Datenquellen

| Quelle | Limit | Schutz implementiert |
|--------|-------|----------------------|
| yfinance | kein offizielles Limit | ✅ 4h-Cache |
| StockTwits | inoffiziell, ~1 Req/2s | ✅ 2s-Sleep zwischen Calls |
| ApeWisdom | kein Limit | ✅ 1h-Cache |
| Finnhub | **60 Calls/Minute** | ✅ 1s-Sleep + 1h-Cache |
| **Alpha Vantage** | **5 Calls/Minute + 25/Tag** | ✅ 13s-Mindestabstand + Tageszähler |
| Marketaux | 100 News/Tag | ✅ Tageszähler in DB |
| SimFin | kein Limit (privat) | ✅ 24h-Cache |

---

## Alpha Vantage: BEIDE Limits gleichzeitig

Das ist die kritischste Datenquelle, weil **zwei unabhängige Limits** gleichzeitig gelten:

```
Täglich:    max. 25 Calls/Tag
Pro Minute: max. 5 Calls/Minute → 1 Call alle 12 Sekunden
```

### Wie es implementiert ist

**Modul-globaler Timestamp** (`_last_av_call_ts` in `alphavantage_fetcher.py`):
- Vor jedem echten API-Call wird `_enforce_rate_limit()` aufgerufen
- Diese Funktion wartet, bis seit dem letzten Call mind. 13 Sekunden vergangen sind
- 13 s statt 12 s = 1 Sekunde Puffer gegen Netz-Jitter
- Der Timestamp ist **prozessglobal** – verhindert Überläufe auch wenn mehrere
  Ticker schnell hintereinander gescannt werden

**Tageszähler in DB** (`configuration`-Tabelle):
- Jeder erfolgreiche AV-Call erhöht `av_calls_today` um 1
- Täglich um 00:01 UTC wird der Zähler durch `quota_reset_job` auf 0 zurückgesetzt
- Wenn `av_calls_today >= 25` → kein weiterer Call, stattdessen Fallback

**Was Alpha Vantage zurückgibt wenn Rate-Limit überschritten:**
```json
{"Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute..."}
```
→ Der Fetcher erkennt diesen `"Note"`-Key und gibt `{}` zurück (kein Absturz).

### Budget-Aufteilung (25 Calls/Tag)

| Verwendung | Calls/Tag | Wann |
|------------|-----------|------|
| Zone-1-Aktien RSI/MACD | max. 10 | Scan 06:00 UTC |
| Gehaltene Positionen | max. 5 | Scan 06:00 UTC |
| Manuelle Refresh-Anfragen via UI | max. 5 | Jederzeit |
| Reserve/Puffer | 5 | – |

**Konsequenz:** Alpha Vantage ist NUR für die Top-15 Aktien des Tages.
Für alle anderen Aktien (Zone 3+4) werden RSI, MACD und Bollinger lokal mit
der `ta`-Bibliothek auf Basis von yfinance-OHLCV berechnet – **kein Limit,
keine Kosten**.

---

## Scan-Strategie: Welche API bekommt welchen Tier?

### Tier-Übersicht

```
Tier 0  gehaltene Positionen (~5–20 Aktien)
        → ALLE APIs: yfinance + ta + Finnhub + AV + StockTwits + SimFin

Tier 1  Zone 1+2 (~150 Aktien)
        → yfinance + ta + Finnhub + StockTwits + ApeWisdom
        → Alpha Vantage: nur Top 10 nach Δ7T (Budget-Schonung)
        → SimFin: falls AV-Budget verbraucht

Tier 2  Zone 3 (~200 Aktien)
        → yfinance + ta + StockTwits + ApeWisdom
        → KEINE Quota-APIs (Finnhub, AV, Marketaux, SimFin)
        → Fundamentals: yfinance (kostenlos)

Tier 3  Zone 4 (~500+ Aktien, täglich 200 rotierend)
        → Nur yfinance + ta-Bibliothek
        → Scan: 200 Aktien/Tag → gesamte Zone 4 alle ~2–3 Tage vollständig
        → KEINE weiteren APIs
```

### Scan-Frequenz für das gesamte Universum (~850 Aktien)

| Tier | Anzahl | Tägliche Scans | Vollständiger Zyklus |
|------|--------|----------------|----------------------|
| 0 (Positionen) | ~10–20 | täglich | täglich |
| 1 (Zone 1+2) | ~150 | täglich | täglich |
| 2 (Zone 3) | ~200 | täglich | täglich |
| 3 (Zone 4) | ~500 | 200/Tag | alle 2–3 Tage |

**→ Jede Aktie wird mindestens alle 3 Tage gescannt** (weit besser als wöchentlich).

### Zeitbedarf für den täglichen Scan

```
yfinance (Tier 0–2, ~350 Aktien):    ~5 Min  (kein Sleep nötig)
Finnhub (Tier 0–1, ~170 Aktien):     ~3 Min  (1s Sleep = 60/Min einhalten)
StockTwits (Tier 0–2, ~350 Aktien):  ~12 Min (2s Sleep je Ticker)
Alpha Vantage (max. 15 Aktien):      ~3 Min  (13s Sleep je Ticker)
Zone 4 yfinance-Rotation (200):      ~3 Min

Gesamt geschätzt: ~25–30 Minuten für den kompletten Tages-Scan
```

---

## Finnhub (60 Calls/Minute)

```python
# In finnhub_fetcher.py: nach jedem Call
time.sleep(1.1)  # 60 Calls/Min → 1 Call/Sek mit 10% Puffer
```

Bei ~170 Aktien (Tier 0+1) mit je 1 Finnhub-Call: **~3 Minuten**.

---

## Marketaux (100 News/Tag)

Marketaux liefert News-Artikel, nicht einzelne Ticker-Calls.
Mit `limit=3` pro Request decken 33 Requests = 33 Ticker ab.
**Strategie:** Nur für Zone 1 einsetzen (max. 50 Ticker), Rest mit Finnhub oder ApeWisdom.

---

## Cache-TTLs im Überblick

| Datentyp | TTL | Begründung |
|----------|-----|-----------|
| OHLCV (yfinance) | 4h | Intraday irrelevant für Tages-Scan |
| Fundamentals (yfinance/SimFin) | 24h | Ändert sich quartalsweise |
| Earnings-Kalender | 24h | Termin ändert sich selten |
| News-Sentiment | 2h | Zeitkritischer als Fundamentals |
| StockTwits Bullish-Ratio | 1h | Stündliche Veränderungen relevant |
| Alpha-Vantage RSI/MACD | 4h | Tages-Indikator |
| ApeWisdom Mentions | 1h | Reddit-Dynamik |
| AV LISTING_STATUS | 7 Tage | Ändert sich kaum |
| Wikipedia-Listen | 7 Tage | Quartalsweise Index-Änderungen |

---

## Notfallplan: API-Ausfall

| Quelle fällt aus | Fallback |
|-----------------|---------|
| Alpha Vantage | RSI/MACD aus `ta`-Bibliothek + yfinance (kein Score-Verlust) |
| Finnhub Sentiment | Marketaux oder ApeWisdom + StockTwits |
| SimFin | yfinance Fundamentals (etwas ungenauer) |
| Marketaux | Finnhub News-Sentiment |
| StockTwits | Sentiment-Score = neutral (12,5/25) |
| yfinance | App pausiert – keine Alternative (unverzichtbar) |
