from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
import yfinance as yf


def calculate_days_to_expiration(expiration: str) -> int:
    """Calculate non-negative calendar days to expiration using date-only arithmetic."""
    expiration_date = pd.to_datetime(expiration).date()
    return max((expiration_date - date.today()).days, 0)


def calculate_time_to_expiration_years(
    expiration: str,
    now: datetime | None = None,
    market_close_hour: int = 16,
    market_close_minute: int = 0,
    timezone_name: str = "America/New_York",
) -> float:
    """Calculate calendar-time years until expiration at market close in configured timezone."""
    tz = ZoneInfo(timezone_name)
    now_dt = now if now is not None else datetime.now(tz)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=tz)
    else:
        now_dt = now_dt.astimezone(tz)

    exp_date = pd.to_datetime(expiration).date()
    exp_dt = datetime(exp_date.year, exp_date.month, exp_date.day, market_close_hour, market_close_minute, tzinfo=tz)
    sec = max((exp_dt - now_dt).total_seconds(), 0.0)
    return sec / (365.0 * 24 * 60 * 60)


def calculate_mid(bid: pd.Series, ask: pd.Series) -> pd.Series:
    return (bid.fillna(0.0) + ask.fillna(0.0)) / 2.0


def calculate_spread_pct(bid: pd.Series, ask: pd.Series) -> pd.Series:
    mid = calculate_mid(bid, ask)
    spread = ask.fillna(0.0) - bid.fillna(0.0)
    return (spread / mid.replace(0, pd.NA)).fillna(0.0)


def calculate_minutes_since_last_trade(last_trade_date: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(last_trade_date, errors="coerce", utc=True)
    now_utc = pd.Timestamp.now(tz="UTC")
    mins = (now_utc - parsed).dt.total_seconds() / 60.0
    return mins.where(parsed.notna(), other=pd.NA).clip(lower=0)


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
        t_years = calculate_time_to_expiration_years(exp)
        hte = t_years * 365.0 * 24.0
        for side_name, side_df in [("call", chain.calls), ("put", chain.puts)]:
            if side_df.empty:
                continue
            part = side_df.copy()
            part["option_type"] = side_name
            part["expiration"] = exp
            part["days_to_expiration"] = dte
            part["time_to_expiration_years"] = t_years
            part["hours_to_expiration"] = hte
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
        "ticker", "option_type", "contractSymbol", "expiration", "days_to_expiration", "time_to_expiration_years", "hours_to_expiration",
        "lastTradeDate", "minutes_since_last_trade", "strike", "lastPrice", "bid", "ask", "mid", "volume", "openInterest",
        "impliedVolatility", "inTheMoney", "moneyness", "spread", "spread_pct"
    ]
    return df[needed].reset_index(drop=True)
