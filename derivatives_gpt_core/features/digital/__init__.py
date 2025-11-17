"""Digital (binary) options feature."""

from derivatives_gpt_core.features.digital.pricing import (
    calculate_digital_option_price,
    convert_days_to_years,
    InvalidParameterError
)

__all__ = [
    "calculate_digital_option_price",
    "convert_days_to_years",
    "InvalidParameterError"
]
