from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from kiwoom_trading_system.market_data import realtime_pipeline


def trade_packet(
    *,
    price: str = "+20800",
    volume: str = "+82",
) -> dict:
    return {
        "trnm": "REAL",
        "data": [
            {
                "type": "0B",
                "name": "주식체결",
                "item": "005930",
                "values": {
                    "20": "165208",
                    "10": price,
                    "15": volume,
                },
            }
        ],
    }


class RealtimeTradePipelineTests(
    unittest.IsolatedAsyncioTestCase
):
    def setUp(self) -> None:
        self.received_at = datetime(
            2026,
            8,
            24,
            7,
            52,
            9,
            tzinfo=timezone.utc,
        )

    async def test_valid_packet_is_normalized(self) -> None:
        async def fake_runner(
            stk_cd,
            *,
            realtime_type,
            duration_seconds,
            max_messages,
            on_realtime_message,
        ):
            self.assertEqual(stk_cd, "005930")
            self.assertEqual(realtime_type, "0B")
            await on_realtime_message(trade_packet())
            return {
                "mode": "demo",
                "closed": True,
            }

        with patch.object(
            realtime_pipeline,
            "run_demo_realtime_baseline",
            new=fake_runner,
        ):
            result = (
                await realtime_pipeline.run_demo_trade_pipeline(
                    "005930",
                    queue_maxsize=1,
                    clock=lambda: self.received_at,
                )
            )

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(
            result.trades[0].instrument_code,
            "005930",
        )
        self.assertEqual(
            result.trades[0].price_krw,
            20800,
        )
        self.assertEqual(
            result.trades[0].source_name,
            "주식체결",
        )
        self.assertEqual(
            result.metrics.realtime_packets,
            1,
        )
        self.assertEqual(
            result.metrics.normalized_trades,
            1,
        )
        self.assertEqual(
            result.metrics.normalization_errors,
            0,
        )
        self.assertLessEqual(
            result.metrics.maximum_queue_depth,
            result.metrics.queue_capacity,
        )
        self.assertTrue(
            result.baseline_summary["closed"]
        )

        with self.assertRaises(TypeError):
            result.baseline_summary["closed"] = False

    async def test_normalization_error_is_isolated(
        self,
    ) -> None:
        async def fake_runner(
            stk_cd,
            *,
            realtime_type,
            duration_seconds,
            max_messages,
            on_realtime_message,
        ):
            await on_realtime_message(
                trade_packet(price="20,800")
            )
            await on_realtime_message(trade_packet())
            return {
                "mode": "demo",
                "closed": True,
            }

        with patch.object(
            realtime_pipeline,
            "run_demo_realtime_baseline",
            new=fake_runner,
        ):
            result = (
                await realtime_pipeline.run_demo_trade_pipeline(
                    queue_maxsize=1,
                    clock=lambda: self.received_at,
                )
            )

        self.assertEqual(
            result.metrics.realtime_packets,
            2,
        )
        self.assertEqual(
            result.metrics.normalization_errors,
            1,
        )
        self.assertEqual(
            result.metrics.normalized_trades,
            1,
        )
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(
            len(
                result.metrics
                .normalization_error_messages
            ),
            1,
        )

    async def test_non_trade_packet_returns_no_trade(
        self,
    ) -> None:
        async def fake_runner(
            stk_cd,
            *,
            realtime_type,
            duration_seconds,
            max_messages,
            on_realtime_message,
        ):
            await on_realtime_message(
                {
                    "trnm": "REAL",
                    "data": [
                        {
                            "type": "0C",
                            "item": "005930",
                            "values": {},
                        }
                    ],
                }
            )
            return {
                "mode": "demo",
                "closed": True,
            }

        with patch.object(
            realtime_pipeline,
            "run_demo_realtime_baseline",
            new=fake_runner,
        ):
            result = (
                await realtime_pipeline.run_demo_trade_pipeline(
                    queue_maxsize=1,
                    clock=lambda: self.received_at,
                )
            )

        self.assertEqual(result.trades, ())
        self.assertEqual(
            result.metrics.realtime_packets,
            1,
        )
        self.assertEqual(
            result.metrics.normalization_errors,
            0,
        )

    async def test_invalid_queue_size_is_rejected(
        self,
    ) -> None:
        for invalid in (0, -1):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    await realtime_pipeline.run_demo_trade_pipeline(
                        queue_maxsize=invalid,
                    )

        for invalid in (True, 1.5, "1"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(TypeError):
                    await realtime_pipeline.run_demo_trade_pipeline(
                        queue_maxsize=invalid,
                    )
