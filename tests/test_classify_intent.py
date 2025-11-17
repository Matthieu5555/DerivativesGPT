"""Tests for classification parameter extraction."""

import pytest
from derivatives_gpt_core.graph_nodes.classify_intent import classify_user_intent
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from derivatives_gpt_core.config import get_settings
from langchain_core.messages import HumanMessage


@pytest.fixture
def settings():
    """Get settings for tests."""
    return get_settings()


def test_extract_volatility_percentage(settings):
    """Classifier should extract 'volatility 10%' as 0.10."""
    state = OptionPricingState(
        messages=[HumanMessage(
            content="Price a call on AAPL strike 150, 30 days, volatility 10%"
        )]
    )

    result = classify_user_intent(state)

    assert result.get('volatility') == 0.10, f"Expected 0.10, got {result.get('volatility')}"


def test_extract_risk_free_rate(settings):
    """Classifier should extract 'rate 3%' as 0.03."""
    state = OptionPricingState(
        messages=[HumanMessage(
            content="Price a call on AAPL strike 150, 30 days, rate 3%"
        )]
    )

    result = classify_user_intent(state)

    assert result.get('risk_free_rate') == 0.03, f"Expected 0.03, got {result.get('risk_free_rate')}"


def test_extract_both_parameters(settings):
    """Classifier should extract both vol and rate."""
    state = OptionPricingState(
        messages=[HumanMessage(
            content="Price a call on AAPL strike 150, 30 days, volatility 15%, risk-free rate 4%"
        )]
    )

    result = classify_user_intent(state)

    assert result.get('volatility') == 0.15, f"Expected 0.15, got {result.get('volatility')}"
    assert result.get('risk_free_rate') == 0.04, f"Expected 0.04, got {result.get('risk_free_rate')}"


def test_no_parameters_provided(settings):
    """Classifier should leave params as None when not provided."""
    state = OptionPricingState(
        messages=[HumanMessage(
            content="Price a call on AAPL strike 150, 30 days"
        )]
    )

    result = classify_user_intent(state)

    assert result.get('volatility') is None, "Should be None when not provided"
    assert result.get('risk_free_rate') is None, "Should be None when not provided"


def test_air_liquide_original_query(settings):
    """Reproduce Air Liquide case with all parameters."""
    state = OptionPricingState(
        messages=[HumanMessage(
            content="Price European call on Air Liquide (AI.PA), strike 10% above current, "
                    "90 days, volatility 10%, risk-free rate 3%"
        )]
    )

    result = classify_user_intent(state)

    # Note: Ticker validation might fail if not in Yahoo Finance
    # Focus on parameter extraction
    assert result.get('time_to_expiry_days') == 90, f"Expected 90 days, got {result.get('time_to_expiry_days')}"
    assert result.get('option_type') == "call", f"Expected 'call', got {result.get('option_type')}"
    assert result.get('volatility') == 0.10, f"Expected 0.10, got {result.get('volatility')}"
    assert result.get('risk_free_rate') == 0.03, f"Expected 0.03, got {result.get('risk_free_rate')}"


def test_volatility_already_decimal(settings):
    """Test extraction when volatility is already in decimal format."""
    state = OptionPricingState(
        messages=[HumanMessage(
            content="Price a call on AAPL with sigma 0.15, 30 days"
        )]
    )

    result = classify_user_intent(state)

    assert result.get('volatility') == 0.15, f"Expected 0.15, got {result.get('volatility')}"


def test_rate_already_decimal(settings):
    """Test extraction when rate is already in decimal format."""
    state = OptionPricingState(
        messages=[HumanMessage(
            content="Price a call on AAPL with r=0.04, 30 days"
        )]
    )

    result = classify_user_intent(state)

    assert result.get('risk_free_rate') == 0.04, f"Expected 0.04, got {result.get('risk_free_rate')}"


def test_volatility_variations(settings):
    """Test different ways to express volatility."""
    variations = [
        ("volatility 20%", 0.20),
        ("vol 25%", 0.25),
        ("with 30% volatility", 0.30),
        ("sigma 0.35", 0.35),
    ]

    for query, expected in variations:
        state = OptionPricingState(
            messages=[HumanMessage(
                content=f"Price a call on AAPL strike 150, 30 days, {query}"
            )]
        )

        result = classify_user_intent(state)
        assert result.get('volatility') == expected, \
            f"For '{query}': expected {expected}, got {result.get('volatility')}"


def test_rate_variations(settings):
    """Test different ways to express risk-free rate."""
    variations = [
        ("rate 3%", 0.03),
        ("risk-free rate 5%", 0.05),
        ("r=0.04", 0.04),
        ("4% rate", 0.04),
    ]

    for query, expected in variations:
        state = OptionPricingState(
            messages=[HumanMessage(
                content=f"Price a call on AAPL strike 150, 30 days, {query}"
            )]
        )

        result = classify_user_intent(state)
        assert result.get('risk_free_rate') == expected, \
            f"For '{query}': expected {expected}, got {result.get('risk_free_rate')}"


def test_classification_still_works(settings):
    """Ensure basic classification still functions with new fields."""
    state = OptionPricingState(
        messages=[HumanMessage(
            content="Price a call on AAPL strike 150, 30 days"
        )]
    )

    result = classify_user_intent(state)

    # Basic classification fields should still work
    assert result.get('can_price') is not None
    assert result.get('option_type') == "call"
    assert result.get('extracted_ticker') == "AAPL"
    assert result.get('strike_price') == 150.0
    assert result.get('time_to_expiry_days') == 30
