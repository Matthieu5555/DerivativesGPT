"""Test LangChain tools."""

import pytest
from derivatives_gpt_core.langchain_tools.risk_free_rate_tool import estimate_risk_free_rate
from derivatives_gpt_core.langchain_tools.black_scholes_tool import price_european_option
from derivatives_gpt_core.config import reset_settings


def test_estimate_risk_free_rate_30_days():
    """Test risk-free rate estimation for 30 days."""
    reset_settings()
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 30})
    assert isinstance(result, str), "Tool should return string"
    assert "T-bill" in result
    assert "%" in result


def test_estimate_risk_free_rate_90_days():
    """Test risk-free rate estimation for 90 days."""
    reset_settings()
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 90})
    assert isinstance(result, str), "Tool should return string"
    assert "T-bill" in result
    assert "%" in result


def test_estimate_risk_free_rate_invalid():
    """Test risk-free rate with invalid input."""
    with pytest.raises(ValueError, match="positive"):
        estimate_risk_free_rate.invoke({"time_horizon_days": -5})


def test_estimate_risk_free_rate_zero():
    """Test risk-free rate with zero input."""
    with pytest.raises(ValueError, match="positive"):
        estimate_risk_free_rate.invoke({"time_horizon_days": 0})


def test_black_scholes_tool_call():
    """Test Black-Scholes tool execution."""
    result = price_european_option.invoke({
        "spot_price": 100.0,
        "strike_price": 100.0,
        "time_to_expiry_days": 30,
        "volatility": 0.25,
        "risk_free_rate": 0.05,
        "option_type": "call"
    })

    assert isinstance(result, str)
    assert "$" in result


def test_black_scholes_tool_invalid_option_type():
    """Test Black-Scholes with invalid option type."""
    with pytest.raises(ValueError, match="call|put"):
        price_european_option.invoke({
            "spot_price": 100.0,
            "strike_price": 100.0,
            "time_to_expiry_days": 30,
            "volatility": 0.25,
            "risk_free_rate": 0.05,
            "option_type": "invalid"
        })
