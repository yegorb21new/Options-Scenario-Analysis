from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.analytics import add_rv_and_relative_scores, build_scenario_grid, compute_greeks, compute_realized_volatility
from src.data import fetch_option_chain, fetch_underlying_and_expirations
from src.plots import iv_smile, iv_surface, pnl_heatmap

st.set_page_config(page_title="Options Volatility Surface & Scenario Analytics Dashboard", layout="wide")
st.title("Options Volatility Surface & Scenario Analytics Dashboard")
st.caption("Educational research tool. Uses public option-chain data and simplified Black-Scholes assumptions. Not investment advice.")
st.warning("Market data is sourced from yfinance/Yahoo and may be delayed or stale. Use broker/platform quotes for live trading decisions.")

with st.sidebar:
    ticker = st.text_input("Ticker", value="NVDA").upper().strip()
    num_exp = st.slider("Upcoming expirations to load", min_value=1, max_value=12, value=6)
    r = st.number_input("Risk-free rate", min_value=0.0, max_value=0.2, value=0.045, step=0.005, format="%.3f")

try:
    spot, expirations, last_updated = fetch_underlying_and_expirations(ticker)
except Exception as exc:
    st.error(f"Unable to fetch market data for {ticker}: {exc}")
    st.stop()

selected_exp = expirations[:num_exp]
try:
    chain = fetch_option_chain(ticker, selected_exp, spot)
except Exception as exc:
    st.error(f"Unable to fetch option chain data: {exc}")
    st.stop()

if chain.empty:
    st.warning("No usable option-chain rows were returned after quality filters.")
    st.stop()

hist = __import__("yfinance").Ticker(ticker).history(period="1y", interval="1d")
rv20 = compute_realized_volatility(hist["Close"], 20)
rv30 = compute_realized_volatility(hist["Close"], 30)
rv60 = compute_realized_volatility(hist["Close"], 60)
chain = add_rv_and_relative_scores(chain, rv20, rv30, rv60)

st.write(f"**Spot:** {spot:.2f}  |  **Last updated:** {last_updated}")
c1, c2, c3 = st.columns(3)
c1.metric("Realized Vol (20d)", f"{rv20:.2%}" if not np.isnan(rv20) else "N/A")
c2.metric("Realized Vol (30d)", f"{rv30:.2%}" if not np.isnan(rv30) else "N/A")
c3.metric("Realized Vol (60d)", f"{rv60:.2%}" if not np.isnan(rv60) else "N/A")

with st.sidebar:
    opt_type_sel = st.selectbox("Option type", ["both", "call", "put"])
    max_spread = st.slider("Max spread %", 0.0, 1.0, 0.25, 0.01)
    min_oi = st.number_input("Min open interest", min_value=0, value=0)
    min_vol = st.number_input("Min volume", min_value=0, value=0)
    money_rng = st.slider("Moneyness range", 0.3, 2.0, (0.7, 1.3), 0.01)
    exp_filter = st.multiselect("Expirations", options=sorted(chain["expiration"].unique()), default=sorted(chain["expiration"].unique()))

filtered = chain.copy()
if opt_type_sel != "both":
    filtered = filtered[filtered["option_type"] == opt_type_sel]
filtered = filtered[
    (filtered["spread_pct"] <= max_spread)
    & (filtered["openInterest"].fillna(0) >= min_oi)
    & (filtered["volume"].fillna(0) >= min_vol)
    & (filtered["moneyness"].between(money_rng[0], money_rng[1]))
    & (filtered["expiration"].isin(exp_filter))
]

st.subheader("Filtered option chain")
show_cols = ["option_type", "expiration", "days_to_expiration", "lastTradeDate", "minutes_since_last_trade", "strike", "bid", "ask", "mid", "volume", "openInterest", "impliedVolatility", "moneyness", "spread_pct", "inTheMoney"]
st.dataframe(filtered[show_cols].style.format({"impliedVolatility": "{:.2%}", "spread_pct": "{:.2%}", "moneyness": "{:.3f}", "minutes_since_last_trade": "{:.1f}"}), use_container_width=True)

x_axis = st.radio("Smile x-axis", ["moneyness", "strike"], horizontal=True)
st.plotly_chart(iv_smile(filtered, x_axis), use_container_width=True)
if len(filtered) > 10:
    st.plotly_chart(iv_surface(filtered), use_container_width=True)
else:
    st.info("Need more filtered points to render IV surface.")

st.subheader("Relative richness/cheapness diagnostics")
st.caption("Relative value scores are crude diagnostics based on current chain IV, realized volatility, and liquidity. They are not predictions and do not account for earnings, dividends, borrow, jumps, or full volatility history.")
screen_cols = ["contractSymbol", "option_type", "expiration", "strike", "impliedVolatility", "spread_pct", "iv_zscore_within_expiration", "relative_value_score"]
st.markdown("**Potentially cheaper by relative IV/liquidity screen**")
st.dataframe(filtered.sort_values("relative_value_score", ascending=False)[screen_cols].head(15), use_container_width=True)
st.markdown("**Potentially richer by relative IV/liquidity screen**")
st.dataframe(filtered.sort_values("relative_value_score", ascending=True)[screen_cols].head(15), use_container_width=True)

st.subheader("Scenario P&L")
st.caption("Scenario prices are theoretical estimates. Actual option prices may differ due to market microstructure, early exercise risk, dividends, skew dynamics, and changes in supply/demand.")
if filtered.empty:
    st.warning("No rows available for scenario analysis after filters.")
    st.stop()

contract = st.selectbox("Select contract", filtered["contractSymbol"].tolist())
row = filtered[filtered["contractSymbol"] == contract].iloc[0]

spot_step = st.selectbox("Spot shock step", [0.025, 0.05], index=1)
iv_step = st.selectbox("IV shock step (absolute)", [0.02, 0.05], index=1)
spot_shocks = list(np.arange(-0.20, 0.2001, spot_step))
iv_shocks = list(np.arange(-0.20, 0.2001, iv_step))
dte = int(row["days_to_expiration"])
time_shifts = {"today": 0, "+1 day": 1, "+1 week": 7, "halfway": max(dte // 2, 0), "expiration": dte}

scenarios = build_scenario_grid(
    S=spot, K=float(row["strike"]), r=float(r), base_iv=float(row["impliedVolatility"]), days_to_expiration=dte,
    option_type=str(row["option_type"]), current_mid=float(row["mid"]), spot_shocks=spot_shocks, iv_shocks=iv_shocks, time_shifts=time_shifts,
)
selected_time = st.selectbox("Time shift for heatmaps", list(time_shifts.keys()))
selected_days_elapsed = time_shifts[selected_time]
shocked_T = max((dte - selected_days_elapsed) / 365.0, 0.0)

st.markdown("**Selected contract summary (for heatmap validation)**")
summary_df = pd.DataFrame([
    {
        "contract_symbol": contract,
        "option_type": row["option_type"],
        "expiration": row["expiration"],
        "days_to_expiration": dte,
        "strike": float(row["strike"]),
        "underlying_price": float(spot),
        "moneyness": float(row["moneyness"]),
        "current_bid": float(row["bid"]),
        "current_ask": float(row["ask"]),
        "current_mid": float(row["mid"]),
        "base_implied_volatility": float(row["impliedVolatility"]),
        "selected_time_shift": selected_time,
        "shocked_time_to_expiration_years": shocked_T,
    }
])
st.dataframe(
    summary_df.style.format(
        {
            "strike": "{:.2f}",
            "underlying_price": "{:.2f}",
            "moneyness": "{:.3f}",
            "current_bid": "{:.2f}",
            "current_ask": "{:.2f}",
            "current_mid": "{:.2f}",
            "base_implied_volatility": "{:.2%}",
            "shocked_time_to_expiration_years": "{:.4f}",
        }
    ),
    use_container_width=True,
)

st.plotly_chart(pnl_heatmap(scenarios, selected_time, "pnl_dollars", "P&L Dollars"), use_container_width=True)
st.plotly_chart(pnl_heatmap(scenarios, selected_time, "pnl_percent", "P&L Percent"), use_container_width=True)

T_now = max(dte / 365.0, 0.0)
greeks = compute_greeks(spot, float(row["strike"]), T_now, float(r), float(row["impliedVolatility"]), str(row["option_type"]))
st.write("**Selected contract details**")
st.json({
    "contract": contract,
    "type": row["option_type"],
    "strike": float(row["strike"]),
    "expiration": row["expiration"],
    "days_to_expiration": dte,
    "current_mid": float(row["mid"]),
    "base_iv": float(row["impliedVolatility"]),
    "greeks": greeks,
})
st.dataframe(scenarios.head(100), use_container_width=True)
