"""
Chart operation result - Pure data structure for success/failure tracking.

Uses factory methods for type-safe construction.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class ChartResult:
    """
    Immutable result of chart creation/display operation.

    Attributes:
        success: Whether operation succeeded
        spot_price: Current spot price (None if failed)
        error_message: User-friendly error message (None if success)
        error_type: Exception type name (None if success)
    """
    success: bool
    spot_price: Optional[float] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    @classmethod
    def success_result(cls, spot_price: float) -> "ChartResult":
        """
        Create successful result.

        Args:
            spot_price: Current spot price from market data

        Returns:
            ChartResult with success=True
        """
        return cls(success=True, spot_price=spot_price)

    @classmethod
    def failure_result(cls, error: Exception, message: str) -> "ChartResult":
        """
        Create failure result.

        Args:
            error: Exception that caused failure
            message: User-friendly error description

        Returns:
            ChartResult with success=False and error details
        """
        return cls(
            success=False,
            error_message=message,
            error_type=type(error).__name__
        )
