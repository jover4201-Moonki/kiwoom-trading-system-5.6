from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from kiwoom_trading_system.market_data.realtime_trade import (
    AggressorSide,
    MarketVenue,
    NormalizedTrade,
)


STATE_SCHEMA_VERSION = 1


class RealtimeTradeStateError(ValueError):
    """Raised when a normalized trade cannot be applied safely."""


@dataclass(frozen=True, slots=True)
class RealtimeTradeState:
    """Immutable observed state for one instrument and one market venue."""

    schema_version: int
    instrument_code: str
    venue: MarketVenue
    first_trade_at: datetime
    last_trade_at: datetime
    first_price_krw: int
    last_price_krw: int
    high_price_krw: int
    low_price_krw: int
    trade_count: int
    buy_trade_count: int
    sell_trade_count: int
    unknown_trade_count: int
    total_trade_volume: int
    buy_trade_volume: int
    sell_trade_volume: int
    observed_trade_value_krw: int

    @property
    def net_aggressor_volume(self) -> int:
        return self.buy_trade_volume - self.sell_trade_volume

    @property
    def volume_weighted_average_price_krw(self) -> Decimal | None:
        if self.total_trade_volume == 0:
            return None
        return Decimal(self.observed_trade_value_krw) / Decimal(
            self.total_trade_volume
        )


def update_realtime_trade_state(
    state: RealtimeTradeState | None,
    trade: NormalizedTrade,
) -> RealtimeTradeState:
    """Return a new state after applying one normalized trade."""

    if state is not None and not isinstance(state, RealtimeTradeState):
        raise TypeError("state must be RealtimeTradeState or None")
    if not isinstance(trade, NormalizedTrade):
        raise TypeError("trade must be NormalizedTrade")

    _validate_trade(trade)
    buy_count, sell_count, unknown_count = _side_counts(
        trade.aggressor_side
    )
    buy_volume, sell_volume = _side_volumes(trade)
    observed_value = trade.price_krw * trade.trade_volume

    if state is None:
        return RealtimeTradeState(
            schema_version=STATE_SCHEMA_VERSION,
            instrument_code=trade.instrument_code,
            venue=trade.venue,
            first_trade_at=trade.trade_at,
            last_trade_at=trade.trade_at,
            first_price_krw=trade.price_krw,
            last_price_krw=trade.price_krw,
            high_price_krw=trade.price_krw,
            low_price_krw=trade.price_krw,
            trade_count=1,
            buy_trade_count=buy_count,
            sell_trade_count=sell_count,
            unknown_trade_count=unknown_count,
            total_trade_volume=trade.trade_volume,
            buy_trade_volume=buy_volume,
            sell_trade_volume=sell_volume,
            observed_trade_value_krw=observed_value,
        )

    _validate_transition(state, trade)

    return RealtimeTradeState(
        schema_version=state.schema_version,
        instrument_code=state.instrument_code,
        venue=state.venue,
        first_trade_at=state.first_trade_at,
        last_trade_at=trade.trade_at,
        first_price_krw=state.first_price_krw,
        last_price_krw=trade.price_krw,
        high_price_krw=max(state.high_price_krw, trade.price_krw),
        low_price_krw=min(state.low_price_krw, trade.price_krw),
        trade_count=state.trade_count + 1,
        buy_trade_count=state.buy_trade_count + buy_count,
        sell_trade_count=state.sell_trade_count + sell_count,
        unknown_trade_count=state.unknown_trade_count + unknown_count,
        total_trade_volume=(
            state.total_trade_volume + trade.trade_volume
        ),
        buy_trade_volume=state.buy_trade_volume + buy_volume,
        sell_trade_volume=state.sell_trade_volume + sell_volume,
        observed_trade_value_krw=(
            state.observed_trade_value_krw + observed_value
        ),
    )


def _validate_trade(trade: NormalizedTrade) -> None:
    if trade.realtime_type != "0B":
        raise RealtimeTradeStateError(
            "trade realtime_type must be 0B"
        )
    if not trade.instrument_code:
        raise RealtimeTradeStateError(
            "instrument_code must not be empty"
        )
    if trade.price_krw <= 0:
        raise RealtimeTradeStateError(
            "price_krw must be positive"
        )
    if trade.trade_volume != abs(trade.signed_trade_volume):
        raise RealtimeTradeStateError(
            "trade volume fields are inconsistent"
        )
    if not _is_aware(trade.trade_at):
        raise RealtimeTradeStateError(
            "trade_at must be timezone-aware"
        )
    if not _is_aware(trade.received_at):
        raise RealtimeTradeStateError(
            "received_at must be timezone-aware"
        )

    expected_side = _expected_side(trade.signed_trade_volume)

    if trade.aggressor_side is not expected_side:
        raise RealtimeTradeStateError(
            "aggressor side is inconsistent"
        )


def _validate_transition(
    state: RealtimeTradeState,
    trade: NormalizedTrade,
) -> None:
    if state.schema_version != STATE_SCHEMA_VERSION:
        raise RealtimeTradeStateError(
            "unsupported state schema version"
        )
    if trade.instrument_code != state.instrument_code:
        raise RealtimeTradeStateError(
            "instrument_code does not match state"
        )
    if trade.venue is not state.venue:
        raise RealtimeTradeStateError(
            "venue does not match state"
        )
    if trade.trade_at < state.last_trade_at:
        raise RealtimeTradeStateError(
            "trade_at is older than state"
        )


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _expected_side(signed_volume: int) -> AggressorSide:
    if signed_volume > 0:
        return AggressorSide.BUY
    if signed_volume < 0:
        return AggressorSide.SELL
    return AggressorSide.UNKNOWN


def _side_counts(
    side: AggressorSide,
) -> tuple[int, int, int]:
    return (
        int(side is AggressorSide.BUY),
        int(side is AggressorSide.SELL),
        int(side is AggressorSide.UNKNOWN),
    )


def _side_volumes(
    trade: NormalizedTrade,
) -> tuple[int, int]:
    return (
        (
            trade.trade_volume
            if trade.aggressor_side is AggressorSide.BUY
            else 0
        ),
        (
            trade.trade_volume
            if trade.aggressor_side is AggressorSide.SELL
            else 0
        ),
    )
