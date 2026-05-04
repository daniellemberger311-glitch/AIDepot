"""Initiales Schema – alle 13 Tabellen

Revision ID: 0001
Revises:
Create Date: 2026-05-04
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stocks",
        sa.Column("ticker",          sa.String(),  primary_key=True),
        sa.Column("name",            sa.String()),
        sa.Column("sector",          sa.String()),
        sa.Column("industry",        sa.String()),
        sa.Column("market_cap",      sa.Float()),
        sa.Column("exchange",        sa.String()),
        sa.Column("universe_source", sa.String()),
        sa.Column("is_active",       sa.Integer(), nullable=False, server_default="1"),
        sa.Column("added_at",        sa.String()),
    )

    op.create_table(
        "daily_scores",
        sa.Column("id",               sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker",           sa.String(),  sa.ForeignKey("stocks.ticker"), nullable=False),
        sa.Column("score_date",       sa.String(),  nullable=False),
        sa.Column("total_score",      sa.Float(),   nullable=False),
        sa.Column("l1_fundamentals",  sa.Float(),   nullable=False, server_default="0"),
        sa.Column("l2_technicals",    sa.Float(),   nullable=False, server_default="0"),
        sa.Column("l3_sentiment",     sa.Float(),   nullable=False, server_default="0"),
        sa.Column("zone",             sa.Integer(), nullable=False),
        sa.Column("delta_1d",         sa.Float()),
        sa.Column("delta_7d",         sa.Float()),
        sa.Column("delta_30d",        sa.Float()),
        sa.Column("strongest_signal", sa.String()),
        sa.Column("next_catalyst",    sa.String()),
        sa.Column("catalyst_days",    sa.Integer()),
        sa.Column("created_at",       sa.String()),
        sa.UniqueConstraint("ticker", "score_date"),
    )
    op.create_index("idx_daily_scores_zone", "daily_scores", ["zone", "score_date"])

    op.create_table(
        "score_history",
        sa.Column("id",          sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker",      sa.String(),  sa.ForeignKey("stocks.ticker"), nullable=False),
        sa.Column("score_date",  sa.String(),  nullable=False),
        sa.Column("total_score", sa.Float(),   nullable=False),
        sa.Column("zone",        sa.Integer(), nullable=False),
        sa.UniqueConstraint("ticker", "score_date"),
    )
    op.create_index("idx_score_history_ticker", "score_history", ["ticker", "score_date"])

    op.create_table(
        "score_breakdown",
        sa.Column("id",                   sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker",               sa.String(),  nullable=False),
        sa.Column("score_date",           sa.String(),  nullable=False),
        sa.Column("pe_vs_sector",         sa.Float(),   server_default="0"),
        sa.Column("eps_beat_streak",      sa.Float(),   server_default="0"),
        sa.Column("revenue_growth",       sa.Float(),   server_default="0"),
        sa.Column("fcf_score",            sa.Float(),   server_default="0"),
        sa.Column("debt_equity",          sa.Float(),   server_default="0"),
        sa.Column("insider_net",          sa.Float(),   server_default="0"),
        sa.Column("earnings_proximity",   sa.Float(),   server_default="0"),
        sa.Column("vcp_score",            sa.Float(),   server_default="0"),
        sa.Column("volume_contraction",   sa.Float(),   server_default="0"),
        sa.Column("price_vs_resistance",  sa.Float(),   server_default="0"),
        sa.Column("rsi_zone",             sa.Float(),   server_default="0"),
        sa.Column("relative_strength",    sa.Float(),   server_default="0"),
        sa.Column("macd_signal",          sa.Float(),   server_default="0"),
        sa.Column("bollinger_squeeze",    sa.Float(),   server_default="0"),
        sa.Column("news_sentiment",       sa.Float(),   server_default="0"),
        sa.Column("stocktwits_ratio",     sa.Float(),   server_default="0"),
        sa.Column("reddit_momentum",      sa.Float(),   server_default="0"),
        sa.Column("analyst_delta",        sa.Float(),   server_default="0"),
        sa.Column("sentiment_suppressed", sa.Integer(), server_default="0"),
        sa.UniqueConstraint("ticker", "score_date"),
    )

    op.create_table(
        "watchlist",
        sa.Column("ticker",          sa.String(),  sa.ForeignKey("stocks.ticker"), primary_key=True),
        sa.Column("current_zone",    sa.Integer(), nullable=False),
        sa.Column("previous_zone",   sa.Integer()),
        sa.Column("zone_since",      sa.String()),
        sa.Column("manual_override", sa.Integer(), server_default="0"),
        sa.Column("notes",           sa.Text()),
        sa.Column("updated_at",      sa.String()),
    )

    op.create_table(
        "options_recommendations",
        sa.Column("id",               sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker",           sa.String(),  nullable=False),
        sa.Column("rec_date",         sa.String(),  nullable=False),
        sa.Column("direction",        sa.String(),  nullable=False, server_default="CALL"),
        sa.Column("leverage_min",     sa.Float()),
        sa.Column("leverage_max",     sa.Float()),
        sa.Column("duration_weeks",   sa.Integer()),
        sa.Column("ko_distance_pct",  sa.Float()),
        sa.Column("entry_trigger",    sa.Float()),
        sa.Column("stop_loss",        sa.Float()),
        sa.Column("base_price_at_rec",sa.Float()),
        sa.Column("atr_at_rec",       sa.Float()),
        sa.Column("score_at_rec",     sa.Float()),
        sa.Column("is_active",        sa.Integer(), server_default="1"),
        sa.Column("created_at",       sa.String()),
        sa.UniqueConstraint("ticker", "rec_date"),
    )

    op.create_table(
        "positions",
        sa.Column("id",                  sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker",              sa.String(),  sa.ForeignKey("stocks.ticker"), nullable=False),
        sa.Column("product_type",        sa.String(),  nullable=False, server_default="WARRANT"),
        sa.Column("direction",           sa.String(),  nullable=False, server_default="LONG"),
        sa.Column("isin",                sa.String()),
        sa.Column("quantity",            sa.Float(),   nullable=False),
        sa.Column("entry_price",         sa.Float(),   nullable=False),
        sa.Column("entry_date",          sa.String(),  nullable=False),
        sa.Column("entry_score",         sa.Float()),
        sa.Column("entry_zone",          sa.Integer()),
        sa.Column("entry_delta_1d",      sa.Float()),
        sa.Column("entry_delta_7d",      sa.Float()),
        sa.Column("entry_delta_30d",     sa.Float()),
        sa.Column("ko_level",            sa.Float()),
        sa.Column("expiry_date",         sa.String()),
        sa.Column("leverage",            sa.Float()),
        sa.Column("underlying_at_entry", sa.Float()),
        sa.Column("is_open",             sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at",          sa.String()),
    )

    op.create_table(
        "transactions",
        sa.Column("id",          sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("position_id", sa.Integer(), sa.ForeignKey("positions.id")),
        sa.Column("ticker",      sa.String(),  nullable=False),
        sa.Column("tx_type",     sa.String(),  nullable=False),
        sa.Column("quantity",    sa.Float(),   nullable=False),
        sa.Column("price",       sa.Float(),   nullable=False),
        sa.Column("tx_date",     sa.String(),  nullable=False),
        sa.Column("score_at_tx", sa.Float()),
        sa.Column("pnl_abs",     sa.Float()),
        sa.Column("pnl_pct",     sa.Float()),
        sa.Column("hold_days",   sa.Integer()),
        sa.Column("notes",       sa.Text()),
        sa.Column("created_at",  sa.String()),
    )

    op.create_table(
        "exit_signals",
        sa.Column("id",              sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("position_id",     sa.Integer(), sa.ForeignKey("positions.id")),
        sa.Column("ticker",          sa.String(),  nullable=False),
        sa.Column("signal_type",     sa.String(),  nullable=False),
        sa.Column("severity",        sa.String(),  nullable=False),
        sa.Column("trigger_value",   sa.Float()),
        sa.Column("message",         sa.Text()),
        sa.Column("recommendation",  sa.String()),
        sa.Column("current_pnl_pct", sa.Float()),
        sa.Column("is_acknowledged", sa.Integer(), server_default="0"),
        sa.Column("signal_date",     sa.String(),  nullable=False),
        sa.Column("created_at",      sa.String()),
    )

    op.create_table(
        "notifications_log",
        sa.Column("id",                sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel",           sa.String(),  nullable=False, server_default="TELEGRAM"),
        sa.Column("notification_type", sa.String(),  nullable=False),
        sa.Column("ticker",            sa.String()),
        sa.Column("message_text",      sa.Text(),    nullable=False),
        sa.Column("sent_at",           sa.String()),
        sa.Column("success",           sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_detail",      sa.Text()),
    )

    op.create_table(
        "signal_quality",
        sa.Column("id",                 sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("position_id",        sa.Integer(), sa.ForeignKey("positions.id")),
        sa.Column("ticker",             sa.String(),  nullable=False),
        sa.Column("signal_types",       sa.Text()),
        sa.Column("score_at_buy",       sa.Float()),
        sa.Column("zone_at_buy",        sa.Integer()),
        sa.Column("delta_7d_at_buy",    sa.Float()),
        sa.Column("pnl_pct",            sa.Float()),
        sa.Column("profitable",         sa.Integer()),
        sa.Column("hold_days",          sa.Integer()),
        sa.Column("fundamental_at_buy", sa.Float()),
        sa.Column("technical_at_buy",   sa.Float()),
        sa.Column("sentiment_at_buy",   sa.Float()),
        sa.Column("created_at",         sa.String()),
    )

    op.create_table(
        "api_cache",
        sa.Column("cache_key",   sa.String(), primary_key=True),
        sa.Column("data_json",   sa.Text(),   nullable=False),
        sa.Column("source",      sa.String(), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(),nullable=False),
        sa.Column("cached_at",   sa.String(), nullable=False),
        sa.Column("expires_at",  sa.String(), nullable=False),
    )
    op.create_index("idx_api_cache_expires", "api_cache", ["expires_at"])

    op.create_table(
        "configuration",
        sa.Column("key",         sa.String(), primary_key=True),
        sa.Column("value",       sa.String(), nullable=False),
        sa.Column("description", sa.String()),
        sa.Column("updated_at",  sa.String()),
    )


def downgrade() -> None:
    op.drop_table("configuration")
    op.drop_index("idx_api_cache_expires", "api_cache")
    op.drop_table("api_cache")
    op.drop_table("signal_quality")
    op.drop_table("notifications_log")
    op.drop_table("exit_signals")
    op.drop_table("transactions")
    op.drop_table("positions")
    op.drop_table("options_recommendations")
    op.drop_table("watchlist")
    op.drop_table("score_breakdown")
    op.drop_index("idx_score_history_ticker", "score_history")
    op.drop_table("score_history")
    op.drop_index("idx_daily_scores_zone", "daily_scores")
    op.drop_table("daily_scores")
    op.drop_table("stocks")
