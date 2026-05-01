import numpy as np
import pandas as pd

from src.analytics import build_scenario_grid, compute_realized_volatility, safe_spread_pct
from src.pricing import black_scholes_price


def test_realized_vol_reasonable():
    np.random.seed(1)
    returns = np.random.normal(0, 0.01, size=120)
    close = 100 * (1 + pd.Series(returns)).cumprod()
    rv = compute_realized_volatility(close, 60)
    assert 0.05 < rv < 0.4


def test_spread_pct_zero_mid_safe():
    spread = pd.Series([0.1, 0.2])
    mid = pd.Series([0.0, 2.0])
    out = safe_spread_pct(spread, mid)
    assert out.iloc[0] == 0.0
    assert out.iloc[1] == 0.1


def test_scenario_uses_time_to_expiration_years_not_integer_days():
    grid = build_scenario_grid(
        S=100,
        K=100,
        r=0.0,
        base_iv=0.2,
        time_to_expiration_years=0.01,
        option_type="call",
        current_mid=1.0,
        spot_shocks=[0.0],
        iv_shocks=[0.0],
        time_shifts={"today": 0.01},
    )
    assert abs(grid.iloc[0]["shocked_T"] - 0.01) < 1e-12


def test_same_day_positive_t_higher_iv_gives_higher_price():
    low_iv = black_scholes_price(100, 100, 0.001, 0.0, 0.1, "call")
    high_iv = black_scholes_price(100, 100, 0.001, 0.0, 0.5, "call")
    assert high_iv > low_iv


def test_expiration_shift_sets_t_zero_and_intrinsic_value():
    grid = build_scenario_grid(
        S=105,
        K=100,
        r=0.01,
        base_iv=0.2,
        time_to_expiration_years=0.01,
        option_type="call",
        current_mid=1.0,
        spot_shocks=[0.0],
        iv_shocks=[0.0],
        time_shifts={"expiration": 0.0},
    )
    assert grid.iloc[0]["shocked_T"] == 0.0
    assert grid.iloc[0]["theoretical_price"] == 5.0
