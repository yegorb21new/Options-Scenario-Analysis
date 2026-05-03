from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from src.analytics import add_rv_and_relative_scores, build_scenario_grid, compute_greeks, compute_intrinsic_extrinsic
from src.cockpit import format_cockpit, prepare_return_horizon_data
from src.data import fetch_option_chain, fetch_underlying_and_expirations
from src.market_data import load_universe_metrics
from src.plots import iv_smile, iv_surface, pnl_heatmap
from src.research_flags import apply_research_flags

from src.etf_metadata import ETF_METADATA

UNIVERSE_GROUPS = {
    "Benchmark": ["SPY", "QQQ", "IWM", "DIA", "TLT", "GLD"],
    "Sectors": ["XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE", "XLC"],
    "Credit/Commodities": ["HYG", "LQD", "SLV", "USO", "UNG"],
    "Global/Thematic": ["FXI", "EEM", "IYR", "SMH", "XBI", "KRE", "ARKK"],
}
ALL_TICKERS = [t for ts in UNIVERSE_GROUPS.values() for t in ts]

st.set_page_config(page_title="Options Market Cockpit", layout="wide")
st.title("Options Market Cockpit")
st.caption("Educational research tool using public yfinance/Yahoo data. Diagnostics only, not investment advice.")
st.warning("Market data may be delayed/stale versus broker feeds. Use broker/platform quotes for live decisions.")


# Override Streamlit single-key shortcuts (c/r) so copy behavior works normally.
components.html(
    """
    <script>
    window.addEventListener('keydown', function(e) {
      const t = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
      const isTyping = ['input','textarea'].includes(t) || (e.target && e.target.isContentEditable);
      if (!isTyping && (e.key === 'c' || e.key === 'r')) {
        e.stopPropagation();
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'C')) {
        e.stopPropagation();
      }
    }, true);
    </script>
    """,
    height=0,
)

with st.sidebar:
    section = st.radio("Navigate", ["Today’s Markets", "Cockpit", "Skew Monitor", "Option Chain / Scenario P&L", "Methodology / Validation"])

sel_col1, sel_col2 = st.columns([3, 2])
with sel_col2:
    with st.popover("Universe Picker"):
        group = st.selectbox("Category", ["All"] + list(UNIVERSE_GROUPS.keys()))
        options = ALL_TICKERS if group == "All" else UNIVERSE_GROUPS[group]
        tickers = st.multiselect("Select tickers", options=options, default=UNIVERSE_GROUPS["Benchmark"], help="Search and select one or more tickers")
if not tickers:
    st.info("Select at least one ticker from the Universe Picker.")
    st.stop()
st.caption("Selected tickers appear as removable chips in the picker above.")

universe_df, hist_map, chain30_map, warnings = load_universe_metrics(tickers)
for w in warnings:
    st.warning(f"Ticker skipped: {w}")
if universe_df.empty:
    st.error("No universe metrics available.")
    st.stop()


def _color_returns(v):
    try:
        return "color: #2ecc71" if float(v) > 0 else ("color: #e74c3c" if float(v) < 0 else "")
    except Exception:
        return ""


if section == "Today’s Markets":
    st.header("Today’s Markets")
    st.subheader("Options Activity")
    cols = ["ticker", "price", "daily_return", "total_option_volume", "put_call_volume_ratio", "volume_to_oi", "approx_30d_iv", "vrp_30d"]
    act = universe_df[cols].sort_values("total_option_volume", ascending=False)
    st.dataframe(
        act.style.format({"price": "{:.2f}", "daily_return": "{:.2%}", "total_option_volume": "{:,.0f}", "put_call_volume_ratio": "{:.2f}", "volume_to_oi": "{:.2f}", "approx_30d_iv": "{:.1%}", "vrp_30d": "{:.1%}"}).map(_color_returns, subset=["daily_return", "vrp_30d"]),
        use_container_width=True,
    )

    st.subheader("Research Flags")
    flagged = apply_research_flags(universe_df)
    show = ["ticker", "research_flag", "approx_30d_iv", "rv_1m", "vrp_30d", "skew_steepness_30d", "score"]
    st.dataframe(flagged[show].sort_values("score", ascending=False).style.format({"approx_30d_iv": "{:.1%}", "rv_1m": "{:.1%}", "vrp_30d": "{:.1%}", "skew_steepness_30d": "{:.1%}", "score": "{:.1f}"}), use_container_width=True)

    st.subheader("Return Horizon")
    horizon = st.selectbox("Horizon", ["Daily", "Weekly", "Monthly", "Quarterly"])
    mode = st.radio("Display mode", ["Return", "Standardized Move"], horizontal=True)
    horizon_map = {"Daily": ("daily_return", 1), "Weekly": ("one_week_return", 5), "Monthly": ("one_month_return", 21), "Quarterly": ("three_month_return", 63)}
    ret_col, days = horizon_map[horizon]
    zmap = {"Daily": "z_score_daily_return", "Weekly": "one_week_z_score", "Monthly": "one_month_z_score", "Quarterly": "three_month_z_score"}
    chart_df = prepare_return_horizon_data(universe_df, ret_col=ret_col, z_col=zmap[horizon], days=days)
    metric = "return" if mode == "Return" else "standardized_move"
    chart_df = chart_df.sort_values(metric).reset_index(drop=True)
    chart_df["color"] = np.where(chart_df[metric] >= 0, "pos", "neg")
    chart_df["period"] = chart_df["period_start"] + " to " + chart_df["period_end"]
    fig = px.bar(chart_df, x="ticker", y=metric, color="color", color_discrete_map={"pos": "#2ecc71", "neg": "#e74c3c"})
    fig.update_traces(
        customdata=np.stack([
            chart_df["description"],
            chart_df["category"],
            chart_df["return"],
            chart_df["z_score"],
            chart_df["implied_vol"],
            chart_df["period"],
        ], axis=1),
        hovertemplate=(
            "<b>TICKER:</b> %{x}<br>"
            "<b>Description:</b> %{customdata[0]}<br>"
            "<b>Category:</b> %{customdata[1]}<br>"
            "<b>Return:</b> %{customdata[2]:.1%}<br>"
            "<b>Z-Score:</b> %{customdata[3]:.2f}<br>"
            "<b>Implied Vol:</b> %{customdata[4]:.1%}<br>"
            "<b>Period:</b> %{customdata[5]}<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False, yaxis_title=mode)
    st.plotly_chart(fig, use_container_width=True)

elif section == "Cockpit":
    st.header("Cockpit")
    cockpit_cols = ["ticker", "price", "daily_return", "z_score_daily_return", "approx_30d_iv", "approx_90d_iv", "vrp_30d", "one_week_return", "one_month_return", "three_month_return", "one_week_z_score", "one_month_z_score", "three_month_z_score", "sd_from_200ma", "rv_1w", "rv_1m", "rv_3m", "corr_spy_1m", "corr_spy_3m", "beta_spy_1m", "beta_spy_3m", "put_skew_30d", "call_skew_30d", "skew_steepness_30d", "total_option_volume", "put_call_volume_ratio"]
    cols = [c for c in cockpit_cols if c in universe_df.columns]
    st.dataframe(format_cockpit(universe_df[cols].sort_values("ticker")), use_container_width=True)

elif section == "Skew Monitor":
    st.header("Skew Monitor (Current Snapshot)")
    st.caption("Current skew snapshot only. Not historical percentile-based richness/cheapness.")
    ticker = st.selectbox("Ticker", universe_df["ticker"].tolist(), key="skew_ticker")
    exp30_chain = chain30_map.get(ticker, pd.DataFrame())
    if exp30_chain.empty:
        st.info("No 30D-like chain available.")
    else:
        st.plotly_chart(iv_smile(exp30_chain, "moneyness"), use_container_width=True)
        row = universe_df[universe_df["ticker"] == ticker].iloc[0]
        st.dataframe(pd.DataFrame([{"atm_iv_30d": row.get("approx_30d_iv"), "put_skew_30d": row.get("put_skew_30d"), "call_skew_30d": row.get("call_skew_30d"), "skew_steepness_30d": row.get("skew_steepness_30d"), "approx_90d_iv": row.get("approx_90d_iv"), "put_skew_90d": row.get("put_skew_90d"), "call_skew_90d": row.get("call_skew_90d"), "skew_steepness_90d": row.get("skew_steepness_90d")}]).style.format("{:.2%}"), use_container_width=True)

elif section == "Option Chain / Scenario P&L":
    st.header("Option Chain / Scenario P&L")
    ticker = st.selectbox("Ticker", universe_df["ticker"].tolist(), key="chain_ticker")
    spot, expirations, _ = fetch_underlying_and_expirations(ticker)
    chain = fetch_option_chain(ticker, expirations[:6], spot)
    chain = compute_intrinsic_extrinsic(chain, spot)
    chain = add_rv_and_relative_scores(chain, np.nan, np.nan, np.nan)

    c1, c2, c3 = st.columns(3)
    opt_type_sel = c1.selectbox("Option type", ["both", "call", "put"])
    max_spread = c2.slider("Max spread %", 0.0, 1.0, 0.15, 0.01)
    max_iv = c3.number_input("Max implied vol", min_value=0.1, value=3.0, step=0.1)
    min_oi = st.number_input("Min open interest", min_value=0, value=100)
    min_vol = st.number_input("Min volume", min_value=0, value=10)
    min_extrinsic = st.number_input("Min extrinsic value", min_value=0.0, value=0.05, step=0.01)
    money_rng = st.slider("Moneyness range", 0.3, 2.0, (0.85, 1.15), 0.01)

    filtered = chain.copy()
    if opt_type_sel != "both":
        filtered = filtered[filtered["option_type"] == opt_type_sel]
    filtered = filtered[(filtered["spread_pct"] <= max_spread) & (filtered["openInterest"].fillna(0) >= min_oi) & (filtered["volume"].fillna(0) >= min_vol) & (filtered["moneyness"].between(money_rng[0], money_rng[1])) & (filtered["extrinsic_value"] >= min_extrinsic) & (filtered["impliedVolatility"] <= max_iv)]
    st.dataframe(filtered.head(200), use_container_width=True)
    st.plotly_chart(iv_smile(filtered, "moneyness"), use_container_width=True)
    if len(filtered) > 10:
        st.plotly_chart(iv_surface(filtered), use_container_width=True)

    contract = st.selectbox("Contract", filtered["contractSymbol"].tolist())
    row = filtered[filtered["contractSymbol"] == contract].iloc[0]
    base_T = float(row["time_to_expiration_years"])
    time_shifts = {"today": base_T, "+1 day": max(base_T - 1 / 365, 0), "+1 week": max(base_T - 7 / 365, 0), "halfway to expiration": base_T / 2, "expiration": 0.0}
    scenarios = build_scenario_grid(spot, float(row["strike"]), 0.045, float(row["impliedVolatility"]), base_T, str(row["option_type"]), float(row["mid"]), list(np.arange(-0.2, 0.21, 0.05)), list(np.arange(-0.2, 0.21, 0.05)), time_shifts)
    selected_time = st.selectbox("Time shift", list(time_shifts.keys()))
    st.plotly_chart(pnl_heatmap(scenarios, selected_time, "pnl_dollars", "P&L Dollars"), use_container_width=True)
    st.plotly_chart(pnl_heatmap(scenarios, selected_time, "pnl_percent", "P&L Percent"), use_container_width=True)
    st.write(compute_greeks(spot, float(row["strike"]), base_T, 0.045, float(row["impliedVolatility"]), str(row["option_type"])))

else:
    st.header("Methodology / Validation")
    st.markdown(
        """
- Public yfinance/Yahoo data can be delayed or stale.
- Skew percentile/richness cross-sectional panel is hidden until historical skew data exists.
- Standardized Move formula: `period_return / (ATM_IV * sqrt(horizon_days / 252))`.
- Percentages are displayed in human-readable format.
- Scenario P&L uses simplified Black-Scholes assumptions and exact seconds-based time to expiration proxy.
- This app provides research diagnostics, not investment recommendations.
"""
    )
