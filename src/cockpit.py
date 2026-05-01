from __future__ import annotations
import pandas as pd

PCT_COLS=[
    'daily_return','one_week_return','one_month_return','three_month_return','approx_30d_iv','approx_90d_iv','vrp_30d','vrp_90d',
    'rv_1w','rv_1m','rv_3m','put_skew_30d','call_skew_30d','skew_steepness_30d'
]

def format_cockpit(df: pd.DataFrame):
    fm={c:'{:.2%}' for c in PCT_COLS if c in df.columns}
    for c in ['z_score_daily_return','one_week_z_score','one_month_z_score','three_month_z_score','sd_from_200ma','beta_spy_1m','beta_spy_3m','corr_spy_1m','corr_spy_3m','put_call_volume_ratio','volume_to_oi']:
        if c in df.columns: fm[c]='{:.2f}'
    return df.style.format(fm)
