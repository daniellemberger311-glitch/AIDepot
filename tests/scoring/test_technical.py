import pandas as pd
from backend.scoring.technical import (
    score_volume_contraction,
    score_price_vs_resistance,
    score_rsi,
    score_relative_strength,
    score_macd,
    score_bollinger_squeeze,
    score_vcp,
)


def make_weekly_df(volumes, closes=None):
    n = len(volumes)
    dates = pd.date_range("2024-01-05", periods=n, freq="W-FRI")
    c = closes or [100.0] * n
    return pd.DataFrame({
        "Open":   c,
        "High":   [v * 1.01 for v in c],
        "Low":    [v * 0.99 for v in c],
        "Close":  c,
        "Volume": volumes,
    }, index=dates)


def make_daily_df(closes, volumes=None):
    n = len(closes)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    v = volumes or [1_000_000] * n
    return pd.DataFrame({
        "Open":   closes,
        "High":   [c * 1.01 for c in closes],
        "Low":    [c * 0.99 for c in closes],
        "Close":  closes,
        "Volume": v,
    }, index=dates)


class TestVolumeContraction:
    def test_insufficient_rows_returns_zero(self):
        df = make_weekly_df([100_000] * 4)
        assert score_volume_contraction(df) == 0.0

    def test_strong_contraction(self):
        # 3W-Ø=70k, 10W-Ø=(7×100k+3×70k)/10=91k → ratio≈0.77 < 0.80 → 5
        vols = [100_000] * 7 + [70_000] * 3
        df = make_weekly_df(vols)
        assert score_volume_contraction(df) == 5.0

    def test_moderate_contraction(self):
        # 3W-Ø=85k, 10W-Ø=(7×100k+3×85k)/10=95.5k → ratio≈0.89 < 0.90 → 3
        vols = [100_000] * 7 + [85_000] * 3
        df = make_weekly_df(vols)
        assert score_volume_contraction(df) == 3.0

    def test_no_contraction(self):
        # Alle gleich → ratio=1.0 → 0
        vols = [100_000] * 10
        df = make_weekly_df(vols)
        assert score_volume_contraction(df) == 0.0

    def test_volume_expansion_returns_zero(self):
        # Letzten 3 Wochen viel höheres Volumen als Ø → kein Kontraktion-Signal
        vols = [50_000] * 7 + [200_000] * 3
        df = make_weekly_df(vols)
        assert score_volume_contraction(df) == 0.0


class TestPriceVsResistance:
    def test_empty_df_returns_zero(self):
        assert score_price_vs_resistance(pd.DataFrame(), None) == 0.0

    def test_very_close_to_resistance(self):
        # distance=(100-98)/100=0.02 < 0.03 → 5
        df = make_daily_df([98.0])
        assert score_price_vs_resistance(df, 100.0) == 5.0

    def test_close_to_resistance(self):
        # distance=(100-94)/100=0.06 < 0.07 → 3
        df = make_daily_df([94.0])
        assert score_price_vs_resistance(df, 100.0) == 3.0

    def test_near_resistance(self):
        # distance=(100-91)/100=0.09 < 0.10 → 1
        df = make_daily_df([91.0])
        assert score_price_vs_resistance(df, 100.0) == 1.0

    def test_far_from_resistance(self):
        # distance=0.20 → 0
        df = make_daily_df([80.0])
        assert score_price_vs_resistance(df, 100.0) == 0.0

    def test_no_high_52w_falls_back_to_df_max(self):
        # Kein high_52w → nimmt df["High"].max(); close=97, max_high≈98.98 → ~0.02 < 0.03 → 5
        df = make_daily_df([98.0] * 5 + [97.0])
        assert score_price_vs_resistance(df, None) == 5.0

    def test_boundary_exactly_3pct(self):
        # distance=(100-97)/100=0.03, NOT < 0.03 → fällt auf < 0.07 → 3
        df = make_daily_df([97.0])
        assert score_price_vs_resistance(df, 100.0) == 3.0


class TestRsi:
    def test_insufficient_data_returns_zero_and_none(self):
        df = make_daily_df([100.0] * 10)
        score, rsi_val = score_rsi(df)
        assert score == 0.0
        assert rsi_val is None

    def test_returns_tuple_of_two(self):
        df = make_daily_df(list(range(50, 90)))
        result = score_rsi(df)
        assert isinstance(result, tuple) and len(result) == 2

    def test_valid_data_returns_numeric_rsi(self):
        closes = list(range(50, 90))  # 40 Tage steigend → RSI sehr hoch
        df = make_daily_df(closes)
        score, rsi_val = score_rsi(df)
        assert rsi_val is not None
        assert isinstance(rsi_val, float)
        assert score in (0.0, 3.0, 5.0)

    def test_monotone_up_rsi_near_100(self):
        # Monoton steigend → RSI nahe 100 → Score 0 (> 75)
        closes = list(range(50, 95))
        df = make_daily_df(closes)
        score, rsi_val = score_rsi(df)
        assert rsi_val is not None and rsi_val > 70


class TestRelativeStrength:
    def test_insufficient_ticker_data(self):
        df = make_daily_df([100.0] * 10)
        df_spy = make_daily_df([100.0] * 25)
        assert score_relative_strength(df, df_spy) == 0.0

    def test_insufficient_spy_data(self):
        df = make_daily_df([100.0] * 25)
        df_spy = make_daily_df([100.0] * 10)
        assert score_relative_strength(df, df_spy) == 0.0

    def test_strong_outperformance(self):
        # Ticker +20%, SPY +5% → rs=1.20/1.05≈1.14 > 1.1 → 4
        t = [100.0] * 21; t[-1] = 120.0
        s = [100.0] * 21; s[-1] = 105.0
        assert score_relative_strength(make_daily_df(t), make_daily_df(s)) == 4.0

    def test_slight_outperformance(self):
        # Ticker +5%, SPY +3% → rs≈1.019, in [1.0, 1.1) → 2
        t = [100.0] * 21; t[-1] = 105.0
        s = [100.0] * 21; s[-1] = 103.0
        assert score_relative_strength(make_daily_df(t), make_daily_df(s)) == 2.0

    def test_underperformance_returns_zero(self):
        # Ticker -5%, SPY +5% → rs<1.0 → 0
        t = [100.0] * 21; t[-1] = 95.0
        s = [100.0] * 21; s[-1] = 105.0
        assert score_relative_strength(make_daily_df(t), make_daily_df(s)) == 0.0


class TestMacd:
    def test_insufficient_data_returns_zero(self):
        df = make_daily_df([100.0] * 20)
        assert score_macd(df) == 0.0

    def test_valid_data_returns_valid_score(self):
        closes = list(range(50, 100))  # 50 Tage
        df = make_daily_df(closes)
        result = score_macd(df)
        assert result in (0.0, 1.0, 3.0)


class TestBollingerSqueeze:
    def test_insufficient_data_returns_zero(self):
        df = make_daily_df([100.0] * 30)
        assert score_bollinger_squeeze(df) == 0.0

    def test_valid_data_returns_valid_score(self):
        # 60 Tage ausreichend für Berechnung
        closes = [100.0 + i * 0.1 for i in range(60)]
        df = make_daily_df(closes)
        result = score_bollinger_squeeze(df)
        assert result in (0.0, 3.0)


class TestVcp:
    def test_empty_df_returns_zero(self):
        assert score_vcp(pd.DataFrame()) == 0.0

    def test_too_few_rows_returns_zero(self):
        df = make_weekly_df([100_000] * 5)
        assert score_vcp(df) == 0.0

    def test_price_far_below_52w_high_returns_zero(self):
        # Kurs weit unter 52W-Hoch (> 10% Abstand) → VCP-Pflichtbedingung nicht erfüllt
        closes = [80.0] * 20  # highs = 80*1.01 = 80.8, max = 80.8
        # Aber wir setzen explizit ein hohes Hoch früh
        df = make_weekly_df([100_000] * 20, closes=closes)
        # Manuell ein hohes Hoch einfügen, damit Kurs weit darunter liegt
        df.at[df.index[0], "High"] = 120.0
        assert score_vcp(df) == 0.0
