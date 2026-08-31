"""Integrate recovered watchlist REAL packets with observed trade state."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

from kiwoom_trading_system.brokers.kiwoom.websocket import (
    run_demo_watchlist_recovery_baseline,
)
from kiwoom_trading_system.market_data.realtime_trade import (
    MarketVenue,
    TradeNormalizationError,
    normalize_trade_packet,
)
from kiwoom_trading_system.screening import RealtimeWatchlist
from kiwoom_trading_system.state.realtime_trade_state import (
    RealtimeTradeState,
    RealtimeTradeStateError,
    update_realtime_trade_state,
)


WatchlistRecoveryStateKey = tuple[str, MarketVenue]


@dataclass(frozen=True, slots=True)
class WatchlistRecoveryStatePipelineMetrics:
    """Processing metrics for one bounded recovered watchlist stream."""

    realtime_packets: int
    normalized_trades: int
    normalization_errors: int
    normalization_error_messages: tuple[str, ...]
    state_updates: int
    state_errors: int
    state_error_messages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WatchlistRecoveryStatePipelineResult:
    """Immutable observed-stream result; server replay is not deduplicated."""

    baseline_summary: Mapping[str, Any]
    states: Mapping[WatchlistRecoveryStateKey, RealtimeTradeState]
    metrics: WatchlistRecoveryStatePipelineMetrics


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def run_demo_watchlist_recovery_state_pipeline(
    watchlist: RealtimeWatchlist,
    *,
    duration_seconds: float = 10.0,
    max_realtime_messages: int = 1,
    max_reconnect_attempts: int = 2,
    initial_backoff_seconds: float = 0.25,
    max_backoff_seconds: float = 2.0,
    clock: Callable[[], datetime] | None = None,
) -> WatchlistRecoveryStatePipelineResult:
    """Normalize and aggregate accepted REAL packets across reconnects."""

    if clock is not None and not callable(clock):
        raise TypeError("clock must be callable.")

    clock_fn = clock or _utc_now
    states: dict[WatchlistRecoveryStateKey, RealtimeTradeState] = {}
    normalization_error_messages: list[str] = []
    state_error_messages: list[str] = []
    realtime_packets = 0
    normalized_trades = 0
    normalization_errors = 0
    state_updates = 0
    state_errors = 0

    async def process_realtime(message: Any) -> None:
        nonlocal realtime_packets
        nonlocal normalized_trades
        nonlocal normalization_errors
        nonlocal state_updates
        nonlocal state_errors

        realtime_packets += 1
        try:
            trades = normalize_trade_packet(
                message,
                received_at=clock_fn(),
            )
        except TradeNormalizationError as error:
            normalization_errors += 1
            normalization_error_messages.append(str(error))
            return

        normalized_trades += len(trades)
        for trade in trades:
            key = (trade.instrument_code, trade.venue)
            try:
                updated_state = update_realtime_trade_state(
                    states.get(key),
                    trade,
                )
            except RealtimeTradeStateError as error:
                state_errors += 1
                state_error_messages.append(str(error))
                continue

            states[key] = updated_state
            state_updates += 1

    baseline_summary = await run_demo_watchlist_recovery_baseline(
        watchlist,
        duration_seconds=duration_seconds,
        max_realtime_messages=max_realtime_messages,
        max_reconnect_attempts=max_reconnect_attempts,
        initial_backoff_seconds=initial_backoff_seconds,
        max_backoff_seconds=max_backoff_seconds,
        on_realtime_message=process_realtime,
    )

    return WatchlistRecoveryStatePipelineResult(
        baseline_summary=MappingProxyType(dict(baseline_summary)),
        states=MappingProxyType(dict(states)),
        metrics=WatchlistRecoveryStatePipelineMetrics(
            realtime_packets=realtime_packets,
            normalized_trades=normalized_trades,
            normalization_errors=normalization_errors,
            normalization_error_messages=tuple(
                normalization_error_messages
            ),
            state_updates=state_updates,
            state_errors=state_errors,
            state_error_messages=tuple(state_error_messages),
        ),
    )


__all__ = [
    "WatchlistRecoveryStateKey",
    "WatchlistRecoveryStatePipelineMetrics",
    "WatchlistRecoveryStatePipelineResult",
    "run_demo_watchlist_recovery_state_pipeline",
]
