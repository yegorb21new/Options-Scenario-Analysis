from __future__ import annotations
import numpy as np
import pandas as pd


def _avg_iv(df: pd.DataFrame) -> float:
    d = df[df['impliedVolatility'].notna() & (df['impliedVolatility']>0)]
    return float(d['impliedVolatility'].mean()) if not d.empty else float('nan')


def compute_skew_metrics(chain_df: pd.DataFrame, spot: float) -> dict[str,float]:
    if chain_df.empty:
        return {k: float('nan') for k in ['atm_iv','otm_put_iv','otm_call_iv','put_skew','call_skew','skew_steepness']}
    d=chain_df.copy(); d['moneyness']=d['strike']/spot
    atm=_avg_iv(d[d['moneyness'].between(0.97,1.03)])
    put=_avg_iv(d[(d['option_type']=='put') & d['moneyness'].between(0.90,0.97)])
    call=_avg_iv(d[(d['option_type']=='call') & d['moneyness'].between(1.03,1.10)])
    return {'atm_iv':atm,'otm_put_iv':put,'otm_call_iv':call,'put_skew':put-atm if not np.isnan(put) and not np.isnan(atm) else np.nan,
            'call_skew':call-atm if not np.isnan(call) and not np.isnan(atm) else np.nan,
            'skew_steepness':put-call if not np.isnan(put) and not np.isnan(call) else np.nan}
