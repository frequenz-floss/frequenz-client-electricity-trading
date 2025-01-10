# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""CLI tool to interact with the trading API."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import click

from frequenz.client.electricity_trading.cli.day_ahead import list_day_ahead_prices

TZ = ZoneInfo("Europe/Berlin")

iso = datetime.fromisoformat


def midnight(days: int = 0) -> str:
    """Return today's midnight."""
    return (
        datetime.combine(datetime.now(TZ), datetime.min.time(), tzinfo=TZ)
        + timedelta(days)
    ).isoformat()


@click.group()
def cli() -> None:
    """CLI tool to interact with the trading API."""


@cli.command()
@click.option("--entsoe-key", required=True, type=str)
@click.option("--start", default=midnight(), type=iso)
@click.option("--end", default=midnight(days=2), type=iso)
@click.option("--country-code", type=str, default="DE_LU")
def list_day_ahead(
    entsoe_key: str, *, start: datetime, end: datetime, country_code: str
) -> None:
    """List day-ahead prices."""
    list_day_ahead_prices(
        entsoe_key=entsoe_key, start=start, end=end, country_code=country_code
    )


def main() -> None:
    """Run the main Click CLI."""
    cli()


if __name__ == "__main__":
    main()
