from backend.scoring.sentiment import (
    score_news_sentiment,
    score_stocktwits_ratio,
    score_reddit_momentum,
    score_analyst_delta,
    apply_suppression_rule,
)


class TestNewsSentiment:
    def test_both_none_returns_neutral(self):
        assert score_news_sentiment(None, None) == 2.0

    def test_strong_positive_both(self):
        assert score_news_sentiment(0.8, 0.7) == 8.0

    def test_single_strong_score_other_none(self):
        # Nur ein Wert > 0.6 → avg=0.8 → 8
        assert score_news_sentiment(0.8, None) == 8.0

    def test_moderate_avg(self):
        # avg=0.35 → 5
        assert score_news_sentiment(0.4, 0.3) == 5.0

    def test_neutral_avg(self):
        # avg=0.15 → 2
        assert score_news_sentiment(0.1, 0.2) == 2.0

    def test_zero_sentiment(self):
        assert score_news_sentiment(0.0, 0.0) == 2.0

    def test_negative_sentiment(self):
        assert score_news_sentiment(-0.3, -0.5) == 0.0

    def test_boundary_exactly_06(self):
        # avg=0.60 ist NOT > 0.60 → fällt auf > 0.30 → 5
        assert score_news_sentiment(0.60, 0.60) == 5.0

    def test_above_06_boundary(self):
        assert score_news_sentiment(0.65, 0.65) == 8.0


class TestStocktwitsRatio:
    def test_none_returns_neutral(self):
        assert score_stocktwits_ratio(None) == 3.0

    def test_high_bullish(self):
        assert score_stocktwits_ratio(0.70) == 7.0

    def test_boundary_065_not_above(self):
        # 0.65 ist NOT > 0.65 → fällt auf >= 0.55 → 5
        assert score_stocktwits_ratio(0.65) == 5.0

    def test_moderate_bullish(self):
        assert score_stocktwits_ratio(0.60) == 5.0

    def test_boundary_055(self):
        # 0.55 >= 0.55 → 5
        assert score_stocktwits_ratio(0.55) == 5.0

    def test_neutral_range(self):
        assert score_stocktwits_ratio(0.50) == 3.0

    def test_boundary_045(self):
        # 0.45 >= 0.45 → 3
        assert score_stocktwits_ratio(0.45) == 3.0

    def test_below_45pct(self):
        assert score_stocktwits_ratio(0.40) == 0.0


class TestRedditMomentum:
    def test_both_zero_neutral(self):
        assert score_reddit_momentum(0, 0) == 1.0

    def test_new_appearance(self):
        # mentions_24h_ago=0 aber jetzt > 0 → 3
        assert score_reddit_momentum(5, 0) == 3.0

    def test_strong_spike_50pct(self):
        # change=(150-100)/100=0.50 → 5
        assert score_reddit_momentum(150, 100) == 5.0

    def test_moderate_growth_20pct(self):
        # change=(120-100)/100=0.20 → 3
        assert score_reddit_momentum(120, 100) == 3.0

    def test_flat(self):
        assert score_reddit_momentum(100, 100) == 1.0

    def test_decline(self):
        assert score_reddit_momentum(80, 100) == 1.0

    def test_above_50pct(self):
        # change=1.0 → 5
        assert score_reddit_momentum(200, 100) == 5.0


class TestAnalystDelta:
    def test_two_upgrades(self):
        assert score_analyst_delta(2) == 5.0

    def test_many_upgrades(self):
        assert score_analyst_delta(5) == 5.0

    def test_one_upgrade(self):
        assert score_analyst_delta(1) == 3.0

    def test_neutral(self):
        assert score_analyst_delta(0) == 1.0

    def test_one_downgrade(self):
        assert score_analyst_delta(-1) == 0.0

    def test_many_downgrades(self):
        assert score_analyst_delta(-3) == 0.0


class TestSuppressionRule:
    def test_no_suppression_good_sentiment(self):
        # L1+L2=55 > 50, aber L3=10 >= 5 → kein Deckel
        score, suppressed = apply_suppression_rule(30.0, 25.0, 10.0)
        assert score == 65.0
        assert suppressed is False

    def test_suppression_caps_zone1_candidate(self):
        # L1+L2=72 > 50, L3=4 < 5 → Total=76 → gedeckelt auf 74
        score, suppressed = apply_suppression_rule(38.0, 34.0, 4.0)
        assert score == 74.0
        assert suppressed is True

    def test_suppression_exact_74_total(self):
        # L1+L2=70 > 50, L3=4 < 5 → Total=74 → min(74,74)=74
        score, suppressed = apply_suppression_rule(40.0, 30.0, 4.0)
        assert score == 74.0
        assert suppressed is True

    def test_suppression_flag_set_even_if_total_below_74(self):
        # L1+L2=55 > 50, L3=3 < 5 → Total=58 → kein Kürzen nötig, aber Flag gesetzt
        score, suppressed = apply_suppression_rule(30.0, 25.0, 3.0)
        assert score == 58.0
        assert suppressed is True

    def test_no_suppression_l1_l2_below_50(self):
        # L1+L2=40 ≤ 50 → keine Unterdrückung
        score, suppressed = apply_suppression_rule(20.0, 20.0, 3.0)
        assert score == 43.0
        assert suppressed is False

    def test_boundary_l1_l2_exactly_50_no_suppression(self):
        # L1+L2=50 ist NOT > 50 → keine Unterdrückung
        score, suppressed = apply_suppression_rule(25.0, 25.0, 3.0)
        assert score == 53.0
        assert suppressed is False

    def test_no_suppression_l3_exactly_5(self):
        # L3=5 ist NOT < 5 → keine Unterdrückung
        score, suppressed = apply_suppression_rule(30.0, 25.0, 5.0)
        assert score == 60.0
        assert suppressed is False
