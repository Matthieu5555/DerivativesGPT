"""Test multi-leg strategy pricing."""

import pytest
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from derivatives_gpt_core.graph_nodes.classify_intent import classify_user_intent
from derivatives_gpt_core.graph_nodes.aggregate_strategy_price import aggregate_strategy_price
from derivatives_gpt_core.graph_nodes.validate_inputs import validate_mathematical_consistency
from derivatives_gpt_core.agent_graph_definition import route_after_validation_new
from langchain_core.messages import HumanMessage


def test_straddle_classification():
    """Test that straddle is correctly classified as can_price with multi_leg."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price a 1-year ATM straddle on TSLA")]
    )

    result = classify_user_intent(state)

    assert result["can_price"] is True
    assert result["response_type"] == "can_price"
    assert result["strategy_type"] == "straddle"
    assert result["multi_leg"] is True
    assert result["legs"] is not None
    assert len(result["legs"]) == 2


def test_strangle_classification():
    """Test that strangle is correctly classified."""
    state = OptionPricingState(
        messages=[HumanMessage(content="AAPL strangle, 140 put 160 call, 60 days")]
    )

    result = classify_user_intent(state)

    assert result["can_price"] is True
    assert result["response_type"] == "can_price"
    assert result["strategy_type"] == "strangle"
    assert result["multi_leg"] is True


def test_straddle_aggregation():
    """Test that straddle prices are summed correctly."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price straddle")],
        strategy_type="straddle",
        execution_results={
            "price_call": {"price": 10.5, "option_type": "call", "strike": 150},
            "price_put": {"price": 8.2, "option_type": "put", "strike": 150}
        },
        legs=[
            {"type": "call", "strike": 150},
            {"type": "put", "strike": 150}
        ]
    )

    result = aggregate_strategy_price(state)

    assert result["option_price"] == pytest.approx(18.7)
    assert result["legs"][0]["price"] == 10.5
    assert result["legs"][1]["price"] == 8.2
    assert "18.70" in result["price_breakdown"]


def test_strangle_aggregation():
    """Test that strangle prices are summed correctly."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price strangle")],
        strategy_type="strangle",
        execution_results={
            "price_call": {"price": 12.0, "option_type": "call", "strike": 160},
            "price_put": {"price": 7.5, "option_type": "put", "strike": 140}
        },
        legs=[
            {"type": "call", "strike": 160},
            {"type": "put", "strike": 140}
        ]
    )

    result = aggregate_strategy_price(state)

    assert result["option_price"] == pytest.approx(19.5)


def test_straddle_validation_same_strike_passes():
    """Test that straddle with same strike passes validation."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price straddle")],
        strategy_type="straddle",
        legs=[
            {"type": "call", "strike": 150},
            {"type": "put", "strike": 150}
        ]
    )

    errors = validate_mathematical_consistency(state)

    assert len(errors) == 0


def test_straddle_validation_different_strikes_fails():
    """Test that straddle with different strikes fails validation."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price straddle")],
        strategy_type="straddle",
        legs=[
            {"type": "call", "strike": 150},
            {"type": "put", "strike": 140}
        ]
    )

    errors = validate_mathematical_consistency(state)

    assert len(errors) > 0
    assert "same strike" in errors[0].lower()


def test_strangle_validation_call_greater_than_put_passes():
    """Test that strangle with call strike > put strike passes validation."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price strangle")],
        strategy_type="strangle",
        legs=[
            {"type": "call", "strike": 160},
            {"type": "put", "strike": 140}
        ]
    )

    errors = validate_mathematical_consistency(state)

    assert len(errors) == 0


def test_strangle_validation_call_less_than_put_fails():
    """Test that strangle with call strike <= put strike fails validation."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price strangle")],
        strategy_type="strangle",
        legs=[
            {"type": "call", "strike": 140},
            {"type": "put", "strike": 160}
        ]
    )

    errors = validate_mathematical_consistency(state)

    assert len(errors) > 0
    assert "call strike must be >" in errors[0].lower()


def test_validation_loop_back_on_first_attempt():
    """Test that validation failures loop back to planner on first attempt."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price straddle")],
        validation_errors=["Strike prices inconsistent"],
        validation_attempt=0,
        max_validation_retries=2,
        plan_generated=True
    )

    route = route_after_validation_new(state)
    assert route == "loop_to_planner"


def test_validation_loop_back_on_second_attempt():
    """Test that validation failures loop back on second attempt if retries left."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price straddle")],
        validation_errors=["Strike prices inconsistent"],
        validation_attempt=1,
        max_validation_retries=2,
        plan_generated=True
    )

    route = route_after_validation_new(state)
    assert route == "loop_to_planner"


def test_validation_gives_up_after_max_retries():
    """Test that validation gives up after max retries exceeded."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price straddle")],
        validation_errors=["Strike prices inconsistent"],
        validation_attempt=2,
        max_validation_retries=2,
        plan_generated=True
    )

    route = route_after_validation_new(state)
    assert route == "validation_failed"


def test_validation_proceeds_on_warnings_only():
    """Test that validation proceeds when only warnings exist."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price straddle")],
        validation_errors=["[INFO] This is informational only"],
        validation_attempt=0,
        max_validation_retries=2,
        plan_generated=True,
        strategy_type="single"  # Single option should go to pricing_complete
    )

    route = route_after_validation_new(state)
    assert route == "pricing_complete"  # After validation, single options go to pricing_complete


def test_spread_aggregation():
    """Test that spread calculates net debit correctly."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price spread")],
        strategy_type="spread",
        execution_results={
            "buy_call": {"price": 10.0, "option_type": "call", "strike": 150},
            "sell_call": {"price": 5.0, "option_type": "call", "strike": 160}
        },
        legs=[
            {"type": "call", "strike": 150, "position": "long"},
            {"type": "call", "strike": 160, "position": "short"}
        ]
    )

    result = aggregate_strategy_price(state)

    # Spread = buy - sell = 10 - 5 = 5
    assert result["option_price"] == pytest.approx(5.0)


def test_single_option_aggregation():
    """Test that single option passes through correctly."""
    state = OptionPricingState(
        messages=[HumanMessage(content="Price call")],
        strategy_type="single",
        execution_results={
            "price_single": {"price": 10.5, "option_type": "call", "strike": 150}
        },
        legs=[{"type": "call", "strike": 150}]
    )

    result = aggregate_strategy_price(state)

    assert result["option_price"] == pytest.approx(10.5)
