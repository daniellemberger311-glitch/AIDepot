"""Scoring-Ebene 3: Sentiment-Analyse (max. 25 Punkte) + Unterdrückungslogik.

Kriterien:
  1. News-Sentiment (Finnhub + Marketaux)  – max. 8 Pkt.
  2. StockTwits Bullish-Ratio              – max. 7 Pkt.
  3. Reddit-Mention-Momentum (ApeWisdom)   – max. 5 Pkt.
  4. Analysten Upgrade/Downgrade (Finnhub) – max. 5 Pkt.

Unterdrückungsregel:
  Wenn (L1 + L2) > 50 UND L3 < 5
  → Gesamtscore wird auf max. 74 gedeckelt (kein Zone-1-Eintrag).
"""
import logging
from sqlalchemy.orm import Session

from backend.fetchers.finnhub_fetcher import FinnhubFetcher
from backend.fetchers.marketaux_fetcher import MarketauxFetcher
from backend.fetchers.stocktwits_fetcher import StockTwitsFetcher
from backend.fetchers.apewisdom_fetcher import ApeWisdomFetcher

logger = logging.getLogger(__name__)


# ── Einzelne Kriterien ──────────────────────────────────────────────────────

def score_news_sentiment(finnhub_score: float | None, marketaux_score: float | None) -> float:
    """
    Ø aus Finnhub + Marketaux News-Sentiment – max. 8 Pkt.
    Erwartet Werte im Bereich –1 bis +1.
    Gibt 2.0 zurück wenn keine Daten verfügbar (neutral).
    """
    scores = [s for s in [finnhub_score, marketaux_score] if s is not None]
    if not scores:
        return 2.0  # neutral: kein Datenverlust
    avg = sum(scores) / len(scores)
    if avg > 0.6:
        return 8.0
    if avg > 0.3:
        return 5.0
    if avg >= 0.0:
        return 2.0
    return 0.0


def score_stocktwits_ratio(bullish_ratio: float | None) -> float:
    """StockTwits Bullish-Ratio – max. 7 Pkt."""
    if bullish_ratio is None:
        return 3.0  # neutral
    r = bullish_ratio
    if r > 0.65:
        return 7.0
    if r >= 0.55:
        return 5.0
    if r >= 0.45:
        return 3.0
    return 0.0


def score_reddit_momentum(mentions_now: int, mentions_24h_ago: int) -> float:
    """
    Reddit-Mention-Momentum via ApeWisdom – max. 5 Pkt.
    Vergleich aktueller Wert vs. Wert von vor 24h.
    """
    if mentions_now == 0 and mentions_24h_ago == 0:
        return 1.0  # kein Signal, neutral
    if mentions_24h_ago == 0:
        return 3.0  # neu aufgetaucht → mittleres Signal
    change = (mentions_now - mentions_24h_ago) / max(mentions_24h_ago, 1)
    if change >= 0.50:
        return 5.0
    if change >= 0.20:
        return 3.0
    return 1.0


def score_analyst_delta(net_upgrade: int) -> float:
    """
    Analysten-Netto-Upgrades (ggü. Vormonat) – max. 5 Pkt.
    net_upgrade = (strongBuy+buy) aktuell – (strongBuy+buy) Vormonat
    """
    if net_upgrade >= 2:
        return 5.0
    if net_upgrade == 1:
        return 3.0
    if net_upgrade == 0:
        return 1.0
    return 0.0  # Netto-Downgrade


def apply_suppression_rule(l1: float, l2: float, l3: float) -> tuple[float, bool]:
    """
    Unterdrückungsregel: Stark negatives Sentiment bei guten Fundamentals/Technicals.
    Wenn (L1 + L2) > 50 UND L3 < 5 → Score gedeckelt auf 74 (kein Zone-1-Eintrag).
    Gibt (gedeckelter_score, wurde_unterdrückt) zurück.
    """
    total = l1 + l2 + l3
    if (l1 + l2) > 50 and l3 < 5:
        return min(total, 74.0), True
    return total, False


# ── Aggregator ──────────────────────────────────────────────────────────────

def compute_sentiment_score(ticker: str, db: Session) -> tuple[float, dict]:
    """
    Berechnet den Sentiment-Score (max. 25 Punkte).
    Gibt (total_score, breakdown_dict) zurück.
    """
    fh_f = FinnhubFetcher(db)
    mx_f = MarketauxFetcher(db)
    st_f = StockTwitsFetcher(db)
    aw_f = ApeWisdomFetcher(db)

    # DAX-/DE-Aktien: StockTwits und ApeWisdom sind US-only → neutral
    is_german = ticker.endswith(".DE")

    fh_sent = fh_f.get_news_sentiment(ticker)
    mx_sent = mx_f.get_news_sentiment(ticker)
    st_sent = st_f.get_sentiment_ratio(ticker) if not is_german else {"bullish_ratio": None, "total": 0}
    aw_ment = aw_f.get_mentions(ticker)        if not is_german else {"mentions": 0, "mentions_24h_ago": 0}
    analyst = fh_f.get_analyst_recommendations(ticker)

    # Nur Scores mit echten Artikeln einfließen lassen (0 bei fehlendem Key ausschließen)
    fh_news_val = fh_sent.get("sentiment_score") if fh_sent.get("articles_count", 0) > 0 else None
    mx_news_val = mx_sent.get("sentiment_score") if mx_sent.get("articles_count", 0) > 0 else None

    s_news    = score_news_sentiment(fh_news_val, mx_news_val)
    s_st      = score_stocktwits_ratio(st_sent.get("bullish_ratio"))
    s_reddit  = score_reddit_momentum(
        aw_ment.get("mentions", 0),
        aw_ment.get("mentions_24h_ago", 0),
    )
    s_analyst = score_analyst_delta(analyst.get("net_upgrade", 0))

    total = s_news + s_st + s_reddit + s_analyst

    breakdown = {
        "news_sentiment":   s_news,
        "stocktwits_ratio": s_st,
        "reddit_momentum":  s_reddit,
        "analyst_delta":    s_analyst,
        # Metadaten für Diagnose
        "_fh_score":        fh_sent.get("sentiment_score"),
        "_mx_score":        mx_sent.get("sentiment_score"),
        "_bullish_ratio":   st_sent.get("bullish_ratio"),
        "_mentions":        aw_ment.get("mentions", 0),
        "_mentions_24h":    aw_ment.get("mentions_24h_ago", 0),
    }

    logger.debug("Sentiment %s: %.1f/25 – News=%.0f ST=%.0f Reddit=%.0f Analyst=%.0f",
                 ticker, total, s_news, s_st, s_reddit, s_analyst)
    return round(total, 1), breakdown
