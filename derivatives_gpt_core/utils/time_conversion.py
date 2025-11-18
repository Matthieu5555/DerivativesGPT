"""
Time conversion utilities for options pricing.

# Called by: All pricing modules (vanilla, american, asian, digital, barrier)
# Purpose: Centralized time conversion to avoid code duplication
"""


def convert_days_to_years(days: float, days_per_year: int = 365) -> float:
    """
    # Called by: features/*/pricing.py modules for time-to-expiry conversion
    # Converts days until expiration to years (required for pricing formulas)
    # Changing days_per_year: Use 252 for trading days, 365 for calendar days (default)

    Args:
        days: Number of days until expiration
        days_per_year: Convention for days in a year (365 calendar, 252 trading)

    Returns:
        Time to expiry in years (float)
    """
    if days < 0:
        raise ValueError(f"Days cannot be negative: {days}")

    return days / days_per_year


def convert_years_to_days(years: float, days_per_year: int = 365) -> float:
    """
    # Called by: Test suites and validation utilities
    # Inverse of convert_days_to_years for round-trip conversion

    Args:
        years: Time in years
        days_per_year: Convention for days in a year

    Returns:
        Number of days (float)
    """
    if years < 0:
        raise ValueError(f"Years cannot be negative: {years}")

    return years * days_per_year
