# Rate-Limit-Strategie

## Das Problem

~850 Aktien täglich mit kostenlosen APIs scannen. Die harten Grenzen:

| API | Limit | Tagesäquivalent |
|-----|-------|-----------------|
| Alpha Vantage | 25 Calls/Tag | 25 Ticker vollständig |
| Finnhub | 60 Calls/Min | ~3.600/Stunde (wenn gleichmäßig verteilt) |
| Marketaux | 100 News/Tag | ~100 Nachrichten |
| yfinance | Unbegrenzt (inoffiziell) | Kein Limit |
| StockTwits | Unbegrenzt (inoffiziell) | Kein Limit, aber freiwillig drosseln |
| ApeWisdom | Unbegrenzt | Kein Limit |
| SimFin | Unbegrenzt (privat) | Kein Limit |

## Lösung: Priorisierte Scan-Warteschlange

```
Tier 0 (Pflicht, immer): Offene Positionen (~10–30 Aktien)
    → Voller 3-Ebenen-Scan, alle APIs nutzen

Tier 1 (Täglich): Zone-1-Aktien (~30–50 Aktien)
    → Voller Scan täglich

Tier 2 (Täglich): Zone-2-Aktien (~100 Aktien)
    → Technisch + Sentiment (Fundamentals aus Cache wenn <3 Tage alt)

Tier 3 (Täglich): Zone-3-Aktien (~200 Aktien)
    → Nur Technik via yfinance + ta-Bibliothek (kein API-Quota)

Tier 4 (Rotation): Zone-4-Rest (~550 Aktien)
    → 200 Aktien/Tag rotierend → jede Aktie alle ~3 Tage
    → Rotation-Index in configuration-Tabelle gespeichert
```

## Alpha-Vantage-Budget (25 Calls/Tag)

```
10 Calls → Tier 0 (offene Positionen, technische Indikatoren)
10 Calls → Top-10 Zone-1-Aktien nach Δ7T
 5 Calls → Reserve für manuelle UI-Anfragen
```

**Wichtig:** Alpha Vantage wird nur als Ergänzung genutzt. Der technische Score
wird primär mit der `ta`-Bibliothek auf yfinance-OHLCV-Daten berechnet – diese
Kombination ist unbegrenzt nutzbar.

## Fallback-Kette

| Datentyp | Primär | Fallback 1 | Fallback 2 |
|----------|--------|-----------|-----------|
| Technische Indikatoren | `ta` + yfinance | Alpha Vantage | — |
| News-Sentiment | Finnhub | Marketaux | Alpha Vantage |
| Fundamentaldaten | SimFin | yfinance | — |
| Insider-Transaktionen | Finnhub | yfinance | — |
| Earnings-Kalender | yfinance | Finnhub | — |

## Cache-TTLs

| Datentyp | TTL | Begründung |
|----------|-----|------------|
| OHLCV-Kursdaten | 4 Stunden | Für täglichen Scan ausreichend |
| Fundamentaldaten (KGV, FCF) | 24 Stunden | Ändert sich höchstens quartalsweise |
| News-Sentiment | 2 Stunden | Zeit-sensitiv, aber nicht minütlich |
| StockTwits Bullish-Ratio | 1 Stunde | Intraday-Stimmung |
| Earnings-Kalender | 24 Stunden | Termine ändern sich selten |
| Analysten-Ratings | 24 Stunden | Täglich ausreichend |

## Cache-Implementierung

Zweistufig:
1. **In-Memory Dict** (`backend/cache/store.py`): Blitzschnell, überlebt innerhalb eines Scans
2. **SQLite `api_cache`-Tabelle**: Persistiert über Neustarts, wird bei jedem Fetch zuerst geprüft

Cache-Key-Format: `"{source}:{data_type}:{ticker}"`  
Beispiele: `"finnhub:sentiment:AAPL"`, `"yfinance:ohlcv:NVDA"`, `"stocktwits:ratio:TSLA"`

## Tagesablauf des Scans (06:00 UTC)

```
06:00:00  Scan startet
06:00:10  StockTwits Trending → Universe updaten
06:00:30  Prioritätswarteschlange bauen
06:01:00  Tier 0 scannen (Positionen, ~5 Min)
06:06:00  Tier 1 scannen (Zone 1, ~15 Min)
06:21:00  Tier 2 scannen (Zone 2, ~20 Min)
06:41:00  Tier 3 scannen (Zone 3, ~25 Min, nur yfinance)
07:06:00  Tier 4 scannen (Zone 4 Rotation, ~30 Min, nur yfinance)
07:36:00  Portfolio-Monitor läuft
07:40:00  Telegram-Benachrichtigungen senden
07:45:00  Scan abgeschlossen, Status in configuration speichern
```

Gesamtdauer: ca. 1:45 Stunden. Zu 06:00 UTC = 08:00 CEST, rechtzeitig für die US-Börseneröffnung.
