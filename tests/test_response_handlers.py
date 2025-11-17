"""Test response handler functions."""

import pytest
from derivatives_gpt_core.graph_nodes.response_handlers import (
    handle_recognize_but_refuse,
    handle_clarify,
    handle_off_topic
)
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from langchain_core.messages import HumanMessage


def test_handle_recognize_but_refuse():
    """Test recognize_but_refuse handler generates educational response."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price an Asian option")],
        product_type="asian_call",
        features_detected=["path_dependent"],
        response_type="recognize_but_refuse",
        reasoning="Asian options require Monte Carlo simulation"
    )
    result = handle_recognize_but_refuse(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    message_content = result["messages"][0].content

    # Check for key elements
    assert "asian" in message_content.lower()
    assert "path-dependent" in message_content.lower() or "path dependent" in message_content.lower()
    assert "can't price" in message_content.lower() or "cannot price" in message_content.lower()


def test_handle_clarify():
    """Test clarify handler asks for missing information."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price an option")],
        response_type="clarify",
        reasoning="Missing ticker, strike, expiration, and option type"
    )
    result = handle_clarify(state)

    assert "messages" in result
    message_content = result["messages"][0].content

    # Check for clarification elements
    assert "ticker" in message_content.lower()
    assert "strike" in message_content.lower()
    assert "expiration" in message_content.lower() or "expiring" in message_content.lower()


def test_handle_off_topic():
    """Test off_topic handler redirects politely."""
    state = OptionPricingState(
        messages=[HumanMessage(content="What's the weather?")],
        response_type="off_topic"
    )
    result = handle_off_topic(state)

    assert "messages" in result
    message_content = result["messages"][0].content

    # Check for redirect elements
    assert "options pricing" in message_content.lower() or "option" in message_content.lower()
    assert "can help" in message_content.lower() or "would you like" in message_content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
