#!/usr/bin/env python3
"""Scoring-Diagnose: Einzelne Ticker vollständig analysieren.

Verwendung:
    python scripts/score_debug.py MU AMD NVDA NBIS TWLO APLD
"""
import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s – %(message)s")

from backend.database import SessionLocal, init_db
from backend.scoring.fundamental import compute_fundamental_score
from backend.scoring.technical   import compute_technical_score
from backend.scoring.sentiment   import compute_sentiment_score, apply_suppression_rule
from backend.scoring.orchestrator import _assign_zone


def score_ticker_debug(ticker: str, db):
    print(f"\n{'='*64}")
    print(f"  {ticker}")
    print(f"{'='*64}")

    l1, l1_bd = compute_fundamental_score(ticker, db)
    l2, l2_bd = compute_technical_score(ticker, db)
    l3, l3_bd = compute_sentiment_score(ticker, db)
    total, suppressed = apply_suppression_rule(l1, l2, l3)
    zone = _assign_zone(total)

    print(f"\n  GESAMT:  {total:.1f}/100  →  Zone {zone}{'  (Unterdrückung aktiv)' if suppressed else ''}")
    print(f"  L1 Fundamental: {l1:.1f}/40")
    print(f"  L2 Technical:   {l2:.1f}/35")
    print(f"  L3 Sentiment:   {l3:.1f}/25")

    print(f"\n  ── L1 Breakdown ──")
    for k, v in l1_bd.items():
        if not k.startswith("_"):
            print(f"    {k:<25} {v:.1f}")
    meta_keys = ["_pe_ratio", "_sector", "_growth_rate", "_days_earn"]
    for k in meta_keys:
        if k in l1_bd and l1_bd[k] is not None:
            print(f"    {k:<25} {l1_bd[k]}")

    print(f"\n  ── L2 Breakdown ──")
    for k, v in l2_bd.items():
        print(f"    {k:<25} {v:.1f}")

    print(f"\n  ── L3 Breakdown ──")
    for k, v in l3_bd.items():
        if not k.startswith("_"):
            print(f"    {k:<25} {v:.1f}")
    for k in ["_fh_score", "_mx_score", "_bullish_ratio", "_mentions", "_mentions_24h"]:
        if k in l3_bd:
            print(f"    {k:<25} {l3_bd[k]}")

    return total, zone


if __name__ == "__main__":
    tickers = sys.argv[1:] or ["MU", "AMD", "NVDA", "NBIS", "TWLO", "APLD"]
    print(f"Analysiere: {', '.join(tickers)}")
    print("(Nutzt Cache – erste Ausführung kann einige Sekunden dauern)")

    with SessionLocal() as db:
        results = []
        for t in tickers:
            try:
                total, zone = score_ticker_debug(t, db)
                results.append((t, total, zone))
            except Exception as e:
                print(f"\n  FEHLER bei {t}: {e}")

    print(f"\n{'='*64}")
    print("  ZUSAMMENFASSUNG")
    print(f"{'='*64}")
    for t, score, zone in sorted(results, key=lambda x: -x[1]):
        bar = "█" * int(score // 5)
        print(f"  {t:<8} Z{zone}  {score:5.1f}/100  {bar}")
