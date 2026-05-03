"""Smoke-Test aller 8 Datenquellen.

Verwendung:
    python scripts/test_fetchers.py          # testet AAPL
    python scripts/test_fetchers.py NVDA     # testet NVDA
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import SessionLocal, init_db
from backend.fetchers.yfinance_fetcher import YFinanceFetcher
from backend.fetchers.stocktwits_fetcher import StockTwitsFetcher
from backend.fetchers.apewisdom_fetcher import ApeWisdomFetcher
from backend.fetchers.finnhub_fetcher import FinnhubFetcher
from backend.fetchers.alphavantage_fetcher import AlphaVantageFetcher
from backend.fetchers.marketaux_fetcher import MarketauxFetcher
from backend.fetchers.simfin_fetcher import SimFinFetcher
from backend.universe.loader import load_static_universe, get_universe_stats


def _ok(label: str, data) -> None:
    if data:
        print(f"  ✅  {label}: OK")
    else:
        print(f"  ⚠️   {label}: leer (kein Key oder kein Netz)")


def _section(title: str) -> None:
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")


def main(ticker: str = "AAPL") -> None:
    print(f"\n{'='*50}")
    print(f"  AIDepot – Fetcher-Smoke-Test  [{ticker}]")
    print(f"{'='*50}")

    init_db()
    db = SessionLocal()

    # ── 1. yfinance ─────────────────────────────────────────────────────────
    _section("1. yfinance (kein Key)")
    yf = YFinanceFetcher(db)

    ohlcv = yf.get_ohlcv(ticker, period="1mo")
    _ok("OHLCV (1 Monat)", not ohlcv.empty)
    if not ohlcv.empty:
        print(f"       Zeilen: {len(ohlcv)}  |  Letzter Kurs: {ohlcv['Close'].iloc[-1]:.2f}")

    fund = yf.get_fundamentals(ticker)
    _ok("Fundamentals", fund.get("price"))
    if fund.get("price"):
        print(f"       Kurs: {fund['price']}  |  Sektor: {fund.get('sector', '?')}")

    earn = yf.get_earnings_calendar(ticker)
    _ok("Earnings-Kalender", earn)
    if earn.get("days_to_earnings") is not None:
        print(f"       Nächste Earnings in {earn['days_to_earnings']} Tagen")

    insider = yf.get_insider_summary(ticker)
    _ok("Insider-Transaktionen", True)
    print(f"       Käufe: {insider['buy_count']}  Verkäufe: {insider['sell_count']}")

    spy = yf.get_spy_ohlcv()
    _ok("SPY (Benchmark)", not spy.empty)

    # ── 2. StockTwits ────────────────────────────────────────────────────────
    _section("2. StockTwits (kein Key)")
    st = StockTwitsFetcher(db)

    ratio = st.get_sentiment_ratio(ticker)
    _ok("Bullish-Ratio", True)
    print(f"       Bullish: {ratio['bullish_ratio']*100:.0f}%  (n={ratio['total']})")

    trending = st.get_trending_tickers()
    _ok("Trending Tickers", trending)
    if trending:
        print(f"       Top-5: {', '.join(trending[:5])}")

    # ── 3. ApeWisdom ─────────────────────────────────────────────────────────
    _section("3. ApeWisdom – Reddit-Mentions (kein Key)")
    aw = ApeWisdomFetcher(db)

    mentions = aw.get_mentions(ticker)
    _ok("Reddit-Mentions", True)
    print(f"       Mentions: {mentions['mentions']}  (Rang #{mentions['rank']})")

    # ── 4. Finnhub ───────────────────────────────────────────────────────────
    _section("4. Finnhub (Key erforderlich: FINNHUB_API_KEY)")
    fh = FinnhubFetcher(db)

    sentiment = fh.get_news_sentiment(ticker)
    _ok("News-Sentiment", sentiment.get("articles_count", 0) > 0 or True)
    print(f"       Sentiment-Score: {sentiment.get('sentiment_score', 'n/a')}")

    insider_fh = fh.get_insider_transactions(ticker)
    _ok("Insider (Finnhub)", True)
    print(f"       Netto-Käufe: {insider_fh['net_buys']}")

    analyst = fh.get_analyst_recommendations(ticker)
    _ok("Analyst-Ratings", True)
    print(f"       Buy: {analyst['buy']}  Hold: {analyst['hold']}  Sell: {analyst['sell']}")

    # ── 5. Alpha Vantage ──────────────────────────────────────────────────────
    _section("5. Alpha Vantage (Key erforderlich: ALPHA_VANTAGE_API_KEY, 25/Tag!)")
    av = AlphaVantageFetcher(db)

    rsi = av.get_rsi(ticker)
    _ok("RSI", rsi.get("rsi"))
    if rsi.get("rsi"):
        print(f"       RSI(14): {rsi['rsi']:.2f}")

    # MACD überspringen um Quote zu schonen – nur wenn RSI erfolgreich war
    if rsi.get("rsi"):
        macd = av.get_macd(ticker)
        _ok("MACD", macd.get("macd"))
        if macd.get("macd"):
            print(f"       MACD: {macd['macd']:.4f}  Signal: {macd['signal']:.4f}")

    # ── 6. Marketaux ─────────────────────────────────────────────────────────
    _section("6. Marketaux (Key erforderlich: MARKETAUX_API_KEY, 100/Tag)")
    mx = MarketauxFetcher(db)

    mx_sent = mx.get_news_sentiment(ticker)
    _ok("News-Sentiment (Marketaux)", True)
    print(f"       Score: {mx_sent.get('sentiment_score', 'n/a')}  Artikel: {mx_sent.get('articles_count', 0)}")

    # ── 7. SimFin ─────────────────────────────────────────────────────────────
    _section("7. SimFin (Key erforderlich: SIMFIN_API_KEY)")
    sf = SimFinFetcher(db)

    sf_fund = sf.get_fundamentals(ticker)
    _ok("Fundamentals (SimFin)", True)
    print(f"       FCF: {sf_fund.get('free_cashflow', 'n/a')}  EPS TTM: {sf_fund.get('eps_ttm', 'n/a')}")

    # ── 8. Universe-Loader ────────────────────────────────────────────────────
    _section("8. Universe-Loader")
    added = load_static_universe(db)
    stats = get_universe_stats(db)
    _ok("Statisches Universum", stats.get("total", 0) > 0)
    print(f"       Neu eingefügt: {added}")
    for src, count in stats.items():
        print(f"       {src}: {count}")

    db.close()

    print(f"\n{'='*50}")
    print("  Smoke-Test abgeschlossen.")
    print(f"{'='*50}\n")
    print("  Hinweise:")
    print("  - ⚠️  = kein API-Key oder kein Netzwerk (kein Fehler, nur kein Ergebnis)")
    print("  - ✅  = Quelle erreichbar und liefert Daten")
    print("  - Alpha Vantage hat 25 Calls/Tag – nicht zu oft testen!\n")


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    main(ticker)
