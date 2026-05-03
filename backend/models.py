from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Text, Boolean,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from backend.database import Base


class Stock(Base):
    __tablename__ = "stocks"
    ticker          = Column(String, primary_key=True)
    name            = Column(String)
    sector          = Column(String)
    industry        = Column(String)
    market_cap      = Column(Float)
    exchange        = Column(String)
    universe_source = Column(String)   # SP500, NASDAQ100, RUSSELL200, WATCHLIST, TRENDING
    is_active       = Column(Integer, nullable=False, default=1)
    added_at        = Column(String, default=lambda: datetime.utcnow().isoformat())


class DailyScore(Base):
    __tablename__ = "daily_scores"
    __table_args__ = (
        UniqueConstraint("ticker", "score_date"),
        Index("idx_daily_scores_zone", "zone", "score_date"),
    )
    id              = Column(Integer, primary_key=True, autoincrement=True)
    ticker          = Column(String, ForeignKey("stocks.ticker"), nullable=False)
    score_date      = Column(String, nullable=False)
    total_score     = Column(Float, nullable=False)
    l1_fundamentals = Column(Float, nullable=False, default=0)
    l2_technicals   = Column(Float, nullable=False, default=0)
    l3_sentiment    = Column(Float, nullable=False, default=0)
    zone            = Column(Integer, nullable=False)
    delta_1d        = Column(Float)
    delta_7d        = Column(Float)
    delta_30d       = Column(Float)
    strongest_signal = Column(String)
    next_catalyst   = Column(String)
    catalyst_days   = Column(Integer)
    created_at      = Column(String, default=lambda: datetime.utcnow().isoformat())


class ScoreHistory(Base):
    __tablename__ = "score_history"
    __table_args__ = (
        UniqueConstraint("ticker", "score_date"),
        Index("idx_score_history_ticker", "ticker", "score_date"),
    )
    id          = Column(Integer, primary_key=True, autoincrement=True)
    ticker      = Column(String, ForeignKey("stocks.ticker"), nullable=False)
    score_date  = Column(String, nullable=False)
    total_score = Column(Float, nullable=False)
    zone        = Column(Integer, nullable=False)


class ScoreBreakdown(Base):
    __tablename__ = "score_breakdown"
    __table_args__ = (UniqueConstraint("ticker", "score_date"),)
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    ticker              = Column(String, nullable=False)
    score_date          = Column(String, nullable=False)
    # Fundamental
    pe_vs_sector        = Column(Float, default=0)
    eps_beat_streak     = Column(Float, default=0)
    revenue_growth      = Column(Float, default=0)
    fcf_score           = Column(Float, default=0)
    debt_equity         = Column(Float, default=0)
    insider_net         = Column(Float, default=0)
    earnings_proximity  = Column(Float, default=0)
    # Technisch
    vcp_score           = Column(Float, default=0)
    volume_contraction  = Column(Float, default=0)
    price_vs_resistance = Column(Float, default=0)
    rsi_zone            = Column(Float, default=0)
    relative_strength   = Column(Float, default=0)
    macd_signal         = Column(Float, default=0)
    bollinger_squeeze   = Column(Float, default=0)
    # Sentiment
    news_sentiment      = Column(Float, default=0)
    stocktwits_ratio    = Column(Float, default=0)
    reddit_momentum     = Column(Float, default=0)
    analyst_delta       = Column(Float, default=0)
    sentiment_suppressed = Column(Integer, default=0)


class WatchlistEntry(Base):
    __tablename__ = "watchlist"
    ticker          = Column(String, ForeignKey("stocks.ticker"), primary_key=True)
    current_zone    = Column(Integer, nullable=False)
    previous_zone   = Column(Integer)
    zone_since      = Column(String)
    manual_override = Column(Integer, default=0)
    notes           = Column(Text)
    updated_at      = Column(String, default=lambda: datetime.utcnow().isoformat())


class OptionsRecommendation(Base):
    __tablename__ = "options_recommendations"
    __table_args__ = (UniqueConstraint("ticker", "rec_date"),)
    id              = Column(Integer, primary_key=True, autoincrement=True)
    ticker          = Column(String, nullable=False)
    rec_date        = Column(String, nullable=False)
    direction       = Column(String, nullable=False, default="CALL")
    leverage_min    = Column(Float)
    leverage_max    = Column(Float)
    duration_weeks  = Column(Integer)
    ko_distance_pct = Column(Float)
    entry_trigger   = Column(Float)
    stop_loss       = Column(Float)
    base_price_at_rec = Column(Float)
    atr_at_rec      = Column(Float)
    score_at_rec    = Column(Float)
    is_active       = Column(Integer, default=1)
    created_at      = Column(String, default=lambda: datetime.utcnow().isoformat())


class Position(Base):
    __tablename__ = "positions"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    ticker              = Column(String, ForeignKey("stocks.ticker"), nullable=False)
    product_type        = Column(String, nullable=False, default="WARRANT")
    direction           = Column(String, nullable=False, default="LONG")
    isin                = Column(String)
    quantity            = Column(Float, nullable=False)
    entry_price         = Column(Float, nullable=False)
    entry_date          = Column(String, nullable=False)
    entry_score         = Column(Float)
    entry_zone          = Column(Integer)
    entry_delta_1d      = Column(Float)
    entry_delta_7d      = Column(Float)
    entry_delta_30d     = Column(Float)
    ko_level            = Column(Float)
    expiry_date         = Column(String)
    leverage            = Column(Float)
    underlying_at_entry = Column(Float)
    is_open             = Column(Integer, nullable=False, default=1)
    created_at          = Column(String, default=lambda: datetime.utcnow().isoformat())
    transactions        = relationship("Transaction", back_populates="position")
    exit_signals        = relationship("ExitSignal", back_populates="position")


class Transaction(Base):
    __tablename__ = "transactions"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"))
    ticker      = Column(String, nullable=False)
    tx_type     = Column(String, nullable=False)   # BUY, SELL, PARTIAL_SELL
    quantity    = Column(Float, nullable=False)
    price       = Column(Float, nullable=False)
    tx_date     = Column(String, nullable=False)
    score_at_tx = Column(Float)
    pnl_abs     = Column(Float)
    pnl_pct     = Column(Float)
    hold_days   = Column(Integer)
    notes       = Column(Text)
    created_at  = Column(String, default=lambda: datetime.utcnow().isoformat())
    position    = relationship("Position", back_populates="transactions")


class ExitSignal(Base):
    __tablename__ = "exit_signals"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    position_id     = Column(Integer, ForeignKey("positions.id"))
    ticker          = Column(String, nullable=False)
    signal_type     = Column(String, nullable=False)  # SCORE_DROP, KO_DISTANCE, EXPIRY_RISK, SENTIMENT_DROP, TARGET
    severity        = Column(String, nullable=False)  # RED, YELLOW, GREEN
    trigger_value   = Column(Float)
    message         = Column(Text)
    recommendation  = Column(String)
    current_pnl_pct = Column(Float)
    is_acknowledged = Column(Integer, default=0)
    signal_date     = Column(String, nullable=False)
    created_at      = Column(String, default=lambda: datetime.utcnow().isoformat())
    position        = relationship("Position", back_populates="exit_signals")


class NotificationLog(Base):
    __tablename__ = "notifications_log"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    channel             = Column(String, nullable=False, default="TELEGRAM")
    notification_type   = Column(String, nullable=False)
    ticker              = Column(String)
    message_text        = Column(Text, nullable=False)
    sent_at             = Column(String, default=lambda: datetime.utcnow().isoformat())
    success             = Column(Integer, nullable=False, default=1)
    error_detail        = Column(Text)


class SignalQuality(Base):
    __tablename__ = "signal_quality"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    position_id         = Column(Integer, ForeignKey("positions.id"))
    ticker              = Column(String, nullable=False)
    signal_types        = Column(Text)   # JSON-Array
    score_at_buy        = Column(Float)
    zone_at_buy         = Column(Integer)
    delta_7d_at_buy     = Column(Float)
    pnl_pct             = Column(Float)
    profitable          = Column(Integer)
    hold_days           = Column(Integer)
    fundamental_at_buy  = Column(Float)
    technical_at_buy    = Column(Float)
    sentiment_at_buy    = Column(Float)
    created_at          = Column(String, default=lambda: datetime.utcnow().isoformat())


class ApiCache(Base):
    __tablename__ = "api_cache"
    __table_args__ = (Index("idx_api_cache_expires", "expires_at"),)
    cache_key   = Column(String, primary_key=True)
    data_json   = Column(Text, nullable=False)
    source      = Column(String, nullable=False)
    ttl_seconds = Column(Integer, nullable=False)
    cached_at   = Column(String, nullable=False)
    expires_at  = Column(String, nullable=False)


class Configuration(Base):
    __tablename__ = "configuration"
    key         = Column(String, primary_key=True)
    value       = Column(String, nullable=False)
    description = Column(String)
    updated_at  = Column(String, default=lambda: datetime.utcnow().isoformat())
