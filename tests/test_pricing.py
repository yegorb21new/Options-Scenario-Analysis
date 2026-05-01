import math

from src.pricing import black_scholes_price


def test_call_put_prices_positive():
    c = black_scholes_price(100, 100, 0.5, 0.04, 0.2, "call")
    p = black_scholes_price(100, 100, 0.5, 0.04, 0.2, "put")
    assert c > 0
    assert p > 0


def test_put_call_parity():
    S, K, T, r, sigma = 120, 100, 0.75, 0.03, 0.25
    c = black_scholes_price(S, K, T, r, sigma, "call")
    p = black_scholes_price(S, K, T, r, sigma, "put")
    lhs = c - p
    rhs = S - K * math.exp(-r * T)
    assert abs(lhs - rhs) < 1e-6


def test_expired_intrinsic_value():
    assert black_scholes_price(110, 100, 0.0, 0.03, 0.2, "call") == 10
    assert black_scholes_price(90, 100, 0.0, 0.03, 0.2, "put") == 10
