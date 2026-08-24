from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

from kiwoom_trading_system.brokers.kiwoom.websocket.demo_baseline import (
    run_demo_realtime_baseline,
)
from kiwoom_trading_system.market_data.realtime_trade import (
    NormalizedTrade,
    TradeNormalizationError,
    normalize_trade_packet,
)


_STOP = object()


@dataclass(frozen=True, slots=True)
class RealtimePipelineMetrics:
    """Bounded processing metrics for one demo pipeline run."""

    queue_capacity: int
    maximum_queue_depth: int
    realtime_packets: int
    normalized_trades: int
    normalization_errors: int
    normalization_error_messages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RealtimePipelineResult:
    """Immutable result of one bounded demo pipeline run."""

    baseline_summary: Mapping[str, Any]
    trades: tuple[NormalizedTrade, ...]
    metrics: RealtimePipelineMetrics


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def run_demo_trade_pipeline(
    stk_cd: str = "005930",
    *,
    realtime_type: str = "0B",
    duration_seconds: float = 10.0,
    max_messages: int = 3,
    queue_maxsize: int = 100,
    clock: Callable[[], datetime] | None = None,
) -> RealtimePipelineResult:
    """Receive REAL packets and normalize 0B trades through one queue."""

    if isinstance(queue_maxsize, bool) or not isinstance(
        queue_maxsize,
        int,
    ):
        raise TypeError("queue_maxsize must be an integer.")

    if queue_maxsize <= 0:
        raise ValueError(
            "queue_maxsize must be greater than zero."
        )

    if clock is not None and not callable(clock):
        raise TypeError("clock must be callable.")

    clock_fn = clock or _utc_now
    queue: asyncio.Queue[object] = asyncio.Queue(
        maxsize=queue_maxsize
    )

    trades: list[NormalizedTrade] = []
    normalization_error_messages: list[str] = []

    realtime_packets = 0
    normalization_errors = 0
    maximum_queue_depth = 0

    async def enqueue_realtime(message: Any) -> None:
        nonlocal realtime_packets
        nonlocal maximum_queue_depth

        if not isinstance(message, Mapping):
            raise TypeError(
                "realtime message must be a mapping."
            )

        received_at = clock_fn()
        await queue.put((message, received_at))

        realtime_packets += 1
        maximum_queue_depth = max(
            maximum_queue_depth,
            queue.qsize(),
        )

    async def consume() -> None:
        nonlocal normalization_errors

        while True:
            item = await queue.get()

            try:
                if item is _STOP:
                    return

                payload, received_at = item

                try:
                    normalized = normalize_trade_packet(
                        payload,
                        received_at=received_at,
                    )
                except TradeNormalizationError as exc:
                    normalization_errors += 1
                    normalization_error_messages.append(
                        str(exc)
                    )
                    continue

                trades.extend(normalized)
            finally:
                queue.task_done()

    async def produce() -> dict[str, Any]:
        try:
            return await run_demo_realtime_baseline(
                stk_cd,
                realtime_type=realtime_type,
                duration_seconds=duration_seconds,
                max_messages=max_messages,
                on_realtime_message=enqueue_realtime,
            )
        finally:
            await queue.put(_STOP)

    async with asyncio.TaskGroup() as task_group:
        producer_task = task_group.create_task(
            produce(),
            name="kiwoom-realtime-producer",
        )
        task_group.create_task(
            consume(),
            name="kiwoom-trade-normalizer",
        )

    await queue.join()
    baseline_summary = producer_task.result()

    metrics = RealtimePipelineMetrics(
        queue_capacity=queue_maxsize,
        maximum_queue_depth=maximum_queue_depth,
        realtime_packets=realtime_packets,
        normalized_trades=len(trades),
        normalization_errors=normalization_errors,
        normalization_error_messages=tuple(
            normalization_error_messages
        ),
    )

    return RealtimePipelineResult(
        baseline_summary=MappingProxyType(
            dict(baseline_summary)
        ),
        trades=tuple(trades),
        metrics=metrics,
    )
