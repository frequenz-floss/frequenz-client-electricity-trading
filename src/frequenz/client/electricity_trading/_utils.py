# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""Utility functions for the electricity trading API client."""

from decimal import Decimal

from ._client import PRECISION_DECIMAL_QUANTITY


def quantize_quantity(value: Decimal | float) -> Decimal:
    """Convert a decimal to a quantity with the correct precision for the API.

    Simply rounds the value to the correct precision using HALF_EVEN rounding.

    Args:
        value: The value to convert in float or Decimal.

    Returns:
        The quantity with the correct precision as a Decimal.
    """
    dec = Decimal(str(value)) if isinstance(value, float) else value
    quantity_step = Decimal(f"1e-{PRECISION_DECIMAL_QUANTITY}")
    quantized = Decimal(dec).quantize(quantity_step, rounding="ROUND_HALF_EVEN")
    return quantized
