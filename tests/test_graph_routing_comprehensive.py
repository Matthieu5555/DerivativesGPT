"""Comprehensive tests for graph routing logic.

Tests all routing functions and edge conditions in agent_graph_definition.py.
"""

import pytest
from derivatives_gpt_core.agent_graph_definition import (
    route_after_initial_classification,
    route_after_asset_classification,
    route_after_option_classification,
    route_after_action_determination,
    route_after_extraction,  # NEW: Parameter extraction routing
    route_after_human_approval,
    route_after_decomposition,
    route_after_planning,
    route_after_validation_new,
    route_after_execution
)
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from langchain_core.messages import HumanMessage


class TestInitialClassificationRouting:
    """Test binary classification routing (option-related vs off-topic)."""

    def test_route_option_related_to_augmentation(self):
        """Test that option-related queries route to augmentation."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Price a call on AAPL")],
            is_option_related=True
        )

        next_node = route_after_initial_classification(state)

        assert next_node == "augment_with_context"

    def test_route_off_topic_to_handler(self):
        """Test that off-topic queries route directly to off_topic handler."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Best restaurant in Paris?")],
            is_option_related=False
        )

        next_node = route_after_initial_classification(state)

        assert next_node == "off_topic"


class TestAssetClassificationRouting:
    """Test asset type classification routing."""

    def test_route_known_asset_to_option_classification(self):
        """Test that known asset types proceed to option classification."""
        for asset_type in ["equity", "fx", "commodity", "interest_rate", "credit"]:
            state = OptionPricingState(
                messages=[HumanMessage(content="Test")],
                asset_type_classified=asset_type
            )

            next_node = route_after_asset_classification(state)

            assert next_node == "classify_option_type", f"Failed for {asset_type}"

    def test_route_unknown_asset_to_clarify(self):
        """Test that unknown asset types route to clarification."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Price a derivative")],
            asset_type_classified="unknown"
        )

        next_node = route_after_asset_classification(state)

        assert next_node == "clarify_asset"


class TestOptionClassificationRouting:
    """Test option type classification routing."""

    def test_route_known_option_to_action_determination(self):
        """Test that known option types proceed to action determination."""
        for option_type in ["vanilla_call", "vanilla_put", "straddle", "asian", "barrier"]:
            state = OptionPricingState(
                messages=[HumanMessage(content="Test")],
                option_type_classified=option_type
            )

            next_node = route_after_option_classification(state)

            assert next_node == "determine_action", f"Failed for {option_type}"

    def test_route_unknown_option_to_clarify(self):
        """Test that unknown option types route to clarification."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Price an option")],
            option_type_classified="unknown"
        )

        next_node = route_after_option_classification(state)

        assert next_node == "clarify_option"


class TestActionDeterminationRouting:
    """Test action determination routing based on response_type."""

    def test_route_can_price_to_extract_parameters(self):
        """Test that priceable options route to parameter extraction first."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            response_type="can_price"
        )

        next_node = route_after_action_determination(state)

        assert next_node == "extract_parameters"  # FIXED: Changed from human_approval

    def test_route_explain_concept(self):
        """Test that concept explanation requests route correctly."""
        state = OptionPricingState(
            messages=[HumanMessage(content="What is delta?")],
            response_type="explain_concept"
        )

        next_node = route_after_action_determination(state)

        assert next_node == "explain_concept"

    def test_route_recognize_but_refuse(self):
        """Test that exotic options route to refusal handler."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Price an Asian option")],
            response_type="recognize_but_refuse"
        )

        next_node = route_after_action_determination(state)

        assert next_node == "recognize_but_refuse"

    def test_route_clarify_parameters(self):
        """Test that missing parameters route to clarification."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Price an option")],
            response_type="clarify"
        )

        next_node = route_after_action_determination(state)

        assert next_node == "clarify_parameters"


class TestParameterExtractionRouting:
    """Test parameter extraction routing (NEW in refactor)."""

    def test_route_extraction_successful_to_validate(self):
        """Test that successful extraction routes to validation."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            extraction_successful=True
        )

        next_node = route_after_extraction(state)

        assert next_node == "validate"

    def test_route_extraction_unsuccessful_to_clarify(self):
        """Test that unsuccessful extraction routes to clarification."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            extraction_successful=False
        )

        next_node = route_after_extraction(state)

        assert next_node == "clarify_parameters"


class TestHumanApprovalRouting:
    """Test human approval routing."""

    def test_route_approved_to_decompose(self):
        """Test that approved requests proceed to decomposition."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            human_approved=True
        )

        next_node = route_after_human_approval(state)

        assert next_node == "decompose"

    def test_route_rejected_to_end(self):
        """Test that rejected requests end workflow."""
        from langgraph.graph import END

        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            human_approved=False
        )

        next_node = route_after_human_approval(state)

        assert next_node == END


class TestDecompositionRouting:
    """Test decomposition routing."""

    def test_route_executable_to_plan(self):
        """Test that executable strategies proceed to planning."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            can_execute=True
        )

        next_node = route_after_decomposition(state)

        assert next_node == "create_plan"

    def test_route_non_executable_to_refuse(self):
        """Test that non-executable strategies route to refusal."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            can_execute=False
        )

        next_node = route_after_decomposition(state)

        assert next_node == "recognize_but_refuse"


class TestPlanningRouting:
    """Test planning routing."""

    def test_route_executable_plan_to_execution(self):
        """Test that executable plans proceed to execution."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            can_execute=True
        )

        next_node = route_after_planning(state)

        assert next_node == "execute"

    def test_route_non_executable_plan_to_refuse(self):
        """Test that non-executable plans route to refusal."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            can_execute=False
        )

        next_node = route_after_planning(state)

        assert next_node == "recognize_but_refuse"


class TestValidationRouting:
    """Test validation routing."""

    def test_route_validation_passed_to_human_approval(self):
        """Test that validated parameters route to human approval (BEFORE execution)."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            validation_errors=[],
            strategy_type="single"
        )

        next_node = route_after_validation_new(state)

        assert next_node == "human_approval"  # FIXED: Validation happens BEFORE human approval

    def test_route_validation_passed_multi_leg_to_human_approval(self):
        """Test that validated multi-leg strategies also route to human approval first."""
        for strategy in ["straddle", "strangle", "spread", "butterfly"]:
            state = OptionPricingState(
                messages=[HumanMessage(content="Test")],
                validation_errors=[],
                strategy_type=strategy
            )

            next_node = route_after_validation_new(state)

            assert next_node == "human_approval", f"Failed for {strategy}"  # FIXED

    def test_route_validation_failed_critical_errors(self):
        """Test that critical validation errors route to failure handler."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            validation_errors=["ERROR: Invalid strike price", "ERROR: Missing ticker"]
        )

        next_node = route_after_validation_new(state)

        assert next_node == "validation_failed"

    def test_route_validation_passed_with_warnings_only(self):
        """Test that warnings alone don't block human approval."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            validation_errors=["WARNING: High volatility", "INFO: Using default rate"],
            strategy_type="single"
        )

        next_node = route_after_validation_new(state)

        assert next_node == "human_approval"  # FIXED: Goes to human_approval, not pricing_complete


class TestExecutionRouting:
    """Test execution routing."""

    def test_route_single_option_to_pricing_complete(self):
        """Test that single option execution routes to pricing_complete."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            strategy_type="single"
        )

        next_node = route_after_execution(state)

        assert next_node == "pricing_complete"  # FIXED: Routes to pricing_complete, not END

    def test_route_multi_leg_to_aggregate(self):
        """Test that multi-leg strategies route to aggregation."""
        for strategy in ["straddle", "strangle", "spread", "butterfly"]:
            state = OptionPricingState(
                messages=[HumanMessage(content="Test")],
                strategy_type=strategy
            )

            next_node = route_after_execution(state)

            assert next_node == "aggregate", f"Failed for {strategy}"


class TestRoutingEdgeCases:
    """Test edge cases and error conditions in routing."""

    def test_routing_with_none_values(self):
        """Test routing handles None values gracefully."""
        state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            asset_type_classified=None,
            option_type_classified=None,
            response_type=None
        )

        # Should handle None gracefully (likely routing to clarification)
        # This tests defensive programming
        try:
            # These should not crash
            route_after_asset_classification(state)
            route_after_option_classification(state)
            route_after_action_determination(state)
        except AttributeError:
            pytest.fail("Routing functions should handle None values gracefully")

    def test_routing_preserves_state_immutability(self):
        """Test that routing functions don't mutate state."""
        original_state = OptionPricingState(
            messages=[HumanMessage(content="Test")],
            response_type="can_price"
        )

        # Store original values
        original_response_type = original_state.response_type

        # Route
        route_after_action_determination(original_state)

        # Verify state unchanged
        assert original_state.response_type == original_response_type
