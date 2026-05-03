import numpy as np
import pandas as pd

from src.market_metrics import correlation_beta
from src.research_flags import apply_research_flags
from src.skew import compute_skew_metrics
from src.vol_metrics import compute_return_metrics
from src.pricing import black_scholes_price


def test_return_and_realized_vol_metrics_exist():
    close = pd.Series(np.linspace(100, 120, 260))
    m = compute_return_metrics(close)
    assert 'one_month_return' in m
    assert 'rv_1m' in m


def test_beta_correlation():
    spy = pd.Series(np.random.normal(0, 0.01, 100))
    asset = spy * 1.5
    corr, beta = correlation_beta(asset, spy, 63)
    assert corr > 0.9
    assert beta > 1.0


def test_atm_iv_and_skew():
    df = pd.DataFrame({
        'option_type':['call','put','put','call'],
        'strike':[100,100,92,108],
        'impliedVolatility':[0.2,0.22,0.30,0.25],
    })
    sk = compute_skew_metrics(df, 100)
    assert sk['atm_iv'] > 0
    assert sk['put_skew'] > 0


def test_vrp_definition():
    iv = 0.30; rv = 0.20
    assert abs((iv-rv) - 0.10) < 1e-12


def test_research_flags_scoring():
    df = pd.DataFrame([{'ticker':'X','vrp_30d':0.2,'approx_30d_iv':0.4,'rv_1m':0.2,'put_skew_30d':0.1,'call_skew_30d':0.1,'z_score_daily_return':3,'one_week_z_score':0,'sd_from_200ma':2.5}])
    out = apply_research_flags(df)
    assert out.loc[0,'score'] > 0


def test_pricing_monotonicity():
    c1 = black_scholes_price(100,100,0.1,0.01,0.2,'call')
    c2 = black_scholes_price(105,100,0.1,0.01,0.2,'call')
    assert c2 > c1
    p1 = black_scholes_price(100,100,0.1,0.01,0.2,'put')
    p2 = black_scholes_price(95,100,0.1,0.01,0.2,'put')
    assert p2 > p1
    v1 = black_scholes_price(100,100,0.1,0.01,0.1,'call')
    v2 = black_scholes_price(100,100,0.1,0.01,0.3,'call')
    assert v2 > v1
    assert black_scholes_price(90,100,0.0,0.01,0.2,'put') == 10
