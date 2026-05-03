from __future__ import annotations
import numpy as np
import pandas as pd


def score_and_flag(row: pd.Series, q: dict[str,float]) -> tuple[str,float]:
    score=0.0; labels=[]
    if row.get('vrp_30d',np.nan) > q['vrp_hi'] and row.get('approx_30d_iv',np.nan)>row.get('rv_1m',np.nan):
        labels.append('High VRP / Sell-Vol Watch'); score+=2
    if row.get('vrp_30d',np.nan) < q['vrp_lo']:
        labels.append('Low VRP / Long-Vol Watch'); score+=2
    if row.get('put_skew_30d',np.nan) > q['put_skew_hi']:
        labels.append('Put Skew Rich'); score+=1.5
    if row.get('call_skew_30d',np.nan) > q['call_skew_hi']:
        labels.append('Call Skew Rich'); score+=1.5
    if abs(row.get('z_score_daily_return',0))>2 or abs(row.get('one_week_z_score',0))>2:
        labels.append('Large Move / High RV'); score+=1
    if abs(row.get('sd_from_200ma',0))>2:
        labels.append('Trend Extended'); score+=1
    if abs(row.get('sd_from_200ma',0))>3:
        labels.append('Mean-Reversion Watch'); score+=1
    return ('; '.join(labels) if labels else 'No major flag'), score


def apply_research_flags(df: pd.DataFrame)->pd.DataFrame:
    out=df.copy()
    q={
        'vrp_hi':float(out['vrp_30d'].quantile(0.75)),
        'vrp_lo':float(out['vrp_30d'].quantile(0.25)),
        'put_skew_hi':float(out['put_skew_30d'].quantile(0.75)),
        'call_skew_hi':float(out['call_skew_30d'].quantile(0.75)),
    }
    flags=out.apply(lambda r: score_and_flag(r,q),axis=1)
    out['research_flag']=[f for f,_ in flags]
    out['score']=[s for _,s in flags]
    return out
