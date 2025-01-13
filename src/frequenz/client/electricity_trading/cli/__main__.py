# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""CLI tool to interact with the trading API."""

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import click

from frequenz.client.electricity_trading.cli.day_ahead import list_day_ahead_prices
from frequenz.client.electricity_trading.cli.etrading import (
    list_orders as run_list_orders,
)
from frequenz.client.electricity_trading.cli.etrading import (
    list_trades as run_list_trades,
)

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
@click.option("--url", required=True, type=str)
@click.option("--key", required=True, type=str)
@click.option("--start", default=None, type=iso)
def list_trades(url: str, key: str, *, start: datetime) -> None:
    """List trades."""
    asyncio.run(run_list_trades(url=url, key=key, delivery_start=start))


@cli.command()
@click.option("--url", required=True, type=str)
@click.option("--key", required=True, type=str)
@click.option("--start", default=None, type=iso)
@click.option("--gid", required=True, type=int)
def list_orders(url: str, key: str, *, start: datetime, gid: int) -> None:
    """List orders."""
    asyncio.run(run_list_orders(url=url, key=key, delivery_start=start, gid=gid))


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
