"""Test classification system with diverse queries."""

import pytest
from derivatives_gpt_core.graph_nodes.classify_intent import classify_user_intent
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from langchain_core.messages import HumanMessage


# Test data: (query, expected_response_type, expected_product_type)
CLASSIFICATION_TEST_CASES = [
    # Priceable queries (10)
    ("Price a call on AAPL strike 150, 30 days", "can_price", "european_call"),
    ("Put option on TSLA strike 200, expiring in 60 days", "can_price", "european_put"),
    ("How much is a GOOGL call, strike $100, 2 weeks?", "can_price", "european_call"),
    ("Value of SPY put at strike 400, 90 days", "can_price", "european_put"),
    ("Price MSFT call option, strike 350, 1 month", "can_price", "european_call"),
    ("AMZN put strike 150, 45 days to expiration", "can_price", "european_put"),
    ("European call on AAPL, strike 175, 3 months", "can_price", "european_call"),
    ("Call option TSLA $300 strike 30 days", "can_price", "european_call"),
    ("Put SPY strike 420 expiring in 2 months", "can_price", "european_put"),
    ("GOOGL call $120 strike 21 days", "can_price", "european_call"),

    # Exotic options - recognize but refuse (10)
    ("Price an Asian call option on AAPL", "recognize_but_refuse", "asian_call"),
    ("Barrier option knock-out at $200", "recognize_but_refuse", "barrier_option"),
    ("Lookback put on TSLA", "recognize_but_refuse", "lookback_put"),
    ("Digital option pays $100 if AAPL > 150", "recognize_but_refuse", "digital_option"),
    ("Basket option on AAPL and GOOGL", "recognize_but_refuse", "basket_option"),
    ("American call on MSFT strike 300", "recognize_but_refuse", "american_call"),
    ("Rainbow option on 3 stocks", "recognize_but_refuse", "rainbow_option"),
    ("Quanto option on European index", "recognize_but_refuse", "quanto_option"),
    ("Variance swap on SPY", "recognize_but_refuse", "variance_swap"),
    ("Chooser option AAPL", "recognize_but_refuse", "chooser_option"),

    # Ambiguous - need clarification (5)
    ("Price an option", "clarify", "unclear"),
    ("How much for a call?", "clarify", "unclear"),
    ("Option on a stock", "clarify", "unclear"),
    ("Strike 100 30 days", "clarify", "unclear"),
    ("AAPL option", "clarify", "unclear"),

    # Off-topic (5)
    ("What's the weather today?", "off_topic", ""),
    ("Should I buy AAPL stock?", "off_topic", ""),
    ("Tell me about the S&P 500", "off_topic", ""),
    ("How do I invest in real estate?", "off_topic", ""),
    ("What's 2+2?", "off_topic", ""),
]


@pytest.mark.parametrize("query,expected_response_type,expected_product_type", CLASSIFICATION_TEST_CASES)
def test_classification(query, expected_response_type, expected_product_type):
    """Test classification for each query."""
    # Create initial state
    state = OptionPricingState(messages=[HumanMessage(content=query)])

    # Classify
    result = classify_user_intent(state)

    # Check response type
    assert result["response_type"] == expected_response_type, \
        f"Query: '{query}' - Expected {expected_response_type}, got {result['response_type']}"

    # Check product type (if expected)
    if expected_product_type:
        assert expected_product_type in result["product_type"].lower(), \
            f"Query: '{query}' - Expected product type containing '{expected_product_type}', got '{result['product_type']}'"


def test_classification_returns_required_fields():
    """Test that classification always returns required fields."""
    state = OptionPricingState(messages=[HumanMessage(content="Price a call on AAPL")])
    result = classify_user_intent(state)

    # Required fields
    assert "can_price" in result
    assert "product_type" in result
    assert "features_detected" in result
    assert "asset_class" in result
    assert "response_type" in result
    assert "reasoning" in result

    # Types
    assert isinstance(result["can_price"], bool)
    assert isinstance(result["product_type"], str)
    assert isinstance(result["features_detected"], list)
    assert isinstance(result["asset_class"], str)
    assert result["response_type"] in ["can_price", "recognize_but_refuse", "clarify", "off_topic"]
    assert isinstance(result["reasoning"], str)


def test_pydantic_validation_catches_errors():
    """Test that Pydantic catches malformed classification."""
    from derivatives_gpt_core.graph_state_schema import ClassificationResult
    import pytest

    # Missing required field
    with pytest.raises(Exception):
        ClassificationResult(
            can_price=True,
            product_type="call",
            # Missing other required fields
        )

    # Invalid response_type
    with pytest.raises(Exception):
        ClassificationResult(
            can_price=True,
            product_type="call",
            features_detected=[],
            asset_class="equity",
            response_type="invalid_type",  # Not in allowed values
            reasoning="test"
        )

    # Wrong type for can_price
    with pytest.raises(Exception):
        ClassificationResult(
            can_price="yes",  # Should be bool
            product_type="call",
            features_detected=[],
            asset_class="equity",
            response_type="can_price",
            reasoning="test"
        )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
