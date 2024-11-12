# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""Module to define the client class."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Awaitable, cast

import grpc

# pylint: disable=no-member
from frequenz.api.electricity_trading.v1 import electricity_trading_pb2
from frequenz.api.electricity_trading.v1.electricity_trading_pb2_grpc import (
    ElectricityTradingServiceStub,
)
from frequenz.channels import Receiver
from frequenz.client.base.client import BaseApiClient
from frequenz.client.base.exception import ClientNotConnected
from frequenz.client.base.streaming import GrpcStreamBroadcaster
from frequenz.client.common.pagination import Params
from google.protobuf import field_mask_pb2, struct_pb2
from typing_extensions import override

from ._types import (
    DeliveryArea,
    DeliveryPeriod,
    GridpoolOrderFilter,
    GridpoolTradeFilter,
    MarketSide,
    Order,
    OrderDetail,
    OrderExecutionOption,
    OrderState,
    OrderType,
    Power,
    Price,
    PublicTrade,
    PublicTradeFilter,
    Trade,
    TradeState,
    UpdateOrder,
)

if TYPE_CHECKING:
    from frequenz.api.electricity_trading.v1.electricity_trading_pb2_grpc import (
        ElectricityTradingServiceAsyncStub,
    )


_logger = logging.getLogger(__name__)


class _Sentinel:
    """A unique object to signify 'no value passed'."""


NO_VALUE = _Sentinel()
PRECISION_DECIMAL_PRICE = 2
PRECISION_DECIMAL_QUANTITY = 1


def validate_decimal_places(value: Decimal, decimal_places: int, name: str) -> None:
    """
    Validate that the decimal places of a given value do not exceed a specified limit.

    Args:
        value: The value to be checked.
        decimal_places: The maximum allowed decimal places.
        name: The name of the value (for error messages).

    Raises:
        ValueError: If the value has more decimal places than allowed.
                    or the value is not a valid decimal number.
    """
    if decimal_places < 0:
        raise ValueError("The decimal places must be a non-negative integer.")

    try:
        exponent = int(value.as_tuple().exponent)
        if abs(exponent) > decimal_places:
            raise ValueError(
                f"The {name} cannot have more than {decimal_places} decimal places."
            )
    except InvalidOperation as exc:
        raise ValueError(
            f"The value {value} for {name} is not a valid decimal number."
        ) from exc


class Client(BaseApiClient):
    """Electricity trading client."""

    _instances: dict[tuple[str, str | None], "Client"] = {}

    def __new__(
        cls, server_url: str, connect: bool = True, auth_key: str | None = None
    ) -> "Client":
        """
        Create a new instance of the client or return an existing one if it already exists.

        Args:
            server_url: The URL of the Electricity Trading service.
            connect: Whether to connect to the server immediately.
            auth_key: The API key for the authorization.

        Returns:
            The client instance.
        """
        key = (server_url, auth_key)

        # Check if an instance already exists for this key
        if key not in cls._instances:
            # If not, create a new instance and store it in the cache
            instance = super(Client, cls).__new__(cls)
            cls._instances[key] = instance

        return cls._instances[key]

    def __init__(
        self, server_url: str, connect: bool = True, auth_key: str | None = None
    ) -> None:
        """Initialize the client.

        Args:
            server_url: The URL of the Electricity Trading service.
            connect: Whether to connect to the server immediately.
            auth_key: The API key for the authorization.
        """
        if not hasattr(
            self, "_initialized"
        ):  # Prevent re-initialization of existing instances
            super().__init__(server_url, connect=connect)
            self._stub: ElectricityTradingServiceAsyncStub | None = None
            if connect:
                self._create_stub()
            self._initialized = True

        self._gridpool_orders_streams: dict[
            tuple[int, GridpoolOrderFilter],
            GrpcStreamBroadcaster[
                electricity_trading_pb2.ReceiveGridpoolOrdersStreamResponse, OrderDetail
            ],
        ] = {}

        self._gridpool_trades_streams: dict[
            tuple[int, GridpoolTradeFilter],
            GrpcStreamBroadcaster[
                electricity_trading_pb2.ReceiveGridpoolTradesStreamResponse, Trade
            ],
        ] = {}

        self._public_trades_streams: dict[
            PublicTradeFilter,
            GrpcStreamBroadcaster[
                electricity_trading_pb2.ReceivePublicTradesStreamResponse, PublicTrade
            ],
        ] = {}

        self._metadata = (("key", auth_key),) if auth_key else ()

    def _create_stub(self) -> None:
        """Create a new gRPC stub for the Electricity Trading service."""
        stub: Any = ElectricityTradingServiceStub(self.channel)
        self._stub = stub

    @override
    def connect(self, server_url: str | None = None) -> None:
        """Connect to the server, possibly using a new URL.

        If the client is already connected and the URL is the same as the previous URL,
        this method does nothing. If you want to force a reconnection, you can call
        [disconnect()][frequenz.client.base.client.BaseApiClient.disconnect] first.

        Args:
            server_url: The URL of the server to connect to. If not provided, the
                previously used URL is used.
        """
        super().connect(server_url)
        self._create_stub()

    @property
    def stub(self) -> ElectricityTradingServiceAsyncStub:
        """
        Get the gRPC stub for the Electricity Trading service.

        Returns:
            The gRPC stub.

        Raises:
            ClientNotConnected: If the client is not connected to the server.
        """
        if self._stub is None:
            raise ClientNotConnected(server_url=self.server_url, operation="stub")
        return self._stub

    async def stream_gridpool_orders(
        # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        gridpool_id: int,
        order_states: list[OrderState] | None = None,
        market_side: MarketSide | None = None,
        delivery_area: DeliveryArea | None = None,
        delivery_period: DeliveryPeriod | None = None,
        tag: str | None = None,
    ) -> Receiver[OrderDetail]:
        """
        Stream gridpool orders.

        Args:
            gridpool_id: ID of the gridpool to stream orders for.
            order_states: List of order states to filter for.
            market_side: Market side to filter for.
            delivery_area: Delivery area to filter for.
            delivery_period: Delivery period to filter for.
            tag: Tag to filter for.

        Returns:
            Async generator of orders.

        Raises:
            grpc.RpcError: If an error occurs while streaming the orders.
        """
        self.validate_params(delivery_period=delivery_period)

        gridpool_order_filter = GridpoolOrderFilter(
            order_states=order_states,
            side=market_side,
            delivery_area=delivery_area,
            delivery_period=delivery_period,
            tag=tag,
        )

        stream_key = (gridpool_id, gridpool_order_filter)

        if stream_key not in self._gridpool_orders_streams:
            try:
                self._gridpool_orders_streams[stream_key] = GrpcStreamBroadcaster(
                    f"electricity-trading-{stream_key}",
                    lambda: self.stub.ReceiveGridpoolOrdersStream(
                        electricity_trading_pb2.ReceiveGridpoolOrdersStreamRequest(
                            gridpool_id=gridpool_id,
                            filter=gridpool_order_filter.to_pb(),
                        ),
                        metadata=self._metadata,
                    ),
                    lambda response: OrderDetail.from_pb(response.order_detail),
                )
            except grpc.RpcError as e:
                _logger.exception(
                    "Error occurred while streaming gridpool orders: %s", e
                )
                raise
        return self._gridpool_orders_streams[stream_key].new_receiver()

    async def stream_gridpool_trades(
        # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        gridpool_id: int,
        trade_states: list[TradeState] | None = None,
        trade_ids: list[int] | None = None,
        market_side: MarketSide | None = None,
        delivery_period: DeliveryPeriod | None = None,
        delivery_area: DeliveryArea | None = None,
    ) -> Receiver[Trade]:
        """
        Stream gridpool trades.

        Args:
            gridpool_id: The ID of the gridpool to stream trades for.
            trade_states: List of trade states to filter for.
            trade_ids: List of trade IDs to filter for.
            market_side: The market side to filter for.
            delivery_period: The delivery period to filter for.
            delivery_area: The delivery area to filter for.

        Returns:
            The gridpool trades streamer.

        Raises:
            grpc.RpcError: If an error occurs while streaming gridpool trades.
        """
        self.validate_params(delivery_period=delivery_period)

        gridpool_trade_filter = GridpoolTradeFilter(
            trade_states=trade_states,
            trade_ids=trade_ids,
            side=market_side,
            delivery_period=delivery_period,
            delivery_area=delivery_area,
        )

        stream_key = (gridpool_id, gridpool_trade_filter)

        if stream_key not in self._gridpool_trades_streams:
            try:
                self._gridpool_trades_streams[stream_key] = GrpcStreamBroadcaster(
                    f"electricity-trading-{stream_key}",
                    lambda: self.stub.ReceiveGridpoolTradesStream(
                        electricity_trading_pb2.ReceiveGridpoolTradesStreamRequest(
                            gridpool_id=gridpool_id,
                            filter=gridpool_trade_filter.to_pb(),
                        ),
                        metadata=self._metadata,
                    ),
                    lambda response: Trade.from_pb(response.trade),
                )
            except grpc.RpcError as e:
                _logger.exception(
                    "Error occurred while streaming gridpool trades: %s", e
                )
                raise
        return self._gridpool_trades_streams[stream_key].new_receiver()

    async def stream_public_trades(
        self,
        states: list[TradeState] | None = None,
        delivery_period: DeliveryPeriod | None = None,
        buy_delivery_area: DeliveryArea | None = None,
        sell_delivery_area: DeliveryArea | None = None,
    ) -> Receiver[PublicTrade]:
        """
        Stream public trades.

        Args:
            states: List of order states to filter for.
            delivery_period: Delivery period to filter for.
            buy_delivery_area: Buy delivery area to filter for.
            sell_delivery_area: Sell delivery area to filter for.

        Returns:
            Async generator of orders.

        Raises:
            grpc.RpcError: If an error occurs while streaming public trades.
        """
        self.validate_params(delivery_period=delivery_period)

        public_trade_filter = PublicTradeFilter(
            states=states,
            delivery_period=delivery_period,
            buy_delivery_area=buy_delivery_area,
            sell_delivery_area=sell_delivery_area,
        )

        if public_trade_filter not in self._public_trades_streams:
            try:
                self._public_trades_streams[public_trade_filter] = (
                    GrpcStreamBroadcaster(
                        f"electricity-trading-{public_trade_filter}",
                        lambda: self.stub.ReceivePublicTradesStream(
                            electricity_trading_pb2.ReceivePublicTradesStreamRequest(
                                filter=public_trade_filter.to_pb(),
                            ),
                            metadata=self._metadata,
                        ),
                        lambda response: PublicTrade.from_pb(response.public_trade),
                    )
                )
            except grpc.RpcError as e:
                _logger.exception("Error occurred while streaming public trades: %s", e)
                raise
        return self._public_trades_streams[public_trade_filter].new_receiver()

    def validate_params(
        # pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-branches
        self,
        price: Price | None | _Sentinel = NO_VALUE,
        quantity: Power | None | _Sentinel = NO_VALUE,
        stop_price: Price | None | _Sentinel = NO_VALUE,
        peak_price_delta: Price | None | _Sentinel = NO_VALUE,
        display_quantity: Power | None | _Sentinel = NO_VALUE,
        delivery_period: DeliveryPeriod | None = None,
        valid_until: datetime | None | _Sentinel = NO_VALUE,
        execution_option: OrderExecutionOption | None | _Sentinel = NO_VALUE,
        order_type: OrderType | None = None,
    ) -> None:
        """
        Validate the parameters of an order.

        This method ensures the following:
        - Price and quantity values have the correct number of decimal places and are positive.
        - The delivery_start and valid_until values are in the future.

        Args:
            price: The price of the order.
            quantity: The quantity of the order.
            stop_price: The stop price of the order.
            peak_price_delta: The peak price delta of the order.
            display_quantity: The display quantity of the order.
            delivery_period: The delivery period of the order.
            valid_until: The valid until of the order.
            execution_option: The execution option of the order.
            order_type: The order type.

        Raises:
            ValueError: If the parameters are invalid.
            NotImplementedError: If the order type is not supported.
        """
        if not isinstance(price, _Sentinel) and price is not None:
            validate_decimal_places(price.amount, PRECISION_DECIMAL_PRICE, "price")
        if not isinstance(quantity, _Sentinel) and quantity is not None:
            validate_decimal_places(quantity.mw, PRECISION_DECIMAL_QUANTITY, "quantity")
        if not isinstance(stop_price, _Sentinel) and stop_price is not None:
            raise NotImplementedError(
                "STOP_LIMIT orders are not supported yet, so stop_price cannot be set."
            )
        if not isinstance(peak_price_delta, _Sentinel) and peak_price_delta is not None:
            raise NotImplementedError(
                "ICEBERG orders are not supported yet, so peak_price_delta cannot be set."
            )
        if not isinstance(display_quantity, _Sentinel) and display_quantity is not None:
            raise NotImplementedError(
                "ICEBERG orders are not supported yet, so display_quantity cannot be set."
            )
        if delivery_period is not None:
            if delivery_period.start < datetime.now(timezone.utc):
                raise ValueError("delivery_period must be in the future")
        if not isinstance(valid_until, _Sentinel) and valid_until is not None:
            if (
                not isinstance(execution_option, _Sentinel)
                and execution_option is not None
            ):
                if execution_option in [
                    OrderExecutionOption.AON,
                    OrderExecutionOption.FOK,
                    OrderExecutionOption.IOC,
                ]:
                    raise ValueError(
                        "valid_until must be None when execution_option is set to AON, FOK, or IOC"
                    )

            if valid_until < datetime.now(timezone.utc):
                raise ValueError("valid_until must be in the future")
        if order_type is not None:
            if order_type != OrderType.LIMIT:
                raise NotImplementedError("Currently only limit orders are supported.")

    async def create_gridpool_order(
        # pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals
        self,
        gridpool_id: int,
        delivery_area: DeliveryArea,
        delivery_period: DeliveryPeriod,
        order_type: OrderType,
        side: MarketSide,
        price: Price,
        quantity: Power,
        stop_price: Price | None = None,
        peak_price_delta: Price | None = None,
        display_quantity: Power | None = None,
        execution_option: OrderExecutionOption | None = None,
        valid_until: datetime | None = None,
        payload: dict[str, struct_pb2.Value] | None = None,
        tag: str | None = None,
    ) -> OrderDetail:
        """
        Create a gridpool order.

        Args:
            gridpool_id: ID of the gridpool to create the order for.
            delivery_area: Delivery area of the order.
            delivery_period: Delivery period of the order.
            order_type: Type of the order.
            side: Side of the order.
            price: Price of the order.
            quantity: Quantity of the order.
            stop_price: Stop price of the order.
            peak_price_delta: Peak price delta of the order.
            display_quantity: Display quantity of the order.
            execution_option: Execution option of the order.
            valid_until: Valid until of the order.
            payload: Payload of the order.
            tag: Tag of the order.

        Returns:
            The created order.

        Raises:
            grpc.RpcError: An error occurred while creating the order.
        """
        self.validate_params(
            price=price,
            quantity=quantity,
            stop_price=stop_price,
            peak_price_delta=peak_price_delta,
            display_quantity=display_quantity,
            delivery_period=delivery_period,
            valid_until=valid_until,
            execution_option=execution_option,
            order_type=order_type,
        )
        order = Order(
            delivery_area=delivery_area,
            delivery_period=delivery_period,
            type=order_type,
            side=side,
            price=price,
            quantity=quantity,
            stop_price=stop_price,
            peak_price_delta=peak_price_delta,
            display_quantity=display_quantity,
            execution_option=execution_option,
            valid_until=valid_until,
            payload=payload,
            tag=tag,
        )

        try:
            response = await cast(
                Awaitable[electricity_trading_pb2.CreateGridpoolOrderResponse],
                self.stub.CreateGridpoolOrder(
                    electricity_trading_pb2.CreateGridpoolOrderRequest(
                        gridpool_id=gridpool_id,
                        order=order.to_pb(),
                    ),
                    metadata=self._metadata,
                ),
            )
        except grpc.RpcError as e:
            _logger.exception("Error occurred while creating gridpool order: %s", e)
            raise

        return OrderDetail.from_pb(response.order_detail)

    async def update_gridpool_order(
        # pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals
        self,
        gridpool_id: int,
        order_id: int,
        price: Price | None | _Sentinel = NO_VALUE,
        quantity: Power | None | _Sentinel = NO_VALUE,
        stop_price: Price | None | _Sentinel = NO_VALUE,
        peak_price_delta: Price | None | _Sentinel = NO_VALUE,
        display_quantity: Power | None | _Sentinel = NO_VALUE,
        execution_option: OrderExecutionOption | None | _Sentinel = NO_VALUE,
        valid_until: datetime | None | _Sentinel = NO_VALUE,
        payload: dict[str, struct_pb2.Value] | None | _Sentinel = NO_VALUE,
        tag: str | None | _Sentinel = NO_VALUE,
    ) -> OrderDetail:
        """
        Update an existing order for a given Gridpool.

        Args:
            gridpool_id: ID of the Gridpool the order belongs to.
            order_id: Order ID.
            price: The updated limit price at which the contract is to be traded.
                This is the maximum price for a BUY order or the minimum price for a SELL order.
            quantity: The updated quantity of the contract being traded, specified in MW.
            stop_price: Applicable for STOP_LIMIT orders. This is the updated stop price that
                triggers the limit order.
            peak_price_delta: Applicable for ICEBERG orders. This is the updated price difference
                between the peak price and the limit price.
            display_quantity: Applicable for ICEBERG orders. This is the updated quantity of the
                order to be displayed in the order book.
            execution_option: Updated execution options such as All or None, Fill or Kill, etc.
            valid_until: This is an updated timestamp defining the time after which the order
                should be cancelled if not filled. The timestamp is in UTC.
            payload: Updated user-defined payload individual to a specific order. This can be any
                data that the user wants to associate with the order.
            tag: Updated user-defined tag to group related orders.

        Returns:
            The updated order.

        Raises:
            ValueError: If no fields to update are provided.
            grpc.RpcError: An error occurred while updating the order.
        """
        self.validate_params(
            price=price,
            quantity=quantity,
            stop_price=stop_price,
            peak_price_delta=peak_price_delta,
            display_quantity=display_quantity,
            valid_until=valid_until,
            execution_option=execution_option,
        )

        params = {
            "price": price,
            "quantity": quantity,
            "stop_price": stop_price,
            "peak_price_delta": peak_price_delta,
            "display_quantity": display_quantity,
            "execution_option": execution_option,
            "valid_until": valid_until,
            "payload": payload,
            "tag": tag,
        }

        if all(value is NO_VALUE for value in params.values()):
            raise ValueError("At least one field to update must be provided.")

        paths = [param for param, value in params.items() if value is not NO_VALUE]

        # Field mask specifying which fields should be updated
        # This is used so that we can update parameters with None values
        update_mask = field_mask_pb2.FieldMask(paths=paths)

        update_order_fields = UpdateOrder(
            price=None if price is NO_VALUE else price,  # type: ignore
            quantity=None if quantity is NO_VALUE else quantity,  # type: ignore
            stop_price=None if stop_price is NO_VALUE else stop_price,  # type: ignore
            peak_price_delta=(
                None if peak_price_delta is NO_VALUE else peak_price_delta  # type: ignore
            ),
            display_quantity=(
                None if display_quantity is NO_VALUE else display_quantity  # type: ignore
            ),
            execution_option=(
                None if execution_option is NO_VALUE else execution_option  # type: ignore
            ),
            valid_until=(
                None if valid_until is NO_VALUE else valid_until  # type: ignore
            ),
            payload=None if payload is NO_VALUE else payload,  # type: ignore
            tag=None if tag is NO_VALUE else tag,  # type: ignore
        )

        try:
            response = await cast(
                Awaitable[electricity_trading_pb2.UpdateGridpoolOrderResponse],
                self.stub.UpdateGridpoolOrder(
                    electricity_trading_pb2.UpdateGridpoolOrderRequest(
                        gridpool_id=gridpool_id,
                        order_id=order_id,
                        update_order_fields=update_order_fields.to_pb(),
                        update_mask=update_mask,
                    ),
                    metadata=self._metadata,
                ),
            )
            return OrderDetail.from_pb(response.order_detail)

        except grpc.RpcError as e:
            _logger.exception("Error occurred while updating gridpool order: %s", e)
            raise

    async def cancel_gridpool_order(
        self, gridpool_id: int, order_id: int
    ) -> OrderDetail:
        """
        Cancel a single order for a given Gridpool.

        Args:
            gridpool_id: The Gridpool to cancel the order for.
            order_id: The order to cancel.

        Returns:
            The cancelled order.

        Raises:
            grpc.RpcError: If an error occurs while cancelling the gridpool order.
        """
        try:
            response = await cast(
                Awaitable[electricity_trading_pb2.CancelGridpoolOrderResponse],
                self.stub.CancelGridpoolOrder(
                    electricity_trading_pb2.CancelGridpoolOrderRequest(
                        gridpool_id=gridpool_id, order_id=order_id
                    ),
                    metadata=self._metadata,
                ),
            )
            return OrderDetail.from_pb(response.order_detail)
        except grpc.RpcError as e:
            _logger.exception("Error occurred while cancelling gridpool order: %s", e)
            raise

    async def cancel_all_gridpool_orders(self, gridpool_id: int) -> int:
        """
        Cancel all orders for a specific Gridpool.

        Args:
            gridpool_id: The Gridpool to cancel the orders for.

        Returns:
            The ID of the Gridpool for which the orders were cancelled.

        Raises:
            grpc.RpcError: If an error occurs while cancelling all gridpool orders.
        """
        try:
            response = await cast(
                Awaitable[electricity_trading_pb2.CancelAllGridpoolOrdersResponse],
                self.stub.CancelAllGridpoolOrders(
                    electricity_trading_pb2.CancelAllGridpoolOrdersRequest(
                        gridpool_id=gridpool_id
                    ),
                    metadata=self._metadata,
                ),
            )

            return response.gridpool_id
        except grpc.RpcError as e:
            _logger.exception(
                "Error occurred while cancelling all gridpool orders: %s", e
            )
            raise

    async def get_gridpool_order(self, gridpool_id: int, order_id: int) -> OrderDetail:
        """
        Get a single order from a given gridpool.

        Args:
            gridpool_id: The Gridpool to retrieve the order for.
            order_id: The order to retrieve.

        Returns:
            The order.

        Raises:
            grpc.RpcError: If an error occurs while getting the order.
        """
        try:
            response = await cast(
                Awaitable[electricity_trading_pb2.GetGridpoolOrderResponse],
                self.stub.GetGridpoolOrder(
                    electricity_trading_pb2.GetGridpoolOrderRequest(
                        gridpool_id=gridpool_id, order_id=order_id
                    ),
                    metadata=self._metadata,
                ),
            )

            return OrderDetail.from_pb(response.order_detail)
        except grpc.RpcError as e:
            _logger.exception("Error occurred while getting gridpool order: %s", e)
            raise

    async def list_gridpool_orders(
        # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        gridpool_id: int,
        order_states: list[OrderState] | None = None,
        side: MarketSide | None = None,
        delivery_period: DeliveryPeriod | None = None,
        delivery_area: DeliveryArea | None = None,
        tag: str | None = None,
        max_nr_orders: int | None = None,
        page_token: str | None = None,
    ) -> list[OrderDetail]:
        """
        List orders for a specific Gridpool with optional filters.

        Args:
            gridpool_id: The Gridpool to retrieve the orders for.
            order_states: List of order states to filter by.
            side: The side of the market to filter by.
            delivery_period: The delivery period to filter by.
            delivery_area: The delivery area to filter by.
            tag: The tag to filter by.
            max_nr_orders: The maximum number of orders to return.
            page_token: The page token to use for pagination.

        Returns:
            The list of orders for that gridpool.

        Raises:
            grpc.RpcError: If an error occurs while listing the orders.
        """
        gridpool_order_filer = GridpoolOrderFilter(
            order_states=order_states,
            side=side,
            delivery_period=delivery_period,
            delivery_area=delivery_area,
            tag=tag,
        )

        pagination_params = Params(
            page_size=max_nr_orders,
            page_token=page_token,
        )

        try:
            response = await cast(
                Awaitable[electricity_trading_pb2.ListGridpoolOrdersResponse],
                self.stub.ListGridpoolOrders(
                    electricity_trading_pb2.ListGridpoolOrdersRequest(
                        gridpool_id=gridpool_id,
                        filter=gridpool_order_filer.to_pb(),
                        pagination_params=pagination_params.to_proto(),
                    ),
                    metadata=self._metadata,
                ),
            )

            orders: list[OrderDetail] = []
            for order_detail in response.order_details:
                try:
                    orders.append(OrderDetail.from_pb(order_detail))
                except InvalidOperation:
                    _logger.error(
                        "Failed to convert order details for order: %s",
                        str(order_detail).replace("\n", ""),
                    )

            return orders
        except grpc.RpcError as e:
            _logger.exception("Error occurred while listing gridpool orders: %s", e)
            raise

    async def list_gridpool_trades(
        # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        gridpool_id: int,
        trade_states: list[TradeState] | None = None,
        trade_ids: list[int] | None = None,
        market_side: MarketSide | None = None,
        delivery_period: DeliveryPeriod | None = None,
        delivery_area: DeliveryArea | None = None,
        max_nr_trades: int | None = None,
        page_token: str | None = None,
    ) -> list[Trade]:
        """
        List trades for a specific Gridpool with optional filters.

        Args:
            gridpool_id: The Gridpool to retrieve the trades for.
            trade_states: List of trade states to filter by.
            trade_ids: List of trade IDs to filter by.
            market_side: The side of the market to filter by.
            delivery_period: The delivery period to filter by.
            delivery_area: The delivery area to filter by.
            max_nr_trades: The maximum number of trades to return.
            page_token: The page token to use for pagination.

        Returns:
            The list of trades for the given gridpool.

        Raises:
            grpc.RpcError: If an error occurs while listing gridpool trades.
        """
        gridpool_trade_filter = GridpoolTradeFilter(
            trade_states=trade_states,
            trade_ids=trade_ids,
            side=market_side,
            delivery_period=delivery_period,
            delivery_area=delivery_area,
        )

        pagination_params = Params(
            page_size=max_nr_trades,
            page_token=page_token,
        )

        try:
            response = await cast(
                Awaitable[electricity_trading_pb2.ListGridpoolTradesResponse],
                self.stub.ListGridpoolTrades(
                    electricity_trading_pb2.ListGridpoolTradesRequest(
                        gridpool_id=gridpool_id,
                        filter=gridpool_trade_filter.to_pb(),
                        pagination_params=pagination_params.to_proto(),
                    ),
                    metadata=self._metadata,
                ),
            )

            return [Trade.from_pb(trade) for trade in response.trades]
        except grpc.RpcError as e:
            _logger.exception("Error occurred while listing gridpool trades: %s", e)
            raise

    async def list_public_trades(
        # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        states: list[TradeState] | None = None,
        delivery_period: DeliveryPeriod | None = None,
        buy_delivery_area: DeliveryArea | None = None,
        sell_delivery_area: DeliveryArea | None = None,
        max_nr_trades: int | None = None,
        page_token: str | None = None,
    ) -> list[PublicTrade]:
        """
        List all executed public orders with optional filters.

        Args:
            states: List of order states to filter by.
            delivery_period: The delivery period to filter by.
            buy_delivery_area: The buy delivery area to filter by.
            sell_delivery_area: The sell delivery area to filter by.
            max_nr_trades: The maximum number of trades to return.
            page_token: The page token to use for pagination.

        Returns:
            The list of public trades.

        Raises:
            grpc.RpcError: If an error occurs while listing public trades.
        """
        public_trade_filter = PublicTradeFilter(
            states=states,
            delivery_period=delivery_period,
            buy_delivery_area=buy_delivery_area,
            sell_delivery_area=sell_delivery_area,
        )

        pagination_params = Params(
            page_size=max_nr_trades,
            page_token=page_token,
        )

        try:
            response = await cast(
                Awaitable[electricity_trading_pb2.ListPublicTradesResponse],
                self.stub.ListPublicTrades(
                    electricity_trading_pb2.ListPublicTradesRequest(
                        filter=public_trade_filter.to_pb(),
                        pagination_params=pagination_params.to_proto(),
                    ),
                    metadata=self._metadata,
                ),
            )

            return [
                PublicTrade.from_pb(public_trade)
                for public_trade in response.public_trades
            ]
        except grpc.RpcError as e:
            _logger.exception("Error occurred while listing public trades: %s", e)
            raise
