from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import yfinance as yf

from src.analytics import safe_spread_pct


@st.cache_data(ttl=300)
def fetch_underlying_and_expirations(ticker: str) -> tuple[float, list[str], str]:
    tk = yf.Ticker(ticker)
    hist = tk.history(period="2d", interval="1d")
    if hist.empty:
        raise ValueError("No underlying price data returned.")
    spot = float(hist["Close"].dropna().iloc[-1])
    expirations = list(tk.options)
    if not expirations:
        raise ValueError("No option expirations found for ticker.")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return spot, expirations, ts


@st.cache_data(ttl=300)
def fetch_option_chain(ticker: str, expirations: list[str], spot: float) -> pd.DataFrame:
    tk = yf.Ticker(ticker)
    rows: list[pd.DataFrame] = []
    today = pd.Timestamp.utcnow().normalize()
    for exp in expirations:
        chain = tk.option_chain(exp)
        exp_ts = pd.Timestamp(exp)
        dte = int((exp_ts - today).days)
        for side_name, side_df in [("call", chain.calls), ("put", chain.puts)]:
            if side_df.empty:
                continue
            part = side_df.copy()
            part["option_type"] = side_name
            part["expiration"] = exp
            part["days_to_expiration"] = dte
            rows.append(part)

    if not rows:
        return pd.DataFrame()

    df = pd.concat(rows, ignore_index=True)
    df["ticker"] = ticker.upper()
    df["mid"] = (df["bid"].fillna(0) + df["ask"].fillna(0)) / 2.0
    df["spread"] = df["ask"].fillna(0) - df["bid"].fillna(0)
    df["moneyness"] = df["strike"] / spot
    df["spread_pct"] = safe_spread_pct(df["spread"], df["mid"])

    df = df[df["impliedVolatility"].notna() & (df["impliedVolatility"] > 0)]
    df = df[~((df["bid"].fillna(0) <= 0) & (df["ask"].fillna(0) <= 0))]

    needed = [
        "ticker", "option_type", "contractSymbol", "expiration", "days_to_expiration", "strike", "lastPrice",
        "bid", "ask", "mid", "volume", "openInterest", "impliedVolatility", "inTheMoney", "moneyness", "spread", "spread_pct"
    ]
    return df[needed].reset_index(drop=True)
