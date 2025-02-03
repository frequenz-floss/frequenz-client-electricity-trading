# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""Module to define the types used with the client."""

# pylint: disable=too-many-lines

from __future__ import annotations  # required for constructor type hinting

import enum
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from functools import wraps
from typing import Callable, Concatenate, ParamSpec, Self, TypeVar

# pylint: disable=no-member
from frequenz.api.common.v1.grid import delivery_area_pb2, delivery_duration_pb2
from frequenz.api.common.v1.market import power_pb2, price_pb2
from frequenz.api.common.v1.types import decimal_pb2
from frequenz.api.electricity_trading.v1 import electricity_trading_pb2
from google.protobuf import json_format, struct_pb2, timestamp_pb2

_logger = logging.getLogger(__name__)


T = TypeVar("T")  # Generic type variable for class methods
P = ParamSpec("P")


def from_pb(
    func: Callable[Concatenate[type[T], P], T]
) -> Callable[Concatenate[type[T], P], T]:
    """Standardize from_pb methods like error handling with this decorator.

    Args:
        func: A class method that converts a protobuf message into an object.

    Returns:
        The wrapped function with standardized error handling.
    """

    @wraps(func)
    def wrapper(cls: type[T], /, *args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(cls, *args, **kwargs)
        except Exception as e:
            _logger.error(
                "Error converting %s from protobuf (`%s`): %s", cls.__name__, *args, e
            )
            raise

    return wrapper


# From frequanz.api.common
class Currency(enum.Enum):
    """
    List of supported currencies.

    New currencies can be added to this enum to support additional markets.
    """

    UNSPECIFIED = price_pb2.Price.Currency.CURRENCY_UNSPECIFIED
    """Currency is not specified."""

    USD = price_pb2.Price.Currency.CURRENCY_USD

    CAD = price_pb2.Price.Currency.CURRENCY_CAD

    EUR = price_pb2.Price.Currency.CURRENCY_EUR

    GBP = price_pb2.Price.Currency.CURRENCY_GBP

    CHF = price_pb2.Price.Currency.CURRENCY_CHF

    CNY = price_pb2.Price.Currency.CURRENCY_CNY

    JPY = price_pb2.Price.Currency.CURRENCY_JPY

    AUD = price_pb2.Price.Currency.CURRENCY_AUD

    NZD = price_pb2.Price.Currency.CURRENCY_NZD

    SGD = price_pb2.Price.Currency.CURRENCY_SGD

    @classmethod
    @from_pb
    def from_pb(cls, currency: price_pb2.Price.Currency.ValueType) -> "Currency":
        """Convert a protobuf Currency value to Currency enum.

        Args:
            currency: Currency to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == currency for e in cls):
            _logger.warning("Unknown currency %s. Returning UNSPECIFIED.", currency)
            return cls.UNSPECIFIED

        return cls(currency)

    def to_pb(self) -> price_pb2.Price.Currency.ValueType:
        """Convert a Currency object to protobuf Currency.

        Returns:
            Protobuf message corresponding to the Currency object.
        """
        return price_pb2.Price.Currency.ValueType(self.value)


@dataclass(frozen=True)
class Price:
    """Price of an order."""

    amount: Decimal
    """Amount of the price."""

    currency: Currency
    """Currency of the price."""

    @classmethod
    @from_pb
    def from_pb(cls, price: price_pb2.Price) -> Self:
        """Convert a protobuf Price to Price object.

        Args:
            price: Price to convert.

        Returns:
            Price object corresponding to the protobuf message.
        """
        return cls(
            amount=Decimal(price.amount.value),
            currency=Currency.from_pb(price.currency),
        )

    def to_pb(self) -> price_pb2.Price:
        """Convert a Price object to protobuf Price.

        Returns:
            Protobuf message corresponding to the Price object.
        """
        decimal_amount = decimal_pb2.Decimal()
        decimal_amount.value = str(self.amount)
        return price_pb2.Price(amount=decimal_amount, currency=self.currency.to_pb())

    def __str__(self) -> str:
        """Return string representation of the Price object.

        Returns:
            String representation of the Price object.
        """
        return f"{self.amount} {self.currency.name}"


@dataclass(frozen=True)
class Power:
    """Represents power unit in Megawatthours (MW)."""

    mw: Decimal

    @classmethod
    @from_pb
    def from_pb(cls, power: power_pb2.Power) -> Self:
        """Convert a protobuf Power to Power object.

        Args:
            power: Power to convert.

        Returns:
            Power object corresponding to the protobuf message.
        """
        return cls(mw=Decimal(power.mw.value))

    def to_pb(self) -> power_pb2.Power:
        """Convert a Power object to protobuf Power.

        Returns:
            Protobuf message corresponding to the Power object.
        """
        decimal_mw = decimal_pb2.Decimal()
        decimal_mw.value = str(self.mw)
        return power_pb2.Power(mw=decimal_mw)

    def __str__(self) -> str:
        """Return the string representation of the Power object.

        Returns:
            The string representation of the Power object.
        """
        return f"{self.mw} MW"


class EnergyMarketCodeType(enum.Enum):
    """
    Specifies the type of identification code used in the energy market.

    This is used for uniquely identifying various entities such as delivery areas, market
    participants, and grid components. This enumeration aims to offer compatibility across
    different jurisdictional standards.
    """

    UNSPECIFIED = (
        delivery_area_pb2.EnergyMarketCodeType.ENERGY_MARKET_CODE_TYPE_UNSPECIFIED
    )
    """Unspecified type. This value is a placeholder and should not be used."""

    EUROPE_EIC = (
        delivery_area_pb2.EnergyMarketCodeType.ENERGY_MARKET_CODE_TYPE_EUROPE_EIC
    )
    """European Energy Identification Code Standard."""

    US_NERC = delivery_area_pb2.EnergyMarketCodeType.ENERGY_MARKET_CODE_TYPE_US_NERC
    """North American Electric Reliability Corporation identifiers."""

    @classmethod
    @from_pb
    def from_pb(
        cls, energy_market_code_type: delivery_area_pb2.EnergyMarketCodeType.ValueType
    ) -> "EnergyMarketCodeType":
        """Convert a protobuf EnergyMarketCodeType value to EnergyMarketCodeType enum.

        Args:
            energy_market_code_type: Energy market code type to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == energy_market_code_type for e in cls):
            _logger.warning(
                "Unknown energy market code type %s. Returning UNSPECIFIED.",
                energy_market_code_type,
            )
            return cls.UNSPECIFIED

        return cls(energy_market_code_type)

    def to_pb(self) -> delivery_area_pb2.EnergyMarketCodeType.ValueType:
        """Convert a EnergyMarketCodeType object to protobuf EnergyMarketCodeType.

        Returns:
            Protobuf message corresponding to the EnergyMarketCodeType object.
        """
        return delivery_area_pb2.EnergyMarketCodeType.ValueType(self.value)


@dataclass(frozen=True)
class DeliveryArea:
    """
    Geographical or administrative region.

    These are, usually defined and maintained by a Transmission System Operator (TSO), where
    electricity deliveries for a contract occur.
    """

    code: str
    """Code representing the unique identifier for the delivery area."""

    code_type: EnergyMarketCodeType
    """Type of code used for identifying the delivery area itself."""

    @classmethod
    @from_pb
    def from_pb(cls, delivery_area: delivery_area_pb2.DeliveryArea) -> Self:
        """Convert a protobuf DeliveryArea to DeliveryArea object.

        Args:
            delivery_area: DeliveryArea to convert.

        Returns:
            DeliveryArea object corresponding to the protobuf message.
        """
        return cls(
            code=delivery_area.code,
            code_type=EnergyMarketCodeType.from_pb(delivery_area.code_type),
        )

    def to_pb(self) -> delivery_area_pb2.DeliveryArea:
        """Convert a DeliveryArea object to protobuf DeliveryArea.

        Returns:
            Protobuf message corresponding to the DeliveryArea object.
        """
        return delivery_area_pb2.DeliveryArea(
            code=self.code, code_type=self.code_type.to_pb()
        )


class DeliveryDuration(enum.Enum):
    """
    Specifies the time increment, in minutes, used for electricity deliveries and trading.

    These durations serve as the basis for defining the delivery period in contracts, and they
    dictate how energy is scheduled and delivered to meet contractual obligations.
    """

    UNSPECIFIED = delivery_duration_pb2.DeliveryDuration.DELIVERY_DURATION_UNSPECIFIED
    """Default value, indicates that the duration is unspecified."""

    MINUTES_5 = delivery_duration_pb2.DeliveryDuration.DELIVERY_DURATION_5
    """5-minute duration."""

    MINUTES_15 = delivery_duration_pb2.DeliveryDuration.DELIVERY_DURATION_15
    """15-minute contract duration."""

    MINUTES_30 = delivery_duration_pb2.DeliveryDuration.DELIVERY_DURATION_30
    """30-minute contract duration."""

    MINUTES_60 = delivery_duration_pb2.DeliveryDuration.DELIVERY_DURATION_60
    """1-hour contract duration."""

    @classmethod
    @from_pb
    def from_pb(
        cls, delivery_duration: delivery_duration_pb2.DeliveryDuration.ValueType
    ) -> "DeliveryDuration":
        """Convert a protobuf DeliveryDuration value to DeliveryDuration enum.

        Args:
            delivery_duration: Delivery duration to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == delivery_duration for e in cls):
            _logger.warning(
                "Unknown delivery duration %s. Returning UNSPECIFIED.",
                delivery_duration,
            )
            return cls.UNSPECIFIED

        return cls(delivery_duration)

    def to_pb(self) -> delivery_duration_pb2.DeliveryDuration.ValueType:
        """Convert a DeliveryDuration object to protobuf DeliveryDuration.

        Returns:
            Protobuf message corresponding to the DeliveryDuration object.
        """
        return delivery_duration_pb2.DeliveryDuration.ValueType(self.value)


class DeliveryPeriod:
    """
    Time period during which the contract is delivered.

    It is defined by a start timestamp and a duration.
    """

    start: datetime
    """Start UTC timestamp represents the beginning of the delivery period.
        This timestamp is inclusive, meaning that the delivery period starts
        from this point in time."""

    duration: DeliveryDuration
    """The length of the delivery period."""

    def __init__(
        self,
        start: datetime,
        duration: timedelta,
    ) -> None:
        """
        Initialize the DeliveryPeriod object.

        Args:
            start: Start UTC timestamp represents the beginning of the delivery period.
            duration: The length of the delivery period.

        Raises:
            ValueError: If the start timestamp does not have a timezone.
                        or if the duration is not 5, 15, 30, or 60 minutes.
        """
        if start.tzinfo is None:
            raise ValueError("Start timestamp must have a timezone.")
        if start.tzinfo != timezone.utc:
            _logger.warning(
                "Start timestamp is not in UTC timezone. Converting to UTC."
            )
            start = start.astimezone(timezone.utc)
        self.start = start

        minutes = duration.total_seconds() / 60
        match minutes:
            case 5:
                self.duration = DeliveryDuration.MINUTES_5
            case 15:
                self.duration = DeliveryDuration.MINUTES_15
            case 30:
                self.duration = DeliveryDuration.MINUTES_30
            case 60:
                self.duration = DeliveryDuration.MINUTES_60
            case _:
                raise ValueError(
                    "Invalid duration value. Duration must be 5, 15, 30, or 60 minutes."
                )

    def __hash__(self) -> int:
        """
        Create hash of the DeliveryPeriod object.

        Returns:
            Hash of the DeliveryPeriod object.
        """
        return hash((self.start, self.duration))

    def __eq__(
        self,
        other: object,
    ) -> bool:
        """Check if two DeliveryPeriod objects are equal."""
        if not isinstance(other, DeliveryPeriod):
            return NotImplemented

        return self.start == other.start and self.duration == other.duration

    def __str__(self) -> str:
        """
        Return string representation of the DeliveryPeriod object.

        Returns:
            String representation of the DeliveryPeriod object.
        """
        duration_map = {
            DeliveryDuration.MINUTES_5: "5min",
            DeliveryDuration.MINUTES_15: "15min",
            DeliveryDuration.MINUTES_30: "30min",
            DeliveryDuration.MINUTES_60: "60min",
        }
        duration_str = duration_map.get(self.duration, "Unknown duration")
        start_str = self.start.strftime("%Y-%m-%d %H:%M:%S %Z")
        return f"DeliveryPeriod(start={start_str}, duration={duration_str})"

    def __repr__(self) -> str:
        """
        Developer-friendly representation of the DeliveryPeriod object.

        Returns:
            Developer-friendly representation of the DeliveryPeriod object.
        """
        return self.__str__()

    @classmethod
    @from_pb
    def from_pb(cls, delivery_period: delivery_duration_pb2.DeliveryPeriod) -> Self:
        """Convert a protobuf DeliveryPeriod to DeliveryPeriod object.

        Args:
            delivery_period: DeliveryPeriod to convert.

        Returns:
            DeliveryPeriod object corresponding to the protobuf message.

        Raises:
            ValueError: If the duration is not 5, 15, 30, or 60 minutes.
        """
        start = delivery_period.start.ToDatetime(tzinfo=timezone.utc)
        delivery_duration_enum = DeliveryDuration.from_pb(delivery_period.duration)

        match delivery_duration_enum:
            case DeliveryDuration.MINUTES_5:
                duration = timedelta(minutes=5)
            case DeliveryDuration.MINUTES_15:
                duration = timedelta(minutes=15)
            case DeliveryDuration.MINUTES_30:
                duration = timedelta(minutes=30)
            case DeliveryDuration.MINUTES_60:
                duration = timedelta(minutes=60)
            case _:
                raise ValueError(
                    "Invalid duration value. Duration must be 5, 15, 30, or 60 minutes."
                )
        return cls(start=start, duration=duration)

    def to_pb(self) -> delivery_duration_pb2.DeliveryPeriod:
        """Convert a DeliveryPeriod object to protobuf DeliveryPeriod.

        Returns:
            Protobuf message corresponding to the DeliveryPeriod object.
        """
        start = timestamp_pb2.Timestamp()
        start.FromDatetime(self.start)
        return delivery_duration_pb2.DeliveryPeriod(
            start=start,
            duration=self.duration.to_pb(),
        )


# From electricity trading api


class OrderExecutionOption(enum.Enum):
    """
    Specific behavior for the execution of an order.

    These options provide control on how an order is handled in the market.

    If no OrderExecutionOption is set, the order remains open until it's fully
    fulfilled, cancelled by the client, `valid_until` timestamp is reached, or
    the end of the trading session.
    """

    UNSPECIFIED = (
        electricity_trading_pb2.OrderExecutionOption.ORDER_EXECUTION_OPTION_UNSPECIFIED
    )
    """The order execution option has not been set."""

    AON = electricity_trading_pb2.OrderExecutionOption.ORDER_EXECUTION_OPTION_AON
    """All or None: Order must be executed in its entirety, or not executed at all."""

    FOK = electricity_trading_pb2.OrderExecutionOption.ORDER_EXECUTION_OPTION_FOK
    """Fill or Kill: Order must be executed immediately in its entirety, or not at all."""

    IOC = electricity_trading_pb2.OrderExecutionOption.ORDER_EXECUTION_OPTION_IOC
    """Immediate or Cancel: Any portion of an order that cannot be filled \
    immediately will be cancelled."""

    @classmethod
    @from_pb
    def from_pb(
        cls,
        order_execution_option: electricity_trading_pb2.OrderExecutionOption.ValueType,
    ) -> "OrderExecutionOption":
        """Convert a protobuf OrderExecutionOption value to OrderExecutionOption enum.

        Args:
            order_execution_option: order execution option to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == order_execution_option for e in OrderExecutionOption):
            _logger.warning(
                "Unknown forecast feature %s. Returning UNSPECIFIED.",
                order_execution_option,
            )
            return cls.UNSPECIFIED

        return OrderExecutionOption(order_execution_option)

    def to_pb(self) -> electricity_trading_pb2.OrderExecutionOption.ValueType:
        """Convert a OrderExecutionOption object to protobuf OrderExecutionOption.

        Returns:
            Protobuf message corresponding to the OrderExecutionOption object.
        """
        return electricity_trading_pb2.OrderExecutionOption.ValueType(self.value)


class OrderType(enum.Enum):
    """Type of the order (specifies how the order is to be executed in the market)."""

    UNSPECIFIED = electricity_trading_pb2.OrderType.ORDER_TYPE_UNSPECIFIED
    """The order type has not been set."""

    LIMIT = electricity_trading_pb2.OrderType.ORDER_TYPE_LIMIT
    """Order to buy or sell at a specific price or better.
    It remains active until it is filled, cancelled, or expired."""

    STOP_LIMIT = electricity_trading_pb2.OrderType.ORDER_TYPE_STOP_LIMIT
    """An order that will be executed at a specified price,
    or better, after a given stop price has been reached."""

    ICEBERG = electricity_trading_pb2.OrderType.ORDER_TYPE_ICEBERG
    """A large order divided into smaller lots to hide the actual order quantity.
    Only the visible part of the order is shown in the order book."""

    BLOCK = electricity_trading_pb2.OrderType.ORDER_TYPE_BLOCK
    """User defined block order, generally a large quantity order filled all at once.
    (Not yet supported)."""

    BALANCE = electricity_trading_pb2.OrderType.ORDER_TYPE_BALANCE
    """Balance order aims to balance supply and demand, usually at
    a specific location or within a system.(Not yet supported)."""

    PREARRANGED = electricity_trading_pb2.OrderType.ORDER_TYPE_PREARRANGED
    """On exchange prearranged trade, a trade that has been privately
    negotiated and then submitted to the exchange. (Not yet supported)."""

    PRIVATE = electricity_trading_pb2.OrderType.ORDER_TYPE_PRIVATE
    """Private and confidential trade, not visible in the public
    order book and has no market impact. (Not yet supported)."""

    @classmethod
    @from_pb
    def from_pb(
        cls, order_type: electricity_trading_pb2.OrderType.ValueType
    ) -> "OrderType":
        """Convert a protobuf OrderType value to OrderType enum.

        Args:
            order_type: Order type to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == order_type for e in cls):
            _logger.warning("Unknown order type %s. Returning UNSPECIFIED.", order_type)
            return cls.UNSPECIFIED

        return cls(order_type)

    def to_pb(self) -> electricity_trading_pb2.OrderType.ValueType:
        """Convert an OrderType enum to protobuf OrderType value.

        Returns:
            Protobuf message corresponding to the OrderType enum.
        """
        return self.value


class MarketSide(enum.Enum):
    """Which side of the market the order is on, either buying or selling."""

    UNSPECIFIED = electricity_trading_pb2.MarketSide.MARKET_SIDE_UNSPECIFIED
    """The side of the market has not been set."""

    BUY = electricity_trading_pb2.MarketSide.MARKET_SIDE_BUY
    """Order to purchase electricity, referred to as a 'bid' in the order book."""

    SELL = electricity_trading_pb2.MarketSide.MARKET_SIDE_SELL
    """Order to sell electricity, referred to as an 'ask' or 'offer' in the order book."""

    @classmethod
    @from_pb
    def from_pb(
        cls, market_side: electricity_trading_pb2.MarketSide.ValueType
    ) -> "MarketSide":
        """Convert a protobuf MarketSide value to MarketSide enum.

        Args:
            market_side: Market side to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == market_side for e in cls):
            _logger.warning(
                "Unknown market side %s. Returning UNSPECIFIED.", market_side
            )
            return cls.UNSPECIFIED

        return cls(market_side)

    def to_pb(self) -> electricity_trading_pb2.MarketSide.ValueType:
        """Convert a MarketSide enum to protobuf MarketSide value.

        Returns:
            Protobuf message corresponding to the MarketSide enum.
        """
        return self.value


class OrderState(enum.Enum):
    """State of an order."""

    UNSPECIFIED = electricity_trading_pb2.OrderState.ORDER_STATE_UNSPECIFIED
    """The order state is not known. Usually the default state of a newly created order object
    before any operations have been applied."""

    PENDING = electricity_trading_pb2.OrderState.ORDER_STATE_PENDING
    """The order has been sent to the marketplace but has not yet been confirmed. This can be due
    to awaiting validation or system processing."""

    ACTIVE = electricity_trading_pb2.OrderState.ORDER_STATE_ACTIVE
    """The order has been confirmed and is open in the market. It may be unfilled or partially
    filled."""

    FILLED = electricity_trading_pb2.OrderState.ORDER_STATE_FILLED
    """The order has been completely filled and there are no remaining quantities on the order."""

    CANCELED = electricity_trading_pb2.OrderState.ORDER_STATE_CANCELED
    """The order has been canceled. This can occur due to a cancellation request by the market
    participant, system, or market operator."""

    EXPIRED = electricity_trading_pb2.OrderState.ORDER_STATE_EXPIRED
    """The order has not been filled within the defined duration and has expired."""

    FAILED = electricity_trading_pb2.OrderState.ORDER_STATE_FAILED
    """The order submission failed and was unable to be placed on the order book, usually due to a
    validation error or system issue."""

    HIBERNATE = electricity_trading_pb2.OrderState.ORDER_STATE_HIBERNATE
    """The order has been entered into the system but is not currently exposed to the market. This
    could be due to certain conditions not yet being met."""

    @classmethod
    @from_pb
    def from_pb(
        cls, order_state: electricity_trading_pb2.OrderState.ValueType
    ) -> "OrderState":
        """Convert a protobuf OrderState value to OrderState enum.

        Args:
            order_state: Order state to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == order_state for e in cls):
            _logger.warning(
                "Unknown order state %s. Returning UNSPECIFIED.", order_state
            )
            return cls.UNSPECIFIED

        return cls(order_state)

    def to_pb(self) -> electricity_trading_pb2.OrderState.ValueType:
        """Convert an OrderState enum to protobuf OrderState value.

        Returns:
            Protobuf message corresponding to the OrderState enum.
        """
        return self.value


class TradeState(enum.Enum):
    """State of a trade."""

    UNSPECIFIED = electricity_trading_pb2.TradeState.TRADE_STATE_UNSPECIFIED
    """The state is not known."""

    ACTIVE = electricity_trading_pb2.TradeState.TRADE_STATE_ACTIVE
    """The trade has been executed in the market."""

    CANCEL_REQUESTED = electricity_trading_pb2.TradeState.TRADE_STATE_CANCEL_REQUESTED
    """A cancellation request for the trade has been submitted."""

    CANCEL_REJECTED = electricity_trading_pb2.TradeState.TRADE_STATE_CANCEL_REJECTED
    """The trade cancellation request was rejected."""

    CANCELED = electricity_trading_pb2.TradeState.TRADE_STATE_CANCELED
    """The trade has been cancelled. This can occur due to a cancellation request by the market
    participant, system, or market operator."""

    RECALL = electricity_trading_pb2.TradeState.TRADE_STATE_RECALLED
    """The trade has been recalled. This could be due to a system issue or a request from the market
    participant or market operator."""

    RECALL_REQUESTED = electricity_trading_pb2.TradeState.TRADE_STATE_RECALL_REQUESTED
    """A recall request for the trade has been submitted."""

    RECALL_REJECTED = electricity_trading_pb2.TradeState.TRADE_STATE_RECALL_REJECTED
    """The trade recall request was rejected."""

    APPROVAL_REQUESTED = (
        electricity_trading_pb2.TradeState.TRADE_STATE_APPROVAL_REQUESTED
    )
    """An approval has been requested."""

    @classmethod
    @from_pb
    def from_pb(
        cls, trade_state: electricity_trading_pb2.TradeState.ValueType
    ) -> "TradeState":
        """Convert a protobuf TradeState value to TradeState enum.

        Args:
            trade_state: The trade state to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == trade_state for e in cls):
            _logger.warning(
                "Unknown trade state %s. Returning UNSPECIFIED.", trade_state
            )
            return cls.UNSPECIFIED

        return cls(trade_state)

    def to_pb(self) -> electricity_trading_pb2.TradeState.ValueType:
        """Convert a TradeState enum to protobuf TradeState value.

        Returns:
            Protobuf message corresponding to the TradeState enum.
        """
        return self.value


class StateReason(enum.Enum):
    """Reason that led to a state change."""

    UNSPECIFIED = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_UNSPECIFIED
    )
    """The reason for the state change has not been specified."""

    ADD = electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_ADD
    """The order was added."""

    MODIFY = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_MODIFY
    )
    """The order was modified."""

    DELETE = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_DELETE
    )
    """The order was deleted."""

    DEACTIVATE = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_DEACTIVATE
    )
    """The order was deactivated."""

    REJECT = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_REJECT
    )
    """The order was rejected."""

    FULL_EXECUTION = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_FULL_EXECUTION
    )
    """The order was fully executed."""

    PARTIAL_EXECUTION = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_PARTIAL_EXECUTION
    )
    """The order was partially executed."""

    ICEBERG_SLICE_ADD = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_ICEBERG_SLICE_ADD
    )
    """An iceberg slice was added."""

    VALIDATION_FAIL = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_VALIDATION_FAIL
    )
    """The order failed validation."""

    UNKNOWN_STATE = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_UNKNOWN_STATE
    )
    """The state of the order is unknown."""

    QUOTE_ADD = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_QUOTE_ADD
    )
    """A quote was added."""

    QUOTE_FULL_EXECUTION = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_QUOTE_FULL_EXECUTION  # noqa: E501
    )
    """A quote was fully executed."""

    QUOTE_PARTIAL_EXECUTION = (
        electricity_trading_pb2.OrderDetail.StateDetail.StateReason.STATE_REASON_QUOTE_PARTIAL_EXECUTION  # noqa: E501
    )
    """A quote was partially executed."""

    @classmethod
    @from_pb
    def from_pb(
        cls,
        state_reason: electricity_trading_pb2.OrderDetail.StateDetail.StateReason.ValueType,
    ) -> "StateReason":
        """Convert a protobuf StateReason value to StateReason enum.

        Args:
            state_reason: State reason to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == state_reason for e in cls):
            _logger.warning(
                "Unknown state reason %s. Returning UNSPECIFIED.", state_reason
            )
            return cls.UNSPECIFIED

        return cls(state_reason)

    def to_pb(
        self,
    ) -> electricity_trading_pb2.OrderDetail.StateDetail.StateReason.ValueType:
        """Convert a StateReason enum to protobuf StateReason value.

        Returns:
            Protobuf message corresponding to the StateReason enum.
        """
        return self.value


class MarketActor(enum.Enum):
    """Actors responsible for an order state change."""

    UNSPECIFIED = (
        electricity_trading_pb2.OrderDetail.StateDetail.MarketActor.MARKET_ACTOR_UNSPECIFIED
    )
    """The actor responsible for the state change has not been specified."""

    USER = electricity_trading_pb2.OrderDetail.StateDetail.MarketActor.MARKET_ACTOR_USER
    """The user was the actor."""

    MARKET_OPERATOR = (
        electricity_trading_pb2.OrderDetail.StateDetail.MarketActor.MARKET_ACTOR_MARKET_OPERATOR
    )
    """The market operator was the actor."""

    SYSTEM = (
        electricity_trading_pb2.OrderDetail.StateDetail.MarketActor.MARKET_ACTOR_SYSTEM
    )
    """The system was the actor."""

    @classmethod
    @from_pb
    def from_pb(
        cls,
        market_actor: electricity_trading_pb2.OrderDetail.StateDetail.MarketActor.ValueType,
    ) -> "MarketActor":
        """Convert a protobuf MarketActor value to MarketActor enum.

        Args:
            market_actor: Market actor to convert.

        Returns:
            Enum value corresponding to the protobuf message.
        """
        if not any(e.value == market_actor for e in cls):
            _logger.warning(
                "Unknown market actor %s. Returning UNSPECIFIED.", market_actor
            )
            return cls.UNSPECIFIED

        return cls(market_actor)

    def to_pb(
        self,
    ) -> electricity_trading_pb2.OrderDetail.StateDetail.MarketActor.ValueType:
        """Convert a MarketActor enum to protobuf MarketActor value.

        Returns:
            Protobuf message corresponding to the MarketActor enum.
        """
        return self.value


@dataclass()
class Order:  # pylint: disable=too-many-instance-attributes
    """Represents an order in the electricity market."""

    delivery_area: DeliveryArea
    """The delivery area where the contract is to be delivered."""

    delivery_period: DeliveryPeriod
    """The delivery period for the contract."""

    type: OrderType
    """The type of order."""

    side: MarketSide
    """Indicates if the order is on the Buy or Sell side of the market."""

    price: Price
    """The limit price at which the contract is to be traded."""

    quantity: Power
    """The quantity of the contract being traded."""

    stop_price: Price | None = None
    """Applicable for STOP_LIMIT orders. The stop price that triggers the limit order."""

    peak_price_delta: Price | None = None
    """Applicable for ICEBERG orders. The price difference between the peak price and
    the limit price."""

    display_quantity: Power | None = None
    """Applicable for ICEBERG orders. The quantity of the order to be displayed in the order
    book."""

    execution_option: OrderExecutionOption | None = None
    """Order execution options such as All or None, Fill or Kill, etc."""

    valid_until: datetime | None = None
    """UTC timestamp defining the time after which the order should be cancelled if not filled."""

    payload: dict[str, struct_pb2.Value] | None = None
    """User-defined payload individual to a specific order. This can be any data that needs to be
    associated with the order."""

    tag: str | None = None
    """User-defined tag to group related orders."""

    def __post_init__(self) -> None:
        """Post initialization checks to ensure that all datetimes are UTC."""
        if self.valid_until is not None:
            if self.valid_until.tzinfo is None:
                raise ValueError("Valid until must be a UTC datetime.")
            if self.valid_until.tzinfo != timezone.utc:
                _logger.warning("Valid until is not a UTC datetime. Converting to UTC.")
                self.valid_until = self.valid_until.astimezone(timezone.utc)

    @classmethod
    @from_pb
    def from_pb(cls, order: electricity_trading_pb2.Order) -> Self:
        """Convert a protobuf Order to Order object.

        Args:
            order: Order to convert.

        Returns:
            Order object corresponding to the protobuf message.
        """
        return cls(
            delivery_area=DeliveryArea.from_pb(order.delivery_area),
            delivery_period=DeliveryPeriod.from_pb(order.delivery_period),
            type=OrderType.from_pb(order.type),
            side=MarketSide.from_pb(order.side),
            price=(
                Price.from_pb(order.price)
                if order.HasField("price")
                else Price(Decimal("NaN"), Currency.UNSPECIFIED)
            ),
            quantity=(
                Power.from_pb(order.quantity)
                if order.HasField("quantity")
                else Power(Decimal("NaN"))
            ),
            stop_price=(
                Price.from_pb(order.stop_price)
                if order.HasField("stop_price")
                else None
            ),
            peak_price_delta=(
                Price.from_pb(order.peak_price_delta)
                if order.HasField("peak_price_delta")
                else None
            ),
            display_quantity=(
                Power.from_pb(order.display_quantity)
                if order.HasField("display_quantity")
                else None
            ),
            execution_option=(
                OrderExecutionOption.from_pb(order.execution_option)
                if order.HasField("execution_option")
                else None
            ),
            valid_until=(
                order.valid_until.ToDatetime(tzinfo=timezone.utc)
                if order.HasField("valid_until")
                else None
            ),
            payload=json_format.MessageToDict(order.payload) if order.payload else None,
            tag=order.tag if order.tag else None,
        )

    def to_pb(self) -> electricity_trading_pb2.Order:
        """
        Convert an Order object to protobuf Order.

        Returns:
            Protobuf message corresponding to the Order object.
        """
        if self.valid_until:
            valid_until = timestamp_pb2.Timestamp()
            valid_until.FromDatetime(self.valid_until)
        else:
            valid_until = None
        return electricity_trading_pb2.Order(
            delivery_area=self.delivery_area.to_pb(),
            delivery_period=self.delivery_period.to_pb(),
            type=electricity_trading_pb2.OrderType.ValueType(self.type.value),
            side=electricity_trading_pb2.MarketSide.ValueType(self.side.value),
            price=self.price.to_pb(),
            quantity=self.quantity.to_pb(),
            stop_price=self.stop_price.to_pb() if self.stop_price else None,
            peak_price_delta=(
                self.peak_price_delta.to_pb() if self.peak_price_delta else None
            ),
            display_quantity=(
                self.display_quantity.to_pb() if self.display_quantity else None
            ),
            execution_option=(
                electricity_trading_pb2.OrderExecutionOption.ValueType(
                    self.execution_option.value
                )
                if self.execution_option
                else None
            ),
            valid_until=valid_until,
            payload=struct_pb2.Struct(fields=self.payload) if self.payload else None,
            tag=self.tag if self.tag else None,
        )

    def __eq__(self, other: object) -> bool:
        """
        Check if two orders are equal.

        Args:
            other: The other order to compare to.

        Returns:
            True if the orders are equal, False otherwise.
        """
        if not isinstance(other, Order):
            return NotImplemented
        return (
            self.delivery_area == other.delivery_area
            and self.delivery_period.start == other.delivery_period.start
            and self.delivery_period.duration == other.delivery_period.duration
            and self.type == other.type
            and self.side == other.side
            and self.price == other.price
            and self.quantity == other.quantity
            and self.stop_price == other.stop_price
            and self.peak_price_delta == other.peak_price_delta
            and self.display_quantity == other.display_quantity
            and (
                self.execution_option == other.execution_option
                or (
                    self.execution_option is None
                    and other.execution_option == OrderExecutionOption.UNSPECIFIED
                )
                or (
                    self.execution_option == OrderExecutionOption.UNSPECIFIED
                    and other.execution_option is None
                )
            )
            and self.valid_until == other.valid_until
            and self.payload == other.payload
            and self.tag == other.tag
        )


@dataclass()
class Trade:  # pylint: disable=too-many-instance-attributes
    """Represents a private trade in the electricity market."""

    id: int
    """ID of the trade."""

    order_id: int
    """ID of the corresponding order."""

    side: MarketSide
    """Indicates if the trade's order was on the Buy or Sell side of the
    market."""

    delivery_area: DeliveryArea
    """Delivery area of the trade."""

    delivery_period: DeliveryPeriod
    """The delivery period for the contract."""

    execution_time: datetime
    """UTC Timestamp of the trade's execution time."""

    price: Price
    """The price at which the trade was executed."""

    quantity: Power
    """The executed quantity of the trade."""

    state: TradeState
    """Current state of the trade."""

    def __post_init__(self) -> None:
        """Post initialization checks to ensure that all datetimes are UTC."""
        if self.execution_time.tzinfo is None:
            raise ValueError("Execution time must have timezone information")
        if self.execution_time.tzinfo != timezone.utc:
            _logger.warning("Execution timenis not in UTC timezone. Converting to UTC.")
            self.execution_time = self.execution_time.astimezone(timezone.utc)

    @classmethod
    @from_pb
    def from_pb(cls, trade: electricity_trading_pb2.Trade) -> Self:
        """Convert a protobuf Trade to Trade object.

        Args:
            trade: Trade to convert.

        Returns:
            Trade object corresponding to the protobuf message.
        """
        return cls(
            id=trade.id,
            order_id=trade.order_id,
            side=MarketSide.from_pb(trade.side),
            delivery_area=DeliveryArea.from_pb(trade.delivery_area),
            delivery_period=DeliveryPeriod.from_pb(trade.delivery_period),
            execution_time=trade.execution_time.ToDatetime(tzinfo=timezone.utc),
            price=Price.from_pb(trade.price),
            quantity=Power.from_pb(trade.quantity),
            state=TradeState.from_pb(trade.state),
        )

    def to_pb(self) -> electricity_trading_pb2.Trade:
        """Convert a Trade object to protobuf Trade.

        Returns:
            Protobuf message corresponding to the Trade object.
        """
        execution_time = timestamp_pb2.Timestamp()
        execution_time.FromDatetime(self.execution_time)

        return electricity_trading_pb2.Trade(
            id=self.id,
            order_id=self.order_id,
            side=electricity_trading_pb2.MarketSide.ValueType(self.side.value),
            delivery_area=self.delivery_area.to_pb(),
            delivery_period=self.delivery_period.to_pb(),
            execution_time=execution_time,
            price=self.price.to_pb(),
            quantity=self.quantity.to_pb(),
            state=electricity_trading_pb2.TradeState.ValueType(self.state.value),
        )


@dataclass(frozen=True)
class StateDetail:
    """Details about the current state of the order."""

    state: OrderState
    """Current state of the order."""

    state_reason: StateReason
    """Reason for the current state."""

    market_actor: MarketActor
    """Actor responsible for the current state."""

    @classmethod
    @from_pb
    def from_pb(
        cls, state_detail: electricity_trading_pb2.OrderDetail.StateDetail
    ) -> Self:
        """Convert a protobuf StateDetail to StateDetail object.

        Args:
            state_detail: StateDetail to convert.

        Returns:
            StateDetail object corresponding to the protobuf message.
        """
        return cls(
            state=OrderState.from_pb(state_detail.state),
            state_reason=StateReason.from_pb(state_detail.state_reason),
            market_actor=MarketActor.from_pb(state_detail.market_actor),
        )

    def to_pb(self) -> electricity_trading_pb2.OrderDetail.StateDetail:
        """Convert a StateDetail object to protobuf StateDetail.

        Returns:
            Protobuf message corresponding to the StateDetail object.
        """
        return electricity_trading_pb2.OrderDetail.StateDetail(
            state=electricity_trading_pb2.OrderState.ValueType(self.state.value),
            state_reason=electricity_trading_pb2.OrderDetail.StateDetail.StateReason.ValueType(
                self.state_reason.value
            ),
            market_actor=electricity_trading_pb2.OrderDetail.StateDetail.MarketActor.ValueType(
                self.market_actor.value
            ),
        )


@dataclass()
class OrderDetail:
    """
    Represents an order with full details, including its ID, state, and associated UTC timestamps.

    Attributes:
        order_id: Unique identifier of the order.
        order: The details of the order.
        state_detail: Details of the order's current state.
        open_quantity: Remaining open quantity for this order.
        filled_quantity: Filled quantity for this order.
        create_time: UTC Timestamp when the order was created.
        modification_time: UTC Timestamp of the last update to the order.
    """

    order_id: int
    order: Order
    state_detail: StateDetail
    open_quantity: Power
    filled_quantity: Power
    create_time: datetime
    modification_time: datetime

    def __post_init__(self) -> None:
        """
        Post initialization checks to ensure that all datetimes are UTC.

        Raises:
            ValueError: If create_time or modification_time do not have timezone information.

        """
        if self.create_time.tzinfo is None:
            raise ValueError("Create time must have timezone information")
        if self.create_time.tzinfo != timezone.utc:
            _logger.warning("Create time is not in UTC timezone. Converting to UTC.")
            self.create_time = self.create_time.astimezone(timezone.utc)

        if self.modification_time.tzinfo is None:
            raise ValueError("Modification time must have timezone information")
        if self.modification_time.tzinfo != timezone.utc:
            _logger.warning(
                "Modification time is not in UTC timezone. Converting to UTC."
            )
            self.modification_time = self.modification_time.astimezone(timezone.utc)

    @classmethod
    @from_pb
    def from_pb(cls, order_detail: electricity_trading_pb2.OrderDetail) -> Self:
        """Convert a protobuf OrderDetail to OrderDetail object.

        Args:
            order_detail: OrderDetail to convert.

        Returns:
            OrderDetail object corresponding to the protobuf message.

        Raises:
            ValueError: If the order price and quantity are not specified for a non-canceled order.
        """
        od = cls(
            order_id=order_detail.order_id,
            order=Order.from_pb(order_detail.order),
            state_detail=StateDetail.from_pb(order_detail.state_detail),
            open_quantity=Power.from_pb(order_detail.open_quantity),
            filled_quantity=Power.from_pb(order_detail.filled_quantity),
            create_time=order_detail.create_time.ToDatetime(tzinfo=timezone.utc),
            modification_time=order_detail.modification_time.ToDatetime(
                tzinfo=timezone.utc
            ),
        )

        # Only cancelled orders are allowed to have missing price or quantity
        missing_price_or_quantity = (
            od.order.price.amount.is_nan()
            or od.order.price.currency == Currency.UNSPECIFIED
            or od.order.quantity.mw.is_nan()
        )
        if missing_price_or_quantity and od.state_detail.state != OrderState.CANCELED:
            raise ValueError(
                f"Price and quantity must be specified for a non-canceled order (`{od}`)."
            )

        return od

    def to_pb(self) -> electricity_trading_pb2.OrderDetail:
        """Convert an OrderDetail object to protobuf OrderDetail.

        Returns:
            Protobuf message corresponding to the OrderDetail object.
        """
        create_time = timestamp_pb2.Timestamp()
        create_time.FromDatetime(self.create_time)
        modification_time = timestamp_pb2.Timestamp()
        modification_time.FromDatetime(self.modification_time)

        return electricity_trading_pb2.OrderDetail(
            order_id=self.order_id,
            order=self.order.to_pb(),
            state_detail=self.state_detail.to_pb(),
            open_quantity=self.open_quantity.to_pb(),
            filled_quantity=self.filled_quantity.to_pb(),
            create_time=create_time,
            modification_time=modification_time,
        )


@dataclass()
class PublicTrade:  # pylint: disable=too-many-instance-attributes
    """Represents a public order in the market."""

    public_trade_id: int
    """ID of the order from the public order book."""

    buy_delivery_area: DeliveryArea
    """Delivery area code of the buy side."""

    sell_delivery_area: DeliveryArea
    """Delivery area code of the sell side."""

    delivery_period: DeliveryPeriod
    """The delivery period for the contract."""

    execution_time: datetime
    """UTC Timestamp of the trades execution time."""

    price: Price
    """The limit price at which the contract is to be traded."""

    quantity: Power
    """The quantity of the contract being traded."""

    state: TradeState
    """State of the order."""

    def __post_init__(self) -> None:
        """Post initialization checks to ensure that all datetimes are UTC."""
        if self.execution_time.tzinfo is None:
            raise ValueError("Execution time must have timezone information")
        if self.execution_time.tzinfo != timezone.utc:
            _logger.warning("Execution time is not in UTC timezone. Converting to UTC.")
            self.execution_time = self.execution_time.astimezone(timezone.utc)

    @classmethod
    @from_pb
    def from_pb(cls, public_trade: electricity_trading_pb2.PublicTrade) -> Self:
        """Convert a protobuf PublicTrade to PublicTrade object.

        Args:
            public_trade: PublicTrade to convert.

        Returns:
            PublicTrade object corresponding to the protobuf message.
        """
        return cls(
            public_trade_id=public_trade.id,
            buy_delivery_area=DeliveryArea.from_pb(public_trade.buy_delivery_area),
            sell_delivery_area=DeliveryArea.from_pb(public_trade.sell_delivery_area),
            delivery_period=DeliveryPeriod.from_pb(public_trade.delivery_period),
            execution_time=public_trade.execution_time.ToDatetime(tzinfo=timezone.utc),
            price=Price.from_pb(public_trade.price),
            quantity=Power.from_pb(public_trade.quantity),
            state=TradeState.from_pb(public_trade.state),
        )

    def to_pb(self) -> electricity_trading_pb2.PublicTrade:
        """Convert a PublicTrade object to protobuf PublicTrade.

        Returns:
            Protobuf message corresponding to the PublicTrade object.
        """
        execution_time = timestamp_pb2.Timestamp()
        execution_time.FromDatetime(self.execution_time)

        return electricity_trading_pb2.PublicTrade(
            id=self.public_trade_id,
            buy_delivery_area=self.buy_delivery_area.to_pb(),
            sell_delivery_area=self.sell_delivery_area.to_pb(),
            delivery_period=self.delivery_period.to_pb(),
            execution_time=execution_time,
            price=self.price.to_pb(),
            quantity=self.quantity.to_pb(),
            state=electricity_trading_pb2.TradeState.ValueType(self.state.value),
        )


@dataclass(frozen=True)
class GridpoolOrderFilter:
    """Parameters for filtering Gridpool orders."""

    order_states: list[OrderState] | None = None
    """List of order states to filter for."""

    side: MarketSide | None = None
    """Market side to filter for."""

    delivery_period: DeliveryPeriod | None = None
    """Delivery period to filter for."""

    delivery_area: DeliveryArea | None = None
    """Delivery area to filter for."""

    tag: str | None = None
    """Tag associated with the orders to be filtered."""

    def __eq__(self, other: object) -> bool:
        """
        Check if two GridpoolOrderFilter objects are equal.

        Args:
            other: GridpoolOrderFilter object to compare with.

        Returns:
            True if the two GridpoolOrderFilter objects are equal, False otherwise.
        """
        if not isinstance(other, GridpoolOrderFilter):
            return NotImplemented
        return (
            self.order_states == other.order_states
            and self.side == other.side
            and self.delivery_period == other.delivery_period
            and self.delivery_area == other.delivery_area
            and self.tag == other.tag
        )

    def __hash__(self) -> int:
        """
        Create hash of the GridpoolOrderFilter object.

        Returns:
            Hash of the GridpoolOrderFilter object.
        """
        return hash(
            (
                tuple(self.order_states) if self.order_states is not None else None,
                self.side,
                self.delivery_period,
                self.delivery_area,
                self.tag,
            )
        )

    @classmethod
    @from_pb
    def from_pb(
        cls, gridpool_order_filter: electricity_trading_pb2.GridpoolOrderFilter
    ) -> Self:
        """Convert a protobuf GridpoolOrderFilter to GridpoolOrderFilter object.

        Args:
            gridpool_order_filter: GridpoolOrderFilter to convert.

        Returns:
            GridpoolOrderFilter object corresponding to the protobuf message.
        """
        return cls(
            order_states=(
                [OrderState.from_pb(state) for state in gridpool_order_filter.states]
                if gridpool_order_filter.states
                else None
            ),
            side=(
                MarketSide.from_pb(gridpool_order_filter.side)
                if gridpool_order_filter.HasField("side")
                else None
            ),
            delivery_period=(
                DeliveryPeriod.from_pb(gridpool_order_filter.delivery_period)
                if gridpool_order_filter.HasField("delivery_period")
                else None
            ),
            delivery_area=(
                DeliveryArea.from_pb(gridpool_order_filter.delivery_area)
                if gridpool_order_filter.HasField("delivery_area")
                else None
            ),
            tag=(
                gridpool_order_filter.tag
                if gridpool_order_filter.HasField("tag")
                else None
            ),
        )

    def to_pb(self) -> electricity_trading_pb2.GridpoolOrderFilter:
        """Convert a GridpoolOrderFilter object to protobuf GridpoolOrderFilter.

        Returns:
            Protobuf GridpoolOrderFilter corresponding to the object.
        """
        return electricity_trading_pb2.GridpoolOrderFilter(
            states=(
                [
                    electricity_trading_pb2.OrderState.ValueType(state.value)
                    for state in self.order_states
                ]
                if self.order_states
                else None
            ),
            side=(
                electricity_trading_pb2.MarketSide.ValueType(self.side.value)
                if self.side
                else None
            ),
            delivery_period=(
                self.delivery_period.to_pb() if self.delivery_period else None
            ),
            delivery_area=self.delivery_area.to_pb() if self.delivery_area else None,
            tag=self.tag if self.tag else None,
        )


@dataclass(frozen=True)
class GridpoolTradeFilter:
    """Parameters for filtering Gridpool trades."""

    trade_states: list[TradeState] | None = None
    """List of trade states to filter for."""

    trade_ids: list[int] | None = None
    """List of trade ids to filter for."""

    side: MarketSide | None = None
    """Market side to filter for."""

    delivery_period: DeliveryPeriod | None = None
    """Delivery period to filter for."""

    delivery_area: DeliveryArea | None = None
    """Delivery area to filter for."""

    def __eq__(self, other: object) -> bool:
        """
        Check if two GridpoolTradeFilter objects are equal.

        Args:
            other: GridpoolTradeFilter object to compare with.

        Returns:
            True if the two GridpoolTradeFilter objects are equal, False otherwise.
        """
        if not isinstance(other, GridpoolTradeFilter):
            return NotImplemented
        return (
            self.trade_states == other.trade_states
            and self.trade_ids == other.trade_ids
            and self.side == other.side
            and self.delivery_period == other.delivery_period
            and self.delivery_area == other.delivery_area
        )

    def __hash__(self) -> int:
        """
        Create hash of the GridpoolTradeFilter object.

        Returns:
            Hash of the GridpoolTradeFilter object.
        """
        return hash(
            (
                tuple(self.trade_states) if self.trade_states is not None else None,
                tuple(self.trade_ids) if self.trade_ids is not None else None,
                self.side,
                self.delivery_period,
                self.delivery_area,
            )
        )

    @classmethod
    @from_pb
    def from_pb(
        cls, gridpool_trade_filter: electricity_trading_pb2.GridpoolTradeFilter
    ) -> "GridpoolTradeFilter":
        """Convert a protobuf GridpoolTradeFilter to GridpoolTradeFilter object.

        Args:
            gridpool_trade_filter: GridpoolTradeFilter to convert.

        Returns:
            GridpoolTradeFilter object corresponding to the protobuf message.
        """
        return cls(
            trade_states=(
                [TradeState.from_pb(state) for state in gridpool_trade_filter.states]
                if gridpool_trade_filter.states
                else None
            ),
            trade_ids=(
                list(gridpool_trade_filter.trade_ids)
                if gridpool_trade_filter.trade_ids
                else None
            ),
            side=(
                MarketSide.from_pb(gridpool_trade_filter.side)
                if gridpool_trade_filter.HasField("side")
                else None
            ),
            delivery_period=(
                DeliveryPeriod.from_pb(gridpool_trade_filter.delivery_period)
                if gridpool_trade_filter.HasField("delivery_period")
                else None
            ),
            delivery_area=(
                DeliveryArea.from_pb(gridpool_trade_filter.delivery_area)
                if gridpool_trade_filter.HasField("delivery_area")
                else None
            ),
        )

    def to_pb(self) -> electricity_trading_pb2.GridpoolTradeFilter:
        """
        Convert a GridpoolTradeFilter object to protobuf GridpoolTradeFilter.

        Returns:
            Protobuf GridpoolTradeFilter corresponding to the object.
        """
        return electricity_trading_pb2.GridpoolTradeFilter(
            states=(
                [TradeState.to_pb(state) for state in self.trade_states]
                if self.trade_states
                else None
            ),
            trade_ids=self.trade_ids if self.trade_ids else None,
            side=MarketSide.to_pb(self.side) if self.side else None,
            delivery_period=(
                self.delivery_period.to_pb() if self.delivery_period else None
            ),
            delivery_area=self.delivery_area.to_pb() if self.delivery_area else None,
        )


@dataclass(frozen=True)
class PublicTradeFilter:
    """Parameters for filtering the historic, publicly executed orders (trades)."""

    states: list[TradeState] | None = None
    """List of order states to filter for."""

    delivery_period: DeliveryPeriod | None = None
    """Delivery period to filter for."""

    buy_delivery_area: DeliveryArea | None = None
    """Delivery area to filter for on the buy side."""

    sell_delivery_area: DeliveryArea | None = None
    """Delivery area to filter for on the sell side."""

    def __eq__(self, other: object) -> bool:
        """
        Check if two PublicTradeFilter objects are equal.

        Args:
            other: PublicTradeFilter object to compare with.

        Returns:
            True if the two PublicTradeFilter objects are equal, False otherwise.
        """
        if not isinstance(other, PublicTradeFilter):
            return NotImplemented
        return (
            self.states == other.states
            and self.delivery_period == other.delivery_period
            and self.buy_delivery_area == other.buy_delivery_area
            and self.sell_delivery_area == other.sell_delivery_area
        )

    def __hash__(self) -> int:
        """
        Create hash of the PublicTradeFilter object.

        Returns:
            Hash of the PublicTradeFilter object.
        """
        return hash(
            (
                tuple(self.states) if self.states is not None else None,
                self.delivery_period,
                self.buy_delivery_area,
                self.sell_delivery_area,
            )
        )

    @classmethod
    @from_pb
    def from_pb(
        cls, public_trade_filter: electricity_trading_pb2.PublicTradeFilter
    ) -> Self:
        """Convert a protobuf PublicTradeFilter to PublicTradeFilter object.

        Args:
            public_trade_filter: PublicTradeFilter to convert.

        Returns:
            PublicTradeFilter object corresponding to the protobuf message.
        """
        return cls(
            states=(
                [TradeState.from_pb(state) for state in public_trade_filter.states]
                if public_trade_filter.states
                else None
            ),
            delivery_period=(
                DeliveryPeriod.from_pb(public_trade_filter.delivery_period)
                if public_trade_filter.HasField("delivery_period")
                else None
            ),
            buy_delivery_area=(
                DeliveryArea.from_pb(public_trade_filter.buy_delivery_area)
                if public_trade_filter.HasField("buy_delivery_area")
                else None
            ),
            sell_delivery_area=(
                DeliveryArea.from_pb(public_trade_filter.sell_delivery_area)
                if public_trade_filter.HasField("sell_delivery_area")
                else None
            ),
        )

    def to_pb(self) -> electricity_trading_pb2.PublicTradeFilter:
        """Convert a PublicTradeFilter object to protobuf PublicTradeFilter.

        Returns:
            Protobuf PublicTradeFilter corresponding to the object.
        """
        return electricity_trading_pb2.PublicTradeFilter(
            states=(
                [
                    electricity_trading_pb2.TradeState.ValueType(state.value)
                    for state in self.states
                ]
                if self.states
                else None
            ),
            delivery_period=(
                self.delivery_period.to_pb() if self.delivery_period else None
            ),
            buy_delivery_area=(
                self.buy_delivery_area.to_pb() if self.buy_delivery_area else None
            ),
            sell_delivery_area=(
                self.sell_delivery_area.to_pb() if self.sell_delivery_area else None
            ),
        )


@dataclass()
class UpdateOrder:  # pylint: disable=too-many-instance-attributes
    """
    Represents the order properties that can be updated after an order has been placed.

    At least one of the optional fields must be set for an update to take place.
    """

    price: Price | None = None
    """The updated limit price at which the contract is to be traded.
    This is the maximum price for a BUY order or the minimum price for a SELL order."""

    quantity: Power | None = None
    """The updated quantity of the contract being traded, specified in MW."""

    stop_price: Price | None = None
    """Applicable for STOP_LIMIT orders. This is the updated stop price that triggers
    the limit order."""

    peak_price_delta: Price | None = None
    """Applicable for ICEBERG orders. This is the updated price difference
    between the peak price and the limit price."""

    display_quantity: Power | None = None
    """Applicable for ICEBERG orders. This is the updated quantity of the order
    to be displayed in the order book."""

    execution_option: OrderExecutionOption | None = None
    """Updated execution options such as All or None, Fill or Kill, etc."""

    valid_until: datetime | None = None
    """This is an updated timestamp defining the time after which the order should
    be cancelled if not filled. The timestamp is in UTC."""

    payload: dict[str, struct_pb2.Value] | None = None
    """Updated user-defined payload individual to a specific order. This can be any data
    that the user wants to associate with the order."""

    tag: str | None = None
    """Updated user-defined tag to group related orders."""

    def __post_init__(self) -> None:
        """Post initialization checks to ensure that all datetimes are UTC."""
        if self.valid_until is not None:
            if self.valid_until.tzinfo is None:
                raise ValueError("Valid until must be a UTC datetime.")
            if self.valid_until.tzinfo != timezone.utc:
                _logger.warning("Valid until is not a UTC datetime. Converting to UTC.")
                self.valid_until = self.valid_until.astimezone(timezone.utc)

    @classmethod
    @from_pb
    def from_pb(
        cls,
        update_order: electricity_trading_pb2.UpdateGridpoolOrderRequest.UpdateOrder,
    ) -> Self:
        """Convert a protobuf UpdateOrder to UpdateOrder object.

        Args:
            update_order: UpdateOrder to convert.

        Returns:
            UpdateOrder object corresponding to the protobuf message.
        """
        return cls(
            price=(
                Price.from_pb(update_order.price)
                if update_order.HasField("price")
                else None
            ),
            quantity=(
                Power.from_pb(update_order.quantity)
                if update_order.HasField("quantity")
                else None
            ),
            stop_price=(
                Price.from_pb(update_order.stop_price)
                if update_order.HasField("stop_price")
                else None
            ),
            peak_price_delta=(
                Price.from_pb(update_order.peak_price_delta)
                if update_order.HasField("peak_price_delta")
                else None
            ),
            display_quantity=(
                Power.from_pb(update_order.display_quantity)
                if update_order.HasField("display_quantity")
                else None
            ),
            execution_option=(
                OrderExecutionOption.from_pb(update_order.execution_option)
                if update_order.HasField("execution_option")
                else None
            ),
            valid_until=(
                update_order.valid_until.ToDatetime(tzinfo=timezone.utc)
                if update_order.HasField("valid_until")
                else None
            ),
            payload=(
                json_format.MessageToDict(update_order.payload)
                if update_order.payload
                else None
            ),
            tag=update_order.tag if update_order.HasField("tag") else None,
        )

    def to_pb(self) -> electricity_trading_pb2.UpdateGridpoolOrderRequest.UpdateOrder:
        """Convert a UpdateOrder object to protobuf UpdateOrder.

        Returns:
            Protobuf UpdateOrder corresponding to the object.
        """
        if self.valid_until:
            valid_until = timestamp_pb2.Timestamp()
            valid_until.FromDatetime(self.valid_until)
        else:
            valid_until = None
        return electricity_trading_pb2.UpdateGridpoolOrderRequest.UpdateOrder(
            price=self.price.to_pb() if self.price else None,
            quantity=self.quantity.to_pb() if self.quantity else None,
            stop_price=self.stop_price.to_pb() if self.stop_price else None,
            peak_price_delta=(
                self.peak_price_delta.to_pb() if self.peak_price_delta else None
            ),
            display_quantity=(
                self.display_quantity.to_pb() if self.display_quantity else None
            ),
            execution_option=(
                electricity_trading_pb2.OrderExecutionOption.ValueType(
                    self.execution_option.value
                )
                if self.execution_option
                else None
            ),
            valid_until=valid_until if self.valid_until else None,
            payload=struct_pb2.Struct(fields=self.payload) if self.payload else None,
            tag=self.tag if self.tag else None,
        )
