"""Test error handling across the application."""

import pytest
from derivatives_gpt_core.graph_nodes.validate_inputs import validate_pricing_parameters
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from langchain_core.messages import HumanMessage


def test_validate_negative_spot():
    """Test validation catches negative spot price."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        spot_price=-100.0,
        strike_price=150.0,
        time_to_expiry_days=30.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="call"
    )

    result = validate_pricing_parameters(state)
    errors = result["validation_errors"]

    assert len(errors) > 0
    assert any("spot price" in e.lower() and "positive" in e.lower() for e in errors)


def test_validate_negative_strike():
    """Test validation catches negative strike price."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        spot_price=100.0,
        strike_price=-150.0,
        time_to_expiry_days=30.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="call"
    )

    result = validate_pricing_parameters(state)
    errors = result["validation_errors"]

    assert len(errors) > 0
    assert any("strike price" in e.lower() and "positive" in e.lower() for e in errors)


def test_validate_negative_time():
    """Test validation catches negative time to expiry."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        spot_price=100.0,
        strike_price=150.0,
        time_to_expiry_days=-30.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="call"
    )

    result = validate_pricing_parameters(state)
    errors = result["validation_errors"]

    assert len(errors) > 0
    assert any("time" in e.lower() and "positive" in e.lower() for e in errors)


def test_validate_unrealistic_volatility():
    """Test validation catches unrealistic volatility."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        spot_price=100.0,
        strike_price=150.0,
        time_to_expiry_days=30.0,
        volatility=5.0,  # 500%
        risk_free_rate=0.05,
        option_type="call"
    )

    result = validate_pricing_parameters(state)
    errors = result["validation_errors"]

    assert len(errors) > 0
    assert any("volatility" in e.lower() and "unrealistic" in e.lower() for e in errors)


def test_validate_missing_parameters():
    """Test validation catches missing parameters."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        spot_price=None,
        strike_price=None,
        time_to_expiry_days=None,
        volatility=None,
        risk_free_rate=None,
        option_type=None
    )

    result = validate_pricing_parameters(state)
    errors = result["validation_errors"]

    # Should have at least 6 errors (one for each missing parameter)
    assert len(errors) >= 6


def test_validate_valid_parameters():
    """Test validation passes for valid parameters."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        spot_price=100.0,
        strike_price=150.0,
        time_to_expiry_days=30.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="call"
    )

    result = validate_pricing_parameters(state)
    errors = result["validation_errors"]

    # Should only have informational messages (if any)
    critical_errors = [e for e in errors if not e.startswith(('WARNING:', '[INFO]'))]
    assert len(critical_errors) == 0


def test_tool_error_handling():
    """Test that tools return error strings instead of crashing."""
    from derivatives_gpt_core.langchain_tools.risk_free_rate_tool import estimate_risk_free_rate

    # Test with negative time
    result = estimate_risk_free_rate.invoke({"time_horizon_days": -30})
    assert "[ERROR]" in result
    assert "Invalid" in result or "positive" in result.lower()


def test_volatility_tool_error_handling():
    """Test volatility tool handles invalid ticker."""
    from derivatives_gpt_core.langchain_tools.volatility_tool import estimate_annualized_volatility

    # Test with invalid ticker
    result = estimate_annualized_volatility.invoke({"ticker": "INVALID123", "lookback_days": 30})
    assert "[ERROR]" in result or "not available" in result.lower()


def test_validate_deeply_otm_option():
    """Test validation detects deeply out-of-the-money options (informational)."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        spot_price=100.0,
        strike_price=300.0,  # Very deep OTM call
        time_to_expiry_days=30.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="call"
    )

    result = validate_pricing_parameters(state)
    errors = result["validation_errors"]

    # Should have informational message about moneyness
    assert any("[INFO]" in e for e in errors)


def test_validate_unrealistic_prices():
    """Test validation catches unrealistically high prices."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        spot_price=200000.0,  # Over $100k
        strike_price=150.0,
        time_to_expiry_days=30.0,
        volatility=0.25,
        risk_free_rate=0.05,
        option_type="call"
    )

    result = validate_pricing_parameters(state)
    errors = result["validation_errors"]

    assert len(errors) > 0
    assert any("unrealistic" in e.lower() for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
