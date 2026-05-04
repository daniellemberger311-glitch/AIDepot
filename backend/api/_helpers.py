"""Gemeinsame Hilfsfunktionen für API-Router."""
from typing import Optional
from backend.models import DailyScore, ScoreBreakdown, OptionsRecommendation
from backend.schemas import StockScoreOut, ScoreBreakdownOut, OptionsRecOut


def build_score_out(
    ds: DailyScore,
    name: Optional[str],
    sector: Optional[str],
    breakdown: Optional[ScoreBreakdown] = None,
    opt_rec: Optional[OptionsRecommendation] = None,
) -> StockScoreOut:
    """DailyScore-Zeile + optionale Zusatzdaten → StockScoreOut."""
    bd_out = None
    if breakdown:
        bd_out = ScoreBreakdownOut(
            pe_vs_sector         = breakdown.pe_vs_sector or 0,
            eps_beat_streak      = breakdown.eps_beat_streak or 0,
            revenue_growth       = breakdown.revenue_growth or 0,
            fcf_score            = breakdown.fcf_score or 0,
            debt_equity          = breakdown.debt_equity or 0,
            insider_net          = breakdown.insider_net or 0,
            earnings_proximity   = breakdown.earnings_proximity or 0,
            vcp_score            = breakdown.vcp_score or 0,
            volume_contraction   = breakdown.volume_contraction or 0,
            price_vs_resistance  = breakdown.price_vs_resistance or 0,
            rsi_zone             = breakdown.rsi_zone or 0,
            relative_strength    = breakdown.relative_strength or 0,
            macd_signal          = breakdown.macd_signal or 0,
            bollinger_squeeze    = breakdown.bollinger_squeeze or 0,
            news_sentiment       = breakdown.news_sentiment or 0,
            stocktwits_ratio     = breakdown.stocktwits_ratio or 0,
            reddit_momentum      = breakdown.reddit_momentum or 0,
            analyst_delta        = breakdown.analyst_delta or 0,
            sentiment_suppressed = bool(breakdown.sentiment_suppressed),
        )

    rec_out = None
    if opt_rec:
        rec_out = OptionsRecOut(
            direction         = opt_rec.direction,
            leverage_min      = opt_rec.leverage_min or 0,
            leverage_max      = opt_rec.leverage_max or 0,
            duration_weeks    = opt_rec.duration_weeks or 0,
            ko_distance_pct   = opt_rec.ko_distance_pct or 0,
            entry_trigger     = opt_rec.entry_trigger,
            stop_loss         = opt_rec.stop_loss,
            base_price_at_rec = opt_rec.base_price_at_rec,
            atr_at_rec        = opt_rec.atr_at_rec,
        )

    return StockScoreOut(
        ticker           = ds.ticker,
        name             = name,
        sector           = sector,
        total_score      = ds.total_score,
        l1_fundamentals  = ds.l1_fundamentals,
        l2_technicals    = ds.l2_technicals,
        l3_sentiment     = ds.l3_sentiment,
        zone             = ds.zone,
        delta_1d         = ds.delta_1d,
        delta_7d         = ds.delta_7d,
        delta_30d        = ds.delta_30d,
        strongest_signal = ds.strongest_signal,
        next_catalyst    = ds.next_catalyst,
        catalyst_days    = ds.catalyst_days,
        score_date       = ds.score_date,
        close_price      = ds.close_price,
        currency         = ds.currency or "USD",
        breakdown        = bd_out,
        options_rec      = rec_out,
    )
