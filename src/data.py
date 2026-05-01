from __future__ import annotations

from datetime import date, datetime, timezone
import pandas as pd
import streamlit as st
import yfinance as yf


def calculate_days_to_expiration(expiration: str) -> int:
    """Calculate non-negative calendar days to expiration using date-only arithmetic."""
    expiration_date = pd.to_datetime(expiration).date()
    return max((expiration_date - date.today()).days, 0)


def calculate_mid(bid: pd.Series, ask: pd.Series) -> pd.Series:
    """Calculate quote midpoint from bid/ask."""
    return (bid.fillna(0.0) + ask.fillna(0.0)) / 2.0


def calculate_spread_pct(bid: pd.Series, ask: pd.Series) -> pd.Series:
    """Calculate spread percentage safely as (ask-bid)/mid."""
    mid = calculate_mid(bid, ask)
    spread = ask.fillna(0.0) - bid.fillna(0.0)
    mid_safe = mid.replace(0, pd.NA)
    return (spread / mid_safe).fillna(0.0)


def calculate_minutes_since_last_trade(last_trade_date: pd.Series) -> pd.Series:
    """Calculate non-negative minutes since last trade; return None where unavailable."""
    parsed = pd.to_datetime(last_trade_date, errors="coerce", utc=True)
    now_utc = pd.Timestamp.now(tz="UTC")
    mins = (now_utc - parsed).dt.total_seconds() / 60.0
    mins = mins.where(parsed.notna(), other=pd.NA)
    mins = mins.clip(lower=0)
    return mins


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
    for exp in expirations:
        chain = tk.option_chain(exp)
        dte = calculate_days_to_expiration(exp)
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
    df["mid"] = calculate_mid(df["bid"], df["ask"])
    df["spread"] = df["ask"].fillna(0.0) - df["bid"].fillna(0.0)
    df["moneyness"] = df["strike"] / spot
    df["spread_pct"] = calculate_spread_pct(df["bid"], df["ask"])
    if "lastTradeDate" in df.columns:
        df["minutes_since_last_trade"] = calculate_minutes_since_last_trade(df["lastTradeDate"])
    else:
        df["lastTradeDate"] = pd.NaT
        df["minutes_since_last_trade"] = pd.NA

    df = df[df["impliedVolatility"].notna() & (df["impliedVolatility"] > 0)]
    df = df[~((df["bid"].fillna(0) <= 0) & (df["ask"].fillna(0) <= 0))]

    needed = [
        "ticker", "option_type", "contractSymbol", "expiration", "days_to_expiration", "lastTradeDate", "minutes_since_last_trade", "strike", "lastPrice",
        "bid", "ask", "mid", "volume", "openInterest", "impliedVolatility", "inTheMoney", "moneyness", "spread", "spread_pct"
    ]
    return df[needed].reset_index(drop=True)
