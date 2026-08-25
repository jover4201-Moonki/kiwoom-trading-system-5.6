from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType
from unittest.mock import AsyncMock, patch

from kiwoom_trading_system.market_data.realtime_pipeline import (
    RealtimePipelineMetrics,
    RealtimePipelineResult,
)
from kiwoom_trading_system.market_data.realtime_trade import (
    MarketVenue,
    normalize_trade_entry,
)
from kiwoom_trading_system.state import realtime_trade_state_pipeline


class RealtimeTradeStatePipelineTests(
    unittest.IsolatedAsyncioTestCase
):
    def test_single_market_state_is_accumulated(self) -> None:
        pipeline_result = _pipeline_result(
            _make_trade(
                time="090000",
                price="+100",
                volume="+3",
            ),
            _make_trade(
                time="090001",
                price="+110",
                volume="-2",
            ),
            _make_trade(
                time="090002",
                price="+90",
                volume="0",
            ),
        )

        result = (
            realtime_trade_state_pipeline
            .aggregate_realtime_trade_states(pipeline_result)
        )
        state = result.states[
            ("005930", MarketVenue.KRX)
        ]

        self.assertIs(result.pipeline_result, pipeline_result)
        self.assertEqual(state.trade_count, 3)
        self.assertEqual(state.high_price_krw, 110)
        self.assertEqual(state.low_price_krw, 90)
        self.assertEqual(state.total_trade_volume, 5)
        self.assertEqual(state.net_aggressor_volume, 1)
        self.assertEqual(state.observed_trade_value_krw, 520)
        self.assertEqual(
            state.volume_weighted_average_price_krw,
            Decimal("104"),
        )
        self.assertEqual(result.metrics.state_updates, 3)
        self.assertEqual(result.metrics.state_errors, 0)

    def test_instruments_and_venues_are_separated(self) -> None:
        result = (
            realtime_trade_state_pipeline
            .aggregate_realtime_trade_states(
                _pipeline_result(
                    _make_trade(item="005930"),
                    _make_trade(
                        time="090001",
                        item="005930_NX",
                    ),
                    _make_trade(
                        time="090002",
                        item="000660",
                    ),
                )
            )
        )

        self.assertEqual(
            set(result.states),
            {
                ("005930", MarketVenue.KRX),
                ("005930", MarketVenue.NXT),
                ("000660", MarketVenue.KRX),
            },
        )
        self.assertEqual(
            result.states[
                ("005930", MarketVenue.KRX)
            ].trade_count,
            1,
        )
        self.assertEqual(
            result.states[
                ("005930", MarketVenue.NXT)
            ].trade_count,
            1,
        )

    def test_state_error_is_isolated_and_counted(self) -> None:
        result = (
            realtime_trade_state_pipeline
            .aggregate_realtime_trade_states(
                _pipeline_result(
                    _make_trade(time="090001"),
                    _make_trade(time="090000"),
                    _make_trade(
                        time="090002",
                        volume="-1",
                    ),
                )
            )
        )
        state = result.states[
            ("005930", MarketVenue.KRX)
        ]

        self.assertEqual(state.trade_count, 2)
        self.assertEqual(result.metrics.state_updates, 2)
        self.assertEqual(result.metrics.state_errors, 1)
        self.assertEqual(
            len(result.metrics.state_error_messages),
            1,
        )
        self.assertIn(
            "older",
            result.metrics.state_error_messages[0],
        )

    def test_unexpected_exception_is_propagated(self) -> None:
        pipeline_result = _pipeline_result(_make_trade())

        with patch.object(
            realtime_trade_state_pipeline,
            "update_realtime_trade_state",
            side_effect=RuntimeError("unexpected"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "unexpected",
            ):
                (
                    realtime_trade_state_pipeline
                    .aggregate_realtime_trade_states(
                        pipeline_result
                    )
                )

    def test_result_mapping_is_read_only_and_input_unchanged(
        self,
    ) -> None:
        trade = _make_trade()
        pipeline_result = _pipeline_result(trade)
        original_trades = pipeline_result.trades

        result = (
            realtime_trade_state_pipeline
            .aggregate_realtime_trade_states(pipeline_result)
        )
        key = ("005930", MarketVenue.KRX)

        self.assertIs(
            pipeline_result.trades,
            original_trades,
        )
        self.assertIs(pipeline_result.trades[0], trade)

        with self.assertRaises(TypeError):
            result.states[key] = result.states[key]

    async def test_demo_runner_result_is_reused(self) -> None:
        pipeline_result = _pipeline_result(_make_trade())
        runner = AsyncMock(return_value=pipeline_result)

        with patch.object(
            realtime_trade_state_pipeline,
            "run_demo_trade_pipeline",
            new=runner,
        ):
            result = await (
                realtime_trade_state_pipeline
                .run_demo_trade_state_pipeline(
                    "005930",
                    realtime_type="0B",
                    duration_seconds=1.0,
                    max_messages=2,
                    queue_maxsize=3,
                )
            )

        runner.assert_awaited_once_with(
            "005930",
            realtime_type="0B",
            duration_seconds=1.0,
            max_messages=2,
            queue_maxsize=3,
            clock=None,
        )
        self.assertIs(result.pipeline_result, pipeline_result)
        self.assertEqual(result.metrics.state_updates, 1)


def _pipeline_result(*trades) -> RealtimePipelineResult:
    return RealtimePipelineResult(
        baseline_summary=MappingProxyType(
            {
                "mode": "demo",
                "closed": True,
            }
        ),
        trades=tuple(trades),
        metrics=RealtimePipelineMetrics(
            queue_capacity=10,
            maximum_queue_depth=1 if trades else 0,
            realtime_packets=len(trades),
            normalized_trades=len(trades),
            normalization_errors=0,
            normalization_error_messages=(),
        ),
    )


def _make_trade(
    *,
    time: str = "090000",
    price: str = "+100",
    volume: str = "+1",
    item: str = "005930",
):
    return normalize_trade_entry(
        {
            "type": "0B",
            "name": "stock trade",
            "item": item,
            "values": {
                "20": time,
                "10": price,
                "15": volume,
            },
        },
        received_at=datetime(
            2026,
            8,
            25,
            tzinfo=UTC,
        ),
    )


if __name__ == "__main__":
    unittest.main()
