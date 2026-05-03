from __future__ import annotations
import numpy as np
import pandas as pd

from src.etf_metadata import get_metadata

PCT_COLS=[
    'daily_return','one_week_return','one_month_return','three_month_return','approx_30d_iv','approx_90d_iv','vrp_30d','vrp_90d',
    'rv_1w','rv_1m','rv_3m','put_skew_30d','call_skew_30d','skew_steepness_30d'
]

def format_cockpit(df: pd.DataFrame):
    fm={c:'{:.2%}' for c in PCT_COLS if c in df.columns}
    for c in ['z_score_daily_return','one_week_z_score','one_month_z_score','three_month_z_score','sd_from_200ma','beta_spy_1m','beta_spy_3m','corr_spy_1m','corr_spy_3m','put_call_volume_ratio','volume_to_oi']:
        if c in df.columns: fm[c]='{:.2f}'
    return df.style.format(fm)


def prepare_return_horizon_data(universe_df: pd.DataFrame, ret_col: str, z_col: str, days: int) -> pd.DataFrame:
    df = universe_df[["ticker", ret_col, "approx_30d_iv", z_col]].copy()
    df = df.rename(columns={ret_col: "return", z_col: "z_score", "approx_30d_iv": "implied_vol"})
    md = df["ticker"].map(get_metadata)
    df["description"] = md.map(lambda x: x["description"])
    df["category"] = md.map(lambda x: x["category"])
    df["expected_move"] = df["implied_vol"] * np.sqrt(days / 252)
    df["standardized_move"] = df["return"] / df["expected_move"].replace(0, np.nan)
    df["period_start"] = (pd.Timestamp.today() - pd.Timedelta(days=days)).strftime("%m/%d/%Y")
    df["period_end"] = pd.Timestamp.today().strftime("%m/%d/%Y")
    return df
