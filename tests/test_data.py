import pandas as pd

from src.data import (
    calculate_days_to_expiration,
    calculate_mid,
    calculate_minutes_since_last_trade,
    calculate_spread_pct,
)


def test_calculate_days_to_expiration_uses_date_only_arithmetic():
    dte = calculate_days_to_expiration("2030-01-17")
    assert isinstance(dte, int)
    assert dte >= 0


def test_calculate_days_to_expiration_handles_tz_aware_input_without_subtraction_error():
    dte = calculate_days_to_expiration("2030-01-17T00:00:00+00:00")
    assert isinstance(dte, int)
    assert dte >= 0


def test_calculate_mid():
    bid = pd.Series([1.0, 2.0])
    ask = pd.Series([1.2, 2.4])
    out = calculate_mid(bid, ask)
    assert out.iloc[0] == 1.1
    assert out.iloc[1] == 2.2


def test_calculate_spread_pct():
    bid = pd.Series([1.0])
    ask = pd.Series([1.2])
    out = calculate_spread_pct(bid, ask)
    assert abs(out.iloc[0] - ((1.2 - 1.0) / 1.1)) < 1e-9


def test_calculate_spread_pct_zero_mid_safe():
    bid = pd.Series([0.0])
    ask = pd.Series([0.0])
    out = calculate_spread_pct(bid, ask)
    assert out.iloc[0] == 0.0


def test_calculate_minutes_since_last_trade_non_negative_or_none():
    s = pd.Series(["2030-01-17T00:00:00+00:00", None])
    out = calculate_minutes_since_last_trade(s)
    assert out.iloc[0] >= 0
    assert pd.isna(out.iloc[1])
