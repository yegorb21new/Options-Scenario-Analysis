from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics import add_rv_and_relative_scores, build_scenario_grid, compute_greeks, compute_intrinsic_extrinsic
from src.cockpit import format_cockpit
from src.data import fetch_option_chain, fetch_underlying_and_expirations
from src.market_data import load_universe_metrics
from src.plots import iv_smile, iv_surface, pnl_heatmap
from src.research_flags import apply_research_flags

DEFAULT_UNIVERSE = "SPY,QQQ,IWM,DIA,XLF,XLE,XLK,XLV,XLI,XLP,XLY,XLU,XLB,XLRE,XLC,TLT,HYG,LQD,GLD,SLV,USO,UNG,FXI,EEM,IYR,SMH,XBI,KRE,ARKK"

st.set_page_config(page_title="Options Market Cockpit", layout="wide")
st.title("Options Market Cockpit")
st.caption("Educational research tool using public yfinance/Yahoo data. Diagnostics only, not investment advice.")
st.warning("Market data may be delayed/stale versus broker feeds. Use broker/platform quotes for live decisions.")

with st.sidebar:
    universe_text = st.text_area("Universe tickers (comma-separated)", value=DEFAULT_UNIVERSE, height=100)
    tickers = [t.strip().upper() for t in universe_text.split(",") if t.strip()]

universe_df, hist_map, chain30_map, warnings = load_universe_metrics(tickers)
for w in warnings:
    st.warning(f"Ticker skipped: {w}")
if universe_df.empty:
    st.error("No universe metrics available.")
    st.stop()

# optional snapshots
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Today’s Markets", "Cockpit", "Skew Monitor", "Option Chain / Scenario P&L", "Methodology / Validation"])

with tab1:
    st.subheader("Options Activity")
    cols=["ticker","price","daily_return","total_option_volume","put_call_volume_ratio","volume_to_oi","approx_30d_iv","vrp_30d"]
    st.dataframe(universe_df[cols].sort_values("total_option_volume", ascending=False).style.format({"daily_return":"{:.2%}","approx_30d_iv":"{:.2%}","vrp_30d":"{:.2%}"}), use_container_width=True)

    st.subheader("Research Flags")
    flagged = apply_research_flags(universe_df)
    show=["ticker","research_flag","approx_30d_iv","rv_1m","vrp_30d","skew_steepness_30d","score"]
    st.dataframe(flagged[show].sort_values("score", ascending=False).style.format({"approx_30d_iv":"{:.2%}","rv_1m":"{:.2%}","vrp_30d":"{:.2%}","skew_steepness_30d":"{:.2%}"}), use_container_width=True)

    st.subheader("Skew Extremes")
    tenor=st.selectbox("Tenor", ["30D","90D"], key="tenor1")
    put_col=f"put_skew_{tenor.lower()}"; call_col=f"call_skew_{tenor.lower()}"
    c1,c2,c3,c4=st.columns(4)
    c1.dataframe(universe_df[["ticker",put_col]].nsmallest(5, put_col).rename(columns={put_col:"Cheap Puts"}))
    c2.dataframe(universe_df[["ticker",put_col]].nlargest(5, put_col).rename(columns={put_col:"Rich Puts"}))
    c3.dataframe(universe_df[["ticker",call_col]].nsmallest(5, call_col).rename(columns={call_col:"Cheap Calls"}))
    c4.dataframe(universe_df[["ticker",call_col]].nlargest(5, call_col).rename(columns={call_col:"Rich Calls"}))
    st.caption("Skew rankings compare option IV by moneyness within the selected universe. They are diagnostics, not recommendations.")

    move_col = st.selectbox("Return horizon", ["daily_return","one_week_return","one_month_return","three_month_return"])
    bdf = universe_df[["ticker",move_col]].sort_values(move_col)
    bdf["color"] = np.where(bdf[move_col] >= 0, "green", "red")
    st.plotly_chart(px.bar(bdf, x="ticker", y=move_col, color="color", color_discrete_map={"green":"#2ecc71","red":"#e74c3c"}), use_container_width=True)

with tab2:
    st.subheader("Cockpit")
    cockpit_cols=["ticker","price","daily_return","z_score_daily_return","approx_30d_iv","approx_90d_iv","vrp_30d","one_week_return","one_month_return","three_month_return","one_week_z_score","one_month_z_score","three_month_z_score","sd_from_200ma","rv_1w","rv_1m","rv_3m","corr_spy_1m","corr_spy_3m","beta_spy_1m","beta_spy_3m","put_skew_30d","call_skew_30d","skew_steepness_30d","total_option_volume","put_call_volume_ratio"]
    cols=[c for c in cockpit_cols if c in universe_df.columns]
    st.dataframe(format_cockpit(universe_df[cols].sort_values("ticker")), use_container_width=True)

with tab3:
    st.subheader("Skew Monitor")
    ticker = st.selectbox("Ticker", universe_df["ticker"].tolist(), key="skew_ticker")
    spot = float(universe_df.loc[universe_df["ticker"]==ticker, "price"].iloc[0])
    exp30_chain=chain30_map.get(ticker, pd.DataFrame())
    if exp30_chain.empty:
        st.info("No 30D-like chain available.")
    else:
        st.plotly_chart(iv_smile(exp30_chain, "moneyness"), use_container_width=True)
        st.dataframe(exp30_chain[["option_type","strike","moneyness","impliedVolatility"]].head(40), use_container_width=True)
        row = universe_df[universe_df["ticker"]==ticker].iloc[0]
        st.write({"atm_iv_30d": row.get("approx_30d_iv"), "put_skew_30d": row.get("put_skew_30d"), "call_skew_30d": row.get("call_skew_30d"), "skew_steepness_30d": row.get("skew_steepness_30d")})

with tab4:
    ticker = st.selectbox("Ticker for chain/scenario", universe_df["ticker"].tolist(), key="chain_ticker")
    spot, expirations, last_updated = fetch_underlying_and_expirations(ticker)
    chain = fetch_option_chain(ticker, expirations[:6], spot)
    chain = compute_intrinsic_extrinsic(chain, spot)
    chain = add_rv_and_relative_scores(chain, np.nan, np.nan, np.nan)
    opt_type_sel = st.selectbox("Option type", ["both", "call", "put"], key="ot4")
    max_spread = st.slider("Max spread %", 0.0, 1.0, 0.15, 0.01, key='sp4')
    min_oi = st.number_input("Min open interest", min_value=0, value=100, key='oi4')
    min_vol = st.number_input("Min volume", min_value=0, value=10, key='vol4')
    min_extrinsic = st.number_input("Min extrinsic value", min_value=0.0, value=0.05, step=0.01, key='ex4')
    max_iv = st.number_input("Max implied volatility", min_value=0.1, value=3.00, step=0.05, key='iv4')
    money_rng = st.slider("Moneyness range", 0.3, 2.0, (0.85, 1.15), 0.01, key='mn4')
    filtered=chain.copy()
    if opt_type_sel!='both': filtered=filtered[filtered['option_type']==opt_type_sel]
    filtered=filtered[(filtered['spread_pct']<=max_spread)&(filtered['openInterest'].fillna(0)>=min_oi)&(filtered['volume'].fillna(0)>=min_vol)&(filtered['moneyness'].between(money_rng[0],money_rng[1]))&(filtered['extrinsic_value']>=min_extrinsic)&(filtered['impliedVolatility']<=max_iv)]
    st.caption("Deep ITM/OTM contracts can have unstable IV because tiny quote differences dominate extrinsic value.")
    st.dataframe(filtered.head(200), use_container_width=True)
    st.plotly_chart(iv_smile(filtered, 'moneyness'), use_container_width=True)
    if len(filtered)>10: st.plotly_chart(iv_surface(filtered), use_container_width=True)

    contract = st.selectbox("Contract", filtered['contractSymbol'].tolist())
    row = filtered[filtered['contractSymbol']==contract].iloc[0]
    base_T=float(row['time_to_expiration_years'])
    time_shifts={"today":base_T,"+1 day":max(base_T-1/365,0),"+1 week":max(base_T-7/365,0),"halfway to expiration":base_T/2,"expiration":0.0}
    scenarios=build_scenario_grid(spot,float(row['strike']),0.045,float(row['impliedVolatility']),base_T,str(row['option_type']),float(row['mid']),list(np.arange(-0.2,0.21,0.05)),list(np.arange(-0.2,0.21,0.05)),time_shifts)
    selected_time=st.selectbox('Time shift', list(time_shifts.keys()))
    st.plotly_chart(pnl_heatmap(scenarios, selected_time, 'pnl_dollars', 'P&L Dollars'), use_container_width=True)
    st.plotly_chart(pnl_heatmap(scenarios, selected_time, 'pnl_percent', 'P&L Percent'), use_container_width=True)
    st.write(compute_greeks(spot,float(row['strike']),base_T,0.045,float(row['impliedVolatility']),str(row['option_type'])))

with tab5:
    st.markdown("""
### Methodology / Validation
- Data source: yfinance/Yahoo public data; quotes may be delayed/stale.
- Vol units: decimal internally (0.25 = 25%), percentages in UI.
- Realized volatility: std(close-to-close returns) * sqrt(252).
- ATM IV: approximate near-ATM average (moneyness ~0.97-1.03).
- VRP: approx IV - realized volatility over matching horizon.
- Skew: OTM put/call IV relative to ATM IV.
- Beta/correlation: rolling covariance/variance and Pearson correlation vs SPY.
- Scenario P&L: Black-Scholes theoretical values under spot/IV/time shocks.
- Time to expiration: exact seconds to 4:00pm ET expiration proxy.
- Not investment advice.
""")
