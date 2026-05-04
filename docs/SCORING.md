# Scoring-System: Vollständige Dokumentation

> **Status:** ✅ vollständig implementiert in `backend/scoring/`  
> Module: `fundamental.py`, `technical.py`, `sentiment.py`, `delta.py`, `options.py`, `orchestrator.py`  
> Unit-Tests: `tests/scoring/` – 116 Tests für alle Scoring-Funktionen

---

## Übersicht

Jede Aktie erhält täglich einen **Gesamtscore von 0–100**, der sich aus drei Ebenen zusammensetzt:

| Ebene | Inhalt | Gewichtung | Max. Punkte |
|-------|--------|------------|-------------|
| L1 | Fundamentalanalyse | 40% | 40 |
| L2 | Technische Analyse | 35% | 35 |
| L3 | Sentiment-Analyse | 25% | 25 |

**Gesamtscore = L1 + L2 + L3** (addieren sich direkt auf 0–100)

---

## Ebene 1 – Fundamental (max. 40 Punkte)

| Kriterium | Max. Pkt. | Logik |
|-----------|-----------|-------|
| KGV vs. Sektorschnitt | 8 | <0,75x Sektor → 8; <1,0x → 6; <1,25x → 4; <1,5x → 2; ≥1,5x → 0 |
| EPS-Überraschungs-Streak | 6 | +2 pro aufeinanderfolgendem Beat, max. 3 Quartale |
| Umsatzwachstum YoY | 6 | >20% → 6; 10–20% → 4; 0–10% → 2; negativ → 0 |
| FCF positiv + wachsend | 5 | FCF > 0 → 2; YoY gewachsen → +3 |
| Verschuldungsgrad (D/E) | 5 | <0,5 → 5; 0,5–1,0 → 3; 1,0–2,0 → 1; >2,0 → 0 |
| Insider-Käufe netto (90 Tage) | 5 | ≥3 Netto-Käufe → 5; 1–2 → 3; neutral → 1; Netto-Verkäufe → 0 |
| Earnings-Nähe (Katalysator) | 5 | 7–14 Tage vorher → 5; 3–7 Tage → 3; >14 Tage oder <3 Tage → 1 |

**Datenquellen:** yfinance (Fundamentals, Earnings-Kalender), SimFin (FCF/Bilanz für D/E), Finnhub (Insider-Transaktionen)

**Hinweis D/E-Ratio:** yfinance gibt `debtToEquity` als Prozent aus (z. B. 50.0 = 0,5× D/E) und wird durch 100 normalisiert. SimFin berechnet direkt aus der Bilanz.

**Fehlende Daten:** Wenn ein Wert nicht verfügbar ist, wird ein neutraler Wert vergeben (z. B. PE: 2 Pkt., D/E: 2 Pkt., Earnings: 1 Pkt.), um fehlende APIs nicht zu bestrafen.

---

## Ebene 2 – Technisch (max. 35 Punkte)

| Kriterium | Max. Pkt. | Logik |
|-----------|-----------|-------|
| VCP-Muster erkannt | 10 | 3 Kontraktionen → 10; 2 → 7; 1 + Volumen sinkt → 4 |
| Volumen-Kontraktion | 5 | 3W-Ø < 80% des 10W-Ø → 5; <90% → 3 |
| Preis-Nähe zu Widerstand | 5 | <3% unter Pivot/52W-Hoch → 5; 3–7% → 3; 7–10% → 1; >10% → 0 |
| RSI 55–70 | 5 | RSI 55–70 → 5; 50–55 od. 70–75 → 3; sonst 0 |
| Relative Stärke vs. SPY | 4 | RS > 1,1 über 20 Handelstage → 4; 1,0–1,1 → 2; <1,0 → 0 |
| MACD-Signal | 3 | Histogramm positiv + steigend → 3; positiv flach → 1 |
| Bollinger-Squeeze | 3 | BB-Breite < 20. Perzentil (letzten 52 Wochen) → 3 |

**Datenquellen:** yfinance OHLCV (täglich + wöchentlich), `ta`-Bibliothek für RSI/MACD/Bollinger

### VCP-Erkennung (Volatility Contraction Pattern nach Minervini)

Das VCP-Muster ist der wichtigste technische Indikator – max. 10 Punkte:

1. **Pflichtbedingung:** Kurs innerhalb 10% des 52-Wochen-Hochs
2. Swing-Hochs der letzten 20 Wochen identifizieren
3. Für jedes Swing-Hoch die Tiefe der folgenden Korrektur messen
4. **Kontraktion zählen** wenn jede Tiefe < 85% der vorherigen (progressiv kleiner)
5. Volumen in Konsolidierungsphasen sinkt progressiv

| Kontraktionen | Volumen sinkt | Punkte |
|---------------|---------------|--------|
| ≥ 3 | egal | 10 |
| 2 | egal | 7 |
| 1 | ja | 4 |
| < 1 oder zu weit vom Hoch | – | 0 |

---

## Ebene 3 – Sentiment (max. 25 Punkte)

| Kriterium | Max. Pkt. | Logik |
|-----------|-----------|-------|
| News-Sentiment | 8 | Ø Finnhub + Marketaux (–1 bis +1): >0,6 → 8; 0,3–0,6 → 5; 0–0,3 → 2; negativ → 0 |
| StockTwits Bullish-Ratio | 7 | >65% → 7; 55–65% → 5; 45–55% → 3; <45% → 0 |
| Reddit-Mention-Momentum | 5 | ApeWisdom: ≥+50% vs. 24h → 5; +20–50% → 3; flach/neu → 1 |
| Analysten Upgrade/Downgrade | 5 | ≥2 Netto-Upgrades (30T) → 5; 1 → 3; neutral → 1; Downgrade → 0 |

**Datenquellen:** Finnhub (News + Analyst-Ratings), Marketaux (News), StockTwits (Stimmung), ApeWisdom (Reddit)

**Deutsche Aktien (`.DE`-Suffix):** StockTwits und ApeWisdom liefern keine DE-Daten.  
→ StockTwits-Score: 3/7 (neutral), Reddit-Score: 1/5 (neutral). Finnhub normalisiert `SAP.DE` → `SAP`.

### Unterdrückungsregel

**Bedingung:** L1 + L2 > 50 **UND** L3 < 5  
**Wirkung:** Gesamtscore wird auf max. 74 gedeckelt → kein Zone-1-Eintrag  
**Zweck:** Verhindert Empfehlungen trotz stark negativem Sentiment bei guten Fundamentals/Technicals

Beispiel: L1=38, L2=34, L3=4 → Total=76 → gedeckelt auf 74 (Zone 2 statt Zone 1)

---

## Zonen-Zuweisung

| Zone | Score | Bedeutung | Aktion |
|------|-------|-----------|--------|
| 1 | ≥ 76 | Signal Aktiv | Optionsschein-Empfehlung ausgeben |
| 2 | 61–75 | Aufbau erkannt | VCP aktiv, beobachten |
| 3 | 41–60 | Auf dem Radar | Erste Anzeichen |
| 4 | < 41 | Universum | Täglich gescannt (Zone-4-Rotation) |

---

## Delta-Berechnung

```
Δ1T  = Score(heute) − Score(gestern)
Δ7T  = Score(heute) − Score(vor 7 Tagen)
Δ30T = Score(heute) − Score(vor 30 Tagen)
```

Alle Werte werden in `score_history` persistiert. Fehlende Historie → `None`.

### Notification-Trigger

| Trigger | Bedingung | Telegram-Typ |
|---------|-----------|--------------|
| Zonen-Aufstieg | Zone wechselt aufwärts (z. B. Z3 → Z2) | `ZONE_CHANGE` |
| 7T-Trend | 3 aufeinanderfolgende Tagesanstiege | `STREAK_7D` |
| Δ1T-Spike | Δ1T > +15 an einem Tag | `DELTA_SPIKE` |
| Exit-Warnung | Score-Fall > −15 oder KO-Abstand < 8% | `EXIT_WARNING` |

---

## Optionsschein-Empfehlung (nur Zone 1)

Abgeleitet aus Score-Kontext + ATR (Average True Range):

| Parameter | Logik |
|-----------|-------|
| Richtung | CALL (Standard); PUT nur wenn Δ7T < −5 |
| Hebel | ATR/Kurs < 2% → 5–6×; 2–3% → 5–7×; >3% → 6–8× |
| Laufzeit | 8 Wochen Basis; +2 Wochen wenn Earnings innerhalb 6 Wochen |
| KO-Abstand | max(12%, 3 × ATR%) |
| Entry-Trigger | Aktueller Kurs × 1,02 (2% über Tagesschluss) |
| Stop-Loss | Letztes Pivot-Tief (aus OHLCV-Daten) |

> **Hebelbereich statt Fixwert:** Die Empfehlung gibt immer eine Range aus (`leverage_min` / `leverage_max`), da das optimale Niveau von der Volatilität und Restlaufzeit des konkreten Scheins abhängt.

---

## Exit-Signale (Portfolio-Beobachtung)

| Signal | Schwelle (Standard) | Priorität | Empfehlung |
|--------|---------------------|-----------|------------|
| Score-Rückgang | > −15 seit Kauf | 🔴 Sofort | VERKAUFEN |
| KO-Abstand | < 8% | 🔴 Sofort | VERKAUFEN |
| Restlaufzeit | < 3 Wochen | 🟡 Prüfen | ROLLEN |
| Sentiment-Einbruch | Bullish-Ratio < 35% | 🟡 Beobachten | BEOBACHTEN |

Alle Schwellen sind in `/config` konfigurierbar (Felder `exit_score_drop`, `exit_ko_distance`, `exit_expiry_weeks`, `exit_bull_ratio`).

---

## Gewichtungen anpassen

Standardgewichtungen (40/35/25) können in `/config` (Tab „Gewichtungen") geändert werden.  
Gespeichert in `configuration`-Tabelle, Schlüssel: `weight_fundamental`, `weight_technical`, `weight_sentiment`.  
Änderungen wirken ab dem nächsten Scan.

---

## Unit-Tests

Die Scoring-Funktionen sind vollständig durch Unit-Tests abgedeckt:

```bash
python -m pytest tests/scoring/ -q
# 116 Tests: Fundamental (40) + Sentiment (41) + Technical (35)
```

Alle Funktionen sind pure (keine DB-Abhängigkeit), synthetische DataFrames simulieren OHLCV-Daten für L2.
