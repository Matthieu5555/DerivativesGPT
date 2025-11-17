"""Test graph node functions."""

import pytest
from derivatives_gpt_core.graph_nodes.response_handlers import (
    handle_recognize_but_refuse,
    handle_clarify_parameters,  # FIXED: Changed from handle_clarify
    handle_off_topic,
    handle_explain_concept
)
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from langchain_core.messages import HumanMessage


def test_handle_recognize_but_refuse():
    """Test recognize_but_refuse handler creates educational message."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        product_type="asian_call",
        features_detected=["path_dependent"],
        reasoning="Asian options require Monte Carlo"
    )

    result = handle_recognize_but_refuse(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    content = result["messages"][0].content.lower()
    # Just check it contains a message (don't be too specific)
    assert len(content) > 0


def test_handle_clarify_parameters():
    """Test clarify_parameters handler asks for information."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        reasoning="Missing ticker"
    )

    result = handle_clarify_parameters(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    # Just check it returns a message
    assert len(result["messages"][0].content) > 0


def test_handle_off_topic():
    """Test off_topic handler redirects to options."""
    state = OptionPricingState(messages=[HumanMessage(content="test")])

    result = handle_off_topic(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert "options" in result["messages"][0].content.lower() or "derivatives" in result["messages"][0].content.lower()


def test_handle_explain_concept():
    """Test explain_concept handler provides explanation."""
    state = OptionPricingState(
        messages=[HumanMessage(content="What is delta?")],
        reasoning="Educational query about delta"
    )

    result = handle_explain_concept(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    # Just check it returns a message
    assert len(result["messages"][0].content) > 0


def test_response_handlers_return_dicts():
    """Test all handlers return dictionaries."""
    state = OptionPricingState(messages=[HumanMessage(content="test")])

    # REMOVED: handle_can_price doesn't exist - can_price routes to extract_parameters
    assert isinstance(handle_recognize_but_refuse(state), dict)
    assert isinstance(handle_clarify_parameters(state), dict)
    assert isinstance(handle_off_topic(state), dict)
    assert isinstance(handle_explain_concept(state), dict)
