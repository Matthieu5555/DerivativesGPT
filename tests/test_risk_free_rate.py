"""Tests for risk-free rate estimation tool."""

import pytest
from derivatives_gpt_core.langchain_tools.risk_free_rate_tool import estimate_risk_free_rate


def test_1month_boundary():
    """Days < 30 should use 1-month T-bill."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 29})
    assert "1-month T-bill" in result


def test_3month_lower_boundary():
    """30 days should use 3-month T-bill."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 30})
    assert "3-month T-bill" in result


def test_3month_upper_boundary():
    """90 days should use 3-month T-bill (boundary fix)."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 90})
    assert "3-month T-bill" in result, f"Expected 3-month T-bill for 90 days, got: {result}"


def test_6month_lower_boundary():
    """91 days should use 6-month T-bill."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 91})
    assert "6-month T-bill" in result


def test_6month_upper_boundary():
    """180 days should use 6-month T-bill (boundary fix)."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 180})
    assert "6-month T-bill" in result


def test_1year_lower_boundary():
    """181 days should use 1-year T-bill."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 181})
    assert "1-year" in result


def test_1year_upper_boundary():
    """365 days should use 1-year T-bill (boundary fix)."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 365})
    assert "1-year" in result


def test_long_term():
    """Over 365 days should use long-term Treasury."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 366})
    assert "long-term Treasury" in result


def test_invalid_time_horizon():
    """Negative or zero days should return error."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 0})
    assert "[ERROR]" in result

    result = estimate_risk_free_rate.invoke({"time_horizon_days": -10})
    assert "[ERROR]" in result


def test_air_liquide_case():
    """Air Liquide case: 90 days should use 3-month, not 6-month."""
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 90})
    assert "3-month T-bill" in result, "90-day option should use 3-month T-bill rate"
    assert "6-month" not in result, "Should not use 6-month rate for 90 days"
