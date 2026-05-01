import numpy as np
import pandas as pd

from src.analytics import compute_realized_volatility, safe_spread_pct


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
