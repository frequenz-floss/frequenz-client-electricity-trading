# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""CLI tool to interact with the trading API."""

from collections import deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import AsyncIterator

from frequenz.client.electricity_trading import (
    Client,
    Currency,
    DeliveryArea,
    DeliveryPeriod,
    EnergyMarketCodeType,
    MarketSide,
    OrderDetail,
    OrderType,
    Power,
    Price,
    PublicTrade,
)


def check_delivery_start(
    ts: datetime, duration: timedelta = timedelta(minutes=15)
) -> None:
    """Validate that the delivery start is a multiple of duration.

    Args:
        ts: Delivery start timestamp.
        duration: Delivery period duration.

    Raises:
        ValueError: If `ts` is not a multiple of `duration`.
    """
    if int(ts.timestamp()) % int(duration.total_seconds()) != 0:
        raise ValueError("Delivery period must be a multiple of `duration`.")


async def list_trades(url: str, key: str, *, delivery_start: datetime) -> None:
    """List trades and stream new trades.

    If delivery_start is provided, list historical trades and stream new trades
    for the 15 minute delivery period starting at delivery_start.
    If no delivery_start is provided, stream new trades for any delivery period.

    Args:
        url: URL of the trading API.
        key: API key.
        delivery_start: Start of the delivery period or None.
    """
    client = Client(server_url=url, auth_key=key)

    print_trade_header()

    delivery_period = None
    # If delivery period is selected, list historical trades also
    if delivery_start is not None:
        check_delivery_start(delivery_start)
        delivery_period = DeliveryPeriod(
            start=delivery_start,
            duration=timedelta(minutes=15),
        )
        lst = client.list_public_trades(delivery_period=delivery_period)

        async for trade in lst:
            print_trade(trade)

        if delivery_start <= datetime.now(timezone.utc):
            return

    stream = await client.stream_public_trades(delivery_period=delivery_period)
    async for trade in stream:
        print_trade(trade)


async def list_orders(
    url: str, key: str, *, delivery_start: datetime, gid: int
) -> None:
    """List orders and stream new orders.

    If delivery_start is provided, list historical orders and stream new orders
    for the 15 minute delivery period starting at delivery_start.
    If no delivery_start is provided, stream new orders for any delivery period.

    Note that retrieved sort order for listed orders (starting from the newest)
    is reversed in chunks trying to bring more recent orders to the bottom.

    Args:
        url: URL of the trading API.
        key: API key.
        delivery_start: Start of the delivery period or None.
        gid: Gridpool ID.
    """
    client = Client(server_url=url, auth_key=key)

    print_order_header()

    delivery_period = None
    # If delivery period is selected, list historical orders also
    if delivery_start is not None:
        check_delivery_start(delivery_start)
        delivery_period = DeliveryPeriod(
            start=delivery_start,
            duration=timedelta(minutes=15),
        )
    lst = client.list_gridpool_orders(gid, delivery_period=delivery_period)

    async for order in reverse_iterator(lst):
        print_order(order)

    if delivery_start and delivery_start <= datetime.now(timezone.utc):
        return

    stream = await client.stream_gridpool_orders(gid, delivery_period=delivery_period)
    async for order in stream:
        print_order(order)


# pylint: disable=too-many-arguments
async def create_order(
    url: str,
    key: str,
    *,
    gid: int,
    delivery_start: datetime,
    delivery_area: str,
    price: str,
    quantity_mw: str,
    currency: str,
    duration: timedelta,
) -> None:
    """Create a limit order for a given price and quantity (in MW).

    The market side is determined by the sign of the quantity, positive for buy orders
    and negative for sell orders. The delivery area code is expected to be in
    EUROPE_EIC format.

    Args:
        url: URL of the trading API.
        key: API key.
        gid: Gridpool ID.
        delivery_start: Start of the delivery period.
        delivery_area: Delivery area code.
        price: Price of the order.
        quantity_mw: Quantity in MW, positive for buy orders and negative for sell orders.
        currency: Currency of the price.
        duration: Duration of the delivery period.
    """
    client = Client(server_url=url, auth_key=key)

    side = MarketSide.SELL if quantity_mw[0] == "-" else MarketSide.BUY
    quantity = Power(mw=Decimal(quantity_mw.lstrip("-")))
    check_delivery_start(delivery_start)
    order = await client.create_gridpool_order(
        gridpool_id=gid,
        delivery_area=DeliveryArea(
            code=delivery_area,
            code_type=EnergyMarketCodeType.EUROPE_EIC,
        ),
        delivery_period=DeliveryPeriod(
            start=delivery_start,
            duration=duration,
        ),
        order_type=OrderType.LIMIT,
        side=side,
        price=Price(
            amount=Decimal(price),
            currency=Currency[currency],
        ),
        quantity=quantity,
    )

    print_order(order)


async def cancel_order(
    url: str, key: str, *, gridpool_id: int, order_id: int | None
) -> None:
    """Cancel an order by order ID.

    If order_id is None, cancel all orders in the gridpool.

    Args:
        url: URL of the trading API.
        key: API key.
        gridpool_id: Gridpool ID.
        order_id: Order ID to cancel or None to cancel all orders.
    """
    client = Client(server_url=url, auth_key=key)
    if order_id is None:
        await client.cancel_all_gridpool_orders(gridpool_id)
    else:
        await client.cancel_gridpool_order(gridpool_id, order_id)


def print_trade_header() -> None:
    """Print trade header in CSV format."""
    header = (
        "public_trade_id,"
        "execution_time,"
        "delivery_period_start,"
        "delivery_period_duration,"
        "buy_delivery_area_code,"
        "sell_delivery_area_code,"
        "buy_delivery_area_code_type,"
        "sell_delivery_area_code_type,"
        "quantity_mw,"
        "currency,"
        "price,"
        "state "
    )
    print(header)


def print_trade(trade: PublicTrade) -> None:
    """Print trade details to stdout in CSV format."""
    values = (
        trade.public_trade_id,
        trade.execution_time.isoformat(),
        trade.delivery_period.start.isoformat(),
        trade.delivery_period.duration,
        trade.buy_delivery_area.code,
        trade.sell_delivery_area.code,
        trade.buy_delivery_area.code_type,
        trade.sell_delivery_area.code_type,
        trade.quantity.mw,
        trade.price.currency,
        trade.price.amount,
        trade.state,
    )
    print(",".join(v.name if isinstance(v, Enum) else str(v) for v in values))


def print_order_header() -> None:
    """Print order header in CSV format."""
    header = (
        "order_id,"
        "create_time,"
        "modification_time,"
        "delivery_period_start,"
        "delivery_period_duration,"
        "delivery_area_code,"
        "delivery_area_code_type,"
        "order_type,"
        "quantity_mw,"
        "open_quantity_mw,"
        "side,"
        "currency,"
        "price,"
        "state"
    )
    print(header)


def print_order(order: OrderDetail) -> None:
    """
    Print order details to stdout in CSV format.

    All fields except the following are printed:
    - order.stop_price
    - order.peak_price_delta
    - order.display_quantity
    - order.execution_option
    - order.valid_until
    - order.payload
    - order.tag
    - state_detail.state_reason
    - state_detail.market_actor
    - filled_quantity

    Args:
        order: OrderDetail object
    """
    values = [
        order.order_id,
        order.create_time.isoformat(),
        order.modification_time.isoformat(),
        order.order.delivery_period.start.isoformat(),
        order.order.delivery_period.duration,
        order.order.delivery_area.code,
        order.order.delivery_area.code_type,
        order.order.type,
        order.order.quantity.mw,
        order.open_quantity.mw,
        order.order.side,
        order.order.price.currency,
        order.order.price.amount,
        order.state_detail.state,
    ]
    print(",".join(v.name if isinstance(v, Enum) else str(v) for v in values))


async def reverse_iterator(
    iterator: AsyncIterator[OrderDetail], chunk_size: int = 100_000
) -> AsyncIterator[OrderDetail]:
    """Reverse an async iterator in chunks to avoid loading all elements into memory.

    Args:
        iterator: Async iterator to reverse.
        chunk_size: Size of the buffer to store elements.

    Yields:
        Elements of the iterator in reverse order.
    """
    buffer: deque[OrderDetail] = deque(maxlen=chunk_size)
    async for item in iterator:
        buffer.append(item)
        if len(buffer) == chunk_size:
            for item in reversed(buffer):
                yield item
            buffer.clear()
    if buffer:
        for item in reversed(buffer):
            yield item
