"""Performance metrics tracking for LangSmith observability."""

import time
from typing import Any


class MetricsTracker:
    """
    Track performance metrics for LangSmith.

    Tracks:
    - Latency: Time taken for operations (classification, pricing, etc.)
    - Counts: Number of tool calls, validation errors, etc.
    - Success: Success/failure rates for operations

    Usage:
        tracker = MetricsTracker()

        # Time an operation
        tracker.start_timer("classification")
        # ... do work ...
        latency = tracker.end_timer("classification")

        # Record counts
        tracker.record_count("tool_calls", 3)

        # Record success
        tracker.record_success("pricing", True)

        # Get all metrics
        metrics = tracker.get_metrics()
    """

    def __init__(self):
        """Initialize empty metrics."""
        self.reset()

    def reset(self) -> None:
        """Reset all metrics to initial state."""
        self._timers: dict[str, float] = {}  # Start times
        self._latencies: dict[str, float] = {}  # Completed latencies
        self._counts: dict[str, int] = {}  # Count metrics
        self._successes: dict[str, list[bool]] = {}  # Success/failure tracking

    def start_timer(self, metric_name: str) -> None:
        """
        Start timing an operation.

        Args:
            metric_name: Name of the operation (e.g., "classification", "pricing")
        """
        self._timers[metric_name] = time.time()

    def end_timer(self, metric_name: str) -> float | None:
        """
        End timing an operation and return elapsed time.

        Args:
            metric_name: Name of the operation

        Returns:
            float: Elapsed time in seconds, or None if timer wasn't started
        """
        if metric_name not in self._timers:
            return None

        start_time = self._timers.pop(metric_name)
        elapsed = time.time() - start_time
        self._latencies[metric_name] = elapsed
        return elapsed

    def record_count(self, metric_name: str, value: int) -> None:
        """
        Record a count metric.

        Args:
            metric_name: Name of the metric (e.g., "tool_calls", "validation_errors")
            value: Count value
        """
        self._counts[metric_name] = value

    def record_success(self, metric_name: str, success: bool) -> None:
        """
        Record success or failure of an operation.

        Args:
            metric_name: Name of the operation (e.g., "pricing", "validation")
            success: True if successful, False if failed
        """
        if metric_name not in self._successes:
            self._successes[metric_name] = []
        self._successes[metric_name].append(success)

    def get_metrics(self) -> dict[str, Any]:
        """
        Get all recorded metrics.

        Returns:
            dict: Dictionary containing:
                - latencies: {operation_name: time_seconds}
                - counts: {metric_name: count_value}
                - success_rates: {operation_name: success_rate}
        """
        # Calculate success rates
        success_rates = {}
        for op_name, results in self._successes.items():
            if results:
                success_rates[op_name] = sum(results) / len(results)

        return {
            "latencies": self._latencies.copy(),
            "counts": self._counts.copy(),
            "success_rates": success_rates
        }


def health_check() -> dict[str, Any]:
    """
    Perform health check of the metrics system.

    Returns:
        dict: Health check result with status and details

    Example:
        >>> health = health_check()
        >>> health["status"]
        "healthy"
    """
    try:
        # Create test tracker
        test_tracker = MetricsTracker()

        # Test timer functionality
        test_tracker.start_timer("test_operation")
        test_tracker.end_timer("test_operation")

        # Test count functionality
        test_tracker.record_count("test_count", 42)

        # Test success functionality
        test_tracker.record_success("test_success", True)

        # Verify metrics were recorded
        metrics = test_tracker.get_metrics()

        checks = {
            "timers": "test_operation" in metrics["latencies"],
            "counts": "test_count" in metrics["counts"],
            "success_rates": "test_success" in metrics["success_rates"]
        }

        all_passed = all(checks.values())

        return {
            "status": "healthy" if all_passed else "degraded",
            "timestamp": time.time(),
            "checks": checks,
            "message": "All checks passed" if all_passed else "Some checks failed"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e),
            "message": f"Health check failed: {e}"
        }


# Global metrics tracker instance
# Reset this at the start of each request in chainlit_web_app.py
metrics_tracker = MetricsTracker()
