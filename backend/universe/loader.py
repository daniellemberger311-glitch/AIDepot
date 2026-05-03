"""Universum-Loader: ~850 US-Aktien aus S&P 500, NASDAQ 100, Russell 2000 Top-200,
persönlicher Watchlist und StockTwits Trending.

Die statischen Listen (SP500, NASDAQ100, RUSSELL200) sind hart codiert und werden
einmal beim Start in die stocks-Tabelle geschrieben. Trending-Ticker werden täglich
aktualisiert.
"""
import logging
from sqlalchemy.orm import Session
from backend.models import Stock

logger = logging.getLogger(__name__)

# ── S&P 500 (Stand: Q1 2025, repräsentative Auswahl; vollständige Liste via Wikipedia) ──
SP500_TICKERS: list[str] = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","BRK-B","TSLA","AVGO","JPM",
    "LLY","UNH","V","XOM","MA","JNJ","PG","COST","HD","MRK","ABBV","CVX",
    "KO","BAC","PEP","WMT","NFLX","CRM","AMD","ADBE","ACN","MCD","TMO","CSCO",
    "ABT","ORCL","LIN","DHR","WFC","TXN","VZ","PM","NEE","AMGN","INTC","RTX",
    "SPGI","HON","UPS","MS","BMY","T","LOW","INTU","ISRG","CAT","SYK","GE",
    "MDT","DE","AXP","MDLZ","PLD","CB","CI","ADI","REGN","TJX","VRTX","ZTS",
    "GILD","MO","MMC","USB","SO","EOG","NOC","SHW","CL","DUK","ITW","AON",
    "ICE","HCA","MCO","BDX","F","PSX","NSC","BSX","D","EMR","PH","SRE","APD",
    "WM","GD","ETN","TGT","KLAC","MCHP","LRCX","FCX","ADP","MET","CHTR","COF",
    "MNST","EW","CTAS","FTNT","ANET","PCAR","IDXX","MSCI","MSI","CME","ROST",
    "AIG","AFL","LHX","HUM","WBA","ECL","GIS","HSY","K","CPB","SWK","NUE",
    "URI","PKG","ALB","LYB","IFF","FMC","MOS","CF","OXY","HAL","SLB","BKR",
    "DVN","FANG","MRO","COP","PSA","SPG","O","WELL","AVB","EQR","ARE","DRE",
    "PXD","VLO","MPC","HES","IP","WRK","SEE","BALL","ATR","ROP","PAYX","FAST",
    "GPC","CINF","LNC","PRU","ALL","HIG","GL","MKL","RE","AJG","MMB","TRV",
    "ACGL","ERIE","RNR","KMPR","THG","NWBI","FNF","FAF","MTG","RDN",
]

# ── NASDAQ 100 (Stand: Q1 2025) ──
NASDAQ100_TICKERS: list[str] = [
    "AAPL","MSFT","NVDA","AMZN","META","TSLA","GOOGL","AVGO","COST","NFLX",
    "AMD","ADBE","ASML","QCOM","INTC","INTU","CSCO","PEP","TMUS","AMAT",
    "TXN","AMGN","HON","SBUX","GILD","ISRG","BKNG","LRCX","ADI","REGN",
    "PANW","VRTX","MDLZ","MELI","KLAC","CDNS","SNPS","FTNT","ABNB","MCHP",
    "CTAS","ORLY","ROP","IDXX","CRWD","DXCM","ILMN","PYPL","PCAR","ADP",
    "EXC","XEL","CHTR","NXPI","FAST","ROST","SGEN","BIIB","MRNA","KDP",
    "CEG","AEP","DLTR","SIRI","TEAM","ANSS","VRSK","ZS","ALGN","DDOG",
    "MDB","TTD","CPRT","FANG","TTWO","CDW","GEHC","GFS","ON","ODFL","CSGP",
    "WBD","LCID","RIVN","ZM","DOCU","OKTA","SPLK","WDAY","VEEV","HUBS",
    "BILL","GTLB","NET","CFLT","HOOD","COIN","RBLX","SNAP","PINS","LYFT",
]

# ── Russell 2000 Top-200 nach Marktkapitalisierung (Stand: Q1 2025) ──
RUSSELL200_TICKERS: list[str] = [
    "SMCI","INSM","AXON","SAIA","ONTO","BOOT","ITCI","CAVA","LNTH","KTOS",
    "AAON","ENPH","BFLY","CPRX","HRMY","MGNI","SFM","KYMR","ASTS","ARWR",
    "RCUS","TMDX","ACMR","IRTC","NTRA","IDYA","BCRX","PTCT","SPRY","ROIV",
    "AGIO","KROS","MRUS","EDIT","FATE","BEAM","NTLA","CRSP","VERV","RARE",
    "BCAB","ALKS","ACAD","ADMA","ARDX","AVIR","BHVN","BNGO","CBPO","CDMO",
    "CLOV","CMRX","CNTA","CODX","COGT","CPHI","CRNX","DCPH","DFIN","DNLI",
    "DTIL","DVAX","DYAI","EGRX","ELYM","ENVA","EPZM","ESTA","ETNB","EVER",
    "FGEN","FOLD","FORM","FROG","FWRG","GERN","GNPX","GRPH","HALO","HIMS",
    "HLVX","HPCO","HRTG","HTBK","IBEX","ICAD","ICCC","IDEX","IMAB","IMGN",
    "IMVT","INVA","IONS","IOVA","IPHA","IRWD","ISEE","ITER","ITOS","JAGX",
    "JANX","JNPR","JOBY","KALA","KALV","KPTI","KRTX","KYMR","LBPH","LGND",
    "LMNX","LPSN","LQDA","LQDT","LWAY","MCRB","MDXG","MGNX","MGTA","MIRM",
    "MKSI","MLTX","MNKD","MODV","MORF","MRNS","MSRT","MTEM","MTTR","NABL",
    "NBTX","NCNA","NEOS","NERV","NKTR","NMRA","NRXP","NTRA","NTST","NUVL",
    "NVAX","NVCR","NVST","NXST","NYMX","NYNY","OCGN","OCUL","OMER","ONCT",
    "OPRA","OPTN","ORGO","OTIC","OVID","OXSQ","PBAX","PCSA","PDCE","PDFS",
    "PHAT","PLRX","PMVP","PNTM","PRAX","PRCT","PRLD","PRME","PRTA","PRTS",
    "PSNL","PTGX","PTLO","PTSI","PULM","PYPD","QNST","RAPT","RCKT","RLAY",
    "RLMD","RMBI","RMED","RMNI","RPID","RPRX","RRBI","RTLX","RUBY","RZLT",
]

# Deduplizierte Gesamtliste
_ALL_STATIC: dict[str, str] = {}
for t in SP500_TICKERS:
    _ALL_STATIC[t] = "SP500"
for t in NASDAQ100_TICKERS:
    _ALL_STATIC.setdefault(t, "NASDAQ100")
for t in RUSSELL200_TICKERS:
    _ALL_STATIC.setdefault(t, "RUSSELL200")


def load_static_universe(db: Session) -> int:
    """Schreibt alle statischen Ticker in die stocks-Tabelle (INSERT OR IGNORE).
    Gibt Anzahl neu eingefügter Zeilen zurück.
    """
    added = 0
    for ticker, source in _ALL_STATIC.items():
        existing = db.get(Stock, ticker)
        if not existing:
            db.add(Stock(ticker=ticker, universe_source=source, is_active=1))
            added += 1
    db.commit()
    logger.info("Universum geladen: %d neue Ticker (Gesamt statisch: %d)", added, len(_ALL_STATIC))
    return added


def add_trending_tickers(db: Session, tickers: list[str]) -> int:
    """Fügt StockTwits-Trending-Ticker als Quelle TRENDING hinzu."""
    added = 0
    for ticker in tickers:
        if ticker and len(ticker) <= 10:
            existing = db.get(Stock, ticker)
            if not existing:
                db.add(Stock(ticker=ticker, universe_source="TRENDING", is_active=1))
                added += 1
            elif existing.universe_source == "TRENDING":
                pass  # schon vorhanden
    if added:
        db.commit()
    return added


def add_personal_ticker(db: Session, ticker: str, name: str = "") -> bool:
    """Fügt einen Ticker zur persönlichen Watchlist hinzu."""
    existing = db.get(Stock, ticker)
    if existing:
        return False
    db.add(Stock(ticker=ticker, name=name, universe_source="WATCHLIST", is_active=1))
    db.commit()
    return True


def get_all_active_tickers(db: Session) -> list[str]:
    """Alle aktiven Ticker im Universum."""
    return [s.ticker for s in db.query(Stock).filter(Stock.is_active == 1).all()]


def get_universe_stats(db: Session) -> dict:
    """Anzahl Ticker pro Quelle."""
    rows = db.query(Stock.universe_source, Stock.is_active).all()
    stats: dict[str, int] = {}
    for source, active in rows:
        if active:
            stats[source] = stats.get(source, 0) + 1
    stats["total"] = sum(stats.values())
    return stats
