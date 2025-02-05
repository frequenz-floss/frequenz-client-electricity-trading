# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""Tests for helper utilities module."""

from decimal import Decimal

from frequenz.client.electricity_trading import quantize_quantity


def test_quantize_quantity() -> None:
    """Test the quantize_quantity function."""

    def test(inp: str, out: str) -> None:
        # check for float
        resf = quantize_quantity(float(inp))
        # ... and decimal
        resd = quantize_quantity(Decimal(inp))

        # check correct type
        assert isinstance(resf, Decimal)
        assert isinstance(resd, Decimal)

        # check correct value
        assert resf == resd == Decimal(out)

        # check negative
        resn = quantize_quantity(-float(inp))
        assert isinstance(resn, Decimal)
        assert resn == Decimal(out) * -1

    test("0.0", "0")
    test("0.01", "0")
    test("0.05", "0")  # round down in ROUND_HALF_EVEN mode
    test("0.051", "0.1")
    test("0.1", "0.1")
    test("0.15", "0.2")  # round up in ROUND_HALF_EVEN mode
    test("0.5", "0.5")
    test("1", "1")
    test("99.89", "99.9")
