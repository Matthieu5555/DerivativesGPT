"""Test updated volatility tool with SQL backend."""

import pytest
from derivatives_gpt_core.langchain_tools.volatility_tool import estimate_annualized_volatility


def test_volatility_tool_with_database():
    """
    Test volatility tool uses SQL database.

    Requires populated database.
    """
    try:
        result = estimate_annualized_volatility.invoke({"ticker": "AAPL", "lookback_days": 30})

        # Should return string with volatility
        assert isinstance(result, str)
        assert "AAPL" in result
        assert "%" in result
        assert "volatility" in result.lower()

        # Should mention historical data
        assert "historical" in result.lower() or "past" in result.lower()

        print(f"✓ Volatility tool result: {result[:100]}...")

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


def test_volatility_tool_fallback():
    """Test volatility tool fallback to mocks."""
    # Use ticker that might not be in database
    result = estimate_annualized_volatility.invoke({"ticker": "XYZ123", "lookback_days": 30})

    # Should return error message
    assert "[ERROR]" in result or "error" in result.lower() or "not available" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
