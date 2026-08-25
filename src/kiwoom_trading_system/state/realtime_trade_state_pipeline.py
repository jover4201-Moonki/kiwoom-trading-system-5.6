from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from kiwoom_trading_system.market_data.realtime_pipeline import (
    RealtimePipelineResult,
    run_demo_trade_pipeline,
)
from kiwoom_trading_system.market_data.realtime_trade import MarketVenue
from kiwoom_trading_system.state.realtime_trade_state import (
    RealtimeTradeState,
    RealtimeTradeStateError,
    update_realtime_trade_state,
)


StateKey = tuple[str, MarketVenue]


@dataclass(frozen=True, slots=True)
class RealtimeTradeStatePipelineMetrics:
    """State-update metrics for one bounded demo pipeline run."""

    state_updates: int
    state_errors: int
    state_error_messages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RealtimeTradeStatePipelineResult:
    """Immutable Phase 7 and Phase 8 integration result."""

    pipeline_result: RealtimePipelineResult
    states: Mapping[StateKey, RealtimeTradeState]
    metrics: RealtimeTradeStatePipelineMetrics


def aggregate_realtime_trade_states(
    pipeline_result: RealtimePipelineResult,
) -> RealtimeTradeStatePipelineResult:
    """Apply normalized trades sequentially by instrument and venue."""

    if not isinstance(pipeline_result, RealtimePipelineResult):
        raise TypeError(
            "pipeline_result must be RealtimePipelineResult"
        )

    states: dict[StateKey, RealtimeTradeState] = {}
    state_error_messages: list[str] = []
    state_updates = 0
    state_errors = 0

    for trade in pipeline_result.trades:
        key = (trade.instrument_code, trade.venue)

        try:
            updated_state = update_realtime_trade_state(
                states.get(key),
                trade,
            )
        except RealtimeTradeStateError as exc:
            state_errors += 1
            state_error_messages.append(str(exc))
            continue

        states[key] = updated_state
        state_updates += 1

    return RealtimeTradeStatePipelineResult(
        pipeline_result=pipeline_result,
        states=MappingProxyType(dict(states)),
        metrics=RealtimeTradeStatePipelineMetrics(
            state_updates=state_updates,
            state_errors=state_errors,
            state_error_messages=tuple(state_error_messages),
        ),
    )


async def run_demo_trade_state_pipeline(
    stk_cd: str = "005930",
    *,
    realtime_type: str = "0B",
    duration_seconds: float = 10.0,
    max_messages: int = 3,
    queue_maxsize: int = 100,
    clock: Callable[[], datetime] | None = None,
) -> RealtimeTradeStatePipelineResult:
    """Run Phase 7 once and calculate Phase 8 states."""

    pipeline_result = await run_demo_trade_pipeline(
        stk_cd,
        realtime_type=realtime_type,
        duration_seconds=duration_seconds,
        max_messages=max_messages,
        queue_maxsize=queue_maxsize,
        clock=clock,
    )
    return aggregate_realtime_trade_states(pipeline_result)


__all__ = [
    "RealtimeTradeStatePipelineMetrics",
    "RealtimeTradeStatePipelineResult",
    "StateKey",
    "aggregate_realtime_trade_states",
    "run_demo_trade_state_pipeline",
]
