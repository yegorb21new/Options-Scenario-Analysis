"""Analytics utilities for options chains and scenario generation."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from src.pricing import (
    black_scholes_delta,
    black_scholes_gamma,
    black_scholes_price,
    black_scholes_theta,
    black_scholes_vega,
)


def safe_spread_pct(spread: pd.Series, mid: pd.Series) -> pd.Series:
    """Calculate spread percentage safely, preventing divide-by-zero issues."""
    mid_safe = mid.replace(0, np.nan)
    result = spread / mid_safe
    return result.fillna(0.0)


def compute_realized_volatility(close: pd.Series, window: int) -> float:
    """Compute annualized realized volatility from close prices over rolling window."""
    returns = close.pct_change().dropna()
    if len(returns) < window:
        return float("nan")
    return float(returns.tail(window).std(ddof=1) * np.sqrt(252))


def add_rv_and_relative_scores(df: pd.DataFrame, rv20: float, rv30: float, rv60: float) -> pd.DataFrame:
    """Add IV-RV and relative value diagnostics columns."""
    out = df.copy()
    out["iv_minus_rv_20d"] = out["impliedVolatility"] - rv20
    out["iv_minus_rv_30d"] = out["impliedVolatility"] - rv30
    out["iv_minus_rv_60d"] = out["impliedVolatility"] - rv60
    out["iv_rv_30d_spread"] = out["iv_minus_rv_30d"]

    grp = out.groupby(["expiration", "option_type"])["impliedVolatility"]
    mean = grp.transform("mean")
    std = grp.transform("std").replace(0, np.nan)
    out["iv_zscore_within_expiration"] = ((out["impliedVolatility"] - mean) / std).fillna(0.0)
    out["liquidity_penalty"] = out["spread_pct"].clip(lower=0.0, upper=1.0)
    out["relative_value_score"] = -out["iv_zscore_within_expiration"] - out["liquidity_penalty"]
    return out


def build_scenario_grid(
    S: float,
    K: float,
    r: float,
    base_iv: float,
    days_to_expiration: int,
    option_type: str,
    current_mid: float,
    spot_shocks: list[float],
    iv_shocks: list[float],
    time_shifts: dict[str, int],
) -> pd.DataFrame:
    """Build scenario grid for theoretical price and P&L."""
    rows = []
    for label, days_elapsed in time_shifts.items():
        T = max((days_to_expiration - days_elapsed) / 365.0, 0.0)
        for spot_shock in spot_shocks:
            shocked_S = S * (1 + spot_shock)
            for iv_shock in iv_shocks:
                shocked_iv = max(base_iv + iv_shock, 1e-4)
                theo = black_scholes_price(shocked_S, K, T, r, shocked_iv, option_type)
                pnl_d = theo - current_mid
                pnl_p = pnl_d / current_mid if current_mid > 0 else np.nan
                rows.append(
                    {
                        "time_shift": label,
                        "days_elapsed": days_elapsed,
                        "spot_shock": spot_shock,
                        "iv_shock": iv_shock,
                        "shocked_underlying": shocked_S,
                        "shocked_iv": shocked_iv,
                        "shocked_T": T,
                        "theoretical_price": theo,
                        "pnl_dollars": pnl_d,
                        "pnl_percent": pnl_p,
                    }
                )
    return pd.DataFrame(rows)


def compute_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> dict[str, float]:
    """Compute standard Black-Scholes Greeks."""
    return {
        "delta": black_scholes_delta(S, K, T, r, sigma, option_type),
        "gamma": black_scholes_gamma(S, K, T, r, sigma),
        "vega": black_scholes_vega(S, K, T, r, sigma),
        "theta": black_scholes_theta(S, K, T, r, sigma, option_type),
    }
