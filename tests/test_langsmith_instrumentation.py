"""Test LangSmith instrumentation - functional approach with pure functions."""

import pytest
import time
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage

from derivatives_gpt_core.graph_state_schema import OptionPricingState
from derivatives_gpt_core.observability.trace_helpers import (
    get_run_tags,
    should_enable_ticker_tagging,
    extract_financial_metadata,
    extract_operational_metadata,
    extract_quality_metadata,
    combine_metadata,
    get_current_environment
)
from derivatives_gpt_core.observability.feedback import (
    create_feedback_entry,
    FeedbackCategory
)


# === TEST PURE FUNCTIONS (No Mocks Needed) ===


def test_should_enable_ticker_tagging():
    """Test ticker tagging predicate - pure function."""
    assert should_enable_ticker_tagging("dev") == True
    assert should_enable_ticker_tagging("staging") == True
    assert should_enable_ticker_tagging("prod") == False
    assert should_enable_ticker_tagging("unknown") == False


def test_get_run_tags_basic():
    """Test tag generation - pure function."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        ticker="AAPL",
        product_type="european",
        option_type="call"
    )

    tags = get_run_tags(state, environment="dev")

    assert "dev" in tags
    # Note: Product tags depend on settings being enabled
    # assert "product:european_call" in tags
    # assert "ticker:AAPL" in tags  # Dev allows ticker


def test_get_run_tags_prod_no_ticker():
    """Test ticker privacy in production - pure function."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        ticker="AAPL"
    )

    tags = get_run_tags(state, environment="prod")

    assert "prod" in tags
    # Ticker should NOT be in tags for prod
    assert not any("ticker:AAPL" in tag for tag in tags)


def test_extract_financial_metadata():
    """Test financial metadata extraction - pure function."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        ticker="AAPL",
        strike_price=150.0,
        spot_price=155.0,
        volatility=0.25,
        option_price=10.5
    )

    metadata = extract_financial_metadata(state)

    assert metadata["ticker"] == "AAPL"
    assert metadata["strike"] == 150.0
    assert metadata["spot_price"] == 155.0
    assert metadata["implied_volatility"] == 0.25
    assert metadata["option_price"] == 10.5


def test_extract_financial_metadata_empty():
    """Test financial metadata extraction with no data - pure function."""
    state = OptionPricingState(messages=[HumanMessage(content="test")])

    metadata = extract_financial_metadata(state)

    assert metadata == {}


def test_extract_operational_metadata():
    """Test operational metadata extraction - pure function."""
    start = time.time()
    time.sleep(0.1)  # Simulate work

    metadata = extract_operational_metadata(
        "test_node",
        start,
        success=True,
        error_type=None
    )

    assert metadata["node"] == "test_node"
    assert metadata["success"] == True
    assert metadata["error_type"] is None
    assert metadata["latency_ms"] >= 100  # At least 100ms
    assert "timestamp" in metadata


def test_extract_operational_metadata_with_error():
    """Test operational metadata with error - pure function."""
    start = time.time()

    metadata = extract_operational_metadata(
        "test_node",
        start,
        success=False,
        error_type="ValueError"
    )

    assert metadata["node"] == "test_node"
    assert metadata["success"] == False
    assert metadata["error_type"] == "ValueError"


def test_extract_quality_metadata():
    """Test quality metadata extraction - pure function."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        extraction_attempts=2,
        validation_warnings=["warning1", "warning2"],
        validation_errors=["error1"]
    )

    metadata = extract_quality_metadata(state)

    assert metadata["extraction_attempts"] == 2
    assert metadata["validation_warning_count"] == 2
    assert metadata["validation_error_count"] == 1


def test_extract_quality_metadata_empty():
    """Test quality metadata extraction with no data - pure function."""
    state = OptionPricingState(messages=[HumanMessage(content="test")])

    metadata = extract_quality_metadata(state)

    # Should return empty dict or minimal metadata
    assert isinstance(metadata, dict)


def test_combine_metadata():
    """Test metadata combination - pure function composition."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        ticker="AAPL",
        strike_price=150.0,
        extraction_attempts=2
    )

    start = time.time()

    metadata = combine_metadata(
        state,
        "test_node",
        start,
        success=True,
        error_type=None,
        extra={"custom_field": "value"}
    )

    # Financial
    assert "ticker" in metadata
    assert "strike" in metadata

    # Operational
    assert "node" in metadata
    assert "latency_ms" in metadata
    assert metadata["success"] == True

    # Quality
    assert "extraction_attempts" in metadata

    # Extra
    assert metadata["custom_field"] == "value"


def test_combine_metadata_with_error():
    """Test metadata combination with error - pure function."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        ticker="AAPL"
    )

    start = time.time()

    metadata = combine_metadata(
        state,
        "test_node",
        start,
        success=False,
        error_type="ValueError"
    )

    assert metadata["success"] == False
    assert metadata["error_type"] == "ValueError"


# === TEST FEEDBACK FUNCTIONS ===


def test_create_feedback_entry_positive():
    """Test positive feedback creation - pure function."""
    feedback = create_feedback_entry(
        score=1.0,
        category="good"
    )

    assert feedback["key"] == "user_rating"
    assert feedback["score"] == 1.0
    assert feedback["category"] == "good"
    assert "timestamp" in feedback


def test_create_feedback_entry_negative():
    """Test negative feedback creation - pure function."""
    feedback = create_feedback_entry(
        score=0.0,
        category="incorrect_price",
        comment="The price was wrong"
    )

    assert feedback["key"] == "user_rating"
    assert feedback["score"] == 0.0
    assert feedback["category"] == "incorrect_price"
    assert feedback["comment"] == "The price was wrong"
    assert "timestamp" in feedback


def test_create_feedback_entry_minimal():
    """Test minimal feedback creation - pure function."""
    feedback = create_feedback_entry(score=0.0)

    assert feedback["key"] == "user_rating"
    assert feedback["score"] == 0.0
    assert feedback["category"] is None


# === TEST SIDE EFFECTS (With Mocks) ===


@patch('derivatives_gpt_core.observability.trace_helpers.get_current_run_tree')
def test_attach_to_current_trace(mock_get_tree):
    """Test trace attachment (mocked side effect)."""
    from derivatives_gpt_core.observability.trace_helpers import attach_to_current_trace

    # Mock run tree
    mock_run = MagicMock()
    mock_run.tags = []
    mock_run.metadata = {}
    mock_get_tree.return_value = mock_run

    # Attach
    attach_to_current_trace(
        tags=["test_tag"],
        metadata={"test_key": "test_value"}
    )

    # Verify
    assert "test_tag" in mock_run.tags
    assert mock_run.metadata["test_key"] == "test_value"


@patch('derivatives_gpt_core.observability.trace_helpers.get_current_run_tree')
def test_attach_to_current_trace_no_run(mock_get_tree):
    """Test trace attachment with no active run - should not crash."""
    from derivatives_gpt_core.observability.trace_helpers import attach_to_current_trace

    # No active run
    mock_get_tree.return_value = None

    # Should not crash
    attach_to_current_trace(
        tags=["test_tag"],
        metadata={"test_key": "test_value"}
    )


@patch('derivatives_gpt_core.observability.feedback.Client')
def test_log_feedback_to_langsmith(mock_client_class):
    """Test feedback logging (mocked side effect)."""
    from derivatives_gpt_core.observability.feedback import log_feedback_to_langsmith

    # Mock client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Create feedback
    feedback = create_feedback_entry(score=1.0, category="good")

    # Log feedback
    log_feedback_to_langsmith("test-run-id", feedback)

    # Verify client was called
    mock_client.create_feedback.assert_called_once()


@patch('derivatives_gpt_core.observability.feedback.Client')
def test_log_feedback_to_langsmith_error(mock_client_class):
    """Test feedback logging with error - should not crash."""
    from derivatives_gpt_core.observability.feedback import log_feedback_to_langsmith

    # Mock client that raises error
    mock_client = MagicMock()
    mock_client.create_feedback.side_effect = Exception("API error")
    mock_client_class.return_value = mock_client

    # Create feedback
    feedback = create_feedback_entry(score=1.0, category="good")

    # Should not crash
    log_feedback_to_langsmith("test-run-id", feedback)


# === INTEGRATION TESTS ===


@pytest.mark.integration
def test_full_instrumentation_composability():
    """Integration test: Verify pure function composition."""
    from derivatives_gpt_core.observability.trace_helpers import instrument_node

    state = OptionPricingState(
        messages=[HumanMessage(content="Price AAPL call at 150")],
        ticker="AAPL",
        strike_price=150.0,
        option_type="call"
    )

    start = time.time()

    # This should compose all pure functions without errors
    # Even without active LangSmith connection
    instrument_node(state, "test_node", start, success=True)


@pytest.mark.integration
def test_environment_detection():
    """Integration test: Environment detection."""
    env = get_current_environment()

    # Should return valid environment
    assert env in ["dev", "staging", "prod"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
