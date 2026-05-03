# Scoring-System: Vollständige Dokumentation

> **Status:** ✅ vollständig implementiert in `backend/scoring/`  
> Module: `fundamental.py`, `technical.py`, `sentiment.py`, `delta.py`, `options.py`, `orchestrator.py`

## Übersicht

Jede Aktie erhält täglich einen **Gesamtscore von 0–100**, der sich aus drei Ebenen zusammensetzt:

| Ebene | Inhalt | Gewichtung | Max. Punkte |
|-------|--------|------------|-------------|
| L1 | Fundamentalanalyse | 40% | 40 |
| L2 | Technische Analyse | 35% | 35 |
| L3 | Sentiment-Analyse | 25% | 25 |

**Gesamtscore = L1 + L2 + L3** (die Punkte addieren sich direkt auf 0–100)

---

## Ebene 1 – Fundamental (max. 40 Punkte)

| Kriterium | Max. Pkt. | Logik |
|-----------|-----------|-------|
| KGV vs. Sektorschnitt | 8 | <0,75x Sektor → 8; <1,0x → 6; <1,25x → 4; >1,5x → 0 |
| EPS-Überraschungs-Streak | 6 | +2 pro aufeinanderfolgendem Beat, max. 3 Quartale |
| Umsatzwachstum YoY | 6 | >20% → 6; 10–20% → 4; 0–10% → 2; negativ → 0 |
| FCF positiv + wachsend | 5 | FCF > 0 → 2; YoY gewachsen → +3 |
| Verschuldungsgrad (D/E) | 5 | <0,5 → 5; 0,5–1,0 → 3; 1,0–2,0 → 1; >2,0 → 0 |
| Insider-Käufe netto (90 Tage) | 5 | ≥3 Käufe → 5; 1–2 → 3; neutral → 1; Verkäufe netto → 0 |
| Earnings-Nähe (Katalysator) | 5 | 7–14 Tage vorher → 5; 3–7 Tage → 3; >14 Tage → 1 |

**Datenquellen:** yfinance (Fundamentals, Earnings), SimFin (KGV/FCF/EPS + Bilanz für D/E), Finnhub (Insider)

**Hinweis D/E-Ratio:** SimFin liefert D/E direkt aus der Bilanz (`Long Term Debt + Short Term Debt / Total Equity`). Fallback: yfinance `debtToEquity` (wird durch 100 normalisiert, da yfinance den Wert als Prozent ausgibt, z. B. 50.0 = 0,5×).

---

## Ebene 2 – Technisch (max. 35 Punkte)

| Kriterium | Max. Pkt. | Logik |
|-----------|-----------|-------|
| VCP-Muster erkannt | 10 | 3 Kontraktionen → 10; 2 → 7; 1 + Vol sinkt → 4 |
| Volumen-Kontraktion | 5 | 3W-Ø < 80% des 10W-Ø → 5; <90% → 3 |
| Preis-Nähe zu Widerstand | 5 | <3% unter Pivot/52W-Hoch → 5; 3–7% → 3; >10% → 0 |
| RSI 55–70 | 5 | RSI 55–70 → 5; 50–55 od. 70–75 → 3; sonst 0 |
| Relative Stärke vs. SPY | 4 | RS > 1,1 über 20 Tage → 4; 1,0–1,1 → 2; <1,0 → 0 |
| MACD-Signal | 3 | Histogramm positiv + steigend → 3; positiv flach → 1 |
| Bollinger-Squeeze | 3 | BB-Breite < 20. Perzentil (52W) → 3 |

### VCP-Erkennung (Volatility Contraction Pattern)

Das VCP-Muster nach Minervini ist der wichtigste technische Indikator:

1. Swing-Hochs der letzten 20 Wochen identifizieren
2. Jede Korrektur muss kleiner als die vorherige sein (Verhältnis < 0,85)
3. Volumen in Down-Wochen sinkt progressiv
4. Kurs innerhalb 10% des 52-Wochen-Hochs
5. Idealerweise 2–4 Kontraktionen erkennbar

**Datenquellen:** yfinance OHLCV, `ta`-Bibliothek für RSI/MACD/Bollinger/ATR

---

## Ebene 3 – Sentiment (max. 25 Punkte)

| Kriterium | Max. Pkt. | Logik |
|-----------|-----------|-------|
| News-Sentiment | 8 | Ø Finnhub + Marketaux: >0,6 → 8; 0,3–0,6 → 5; 0–0,3 → 2; negativ → 0 |
| StockTwits Bullish-Ratio | 7 | >65% → 7; 55–65% → 5; 45–55% → 3; <45% → 0 |
| Reddit-Mention-Momentum | 5 | ApeWisdom: +50% vs. 7T-Ø → 5; +20–50% → 3; flach → 1 |
| Analysten Upgrade/Downgrade | 5 | ≥2 Netto-Upgrades (30T) → 5; 1 → 3; neutral → 1; Downgrade → 0 |

**Hinweis für deutsche Aktien (`.DE`-Suffix):** StockTwits und ApeWisdom sind US-exklusive Dienste. Für Ticker wie `SAP.DE` werden diese Quellen übersprungen und Standardwerte eingesetzt (Bullish-Ratio: neutral 3/7 Punkte, Reddit-Momentum: 1/5 Punkte). Finnhub-Aufrufe normalisieren das Symbol automatisch (`SAP.DE` → `SAP`).

### Unterdrückungslogik

**Wenn:** L1 + L2 kombiniert > 50 **UND** L3-Score < 5  
**Dann:** Gesamtscore wird auf max. 74 gedeckelt → kein Zone-1-Eintrag  
**Zweck:** Verhindert Empfehlungen trotz stark negativem Sentiment

---

## Zonen-Zuweisung

| Zone | Score | Bedeutung | Aktion |
|------|-------|-----------|--------|
| 1 | ≥ 76 | Signal Aktiv | Optionsschein-Empfehlung ausgeben |
| 2 | 61–75 | Aufbau erkannt | VCP aktiv, beobachten |
| 3 | 41–60 | Auf dem Radar | Erste Anzeichen |
| 4 | < 41 | Universum | Täglich gescannt |

---

## Delta-Berechnung

```
Δ1T  = Score(heute) − Score(gestern)
Δ7T  = Score(heute) − Score(vor 7 Tagen)
Δ30T = Score(heute) − Score(vor 30 Tagen)
```

Alle Werte werden in `score_history` persistiert. Fehlende Historie → `None`.

### Notification-Trigger

| Trigger | Bedingung | Typ |
|---------|-----------|-----|
| Zonen-Aufstieg | Zone wechselt aufwärts | `ZONE_CHANGE` |
| 7T-Trend | 3 aufeinanderfolgende tägliche Anstiege | `STREAK_7D` |
| Δ1T-Spike | Δ1T > +15 an einem Tag | `DELTA_SPIKE` |
| Exit-Warnung | Score-Fall > −15 oder KO < 8% | `EXIT_WARNING` |

---

## Optionsschein-Empfehlung (nur Zone 1)

Abgeleitet aus Score-Kontext + ATR:

| Parameter | Logik |
|-----------|-------|
| Richtung | CALL (Standard); PUT nur wenn Δ7T < −5 |
| Hebel | ATR/Kurs < 2% → 5–6x; 2–3% → 5–7x; >3% → 6–8x |
| Laufzeit | 8 Wochen Basis; +2 Wochen wenn Earnings ≤ 6 Wochen |
| KO-Abstand | max(12%, 3 × ATR%) |
| Einstieg | Aktueller Kurs × 1,02 (2% über aktuellem Niveau) |
| Stop-Loss | Letzter Pivot-Tief (aus OHLCV) |

> **Hebelbereich statt Fixwert:** Die Empfehlung gibt immer eine Range aus (`leverage_min`/`leverage_max`), da das optimale Niveau von Volatilität und Restlaufzeit des konkreten Scheins abhängt.

---

## Exit-Signale (Portfolio-Beobachtung)

| Signal | Schwelle | Priorität | Empfehlung |
|--------|----------|-----------|------------|
| Score-Rückgang | > −15 seit Kauf | 🔴 Sofort | VERKAUFEN |
| KO-Abstand | < 8% | 🔴 Sofort | VERKAUFEN |
| Restlaufzeit | < 3 Wochen | 🟡 Prüfen | ROLLEN |
| Sentiment-Einbruch | Bullish-Ratio < 35% | 🟡 Beobachten | BEOBACHTEN |
| Kursziel erreicht | Konfigurierbar | 🟢 Gewinn | GEWINNNEHMEN |

---

## Gewichtungen anpassen

Die Standardgewichtungen (40/35/25) können in der App-Konfiguration geändert werden.  
Gespeichert in `configuration`-Tabelle, Schlüssel: `weight_fundamental`, `weight_technical`, `weight_sentiment`.  
Änderungen wirken ab dem nächsten Scan.
