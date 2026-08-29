import asyncio
import unittest
from unittest.mock import patch

import kiwoom_trading_system.brokers.kiwoom.websocket as websocket_package
from kiwoom_trading_system.brokers.kiwoom.websocket import (
    watchlist_baseline as baseline,
)
from kiwoom_trading_system.brokers.kiwoom.websocket.demo_baseline import (
    RealtimeResponseError,
)
from kiwoom_trading_system.screening import (
    RealtimeWatchCandidate,
    RealtimeWatchlist,
    RealtimeWatchlistMetrics,
)


def _watchlist(
    *stock_codes: str,
    realtime_type: str = "0B",
) -> RealtimeWatchlist:
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
        realtime_type=realtime_type,
    )


class FakeWebSocketClient:
    def __init__(
        self,
        messages=(),
        *,
        send_error: Exception | None = None,
    ):
        self.messages = tuple(messages)
        self.send_error = send_error
        self.is_connected = False
        self.connect_calls = []
        self.sent_packets = []
        self.close_calls = 0

    async def connect(self, *, api_url: str) -> None:
        self.connect_calls.append(api_url)
        self.is_connected = True

    async def send(self, packet) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent_packets.append(packet)

    async def iter_messages(self):
        for message in self.messages:
            yield message

    async def close(self) -> None:
        self.close_calls += 1
        self.is_connected = False


class HangingWebSocketClient(FakeWebSocketClient):
    async def iter_messages(self):
        await asyncio.Event().wait()
        if False:
            yield None


class DemoWatchlistBaselineTests(unittest.IsolatedAsyncioTestCase):
    async def test_multiple_items_registration_receive_and_close(self):
        client = FakeWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL", "data": [{"item": "035420"}]},
            ]
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            summary = await baseline.run_demo_watchlist_realtime_baseline(
                _watchlist("035420", "005930"),
                duration_seconds=1.0,
                max_messages=2,
            )

        self.assertEqual(client.connect_calls, [baseline.API_URL])
        self.assertEqual(
            client.sent_packets,
            [
                {
                    "trnm": "REG",
                    "grp_no": "1",
                    "refresh": "1",
                    "data": [
                        {
                            "item": ["035420", "005930"],
                            "type": ["0B"],
                        }
                    ],
                }
            ],
        )
        self.assertEqual(
            summary["stock_codes"],
            ("035420", "005930"),
        )
        self.assertEqual(summary["registered_item_count"], 2)
        self.assertEqual(summary["messages_received"], 2)
        self.assertEqual(summary["realtime_messages"], 1)
        self.assertEqual(summary["system_messages"], 1)
        self.assertEqual(summary["message_types"], ["REG", "REAL"])
        self.assertTrue(summary["registration_acknowledged"])
        self.assertFalse(summary["timed_out"])
        self.assertTrue(summary["closed"])
        self.assertEqual(client.close_calls, 1)

    async def test_realtime_handler_receives_only_real(self):
        messages = [
            {"trnm": "PING"},
            {"trnm": "REAL", "data": [{"item": "005930"}]},
        ]
        client = FakeWebSocketClient(messages)
        handled = []

        async def handle(message):
            handled.append(message)

        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            await baseline.run_demo_watchlist_realtime_baseline(
                _watchlist("005930"),
                duration_seconds=1.0,
                max_messages=2,
                on_realtime_message=handle,
            )

        self.assertEqual(handled, [messages[1]])

    async def test_empty_watchlist_is_rejected_before_environment(self):
        with patch.object(
            baseline,
            "ensure_demo_websocket_environment",
        ) as environment:
            with self.assertRaises(
                baseline.EmptyRealtimeWatchlistError
            ):
                await baseline.run_demo_watchlist_realtime_baseline(
                    _watchlist()
                )
        environment.assert_not_called()

    async def test_non_watchlist_is_rejected_before_environment(self):
        with patch.object(
            baseline,
            "ensure_demo_websocket_environment",
        ) as environment:
            with self.assertRaises(TypeError):
                await baseline.run_demo_watchlist_realtime_baseline(
                    object()
                )
        environment.assert_not_called()

    async def test_non_default_type_is_rejected_before_environment(self):
        with patch.object(
            baseline,
            "ensure_demo_websocket_environment",
        ) as environment:
            with self.assertRaises(ValueError):
                await baseline.run_demo_watchlist_realtime_baseline(
                    _watchlist("005930", realtime_type="0C")
                )
        environment.assert_not_called()

    async def test_timeout_closes_client(self):
        client = HangingWebSocketClient()
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            summary = await baseline.run_demo_watchlist_realtime_baseline(
                _watchlist("005930"),
                duration_seconds=0.01,
                max_messages=1,
            )

        self.assertTrue(summary["timed_out"])
        self.assertTrue(summary["closed"])
        self.assertEqual(client.close_calls, 1)

    async def test_failed_response_closes_client(self):
        client = FakeWebSocketClient(
            [
                {
                    "trnm": "REG",
                    "return_code": -100,
                    "return_msg": "failed",
                }
            ]
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaises(RealtimeResponseError):
                await baseline.run_demo_watchlist_realtime_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                    max_messages=1,
                )

        self.assertEqual(client.close_calls, 1)
        self.assertFalse(client.is_connected)

    async def test_send_error_closes_client(self):
        client = FakeWebSocketClient(
            send_error=RuntimeError("send failed")
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "send failed"):
                await baseline.run_demo_watchlist_realtime_baseline(
                    _watchlist("005930")
                )

        self.assertEqual(client.close_calls, 1)
        self.assertFalse(client.is_connected)

    async def test_invalid_limits_are_rejected_before_environment(self):
        invalid_cases = [
            ({"duration_seconds": True}, TypeError),
            ({"duration_seconds": 0}, ValueError),
            ({"max_messages": True}, TypeError),
            ({"max_messages": 0}, ValueError),
        ]
        for kwargs, expected_error in invalid_cases:
            with self.subTest(kwargs=kwargs):
                with patch.object(
                    baseline,
                    "ensure_demo_websocket_environment",
                ) as environment:
                    with self.assertRaises(expected_error):
                        await baseline.run_demo_watchlist_realtime_baseline(
                            _watchlist("005930"),
                            **kwargs,
                        )
                environment.assert_not_called()

    async def test_invalid_handler_is_rejected_before_environment(self):
        with patch.object(
            baseline,
            "ensure_demo_websocket_environment",
        ) as environment:
            with self.assertRaises(TypeError):
                await baseline.run_demo_watchlist_realtime_baseline(
                    _watchlist("005930"),
                    on_realtime_message=object(),
                )
        environment.assert_not_called()

    def test_baseline_decision_requires_complete_summary(self):
        summary = {
            "mode": "demo",
            "ws_base_url": baseline.DEMO_WS_BASE_URL,
            "registered_item_count": 2,
            "connected": True,
            "registration_sent": True,
            "registration_acknowledged": True,
            "closed": True,
        }
        self.assertTrue(
            baseline.demo_watchlist_baseline_passed(summary)
        )

        for key in tuple(summary):
            with self.subTest(key=key):
                incomplete = dict(summary)
                incomplete.pop(key)
                self.assertFalse(
                    baseline.demo_watchlist_baseline_passed(incomplete)
                )

    def test_public_package_exports_phase13_contract(self):
        self.assertIs(
            websocket_package.EmptyRealtimeWatchlistError,
            baseline.EmptyRealtimeWatchlistError,
        )
        self.assertIs(
            websocket_package.run_demo_watchlist_realtime_baseline,
            baseline.run_demo_watchlist_realtime_baseline,
        )
        self.assertIs(
            websocket_package.demo_watchlist_baseline_passed,
            baseline.demo_watchlist_baseline_passed,
        )


if __name__ == "__main__":
    unittest.main()
