# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""Examples usage of the Electricity Trading API."""

import argparse
import asyncio
import enum
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Type, TypeVar

from frequenz.client.electricity_trading import (
    Client,
    Currency,
    DeliveryArea,
    DeliveryPeriod,
    EnergyMarketCodeType,
    MarketSide,
    OrderType,
    Power,
    Price,
)

T = TypeVar("T", bound=enum.Enum)

# Default delivery duration for orders.
# This is a constant as it is the only duration currently supported by the API.
DELIVERY_DURATION = timedelta(minutes=15)

# Default energy market code type.
ENERGY_MARKET_CODE_TYPE = EnergyMarketCodeType.EUROPE_EIC

# Maximum number of public trades to receive when testing streaming.
MAX_NR_OF_PUBLIC_TRADES = 5


def main() -> None:
    """Parse arguments and run the client."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        type=str,
        help="URL of the Electricity Trading service. Default is the testing environment.",
        default="grpc://electricity-trading-testing.api.frequenz.com:443?ssl=true",
    )
    parser.add_argument(
        "--api_key",
        type=str,
        help="API key for the Electricity Trading service",
        required=True,
    )
    parser.add_argument(
        "--gridpool_id",
        type=int,
        help="Gridpool ID",
        required=True,
    )

    # Optional arguments for various request parameters
    parser.add_argument(
        "--price",
        type=Decimal,
        help="Price of the order. Default is 50.",
        required=False,
        default=Decimal("50.0"),
    )
    parser.add_argument(
        "--quantity",
        type=Decimal,
        help="Quantity of the order. Default is 0.1.",
        required=False,
        default=Decimal("0.1"),
    )
    parser.add_argument(
        "--delivery_area_code",
        type=str,
        help="Delivery area code of the order (in EIC format). Default is TenneT.",
        required=False,
        default="10YDE-EON------1",  # TenneT
    )
    parser.add_argument(
        "--currency",
        type=Currency,
        help="Currency of the order. Default is EUR.",
        required=False,
        default=Currency.EUR,
    )
    parser.add_argument(
        "--order_type",
        type=OrderType,
        help="Type of order (specifies how the order is to be executed in the market). "
        "Default is LIMIT.",
        required=False,
        default=OrderType.LIMIT,
    )
    parser.add_argument(
        "--side",
        type=str,
        help="Side of the order (BUY or SELL). Default is BUY.",
        required=False,
        default="BUY",
    )
    parser.add_argument(
        "--delivery_start",
        type=datetime.fromisoformat,
        help="Start of the delivery period in YYYY-MM-DDTHH:MM:SS format. "
        "Default is tomorrow at 12:00.",
        required=False,
        default=(datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        ),
    )

    args = parser.parse_args()

    # Run the example
    asyncio.run(run(args))


def parse_enum(enum_type: Type[T], value: str) -> T:
    """
    Parse enum types in argparse.

    Args:
        enum_type: The enum class to parse the value for.
        value: The string value to parse.

    Returns:
        The corresponding enum member.

    Raises:
        argparse.ArgumentTypeError: If the value is not a valid enum member.
    """
    if isinstance(value, enum_type):
        # If the value is already an enum member, return it.
        return value
    try:
        return enum_type[value.upper()]
    except KeyError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid value: {value}. Must be one of {', '.join(enum_type.__members__.keys())}"
        ) from exc


def convert_args_to_order_params(args: argparse.Namespace) -> dict[str, Any]:
    """Convert command line arguments to order parameters.

    Args:
        args: The command line arguments.

    Returns:
        A dictionary of order parameters.
    """
    order_params: dict[str, Any] = {}
    if args.price and args.currency:
        currency = parse_enum(Currency, args.currency)
        order_params["price"] = Price(amount=args.price, currency=currency)
    if args.quantity:
        order_params["quantity"] = Power(mw=args.quantity)
    if args.delivery_area_code:
        order_params["delivery_area"] = DeliveryArea(
            code=args.delivery_area_code, code_type=ENERGY_MARKET_CODE_TYPE
        )
    if args.delivery_start:
        order_params["delivery_period"] = DeliveryPeriod(
            start=args.delivery_start, duration=DELIVERY_DURATION
        )
    if args.order_type:
        order_params["order_type"] = parse_enum(OrderType, args.order_type)
    if args.side:
        order_params["side"] = parse_enum(MarketSide, args.side)
    return order_params


async def run(args: argparse.Namespace) -> None:
    """Run the Electricity Trading client."""
    order_params = convert_args_to_order_params(args)
    client = Client(server_url=args.url, auth_key=args.api_key)

    # Create an order
    order = await client.create_gridpool_order(
        gridpool_id=args.gridpool_id,
        delivery_area=order_params["delivery_area"],
        delivery_period=order_params["delivery_period"],
        side=order_params["side"],
        price=order_params["price"],
        quantity=order_params["quantity"],
        order_type=order_params["order_type"],
    )
    print(f"Created order: {order}\n")

    # List all orders, filtered by delivery period
    async for order in client.list_gridpool_orders(
        gridpool_id=args.gridpool_id,
        delivery_period=order_params["delivery_period"],
    ):
        print(f"Order: {order}\n")

    # Stream public trades & stop after 5 trades
    stream_public_trades = await client.stream_public_trades()
    for _ in range(MAX_NR_OF_PUBLIC_TRADES):
        public_trade = await anext(stream_public_trades)
        print(f"Received public trade: {public_trade}\n")


if __name__ == "__main__":
    main()
