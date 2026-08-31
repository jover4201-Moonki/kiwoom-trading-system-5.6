from __future__ import annotations

import asyncio
import copy
import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import kiwoom_trading_system.state as state_package
from kiwoom_trading_system.brokers.kiwoom.websocket import (
    WatchlistRecoveryExhaustedError,
)
from kiwoom_trading_system.market_data.realtime_trade import MarketVenue
from kiwoom_trading_system.screening import (
    RealtimeWatchCandidate,
    RealtimeWatchlist,
    RealtimeWatchlistMetrics,
)
from kiwoom_trading_system.state import (
    watchlist_recovery_state_pipeline as pipeline,
)


NOW = datetime(2026, 8, 31, tzinfo=UTC)


def _watchlist(*stock_codes: str) -> RealtimeWatchlist:
    candidates = tuple(
        RealtimeWatchCandidate(
            source_rank=index,
            stock_code=stock_code,
            stock_name=f"stock-{index}",
            exchange_scope="0",
        )
        for index, stock_code in enumerate(stock_codes, start=1)
    )
    return RealtimeWatchlist(
        candidates=candidates,
        metrics=RealtimeWatchlistMetrics(
            input_candidate_count=len(candidates),
            accepted_candidate_count=len(candidates),
            invalid_code_count=0,
            duplicate_code_count=0,
        ),
    )


def _entry(
    *,
    item: str = "005930",
    time: str = "090000",
    price: str = "+100",
    volume: str = "+1",
    realtime_type: str = "0B",
):
    return {
        "type": realtime_type,
        "name": "stock trade",
        "item": item,
        "values": {
            "20": time,
            "10": price,
            "15": volume,
        },
    }


def _packet(*entries):
    return {"trnm": "REAL", "data": list(entries)}


async def _run_packets(callback, packets, summary=None):
    for packet in packets:
        await callback(packet)
    return dict(summary or {"mode": "demo", "closed": True})


class WatchlistRecoveryStatePipelineTests(
    unittest.IsolatedAsyncioTestCase
):
    async def test_valid_packets_are_normalized_and_accumulated(self):
        packets = [
            _packet(
                _entry(time="090000", price="+100", volume="+3"),
                _entry(time="090001", price="+110", volume="-2"),
            )
        ]

        async def runner(watchlist, **kwargs):
            return await _run_packets(
                kwargs["on_realtime_message"],
                packets,
            )

        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            result = await (
                pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930"),
                    clock=lambda: NOW,
                )
            )

        state = result.states[("005930", MarketVenue.KRX)]
        self.assertEqual(state.trade_count, 2)
        self.assertEqual(state.total_trade_volume, 5)
        self.assertEqual(state.net_aggressor_volume, 1)
        self.assertEqual(result.metrics.realtime_packets, 1)
        self.assertEqual(result.metrics.normalized_trades, 2)
        self.assertEqual(result.metrics.state_updates, 2)

    async def test_instruments_and_venues_are_separated(self):
        packet = _packet(
            _entry(item="005930"),
            _entry(item="005930_NX", time="090001"),
            _entry(item="000660", time="090002"),
            _entry(item="005930_AL", time="090003"),
        )

        async def runner(watchlist, **kwargs):
            return await _run_packets(
                kwargs["on_realtime_message"],
                [packet],
            )

        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            result = await (
                pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930", "000660"),
                    clock=lambda: NOW,
                )
            )

        self.assertEqual(
            set(result.states),
            {
                ("005930", MarketVenue.KRX),
                ("005930", MarketVenue.NXT),
                ("000660", MarketVenue.KRX),
                ("005930", MarketVenue.SOR),
            },
        )

    async def test_normalization_error_is_isolated(self):
        packets = [
            {"trnm": "REAL", "data": "invalid"},
            _packet(_entry()),
        ]

        async def runner(watchlist, **kwargs):
            return await _run_packets(
                kwargs["on_realtime_message"],
                packets,
            )

        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            result = await (
                pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930"),
                    clock=lambda: NOW,
                )
            )

        self.assertEqual(result.metrics.realtime_packets, 2)
        self.assertEqual(result.metrics.normalization_errors, 1)
        self.assertEqual(len(result.metrics.normalization_error_messages), 1)
        self.assertEqual(result.metrics.state_updates, 1)

    async def test_nontrade_real_packet_produces_no_state(self):
        async def runner(watchlist, **kwargs):
            return await _run_packets(
                kwargs["on_realtime_message"],
                [_packet(_entry(realtime_type="0A"))],
            )

        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            result = await (
                pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930"),
                    clock=lambda: NOW,
                )
            )

        self.assertEqual(dict(result.states), {})
        self.assertEqual(result.metrics.realtime_packets, 1)
        self.assertEqual(result.metrics.normalized_trades, 0)
        self.assertEqual(result.metrics.normalization_errors, 0)

    async def test_state_error_is_isolated(self):
        packets = [
            _packet(_entry(time="090001")),
            _packet(_entry(time="090000")),
            _packet(_entry(time="090002", volume="-2")),
        ]

        async def runner(watchlist, **kwargs):
            return await _run_packets(
                kwargs["on_realtime_message"],
                packets,
            )

        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            result = await (
                pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930"),
                    clock=lambda: NOW,
                )
            )

        state = result.states[("005930", MarketVenue.KRX)]
        self.assertEqual(state.trade_count, 2)
        self.assertEqual(result.metrics.normalized_trades, 3)
        self.assertEqual(result.metrics.state_updates, 2)
        self.assertEqual(result.metrics.state_errors, 1)
        self.assertIn("older", result.metrics.state_error_messages[0])

    async def test_result_is_immutable_and_input_is_unchanged(self):
        watchlist = _watchlist("005930")
        original_watchlist = copy.deepcopy(watchlist)
        summary = {"mode": "demo", "closed": True}

        async def runner(candidate, **kwargs):
            self.assertIs(candidate, watchlist)
            return await _run_packets(
                kwargs["on_realtime_message"],
                [_packet(_entry())],
                summary,
            )

        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            result = await (
                pipeline.run_demo_watchlist_recovery_state_pipeline(
                    watchlist,
                    clock=lambda: NOW,
                )
            )

        summary["mode"] = "changed"
        self.assertEqual(watchlist, original_watchlist)
        self.assertEqual(result.baseline_summary["mode"], "demo")
        with self.assertRaises(TypeError):
            result.baseline_summary["mode"] = "changed"
        with self.assertRaises(TypeError):
            result.states[("005930", MarketVenue.KRX)] = None

    async def test_options_and_clock_are_forwarded(self):
        watchlist = _watchlist("005930")
        runner = AsyncMock(return_value={"mode": "demo"})
        clock = lambda: NOW
        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            result = await (
                pipeline.run_demo_watchlist_recovery_state_pipeline(
                    watchlist,
                    duration_seconds=1.5,
                    max_realtime_messages=4,
                    max_reconnect_attempts=3,
                    initial_backoff_seconds=0.1,
                    max_backoff_seconds=0.8,
                    clock=clock,
                )
            )

        runner.assert_awaited_once()
        args, kwargs = runner.await_args
        self.assertEqual(args, (watchlist,))
        callback = kwargs.pop("on_realtime_message")
        self.assertTrue(callable(callback))
        self.assertEqual(
            kwargs,
            {
                "duration_seconds": 1.5,
                "max_realtime_messages": 4,
                "max_reconnect_attempts": 3,
                "initial_backoff_seconds": 0.1,
                "max_backoff_seconds": 0.8,
            },
        )
        self.assertEqual(dict(result.states), {})

    async def test_invalid_clock_fails_before_recovery_runner(self):
        runner = AsyncMock()
        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            with self.assertRaisesRegex(TypeError, "clock"):
                await pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930"),
                    clock=object(),
                )

        runner.assert_not_awaited()

    async def test_recovery_exhaustion_is_propagated(self):
        error = WatchlistRecoveryExhaustedError(
            2,
            EOFError("ended"),
            {"retry_exhausted": True},
        )
        runner = AsyncMock(side_effect=error)
        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            with self.assertRaises(
                WatchlistRecoveryExhaustedError
            ) as raised:
                await pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930")
                )

        self.assertIs(raised.exception, error)

    async def test_timeout_is_propagated(self):
        runner = AsyncMock(side_effect=TimeoutError("deadline"))
        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            with self.assertRaisesRegex(TimeoutError, "deadline"):
                await pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930")
                )

    async def test_cancellation_is_propagated(self):
        runner = AsyncMock(side_effect=asyncio.CancelledError())
        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            with self.assertRaises(asyncio.CancelledError):
                await pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930")
                )

    async def test_unexpected_normalizer_error_is_propagated(self):
        async def runner(watchlist, **kwargs):
            return await _run_packets(
                kwargs["on_realtime_message"],
                [_packet(_entry())],
            )

        with (
            patch.object(
                pipeline,
                "run_demo_watchlist_recovery_baseline",
                new=runner,
            ),
            patch.object(
                pipeline,
                "normalize_trade_packet",
                side_effect=RuntimeError("normalizer failed"),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "normalizer failed",
            ):
                await pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930"),
                    clock=lambda: NOW,
                )

    async def test_unexpected_updater_error_is_propagated(self):
        async def runner(watchlist, **kwargs):
            return await _run_packets(
                kwargs["on_realtime_message"],
                [_packet(_entry())],
            )

        with (
            patch.object(
                pipeline,
                "run_demo_watchlist_recovery_baseline",
                new=runner,
            ),
            patch.object(
                pipeline,
                "update_realtime_trade_state",
                side_effect=RuntimeError("updater failed"),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "updater failed",
            ):
                await pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930"),
                    clock=lambda: NOW,
                )

    async def test_expected_metrics_sequences_are_immutable(self):
        async def runner(watchlist, **kwargs):
            return await _run_packets(
                kwargs["on_realtime_message"],
                [{"trnm": "REAL", "data": "invalid"}],
            )

        with patch.object(
            pipeline,
            "run_demo_watchlist_recovery_baseline",
            new=runner,
        ):
            result = await (
                pipeline.run_demo_watchlist_recovery_state_pipeline(
                    _watchlist("005930"),
                    clock=lambda: NOW,
                )
            )

        self.assertIsInstance(
            result.metrics.normalization_error_messages,
            tuple,
        )
        self.assertIsInstance(result.metrics.state_error_messages, tuple)

    def test_public_exports_reference_pipeline_objects(self):
        self.assertIs(
            state_package.WatchlistRecoveryStatePipelineResult,
            pipeline.WatchlistRecoveryStatePipelineResult,
        )
        self.assertIs(
            state_package.run_demo_watchlist_recovery_state_pipeline,
            pipeline.run_demo_watchlist_recovery_state_pipeline,
        )


if __name__ == "__main__":
    unittest.main()
