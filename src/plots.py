from __future__ import annotations

import pandas as pd
import plotly.express as px


def iv_smile(df: pd.DataFrame, x_axis: str):
    return px.scatter(
        df,
        x=x_axis,
        y="impliedVolatility",
        color="expiration",
        facet_row="option_type" if df["option_type"].nunique() > 1 else None,
        hover_data=["strike", "expiration", "impliedVolatility", "mid", "volume", "openInterest"],
        title="Implied Volatility Smile/Skew",
    )


def iv_surface(df: pd.DataFrame):
    return px.scatter_3d(
        df,
        x="moneyness",
        y="days_to_expiration",
        z="impliedVolatility",
        color="impliedVolatility",
        hover_data=["option_type", "expiration", "strike", "mid"],
        title="IV Surface (Scatter)",
    )


def pnl_heatmap(df: pd.DataFrame, time_shift: str, value_col: str, title: str):
    sub = df[df["time_shift"] == time_shift].copy()
    pivot = sub.pivot_table(index="iv_shock", columns="spot_shock", values=value_col)
    return px.imshow(pivot, text_auto=True, aspect="auto", title=title)
