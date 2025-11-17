"""Test LangSmith observability features (metrics and tagging)."""

import pytest
from derivatives_gpt_core.observability.metrics import MetricsTracker
from derivatives_gpt_core.observability.langsmith_setup import get_run_tags
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from derivatives_gpt_core.config import get_settings
from langchain_core.messages import HumanMessage
import time


# ========================================
# METRICS TRACKER TESTS
# ========================================

def test_metrics_tracker_timer():
    """Test timer functionality."""
    tracker = MetricsTracker()

    # Start and end a timer
    tracker.start_timer("test_operation")
    time.sleep(0.01)  # Sleep for 10ms
    elapsed = tracker.end_timer("test_operation")

    assert elapsed is not None
    assert elapsed >= 0.01  # Should be at least 10ms
    assert elapsed < 1.0  # Should be less than 1 second

    # Check metrics
    metrics = tracker.get_metrics()
    assert "test_operation" in metrics["latencies"]
    assert metrics["latencies"]["test_operation"] >= 0.01


def test_metrics_tracker_counts():
    """Test count recording."""
    tracker = MetricsTracker()

    # Record some counts
    tracker.record_count("tool_calls", 3)
    tracker.record_count("validation_errors", 0)
    tracker.record_count("retries", 1)

    # Check metrics
    metrics = tracker.get_metrics()
    assert metrics["counts"]["tool_calls"] == 3
    assert metrics["counts"]["validation_errors"] == 0
    assert metrics["counts"]["retries"] == 1


def test_metrics_tracker_success():
    """Test success/failure tracking."""
    tracker = MetricsTracker()

    # Record successes and failures
    tracker.record_success("pricing", True)
    tracker.record_success("pricing", True)
    tracker.record_success("pricing", False)
    tracker.record_success("classification", True)

    # Check metrics
    metrics = tracker.get_metrics()
    assert metrics["success_rates"]["pricing"] == 2/3  # 2 successes out of 3
    assert metrics["success_rates"]["classification"] == 1.0  # 100% success


def test_metrics_tracker_reset():
    """Test reset functionality."""
    tracker = MetricsTracker()

    # Record some metrics
    tracker.start_timer("operation")
    tracker.end_timer("operation")
    tracker.record_count("items", 5)
    tracker.record_success("task", True)

    # Verify metrics exist
    metrics_before = tracker.get_metrics()
    assert len(metrics_before["latencies"]) > 0
    assert len(metrics_before["counts"]) > 0
    assert len(metrics_before["success_rates"]) > 0

    # Reset
    tracker.reset()

    # Verify metrics are empty
    metrics_after = tracker.get_metrics()
    assert len(metrics_after["latencies"]) == 0
    assert len(metrics_after["counts"]) == 0
    assert len(metrics_after["success_rates"]) == 0


def test_metrics_tracker_end_without_start():
    """Test ending a timer that was never started."""
    tracker = MetricsTracker()

    # End timer that was never started
    elapsed = tracker.end_timer("nonexistent")

    assert elapsed is None


# ========================================
# TAGGING TESTS
# ========================================

def test_get_run_tags_full():
    """Test get_run_tags with all tags enabled."""
    # Create state with full information
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        product_type="european",
        option_type="call",
        asset_class="equity",
        ticker="AAPL"
    )

    # Enable all tags (need to temporarily modify settings)
    settings = get_settings()
    original_ticker_tag = settings.langsmith_tag_ticker

    # Temporarily enable ticker tagging
    settings.langsmith_tag_ticker = True

    try:
        tags = get_run_tags(state)

        # Should have all 4 tags
        assert len(tags) >= 3  # At minimum: product, asset, method

        # Check specific tags
        assert any("product:european_call" in tag for tag in tags)
        assert any("asset:equity" in tag for tag in tags)
        assert any("method:black_scholes" in tag for tag in tags)
        assert any("ticker:AAPL" in tag for tag in tags)

    finally:
        # Restore original setting
        settings.langsmith_tag_ticker = original_ticker_tag


def test_get_run_tags_selective():
    """Test get_run_tags with selective tag configuration."""
    # Create state
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        product_type="european",
        option_type="put",
        asset_class="equity",
        ticker="TSLA"
    )

    # Get settings (ticker tagging should be disabled by default)
    settings = get_settings()

    tags = get_run_tags(state)

    # Should NOT have ticker tag (disabled by default)
    assert not any("ticker:TSLA" in tag for tag in tags)

    # Should have other tags
    assert any("product:european_put" in tag for tag in tags)
    assert any("asset:equity" in tag for tag in tags)


def test_get_run_tags_no_ticker():
    """Test that ticker tagging is disabled by default (privacy)."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        product_type="european",
        option_type="call",
        asset_class="equity",
        ticker="GOOGL"
    )

    settings = get_settings()
    assert settings.langsmith_tag_ticker is False  # Should be disabled by default

    tags = get_run_tags(state)
    assert not any("ticker:" in tag for tag in tags)


def test_get_run_tags_missing_fields():
    """Test get_run_tags handles missing state fields gracefully."""
    # State with minimal information
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        product_type=None,
        asset_class=None,
        ticker=None
    )

    # Should not crash, just return fewer tags
    tags = get_run_tags(state)

    # Might have method tag, but not product or asset
    assert not any("product:" in tag for tag in tags)
    assert not any("asset:" in tag for tag in tags)


def test_get_run_tags_product_inference():
    """Test that method tag is inferred from product type."""
    state = OptionPricingState(
        messages=[HumanMessage(content="test")],
        product_type="european",
        option_type="call",
        asset_class="equity"
    )

    tags = get_run_tags(state)

    # Should infer Black-Scholes for European options
    assert any("method:black_scholes" in tag for tag in tags)


# ========================================
# INTEGRATION TESTS (if API keys available)
# ========================================

def test_classification_metrics_integration():
    """
    Test that classify_intent actually records metrics.

    NOTE: Requires API keys. Skips if not available.
    """
    pytest.skip("Integration test requires API keys - run manually")

    # This test would:
    # 1. Create a state with a user message
    # 2. Call classify_user_intent(state)
    # 3. Check that metrics_tracker has classification latency and success


def test_pricing_metrics_integration():
    """
    Test that calculate_option_price actually records metrics.

    NOTE: Requires API keys. Skips if not available.
    """
    pytest.skip("Integration test requires API keys - run manually")

    # This test would:
    # 1. Create a state with pricing parameters
    # 2. Call calculate_option_price(state)
    # 3. Check that metrics_tracker has:
    #    - pricing latency
    #    - tool_calls count (should be 3)
    #    - pricing success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
