# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""System tests for Electricity Trading API."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Generator

import os
import grpc
import pytest

from frequenz.client.electricity_trading import (
    Client,
    Currency,
    DeliveryArea,
    DeliveryPeriod,
    EnergyMarketCodeType,
    MarketSide,
    OrderDetail,
    OrderState,
    OrderType,
    Power,
    Price,
)

API_KEY = os.getenv("API_KEY", None)
if not API_KEY:
    raise ValueError("API Key is not set")
GRIDPOOL_ID = os.getenv("GRIDPOOL_ID", None)
if not GRIDPOOL_ID:
    raise ValueError("Gridpool ID is not set")
GRIDPOOL_ID = int(GRIDPOOL_ID)
SERVER_URL = "grpc://electricity-trading-testing.api.frequenz.com:443?ssl=true"


@pytest.fixture
async def set_up() -> dict[str, Any]:
    """Set up the test suite."""
    client = Client(
        server_url=SERVER_URL,
        auth_key=API_KEY,
    )

    delivery_area = DeliveryArea(
        code="10YDE-EON------1", code_type=EnergyMarketCodeType.EUROPE_EIC
    )
    # Setting delivery start to the next whole hour after two hours from now
    delivery_start = (datetime.now(timezone.utc) + timedelta(hours=3)).replace(
        minute=0, second=0, microsecond=0
    )
    delivery_period = DeliveryPeriod(
        start=delivery_start,
        duration=timedelta(minutes=15),
    )
    price = Price(amount=Decimal("56"), currency=Currency.EUR)
    quantity = Power(mw=Decimal("0.1"))
    order_type = OrderType.LIMIT

    return {
        "client": client,
        "delivery_area": delivery_area,
        "delivery_period": delivery_period,
        "price": price,
        "quantity": quantity,
        "order_type": order_type,
    }


async def create_test_order(
    set_up: dict[str, Any],
    side: MarketSide = MarketSide.BUY,
    price: Price | None = None,
    delivery_period: DeliveryPeriod | None = None,
) -> OrderDetail:
    """Create a test order with customizable parameters."""
    order_price = price or set_up["price"]
    order_delivery_period = delivery_period or set_up["delivery_period"]
    order = await set_up["client"].create_gridpool_order(
        gridpool_id=GRIDPOOL_ID,
        delivery_area=set_up["delivery_area"],
        delivery_period=order_delivery_period,
        order_type=set_up["order_type"],
        side=side,
        price=order_price,
        quantity=set_up["quantity"],
        tag="api-integration-test",
    )
    return order  # type: ignore


async def create_test_trade(
    set_up: dict[str, Any],
) -> tuple[OrderDetail, OrderDetail]:
    """
    Create identical orders on opposite sides to try to trigger a trade.

    Args:
        set_up: The setup dictionary.
    Returns:
        A tuple of the created buy and sell orders.
    """
    # Set a different delivery period so that it is the only trade retrieved
    # It should also be < 9 hours from now since EPEX's intraday order book opens at 15:00
    delivery_start = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(
        minute=0, second=0, microsecond=0
    )
    delivery_period = DeliveryPeriod(
        start=delivery_start,
        duration=timedelta(minutes=15),
    )
    buy_order = await create_test_order(
        set_up=set_up,
        delivery_period=delivery_period,
        side=MarketSide.BUY,
        price=Price(amount=Decimal("33"), currency=Currency.EUR),
    )

    sell_order = await create_test_order(
        set_up=set_up,
        delivery_period=delivery_period,
        side=MarketSide.SELL,
        price=Price(amount=Decimal("33"), currency=Currency.EUR),
    )

    return buy_order, sell_order


@pytest.mark.asyncio
async def test_create_and_get_order(set_up: dict[str, Any]) -> None:
    """Test creating a gridpool order and ensure it exists in the system."""
    # Create an order first
    order = await create_test_order(set_up)
    assert order is not None, "Order creation failed"

    # Fetch order to check it exists remotely
    fetched_order = await set_up["client"].get_gridpool_order(
        GRIDPOOL_ID, order.order_id
    )

    assert fetched_order.order == order.order, "Order mismatch"


@pytest.mark.asyncio
async def test_create_order_invalid_delivery_start_one_day_ago(
    set_up: dict[str, Any]
) -> None:
    """Test creating an order with a passed delivery start (one day ago)."""
    # Create an order with a delivery start in the past
    delivery_start = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
        minute=0, second=0, microsecond=0
    )
    delivery_period = DeliveryPeriod(
        start=delivery_start,
        duration=timedelta(minutes=15),
    )
    with pytest.raises(ValueError, match="delivery_period must be in the future"):
        await create_test_order(set_up, delivery_period=delivery_period)


@pytest.mark.asyncio
async def test_create_order_invalid_delivery_start_one_hour_ago(
    set_up: dict[str, Any]
) -> None:
    """Test creating an order with a passed delivery start (one hour ago)."""
    # Create an order with a delivery start in the past
    delivery_start = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(
        minute=0, second=0, microsecond=0
    )
    delivery_period = DeliveryPeriod(
        start=delivery_start,
        duration=timedelta(minutes=15),
    )
    with pytest.raises(ValueError, match="delivery_period must be in the future"):
        await create_test_order(set_up, delivery_period=delivery_period)


@pytest.mark.asyncio
async def test_create_order_invalid_delivery_start_15_minutes_ago(
    set_up: dict[str, Any]
) -> None:
    """Test creating an order with a passed delivery start (15 minutes ago)."""
    # Create an order with a delivery start in the past
    delivery_start = (datetime.now(timezone.utc) - timedelta(minutes=15)).replace(
        minute=0, second=0, microsecond=0
    )
    delivery_period = DeliveryPeriod(
        start=delivery_start,
        duration=timedelta(minutes=15),
    )
    with pytest.raises(ValueError, match="delivery_period must be in the future"):
        await create_test_order(set_up, delivery_period=delivery_period)


@pytest.mark.asyncio
async def test_list_gridpool_orders(set_up: dict[str, Any]) -> None:
    """Test listing gridpool orders and ensure they exist in the system."""
    # Create several orders
    created_orders_id = [(await create_test_order(set_up)).order_id for _ in range(10)]

    # List the orders and check they are present
    orders = await set_up["client"].list_gridpool_orders(
        gridpool_id=GRIDPOOL_ID, delivery_period=set_up["delivery_period"]
    )  # filter by delivery period to avoid fetching too many orders

    listed_orders_id = [order.order_id for order in orders]
    for order_id in created_orders_id:
        assert order_id in listed_orders_id, f"Order ID {order_id} not found"


@pytest.mark.asyncio
async def test_update_order_price(set_up: dict[str, Any]) -> None:
    """Test updating the price of an order."""
    # Create an order first
    order = await create_test_order(set_up)

    # Update the order price and check the update was successful
    new_price = Price(amount=Decimal("50"), currency=Currency.EUR)
    updated_order = await set_up["client"].update_gridpool_order(
        gridpool_id=GRIDPOOL_ID, order_id=order.order_id, price=new_price
    )

    assert updated_order.order.price.amount == new_price.amount, "Price update failed"
    fetched_order = await set_up["client"].get_gridpool_order(
        GRIDPOOL_ID, order.order_id
    )
    assert (
        fetched_order.order.price.amount == updated_order.order.price.amount
    ), "Fetched price mismatch after update"
    assert (
        order.order.price.amount != new_price.amount
    ), "Original price should not be the same as the updated price"


@pytest.mark.asyncio
async def test_update_order_quantity_failure(set_up: dict[str, Any]) -> None:
    """Test updating the quantity of an order and ensure it fails."""
    # Create an order first
    order = await create_test_order(set_up)

    quantity = Power(mw=Decimal("10"))

    # Expected failure as quantity update is not supported
    with pytest.raises(grpc.aio.AioRpcError) as excinfo:
        await set_up["client"].update_gridpool_order(
            gridpool_id=GRIDPOOL_ID, order_id=order.order_id, quantity=quantity
        )

    assert str(excinfo.value.details()) == "Updating 'quantity' is not allowed."
    assert (
        excinfo.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    ), "Expected INVALID_ARGUMENT error"


@pytest.mark.asyncio
async def test_cancel_order(set_up: dict[str, Any]) -> None:
    """Test cancelling an order."""
    # Create the order to be cancelled
    order = await create_test_order(set_up)

    # Cancel the created order and ensure it's cancelled
    cancelled_order = await set_up["client"].cancel_gridpool_order(
        GRIDPOOL_ID, order.order_id
    )
    assert cancelled_order.order_id == order.order_id, "Order cancellation failed"

    fetched_order = await set_up["client"].get_gridpool_order(
        GRIDPOOL_ID, order.order_id
    )
    assert (
        fetched_order.state_detail.state == OrderState.CANCELED
    ), "Order state should be CANCELED"


@pytest.mark.asyncio
async def test_update_cancelled_order_failure(set_up: dict[str, Any]) -> None:
    """Test updating a cancelled order and ensure it fails."""
    # Create an order first
    order = await create_test_order(set_up)

    # Cancel the created order
    await set_up["client"].cancel_gridpool_order(GRIDPOOL_ID, order.order_id)

    # Expected failure as cancelled order cannot be updated
    with pytest.raises(grpc.aio.AioRpcError) as excinfo:
        await set_up["client"].update_gridpool_order(
            gridpool_id=GRIDPOOL_ID, order_id=order.order_id, price=set_up["price"]
        )
    assert (
        excinfo.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    ), "Expected INVALID_ARGUMENT error"


@pytest.mark.asyncio
async def test_cancel_all_orders(set_up: dict[str, Any]) -> None:
    """Test cancelling all orders."""
    # Create multiple orders
    for _ in range(10):
        await create_test_order(set_up)

    # Cancel all orders and check that did indeed get cancelled
    await set_up["client"].cancel_all_gridpool_orders(GRIDPOOL_ID)

    orders = await set_up["client"].list_gridpool_orders(gridpool_id=GRIDPOOL_ID)

    for order in orders:
        assert (
            order.state_detail.state == OrderState.CANCELED
        ), f"Order {order.order_id} not canceled"


@pytest.mark.asyncio
async def test_list_gridpool_trades(set_up: dict[str, Any]) -> None:
    """Test listing gridpool trades."""
    buy_order, sell_order = await create_test_trade(set_up)
    trades = await set_up["client"].list_gridpool_trades(
        GRIDPOOL_ID,
        delivery_period=buy_order.order.delivery_period,
    )
    assert len(trades) >= 1


@pytest.mark.asyncio
async def test_list_public_trades(set_up: dict[str, Any]) -> None:
    """Test listing public trades."""
    public_trades = await set_up["client"].list_public_trades(
        delivery_period=set_up["delivery_period"],
        max_nr_trades=10,
    )
    assert len(public_trades) >= 0


@pytest.mark.asyncio
async def test_stream_gridpool_orders(set_up: dict[str, Any]) -> None:
    """Test streaming gridpool orders."""
    stream = await set_up["client"].stream_gridpool_orders(GRIDPOOL_ID)
    test_order = await create_test_order(set_up)

    try:
        # Stream trades with a 15-second timeout to avoid indefinite hanging
        streamed_order = await asyncio.wait_for(anext(stream), timeout=15)
        assert streamed_order is not None, "Failed to receive streamed order."
        assert (
            streamed_order.order == test_order.order
        ), "Streamed order does not match created order"
    except asyncio.TimeoutError:
        pytest.fail("Streaming timed out, no order received in 15 seconds")


@pytest.mark.asyncio
async def test_stream_public_trades(set_up: dict[str, Any]) -> None:
    """Test stream public trades."""
    stream = await set_up["client"].stream_public_trades()

    try:
        # Stream trades with a 15-second timeout to avoid indefinite hanging
        streamed_trade = await asyncio.wait_for(anext(stream), timeout=15)
        assert streamed_trade is not None, "Failed to receive streamed trade"
    except asyncio.TimeoutError:
        pytest.fail("Streaming timed out, no trade received in 15 seconds")


@pytest.mark.asyncio
async def test_stream_gridpool_trades(set_up: dict[str, Any]) -> None:
    """Test stream gridpool trades."""
    stream = await set_up["client"].stream_gridpool_trades(GRIDPOOL_ID)

    # Create identical orders on opposite sides to try to trigger a trade
    await create_test_trade(set_up)

    try:
        # Stream trades with a 15-second timeout to avoid indefinite hanging
        streamed_trade = await asyncio.wait_for(anext(stream), timeout=15)
        assert streamed_trade is not None, "Failed to receive streamed trade"
    except asyncio.TimeoutError:
        pytest.fail("Streaming timed out, no trade received in 15 seconds")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
