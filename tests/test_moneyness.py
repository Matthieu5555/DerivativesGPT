"""Tests for moneyness calculation utilities."""

import pytest
from derivatives_gpt_core.utils.moneyness import (
    calculate_moneyness,
    get_moneyness_ratio,
    explain_moneyness
)


def test_call_otm():
    """Call with strike above spot is OTM."""
    result = calculate_moneyness(100, 110, "call")
    assert result == "out-of-the-money"


def test_call_itm():
    """Call with strike below spot is ITM."""
    result = calculate_moneyness(110, 100, "call")
    assert result == "in-the-money"


def test_call_atm():
    """Call with strike near spot is ATM."""
    result = calculate_moneyness(100, 101, "call")
    assert result == "at-the-money"


def test_put_itm():
    """Put with strike above spot is ITM."""
    result = calculate_moneyness(100, 110, "put")
    assert result == "in-the-money"


def test_put_otm():
    """Put with strike below spot is OTM."""
    result = calculate_moneyness(110, 100, "put")
    assert result == "out-of-the-money"


def test_put_atm():
    """Put with strike near spot is ATM."""
    result = calculate_moneyness(100, 101, "put")
    assert result == "at-the-money"


def test_air_liquide_case_actual_price():
    """Reproduce Air Liquide case: call with strike 10% above spot."""
    # If spot = 150, strike = 165 (10% above)
    result = calculate_moneyness(150, 165, "call")
    assert result == "out-of-the-money", "Strike 10% above spot = OTM for call"


def test_air_liquide_case_assumed_price():
    """Air Liquide case with assumed $100 spot."""
    # Even with assumed $100 spot
    result = calculate_moneyness(100, 110, "call")
    assert result == "out-of-the-money", "Strike 10% above $100 spot = OTM for call"


def test_invalid_spot_price():
    """Negative or zero spot price should raise error."""
    with pytest.raises(ValueError, match="Prices must be positive"):
        calculate_moneyness(-100, 110, "call")

    with pytest.raises(ValueError, match="Prices must be positive"):
        calculate_moneyness(0, 110, "call")


def test_invalid_strike_price():
    """Negative or zero strike price should raise error."""
    with pytest.raises(ValueError, match="Prices must be positive"):
        calculate_moneyness(100, -110, "call")

    with pytest.raises(ValueError, match="Prices must be positive"):
        calculate_moneyness(100, 0, "call")


def test_invalid_option_type():
    """Invalid option type should raise error."""
    with pytest.raises(ValueError, match="Option type must be 'call' or 'put'"):
        calculate_moneyness(100, 110, "invalid")

    with pytest.raises(ValueError, match="Option type must be 'call' or 'put'"):
        calculate_moneyness(100, 110, "Call")  # Case sensitive


def test_moneyness_ratio():
    """Test ratio calculation."""
    ratio = get_moneyness_ratio(110, 100)
    assert ratio == 1.1

    ratio = get_moneyness_ratio(100, 110)
    assert abs(ratio - 0.9090909) < 0.001


def test_moneyness_ratio_invalid_strike():
    """Zero or negative strike should raise error."""
    with pytest.raises(ValueError, match="Strike price must be positive"):
        get_moneyness_ratio(100, 0)


def test_explanation_otm():
    """Test OTM explanation generation."""
    explanation = explain_moneyness(100, 110, "call")
    assert "out-of-the-money" in explanation.lower()
    assert "$10.00" in explanation  # Distance to profitability
    assert "no intrinsic value" in explanation.lower()


def test_explanation_itm():
    """Test ITM explanation generation."""
    explanation = explain_moneyness(110, 100, "call")
    assert "in-the-money" in explanation.lower()
    assert "$10.00" in explanation  # Intrinsic value
    assert "intrinsic value" in explanation.lower()


def test_explanation_atm():
    """Test ATM explanation generation."""
    explanation = explain_moneyness(100, 101, "call")
    assert "at-the-money" in explanation.lower()
    assert "minimal intrinsic value" in explanation.lower()


def test_boundary_cases():
    """Test edge cases for ATM threshold."""
    # Exactly at strike
    assert calculate_moneyness(100, 100, "call") == "at-the-money"
    assert calculate_moneyness(100, 100, "put") == "at-the-money"

    # Just within 2% threshold (ATM)
    assert calculate_moneyness(100, 101.5, "call") == "at-the-money"
    assert calculate_moneyness(100, 98.5, "call") == "at-the-money"

    # Just outside 2% threshold
    assert calculate_moneyness(100, 103, "call") == "out-of-the-money"
    assert calculate_moneyness(100, 97, "call") == "in-the-money"


def test_deeply_otm():
    """Test deeply out-of-the-money options."""
    result = calculate_moneyness(100, 200, "call")
    assert result == "out-of-the-money"

    result = calculate_moneyness(200, 100, "put")
    assert result == "out-of-the-money"


def test_deeply_itm():
    """Test deeply in-the-money options."""
    result = calculate_moneyness(200, 100, "call")
    assert result == "in-the-money"

    result = calculate_moneyness(100, 200, "put")
    assert result == "in-the-money"


def test_real_world_prices():
    """Test with realistic stock prices."""
    # NVDA-like scenario: $450 stock, $500 call
    result = calculate_moneyness(450, 500, "call")
    assert result == "out-of-the-money"

    # AAPL-like scenario: $180 stock, $150 call
    result = calculate_moneyness(180, 150, "call")
    assert result == "in-the-money"

    # SPY-like scenario: $450 stock, $400 put
    result = calculate_moneyness(450, 400, "put")
    assert result == "out-of-the-money"
