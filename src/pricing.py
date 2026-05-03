"""Black-Scholes pricing and Greeks utilities."""

from __future__ import annotations

import math
from scipy.stats import norm


VALID_TYPES = {"call", "put"}


def _validate_option_type(option_type: str) -> str:
    ot = option_type.lower()
    if ot not in VALID_TYPES:
        raise ValueError("option_type must be 'call' or 'put'.")
    return ot


def _intrinsic_value(S: float, K: float, option_type: str) -> float:
    return max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    """Return Black-Scholes theoretical price for a European option."""
    option_type = _validate_option_type(option_type)
    if S <= 0 or K <= 0:
        raise ValueError("S and K must be positive.")
    if T <= 0:
        return _intrinsic_value(S, K, option_type)
    if sigma <= 0:
        discounted_strike = K * math.exp(-r * T)
        return max(S - discounted_strike, 0.0) if option_type == "call" else max(discounted_strike - S, 0.0)

    d1, d2 = _d1_d2(S, K, T, r, sigma)
    if option_type == "call":
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def black_scholes_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    """Return Black-Scholes delta."""
    option_type = _validate_option_type(option_type)
    if S <= 0 or K <= 0:
        raise ValueError("S and K must be positive.")
    if T <= 0:
        if option_type == "call":
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0
    if sigma <= 0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return norm.cdf(d1) if option_type == "call" else norm.cdf(d1) - 1.0


def black_scholes_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Return Black-Scholes gamma."""
    if S <= 0 or K <= 0:
        raise ValueError("S and K must be positive.")
    if T <= 0 or sigma <= 0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return norm.pdf(d1) / (S * sigma * math.sqrt(T))


def black_scholes_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Return Black-Scholes vega for 1.00 absolute vol change."""
    if S <= 0 or K <= 0:
        raise ValueError("S and K must be positive.")
    if T <= 0 or sigma <= 0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return S * norm.pdf(d1) * math.sqrt(T)


def black_scholes_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    """Return Black-Scholes theta per year."""
    option_type = _validate_option_type(option_type)
    if S <= 0 or K <= 0:
        raise ValueError("S and K must be positive.")
    if T <= 0 or sigma <= 0:
        return 0.0
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    first = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
    if option_type == "call":
        return first - r * K * math.exp(-r * T) * norm.cdf(d2)
    return first + r * K * math.exp(-r * T) * norm.cdf(-d2)
