from __future__ import annotations
import numpy as np
import pandas as pd


def annualized_realized_vol(returns: pd.Series, window: int) -> float:
    r = returns.dropna()
    if len(r) < window:
        return float('nan')
    return float(r.tail(window).std(ddof=1) * np.sqrt(252))


def compute_return_metrics(close: pd.Series) -> dict[str, float]:
    ret = close.pct_change().dropna()
    out = {}
    out['daily_return'] = float(ret.iloc[-1]) if len(ret) else float('nan')
    for name, w in [('one_week_return',5),('one_month_return',21),('three_month_return',63)]:
        out[name] = float(close.iloc[-1]/close.iloc[-w-1]-1) if len(close) > w else float('nan')
    out['rv_1w'] = annualized_realized_vol(ret,5)
    out['rv_1m'] = annualized_realized_vol(ret,21)
    out['rv_3m'] = annualized_realized_vol(ret,63)
    std20 = ret.tail(20).std(ddof=1) if len(ret)>=20 else np.nan
    out['z_score_daily_return'] = out['daily_return']/std20 if std20 and not np.isnan(std20) else np.nan
    def roll_z(window_days:int, horizon:int, val:float):
        r=close.pct_change(horizon).dropna()
        s=r.tail(window_days).std(ddof=1) if len(r)>=window_days else np.nan
        return val/s if s and not np.isnan(s) else np.nan
    out['one_week_z_score']=roll_z(60,5,out['one_week_return'])
    out['one_month_z_score']=roll_z(60,21,out['one_month_return'])
    out['three_month_z_score']=roll_z(60,63,out['three_month_return'])
    sma200 = close.tail(200).mean() if len(close)>=200 else np.nan
    out['simple_moving_average_200d']=float(sma200) if not np.isnan(sma200) else np.nan
    std200 = close.tail(200).std(ddof=1) if len(close)>=200 else np.nan
    out['sd_from_200ma']=(close.iloc[-1]-sma200)/std200 if std200 and not np.isnan(std200) else np.nan
    return out
