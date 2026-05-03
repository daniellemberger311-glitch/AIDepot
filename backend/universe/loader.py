"""Universum-Loader: ~850+ US-Aktien + optional DAX 40.

Aufbau (Priorität):
  1. S&P 500 + NASDAQ 100 + Russell 200 + S&P 400 Mid Cap + DAX 40 (hardkodiert, Stand Q1 2025)
  2. Wikipedia-Fetch bei Internetverbindung → hält Listen automatisch aktuell (wöchentlich)
  3. Alpha Vantage LISTING_STATUS → NYSE/NASDAQ-Reserve (wöchentlich, 1 Credit)
  4. StockTwits Trending (täglich, durch scheduler.py ergänzt)
  5. Persönliche Watchlist (manuell via API oder direkt)

Scan-Strategie (Mindestfrequenz: alle Aktien ≥ 1x/Woche):
  Tier 0 – gehaltene Positionen:   täglich, alle APIs
  Tier 1 – Zone 1+2 (~150):        täglich, alle APIs
  Tier 2 – Zone 3 (~200):          täglich, yfinance+ta+StockTwits (keine Quota-APIs)
  Tier 3 – Zone 4 (~500+):         200/Tag rotierend (konfigurierbar)
                                    → 500 Aktien / 200 pro Tag = 2,5 Tage
                                    → bis 1.400 Zone-4-Aktien wöchentlich garantiert

Aktualisierung der Index-Listen:
  - Automatisch: wöchentlich sonntags 02:00 UTC via Wikipedia-Fetch (scheduler.py)
  - Manuell: POST /api/universe/refresh (Frontend-Button auf Konfig-Seite)
  - Hardkodierte Listen: Stand Q1 2025 (Fallback wenn kein Internetzugang)

DAX-Hinweis:
  Deutsche Aktien werden mit .DE-Suffix gespeichert (SAP.DE, SIE.DE).
  yfinance unterstützt .DE; alle relativen Berechnungen (RSI, VCP, Momentum)
  funktionieren währungsunabhängig. Sentiment-Quellen (StockTwits, ApeWisdom)
  liefern für .DE-Ticker kaum Daten → Sentiment-Score = neutral 12,5/25.
"""
import logging
import time
import requests
import csv
import io
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import Stock, Configuration

logger = logging.getLogger(__name__)

# ── S&P 500 – vollständige Liste (Stand Q1 2025, ~503 Ticker) ─────────────────
SP500_TICKERS: list[str] = [
    # A
    "AAPL","ABBV","ABNB","ABT","ACGL","ADP","ADBE","ADI","ADM",
    "AEE","AEP","AES","AFL","AIG","AIZ","AJG","AKAM","ALB","ALGN",
    "ALL","ALLE","ALNY","AMAT","AMCR","AMD","AME","AMGN","AMP","AMT",
    "AMZN","ANET","AON","AOS","APA","APD","APH","APTV","ARE","ATO",
    "AVB","AVGO","AVY","AWK","AXON","AXP","AZO",
    # B
    "BA","BAC","BALL","BAX","BBWI","BDX","BEN","BF-B","BG","BIIB",
    "BK","BKNG","BKR","BLDR","BLK","BMY","BR","BRK-B","BRO","BSX","BWA",
    # C
    "CAG","CAH","CARR","CAT","CB","CBOE","CBRE","CCI","CCL","CDNS",
    "CDW","CE","CEG","CF","CFG","CHD","CHRW","CHTR","CI","CINF","CL",
    "CLX","CMA","CMCSA","CME","CMG","CMI","CMS","CNC","CNP","COF",
    "COO","COP","COST","CPAY","CPB","CPRT","CRL","CRM","CSCO","CSGP",
    "CSX","CTAS","CTLT","CTSH","CTVA","CVS","CVX",
    # D
    "D","DAL","DAY","DD","DE","DFS","DG","DGX","DHI","DHR","DIS",
    "DLTR","DOC","DOV","DOW","DPZ","DRI","DTE","DUK","DVA","DVN",
    # E
    "EA","EBAY","ECL","ED","EFX","EG","EIX","EL","ELV","EMN","EMR",
    "ENPH","EOG","EPAM","EQIX","EQR","EQT","ES","ESS","ETN","ETR",
    "EVRG","EW","EXC","EXPD","EXPE","EXR",
    # F
    "F","FANG","FAST","FCX","FDS","FDX","FE","FFIV","FI","FICO","FIS",
    "FITB","FMC","FOX","FOXA","FRT","FSLR","FTNT","FTV",
    # G
    "GD","GDDY","GE","GEHC","GEN","GEV","GILD","GIS","GL","GLW","GM",
    "GNRC","GOOGL","GOOG","GPC","GPN","GRMN","GS","GWW",
    # H
    "HAL","HAS","HBAN","HCA","HD","HES","HIG","HII","HLT","HOLX",
    "HON","HPE","HPQ","HRL","HSIC","HST","HSY","HUBB","HUM","HWM",
    # I
    "IBM","ICE","IDXX","IEX","IFF","ILMN","INCY","INTC","INTU","INVH",
    "IP","IPG","IQV","IR","IRM","ISRG","IT","ITW","IVZ",
    # J
    "JBHT","JBL","JCI","JKHY","JNJ","JNPR","JPM",
    # K
    "K","KDP","KEY","KEYS","KHC","KIM","KLAC","KMB","KMI","KMX","KO","KR",
    # L
    "L","LDOS","LEN","LH","LHX","LIN","LKQ","LLY","LMT","LNT","LOW",
    "LRCX","LULU","LUV","LVS","LYB","LYV",
    # M
    "MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT","MET",
    "META","MGM","MHK","MKC","MKTX","MLM","MMC","MMM","MO","MOH","MOS",
    "MPC","MPWR","MRK","MRNA","MRO","MS","MSCI","MSFT","MSI","MTB","MTD","MU",
    # N
    "NCLH","NDAQ","NEE","NEM","NFLX","NI","NKE","NOC","NOW","NRG","NSC",
    "NTAP","NTRS","NUE","NVDA","NVR","NWS","NWSA",
    # O
    "ODFL","OKE","OMC","ON","ORCL","ORLY","OXY",
    # P
    "PANW","PARA","PAYC","PAYX","PCAR","PCG","PEG","PEP","PFE","PFG",
    "PG","PGR","PH","PHM","PLD","PM","PNC","PNR","PNW","PODD","POOL",
    "PPG","PPL","PRU","PSA","PSX","PTC","PWR",
    # Q
    "QCOM","QRVO",
    # R
    "RCL","REG","REGN","RF","RJF","RL","RMD","ROK","ROL","ROP","ROST","RPM","RSG",
    # S
    "SBAC","SBUX","SCHW","SHW","SJM","SLB","SMCI","SNA","SNPS","SO",
    "SPG","SPGI","SRE","STE","STLD","STT","STX","STZ","SWK","SWKS",
    "SYF","SYK","SYY",
    # T
    "T","TAP","TDG","TDY","TECH","TEL","TER","TFC","TFX","TGT","TJX",
    "TMO","TMUS","TPR","TRGP","TRMB","TROW","TRV","TSCO","TSLA","TSN",
    "TT","TTWO","TXN","TXT","TYL",
    # U
    "UAL","UDR","UHS","ULTA","UNH","UNP","UPS","URI","USB",
    # V
    "V","VICI","VLO","VLTO","VMC","VRSK","VRSN","VRTX","VTR","VTRS","VZ",
    # W
    "WAB","WAT","WBA","WBD","WDC","WELL","WFC","WHR","WM","WMB","WMT",
    "WRB","WST","WTW","WY","WYNN",
    # X-Z
    "XEL","XOM","XYL","YUM","ZBH","ZION","ZTS",
]

# ── NASDAQ 100 – vollständige Liste (Stand Q1 2025, 101 Ticker) ───────────────
NASDAQ100_TICKERS: list[str] = [
    "AAPL","ABNB","ADBE","ADI","ADP","ADSK","AEP","AMAT","AMD","AMGN",
    "AMZN","ANSS","ASML","AVGO","AZN","BIIB","BKNG","BKR","CCEP","CDNS",
    "CDW","CEG","CHTR","CMCSA","COST","CPRT","CRWD","CSCO","CSGP","CSX",
    "CTAS","CTSH","DDOG","DXCM","EA","EXC","FANG","FAST","FTNT","GEHC",
    "GFS","GILD","GOOG","GOOGL","HON","IDXX","ILMN","INTC","INTU","ISRG",
    "KDP","KHC","KLAC","LRCX","LULU","MAR","MCHP","MDB","MDLZ","MELI",
    "META","MNST","MRNA","MRVL","MSFT","MU","NFLX","NVDA","NXPI","ODFL",
    "ON","ORLY","PANW","PAYX","PCAR","PDD","PEP","PYPL","QCOM","REGN",
    "ROP","ROST","SBUX","SIRI","SMCI","SNPS","TEAM","TMUS","TSLA","TTD",
    "TTWO","TXN","VRSK","VRTX","WBD","WDAY","XEL","ZM","ZS",
    "FTNT","ABNB","DDOG","CRWD","MRVL","OKTA","VEEV","HUBS","BILL","NET",
]

# ── Russell 2000 Top 200 nach Marktkapitalisierung (Stand Q1 2025) ─────────────
RUSSELL200_TICKERS: list[str] = [
    # Marktkapitalisierung 1–50
    "SMCI","AXON","SAIA","ONTO","BOOT","ITCI","CAVA","KTOS","AAON",
    "IRTC","NTRA","SFM","TMDX","ACMR","BRBR","RUSHA","LNTH","KYMR",
    "PRCT","STRL","PLXS","MYRG","ENSG","MGNI","IBP","HIMS","KRYS",
    "SUPN","PCVX","ARWR","RCUS","PRAX","INSM","CRNX","SPRY","ROIV",
    "IDYA","BCRX","AGIO","KROS","MRUS","RARE","GERN","FOLD","DVAX",
    "ALKS","ACAD","ADMA","ARDX","AVIR",
    # 51–100
    "BHVN","BNGO","CBPO","CDMO","CLOV","CMRX","CNTA","COGT","CPHI",
    "DCPH","DFIN","DNLI","DTIL","DYAI","EGRX","ELYM","ENVA","EPZM",
    "ESTA","ETNB","EVER","FGEN","FORM","FROG","FWRG","GNPX","GRPH",
    "HALO","HLVX","HRMY","HSII","HTBK","ICAD","IDEX","IMAB","IMGN",
    "IMVT","INVA","IONS","IOVA","IPHA","IRWD","ISEE","ITER","ITOS",
    "JAGX","JANX","JOBY","KALA","KALV",
    # 101–150
    "KPTI","KRTX","LBPH","LGND","LMNX","LPSN","LQDA","LQDT","LWAY",
    "MCRB","MDXG","MGNX","MGTA","MIRM","MKSI","MLTX","MNKD","MODV",
    "MORF","MRNS","MSRT","MTEM","MTTR","NABL","NBTX","NCNA","NEOS",
    "NERV","NKTR","NMRA","NRXP","NTST","NUVL","NVAX","NVCR","NVST",
    "NXST","NYMX","NYNY","OCGN","OCUL","OMER","ONCT","OPRA","OPTN",
    "ORGO","OTIC","OVID","OXSQ",
    # 151–200
    "PBAX","PCSA","PDFS","PHAT","PLRX","PMVP","PNTM","PRLD","PRME",
    "PRTA","PRTS","PSNL","PTGX","PTLO","PTSI","PULM","PYPD","QNST",
    "RAPT","RCKT","RLAY","RLMD","RMBI","RMED","RMNI","RPID","RPRX",
    "RRBI","RTLX","RUBY","RZLT","SDGR","SEIC","SEER","SGMO","SILK",
    "SLNO","SMAR","SPNV","SQSP","SRPT","SSKN","STAA","STEM","STOK",
    "STRN","STRO","SVRA","SWAV","SYNH","TASK",
]

# ── S&P 400 Mid Cap – Top 100 nach Marktkapitalisierung (Stand Q1 2025) ────────
# Wachstums-Aktien vor dem Sprung in den S&P 500 – oft frühe VCP-Kandidaten
SP400_TICKERS: list[str] = [
    "ACI","ACM","ACHC","ACLX","AFG","AGIO","AIT","ALEX","ALGM","ALKS",
    "AMG","AMKR","ANF","AOS","APA","APAM","ATGE","ATR","AVAV","AVT",
    "AX","AXTA","BCC","BELFB","BJ","BLD","BRX","BXMT","CABO","CADE",
    "CBT","CCOI","CDP","CFR","CHE","CHRD","CLF","CLH","CMA","CMC",
    "CNH","CNM","COHU","COLM","CPF","CRS","CVI","CW","DAN","DINO",
    "DKS","DLB","DLX","DORM","DXC","EAT","EIG","ENVA","ESE","ESNT",
    "ETSY","EWBC","EXLS","EXPI","FAF","FBP","FBIN","FCNCA","FHI","FLO",
    "FNB","FNF","FR","FYBR","GEF","GHC","GL","GMS","GNW","GOOG",
    "GPK","GPI","GWW","HAE","HALO","HBI","HI","HIW","HLI","HMST",
    "HRB","HSII","HXL","IAC","IBP","ICUI","IDA","IDCC","IESC","IFS",
    "IGT","INGR","INSP","IPGP","ITT","JELD","JHG","JNPR","KAI","KFRC",
    "KNF","KNTK","KRC","LCII","LEA","LNC","LSTR","MARA","MAS","MATX",
]

# ── DAX 40 – Deutsche Standardwerte (Stand Q1 2025, .DE-Suffix) ───────────────
# Ergänzend zu US-Märkten laut Original-Spezifikation
# Hinweis: Sentiment via StockTwits/ApeWisdom minimal → Score-Ebene 3 = neutral
DAX40_TICKERS: list[str] = [
    "ADS.DE","AIR.DE","ALV.DE","BAS.DE","BAYN.DE","BMW.DE","BNR.DE",
    "CON.DE","1COV.DE","DB1.DE","DBK.DE","DHL.DE","DTE.DE","EOAN.DE",
    "FRE.DE","HEI.DE","HEN3.DE","HNR1.DE","IFX.DE","LIN.DE","MBG.DE",
    "MRK.DE","MTX.DE","MUV2.DE","P911.DE","PAH3.DE","RHM.DE","RWE.DE",
    "SAP.DE","SHL.DE","SIE.DE","SRT.DE","SY1.DE","VNA.DE","VOW3.DE",
    "ZAL.DE","ENR.DE","EVT.DE","FNTN.DE","QIA.DE",
]

# ── Dow Jones 30 (größtenteils in SP500 enthalten, nur Ergänzungen) ────────────
DOW30_TICKERS: list[str] = [
    # Diese Ticker sind in SP500 bereits enthalten; keine Duplikate nötig.
    # Dow Jones 30: AAPL, AMGN, AXP, BA, CAT, CRM, CSCO, CVX, DIS, DOW,
    # GS, HD, HON, IBM, INTC, JNJ, JPM, KO, MCD, MMM, MRK, MSFT, NKE,
    # PG, TRV, UNH, V, VZ, WBA, WMT → alle in SP500_TICKERS enthalten
]

# ── Persönliche Watchlist (Beispiel-Starter) ──────────────────────────────────
PERSONAL_TICKERS: list[str] = [
    "ASTS",   # AST SpaceMobile – typischer Pre-Breakout
    "SNDK",   # SanDisk/Western Digital Spin-off
    "TSLA",   # Tesla
    "PLTR",   # Palantir
    "MSTR",   # MicroStrategy
    "RKLB",   # Rocket Lab
    "LUNR",   # Intuitive Machines
    "ACHR",   # Archer Aviation
    "JOBY",   # Joby Aviation
    "IONQ",   # IonQ Quantum Computing
]

# Deduplizierte Gesamtliste mit Quellen-Tagging
def _build_static_map() -> dict[str, str]:
    result: dict[str, str] = {}
    for t in SP500_TICKERS:
        result[t] = "SP500"
    for t in NASDAQ100_TICKERS:
        result.setdefault(t, "NASDAQ100")
    for t in RUSSELL200_TICKERS:
        result.setdefault(t, "RUSSELL200")
    for t in SP400_TICKERS:
        result.setdefault(t, "SP400")
    for t in DAX40_TICKERS:
        result.setdefault(t, "DAX40")
    for t in PERSONAL_TICKERS:
        result.setdefault(t, "WATCHLIST")
    return result


def load_static_universe(db: Session) -> int:
    """Schreibt alle statischen Ticker in die stocks-Tabelle.
    Gibt Anzahl neu eingefügter Zeilen zurück.
    """
    mapping = _build_static_map()
    added = 0
    for ticker, source in mapping.items():
        existing = db.get(Stock, ticker)
        if not existing:
            db.add(Stock(ticker=ticker, universe_source=source, is_active=1))
            added += 1
    db.commit()
    logger.info(
        "Statisches Universum geladen: %d neu | Gesamt: %d",
        added, len(mapping)
    )
    return added


def load_from_wikipedia(db: Session) -> int:
    """Aktualisiert S&P 500 und NASDAQ 100 von Wikipedia.
    Funktioniert auf dem eigenen Rechner; scheitert in gesperrten Umgebungen.
    Wird wöchentlich vom Scheduler aufgerufen.
    """
    added = 0
    # (col, table_index_hint) – Spaltennamen je nach Wikipedia-Seite
    sources = {
        "SP500":     ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol"),
        "NASDAQ100": ("https://en.wikipedia.org/wiki/Nasdaq-100",                   "Ticker"),
        "SP400":     ("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",  "Ticker"),
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AIDepot/1.0)"}

    for source, (url, col) in sources.items():
        try:
            import pandas as pd
            tables = pd.read_html(url, storage_options={"User-Agent": headers["User-Agent"]})
            # Richtige Tabelle finden
            for table in tables:
                if col in table.columns:
                    raw = table[col].dropna().tolist()
                    # US-Ticker: "." → "-" (BRK.B → BRK-B); .DE-Ticker unverändert
                    tickers = [
                        t.replace(".", "-") if not t.endswith(".DE") else t
                        for t in raw if isinstance(t, str)
                    ]
                    for ticker in tickers:
                        if 1 <= len(ticker) <= 12:
                            existing = db.get(Stock, ticker)
                            if not existing:
                                db.add(Stock(ticker=ticker, universe_source=source, is_active=1))
                                added += 1
                    break
            db.commit()
            logger.info("Wikipedia %s: geladen", source)
        except Exception as exc:
            logger.debug("Wikipedia %s nicht erreichbar (%s) – nutze hardkodierte Liste", source, exc)

    return added


def load_from_av_listing(db: Session, api_key: str) -> int:
    """Einmaliger Alpha-Vantage-Call (LISTING_STATUS) um alle aktiven US-Aktien
    als potenzielle Ticker-Basis zu haben. Wird nur wöchentlich aufgerufen.
    Kostet 1 API-Credit.
    """
    if not api_key:
        return 0

    # Nur ausführen, wenn zuletzt vor mehr als 7 Tagen
    last_row = db.get(Configuration, "av_listing_last_updated")
    if last_row and last_row.value:
        try:
            last = datetime.fromisoformat(last_row.value)
            if datetime.utcnow() - last < timedelta(days=7):
                logger.info("AV LISTING_STATUS: Noch frisch (letzte Aktualisierung %s)", last_row.value)
                return 0
        except ValueError:
            pass

    try:
        resp = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "LISTING_STATUS", "apikey": api_key},
            timeout=30,
        )
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        added = 0
        for row in reader:
            if (
                row.get("status") == "Active"
                and row.get("assetType") == "Stock"
                and row.get("exchange") in ("NYSE", "NASDAQ")
            ):
                ticker = row.get("symbol", "").strip()
                name   = row.get("name", "").strip()
                if not ticker or len(ticker) > 10 or not ticker.isalpha():
                    continue
                existing = db.get(Stock, ticker)
                if not existing:
                    db.add(Stock(ticker=ticker, name=name, universe_source="NYSE_NASDAQ", is_active=0))
                    added += 1
                elif not existing.name and name:
                    existing.name = name
        db.commit()

        # Timestamp aktualisieren
        ts_row = db.get(Configuration, "av_listing_last_updated")
        if ts_row:
            ts_row.value = datetime.utcnow().isoformat()
        else:
            db.add(Configuration(key="av_listing_last_updated", value=datetime.utcnow().isoformat()))
        db.commit()

        logger.info("AV LISTING_STATUS: %d neue Ticker hinzugefügt (inaktiv, für Suche verfügbar)", added)
        return added

    except Exception as exc:
        logger.warning("AV LISTING_STATUS fehlgeschlagen: %s", exc)
        return 0


def add_trending_tickers(db: Session, tickers: list[str]) -> int:
    """Fügt StockTwits-Trending-Ticker als Quelle TRENDING hinzu.
    Setzt is_active=1, damit sie im täglichen Scan berücksichtigt werden.
    """
    added = 0
    for ticker in tickers:
        ticker = ticker.strip().upper()
        if not ticker or len(ticker) > 10:
            continue
        existing = db.get(Stock, ticker)
        if not existing:
            db.add(Stock(ticker=ticker, universe_source="TRENDING", is_active=1))
            added += 1
        elif existing.universe_source == "TRENDING" and not existing.is_active:
            existing.is_active = 1
    if added:
        db.commit()
    return added


def add_personal_ticker(db: Session, ticker: str, name: str = "") -> bool:
    """Fügt einen Ticker zur persönlichen Watchlist hinzu."""
    ticker = ticker.strip().upper()
    existing = db.get(Stock, ticker)
    if existing:
        if existing.universe_source != "WATCHLIST":
            existing.universe_source = "WATCHLIST"
            db.commit()
        return False
    db.add(Stock(ticker=ticker, name=name, universe_source="WATCHLIST", is_active=1))
    db.commit()
    return True


def remove_personal_ticker(db: Session, ticker: str) -> bool:
    """Entfernt einen Ticker aus der persönlichen Watchlist."""
    existing = db.get(Stock, ticker)
    if existing and existing.universe_source == "WATCHLIST":
        existing.is_active = 0
        db.commit()
        return True
    return False


def get_all_active_tickers(db: Session) -> list[str]:
    """Alle aktiven Ticker im Universum (is_active=1)."""
    return [s.ticker for s in db.query(Stock).filter(Stock.is_active == 1).all()]


def get_universe_stats(db: Session) -> dict:
    """Anzahl Ticker pro Quelle (nur aktive)."""
    rows = db.query(Stock.universe_source, Stock.is_active).all()
    stats: dict[str, int] = {}
    for source, active in rows:
        if active:
            stats[source] = stats.get(source, 0) + 1
    stats["total"] = sum(v for k, v in stats.items() if k != "total")
    return stats
