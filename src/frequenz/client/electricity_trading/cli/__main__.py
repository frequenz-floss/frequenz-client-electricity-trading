# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""CLI tool to interact with the trading API."""

import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from frequenz.client.electricity_trading.cli.day_ahead import list_day_ahead_prices


def main() -> None:
    """Run main entry point for the CLI tool."""
    tz = ZoneInfo("Europe/Berlin")
    midnight = datetime.combine(datetime.now(tz), datetime.min.time(), tzinfo=tz)
    parser = argparse.ArgumentParser()
    parser.add_argument("--entsoe_key", type=str, required=True)
    parser.add_argument(
        "--start",
        type=datetime.fromisoformat,
        required=False,
        default=midnight,
    )
    parser.add_argument(
        "--end",
        type=datetime.fromisoformat,
        required=False,
        default=midnight + timedelta(days=2),
    )
    parser.add_argument("--country_code", type=str, required=False, default="DE_LU")
    args = parser.parse_args()

    list_day_ahead_prices(
        entsoe_key=args.entsoe_key,
        start=args.start,
        end=args.end,
        country_code=args.country_code,
    )


if __name__ == "__main__":
    main()
