from pydantic import BaseModel
from typing import Optional


# ── Aktien & Scores ──────────────────────────────────────────────────────────

class ScoreBreakdownOut(BaseModel):
    pe_vs_sector: float = 0
    eps_beat_streak: float = 0
    revenue_growth: float = 0
    fcf_score: float = 0
    debt_equity: float = 0
    insider_net: float = 0
    earnings_proximity: float = 0
    vcp_score: float = 0
    volume_contraction: float = 0
    price_vs_resistance: float = 0
    rsi_zone: float = 0
    relative_strength: float = 0
    macd_signal: float = 0
    bollinger_squeeze: float = 0
    news_sentiment: float = 0
    stocktwits_ratio: float = 0
    reddit_momentum: float = 0
    analyst_delta: float = 0
    sentiment_suppressed: bool = False


class OptionsRecOut(BaseModel):
    direction: str
    leverage_min: float
    leverage_max: float
    duration_weeks: int
    ko_distance_pct: float
    entry_trigger: Optional[float]
    stop_loss: Optional[float]
    base_price_at_rec: Optional[float]
    atr_at_rec: Optional[float]


class StockScoreOut(BaseModel):
    ticker: str
    name: Optional[str]
    sector: Optional[str]
    total_score: float
    l1_fundamentals: float
    l2_technicals: float
    l3_sentiment: float
    zone: int
    delta_1d: Optional[float]
    delta_7d: Optional[float]
    delta_30d: Optional[float]
    strongest_signal: Optional[str]
    next_catalyst: Optional[str]
    catalyst_days: Optional[int]
    score_date: str
    breakdown: Optional[ScoreBreakdownOut] = None
    options_rec: Optional[OptionsRecOut] = None


class ScoreHistoryPoint(BaseModel):
    score_date: str
    total_score: float
    zone: int


# ── Portfolio ────────────────────────────────────────────────────────────────

class PositionCreate(BaseModel):
    ticker: str
    product_type: str = "WARRANT"
    direction: str = "LONG"
    isin: Optional[str] = None
    quantity: float
    entry_price: float
    entry_date: str
    ko_level: Optional[float] = None
    expiry_date: Optional[str] = None
    leverage: Optional[float] = None
    underlying_at_entry: Optional[float] = None
    notes: Optional[str] = None


class PositionClose(BaseModel):
    sell_price: float
    sell_date: str
    notes: Optional[str] = None


class ExitSignalOut(BaseModel):
    id: int
    position_id: int
    ticker: str
    signal_type: str
    severity: str
    trigger_value: Optional[float]
    message: Optional[str]
    recommendation: Optional[str]
    current_pnl_pct: Optional[float]
    is_acknowledged: bool
    signal_date: str


class PositionOut(BaseModel):
    id: int
    ticker: str
    name: Optional[str] = None
    product_type: str
    direction: str
    isin: Optional[str]
    quantity: float
    entry_price: float
    entry_date: str
    entry_score: Optional[float]
    entry_zone: Optional[int]
    ko_level: Optional[float]
    expiry_date: Optional[str]
    leverage: Optional[float]
    underlying_at_entry: Optional[float]
    is_open: bool
    current_score: Optional[float] = None
    current_zone: Optional[int] = None
    current_underlying: Optional[float] = None
    ko_distance_pct: Optional[float] = None
    days_to_expiry: Optional[int] = None
    unrealized_pnl_pct: Optional[float] = None
    status: Optional[str] = None   # HALTEN / BEOBACHTEN / EXIT
    exit_signals: list[ExitSignalOut] = []


# ── Transaktionen ────────────────────────────────────────────────────────────

class TransactionOut(BaseModel):
    id: int
    position_id: Optional[int]
    ticker: str
    tx_type: str
    quantity: float
    price: float
    tx_date: str
    score_at_tx: Optional[float]
    pnl_abs: Optional[float]
    pnl_pct: Optional[float]
    hold_days: Optional[int]
    notes: Optional[str]


# ── Dashboard ────────────────────────────────────────────────────────────────

class DashboardOut(BaseModel):
    total_pnl_abs: float
    total_pnl_pct: Optional[float]
    open_positions: int
    top_signals: list[StockScoreOut]
    exit_alerts: list[ExitSignalOut]


# ── Signalqualität ───────────────────────────────────────────────────────────

class SignalQualityOut(BaseModel):
    signal_type: str
    total_trades: int
    profitable: int
    win_rate_pct: float
    avg_pnl_pct: float


# ── Konfiguration ────────────────────────────────────────────────────────────

class ConfigOut(BaseModel):
    weight_fundamental: int
    weight_technical: int
    weight_sentiment: int
    zone1_min_score: int
    zone2_min_score: int
    zone3_min_score: int
    alert_delta_1d: float
    exit_score_drop: float
    exit_ko_distance: float
    exit_expiry_weeks: int
    exit_bull_ratio: float


class ConfigUpdate(BaseModel):
    weight_fundamental: Optional[int] = None
    weight_technical: Optional[int] = None
    weight_sentiment: Optional[int] = None
    zone1_min_score: Optional[int] = None
    zone2_min_score: Optional[int] = None
    zone3_min_score: Optional[int] = None
    alert_delta_1d: Optional[float] = None
    exit_score_drop: Optional[float] = None
    exit_ko_distance: Optional[float] = None
    exit_expiry_weeks: Optional[int] = None
    exit_bull_ratio: Optional[float] = None


# ── Backtesting ──────────────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    ticker: str
    from_date: str   # YYYY-MM-DD
    to_date: str     # YYYY-MM-DD


class BacktestSignalEvent(BaseModel):
    date: str
    event_type: str   # ZONE_CHANGE, DELTA_SPIKE, STREAK_7D
    from_zone: Optional[int] = None
    to_zone: Optional[int] = None
    score: float
    delta_1d: Optional[float] = None
    delta_7d: Optional[float] = None
    description: str


class BacktestDataPoint(BaseModel):
    date: str
    close: float
    score: float
    zone: int
    delta_1d: Optional[float]
    delta_7d: Optional[float]


class BacktestResult(BaseModel):
    ticker: str
    from_date: str
    to_date: str
    price_data: list[BacktestDataPoint]
    signals: list[BacktestSignalEvent]
    total_signals: int
    zone1_entries: int
    summary: Optional[dict] = None
