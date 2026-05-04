from backend.scoring.fundamental import (
    score_pe_vs_sector,
    score_eps_beat_streak,
    score_revenue_growth,
    score_fcf,
    score_debt_equity,
    score_insider_net,
    score_earnings_proximity,
)


class TestPeVsSector:
    def test_none_returns_neutral(self):
        assert score_pe_vs_sector(None, "Technology") == 2.0

    def test_negative_pe_returns_neutral(self):
        assert score_pe_vs_sector(-5.0, "Technology") == 2.0

    def test_zero_pe_returns_neutral(self):
        assert score_pe_vs_sector(0.0, "Technology") == 2.0

    def test_below_75pct_of_sector_avg(self):
        # Technology avg=28; 20/28=0.71 < 0.75 → 8
        assert score_pe_vs_sector(20.0, "Technology") == 8.0

    def test_between_75_and_100pct(self):
        # 22/28=0.786 → 6
        assert score_pe_vs_sector(22.0, "Technology") == 6.0

    def test_between_100_and_125pct(self):
        # 30/28=1.07 → 4
        assert score_pe_vs_sector(30.0, "Technology") == 4.0

    def test_between_125_and_150pct(self):
        # 38/28=1.36 → 2
        assert score_pe_vs_sector(38.0, "Technology") == 2.0

    def test_above_150pct(self):
        # 50/28=1.79 → 0
        assert score_pe_vs_sector(50.0, "Technology") == 0.0

    def test_unknown_sector_returns_neutral(self):
        # Unbekannter Sektor → kein Vergleich möglich → neutral 2.0
        assert score_pe_vs_sector(14.0, "UnknownSector") == 2.0
        assert score_pe_vs_sector(14.0, "") == 2.0


class TestEpsBeatStreak:
    def test_empty_list(self):
        assert score_eps_beat_streak([]) == 0.0

    def test_none_input(self):
        assert score_eps_beat_streak(None) == 0.0

    def test_one_beat(self):
        assert score_eps_beat_streak([{"beat": True}]) == 2.0

    def test_two_consecutive_beats(self):
        assert score_eps_beat_streak([{"beat": True}, {"beat": True}]) == 4.0

    def test_three_beats_gives_max(self):
        assert score_eps_beat_streak([{"beat": True}] * 3) == 6.0

    def test_more_than_three_still_capped_at_6(self):
        assert score_eps_beat_streak([{"beat": True}] * 5) == 6.0

    def test_streak_broken_by_miss(self):
        history = [{"beat": True}, {"beat": False}, {"beat": True}]
        assert score_eps_beat_streak(history) == 2.0

    def test_first_miss_gives_zero(self):
        history = [{"beat": False}, {"beat": True}, {"beat": True}]
        assert score_eps_beat_streak(history) == 0.0


class TestRevenueGrowth:
    def test_none_returns_neutral(self):
        assert score_revenue_growth(None) == 2.0

    def test_above_20pct(self):
        assert score_revenue_growth(0.25) == 6.0

    def test_exactly_20pct_falls_to_next_bracket(self):
        # 0.20 is NOT > 0.20 → falls to > 0.10 → 4
        assert score_revenue_growth(0.20) == 4.0

    def test_between_10_and_20pct(self):
        assert score_revenue_growth(0.15) == 4.0

    def test_zero_growth(self):
        assert score_revenue_growth(0.0) == 2.0

    def test_small_positive_growth(self):
        assert score_revenue_growth(0.05) == 2.0

    def test_negative_growth(self):
        assert score_revenue_growth(-0.10) == 0.0


class TestFcf:
    def test_none_returns_neutral(self):
        # Keine Daten → neutral 1.0 (konsistent mit anderen Kriterien)
        assert score_fcf(None, None) == 1.0

    def test_negative_fcf(self):
        assert score_fcf(-1_000_000, None) == 0.0

    def test_positive_no_prev(self):
        assert score_fcf(5_000_000, None) == 2.0

    def test_positive_and_growing(self):
        assert score_fcf(10_000_000, 8_000_000) == 5.0

    def test_positive_but_declining(self):
        assert score_fcf(8_000_000, 10_000_000) == 2.0


class TestDebtEquity:
    def test_none_returns_neutral(self):
        assert score_debt_equity(None) == 2.0

    def test_high_raw_value_normalized_below_50pct(self):
        # 40 → 40/100=0.4 < 0.5 → 5
        assert score_debt_equity(40.0) == 5.0

    def test_high_raw_value_normalized_50_to_100pct(self):
        # 70 → 0.7 → 3
        assert score_debt_equity(70.0) == 3.0

    def test_high_raw_value_normalized_100_to_200pct(self):
        # 150 → 1.5 → 1
        assert score_debt_equity(150.0) == 1.0

    def test_high_raw_value_normalized_above_200pct(self):
        # 250 → 2.5 → 0
        assert score_debt_equity(250.0) == 0.0

    def test_ratio_value_below_50pct(self):
        # 0.4 (already a ratio, ≤ 10) → no normalization → 5
        assert score_debt_equity(0.4) == 5.0

    def test_ratio_value_above_200pct(self):
        # 3.0 (≤ 10, treated as ratio) → 0
        assert score_debt_equity(3.0) == 0.0


class TestInsiderNet:
    def test_three_net_buys(self):
        assert score_insider_net(3, 0) == 5.0

    def test_net_buy_above_threshold(self):
        # 5 buys, 2 sells → net=3 → 5
        assert score_insider_net(5, 2) == 5.0

    def test_one_net_buy(self):
        assert score_insider_net(2, 1) == 3.0

    def test_neutral_no_activity(self):
        assert score_insider_net(0, 0) == 1.0

    def test_equal_buys_and_sells_neutral(self):
        assert score_insider_net(3, 3) == 1.0

    def test_net_sell(self):
        assert score_insider_net(0, 1) == 0.0


class TestEarningsProximity:
    def test_none_returns_1(self):
        assert score_earnings_proximity(None) == 1.0

    def test_optimal_window_10_days(self):
        assert score_earnings_proximity(10) == 5.0

    def test_boundary_7_days(self):
        assert score_earnings_proximity(7) == 5.0

    def test_boundary_14_days(self):
        assert score_earnings_proximity(14) == 5.0

    def test_3_to_6_days(self):
        assert score_earnings_proximity(5) == 3.0

    def test_boundary_3_days(self):
        assert score_earnings_proximity(3) == 3.0

    def test_far_future_earnings(self):
        assert score_earnings_proximity(30) == 1.0

    def test_imminent_earnings_less_than_3_days(self):
        assert score_earnings_proximity(1) == 1.0

    def test_zero_days(self):
        assert score_earnings_proximity(0) == 1.0
