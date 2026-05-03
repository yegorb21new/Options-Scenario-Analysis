import numpy as np
import pandas as pd

from src.analytics import (
    add_rv_and_relative_scores,
    assign_moneyness_bucket,
    build_scenario_grid,
    compute_intrinsic_extrinsic,
    compute_realized_volatility,
    safe_spread_pct,
)
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


def test_intrinsic_extrinsic_call_put_and_negative_extrinsic_flag():
    df = pd.DataFrame(
        {
            "option_type": ["call", "put"],
            "strike": [90.0, 110.0],
            "mid": [9.0, 9.0],
        }
    )
    out = compute_intrinsic_extrinsic(df, underlying_price=100.0)
    assert out.loc[0, "intrinsic_value"] == 10.0
    assert out.loc[1, "intrinsic_value"] == 10.0
    assert out.loc[0, "extrinsic_value"] == -1.0
    assert out.loc[1, "extrinsic_value"] == -1.0


def test_moneyness_bucket_assignment():
    assert assign_moneyness_bucket(0.75) == "<0.80"
    assert assign_moneyness_bucket(0.92) == "0.90-0.95"
    assert assign_moneyness_bucket(1.07) == "1.05-1.10"
    assert assign_moneyness_bucket(1.25) == ">1.20"


def test_relative_value_grouping_with_buckets():
    df = pd.DataFrame(
        {
            "expiration": ["2026-06-19", "2026-06-19", "2026-06-19"],
            "option_type": ["call", "call", "call"],
            "moneyness": [0.93, 0.94, 1.15],
            "impliedVolatility": [0.25, 0.35, 0.30],
            "spread_pct": [0.05, 0.05, 0.05],
        }
    )
    out = add_rv_and_relative_scores(df, 0.2, 0.2, 0.2)
    # first two compare together in same bucket; third is separate bucket -> zscore 0
    assert out.loc[2, "iv_zscore_within_expiration"] == 0.0


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


def test_eligibility_filters_exclude_failing_contracts():
    df = pd.DataFrame({
        "spread_pct": [0.10, 0.30],
        "openInterest": [200, 200],
        "volume": [20, 20],
        "moneyness": [1.0, 1.0],
        "extrinsic_value": [0.10, 0.10],
        "extrinsic_pct_of_mid": [0.05, 0.05],
        "impliedVolatility": [0.5, 0.5],
    })
    eligible = df[(df["spread_pct"] <= 0.15) & (df["openInterest"] >= 100) & (df["volume"] >= 10) &
                  (df["moneyness"].between(0.85, 1.15)) & (df["extrinsic_value"] >= 0.05) &
                  (df["extrinsic_pct_of_mid"] >= 0.02) & (df["impliedVolatility"] <= 3.0)]
    assert len(eligible) == 1
