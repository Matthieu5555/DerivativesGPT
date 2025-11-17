"""Test pricing mathematics."""

import pytest
from derivatives_gpt_core.features.vanilla.pricing import (
    calculate_black_scholes_price,
    InvalidParameterError
)


def test_black_scholes_call_atm():
    """Test at-the-money call option."""
    price = calculate_black_scholes_price(
        spot_price=100.0,
        strike_price=100.0,
        time_to_expiry_years=1.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="call"
    )

    assert price > 0
    assert price < 100  # Sanity check


def test_black_scholes_put_atm():
    """Test at-the-money put option."""
    price = calculate_black_scholes_price(
        spot_price=100.0,
        strike_price=100.0,
        time_to_expiry_years=1.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="put"
    )

    assert price > 0
    assert price < 100  # Sanity check


def test_black_scholes_call_deep_itm():
    """Test deep in-the-money call."""
    price = calculate_black_scholes_price(
        spot_price=150.0,
        strike_price=100.0,
        time_to_expiry_years=1.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="call"
    )

    assert price > 50  # Should be > intrinsic value
    assert price < 150


def test_black_scholes_put_deep_otm():
    """Test deep out-of-the-money put."""
    price = calculate_black_scholes_price(
        spot_price=150.0,
        strike_price=100.0,
        time_to_expiry_years=1.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="put"
    )

    assert price > 0
    assert price < 10  # Should be very small


def test_black_scholes_negative_spot():
    """Test error handling for negative spot price."""
    with pytest.raises(InvalidParameterError, match="Spot price must be positive"):
        calculate_black_scholes_price(
            spot_price=-100.0,
            strike_price=100.0,
            time_to_expiry_years=1.0,
            volatility=0.25,
            risk_free_rate=0.05,
            option_type="call"
        )


def test_black_scholes_zero_time():
    """Test error handling for zero time to expiry."""
    with pytest.raises(InvalidParameterError, match="Time must be positive"):
        calculate_black_scholes_price(
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry_years=0.0,
            volatility=0.25,
            risk_free_rate=0.05,
            option_type="call"
        )


def test_black_scholes_invalid_volatility():
    """Test error handling for invalid volatility."""
    with pytest.raises(InvalidParameterError, match="Volatility must be 0.01-2.0"):
        calculate_black_scholes_price(
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry_years=1.0,
            volatility=-0.25,
            risk_free_rate=0.05,
            option_type="call"
        )


def test_black_scholes_put_call_parity():
    """Test put-call parity relationship."""
    spot = 100.0
    strike = 100.0
    time = 1.0
    vol = 0.25
    rate = 0.05

    call_price = calculate_black_scholes_price(spot, strike, time, vol, rate, "call")
    put_price = calculate_black_scholes_price(spot, strike, time, vol, rate, "put")

    import math
    # C - P = S - K*e^(-rT)
    left_side = call_price - put_price
    right_side = spot - strike * math.exp(-rate * time)

    assert abs(left_side - right_side) < 0.01  # Should satisfy put-call parity
