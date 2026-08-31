import asyncio
import copy
import unittest
from unittest.mock import AsyncMock, call, patch

from websockets.exceptions import ConnectionClosedError

import kiwoom_trading_system.brokers.kiwoom.websocket as websocket_package
from kiwoom_trading_system.brokers.kiwoom.websocket import (
    watchlist_recovery_baseline as recovery,
)
from kiwoom_trading_system.brokers.kiwoom.websocket.demo_baseline import (
    RealtimeResponseError,
)
from kiwoom_trading_system.screening import (
    RealtimeWatchCandidate,
    RealtimeWatchlist,
    RealtimeWatchlistMetrics,
)


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


class RecoveryWebSocketClient:
    def __init__(
        self,
        name: str,
        messages=(),
        *,
        connect_error: BaseException | None = None,
        stream_error: BaseException | None = None,
        send_errors=(),
        close_error: BaseException | None = None,
        hang_after_messages: bool = False,
        events: list[str] | None = None,
    ) -> None:
        self.name = name
        self.messages = tuple(messages)
        self.connect_error = connect_error
        self.stream_error = stream_error
        self.send_errors = tuple(send_errors)
        self.close_error = close_error
        self.hang_after_messages = hang_after_messages
        self.events = events if events is not None else []
        self.is_connected = False
        self.connect_calls: list[str] = []
        self.sent_packets = []
        self.send_calls = 0
        self.iter_messages_calls = 0
        self.close_calls = 0

    async def connect(self, *, api_url: str) -> None:
        self.events.append(f"{self.name}:connect")
        self.connect_calls.append(api_url)
        if self.connect_error is not None:
            raise self.connect_error
        self.is_connected = True

    async def send(self, packet) -> None:
        message_type = packet.get("trnm")
        self.events.append(f"{self.name}:send:{message_type}")
        call_index = self.send_calls
        self.send_calls += 1
        if call_index < len(self.send_errors):
            error = self.send_errors[call_index]
            if error is not None:
                raise error
        self.sent_packets.append(packet)

    async def iter_messages(self):
        self.iter_messages_calls += 1
        for message in self.messages:
            self.events.append(
                f"{self.name}:receive:{message.get('trnm')}"
            )
            yield message
        if self.stream_error is not None:
            raise self.stream_error
        if self.hang_after_messages:
            await asyncio.Event().wait()
            if False:
                yield None

    async def close(self) -> None:
        self.events.append(f"{self.name}:close")
        self.close_calls += 1
        self.is_connected = False
        if self.close_error is not None:
            raise self.close_error


class DemoWatchlistRecoveryBaselineTests(
    unittest.IsolatedAsyncioTestCase
):
    async def test_normal_stream_end_reconnects_and_reregisters(self):
        events: list[str] = []
        first = RecoveryWebSocketClient(
            "first",
            [{"trnm": "REG", "return_code": 0}],
            events=events,
        )
        second = RecoveryWebSocketClient(
            "second",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL", "data": [{"item": "005930"}]},
                {"trnm": "REMOVE", "return_code": 0},
            ],
            events=events,
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                side_effect=[first, second],
            ) as factory,
        ):
            summary = await recovery.run_demo_watchlist_recovery_baseline(
                _watchlist("005930"),
                duration_seconds=1.0,
                initial_backoff_seconds=0.0,
                max_backoff_seconds=0.0,
            )

        self.assertEqual(factory.call_count, 2)
        self.assertEqual(first.iter_messages_calls, 1)
        self.assertEqual(second.iter_messages_calls, 1)
        self.assertEqual(
            [packet["trnm"] for packet in first.sent_packets],
            ["REG"],
        )
        self.assertEqual(
            [packet["trnm"] for packet in second.sent_packets],
            ["REG", "REMOVE"],
        )
        self.assertEqual(summary["connection_attempts"], 2)
        self.assertEqual(summary["disconnects_detected"], 1)
        self.assertEqual(summary["reconnect_attempts"], 1)
        self.assertEqual(summary["reconnect_successes"], 1)
        self.assertEqual(summary["registrations_sent"], 2)
        self.assertEqual(summary["registrations_acknowledged"], 2)
        self.assertTrue(summary["reregistration_sent"])
        self.assertTrue(summary["reregistration_acknowledged"])
        self.assertTrue(summary["recovered"])
        self.assertTrue(summary["closed"])
        self.assertEqual(first.close_calls, 1)
        self.assertEqual(second.close_calls, 1)
        self.assertLess(
            events.index("second:connect"),
            events.index("second:send:REG"),
        )

    async def test_eof_recovery_preserves_cumulative_real_count(self):
        first = RecoveryWebSocketClient(
            "first",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "PING"},
                {"trnm": "REAL", "data": [{"item": "005930"}]},
            ],
            stream_error=EOFError("stream ended"),
        )
        second = RecoveryWebSocketClient(
            "second",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL", "data": [{"item": "000660"}]},
                {"trnm": "REMOVE", "return_code": 0},
            ],
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                side_effect=[first, second],
            ),
        ):
            summary = await recovery.run_demo_watchlist_recovery_baseline(
                _watchlist("005930", "000660"),
                duration_seconds=1.0,
                max_realtime_messages=2,
                initial_backoff_seconds=0.0,
                max_backoff_seconds=0.0,
            )

        self.assertEqual(summary["realtime_messages"], 2)
        self.assertEqual(summary["system_messages"], 4)
        self.assertEqual(summary["message_types"], ["REG", "PING", "REAL", "REMOVE"])
        self.assertTrue(
            recovery.demo_watchlist_recovery_baseline_passed(summary)
        )

    async def test_connection_closed_error_is_recoverable(self):
        first = RecoveryWebSocketClient(
            "first",
            [{"trnm": "REG", "return_code": 0}],
            stream_error=ConnectionClosedError(None, None),
        )
        second = RecoveryWebSocketClient(
            "second",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": 0},
            ],
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                side_effect=[first, second],
            ),
        ):
            summary = await recovery.run_demo_watchlist_recovery_baseline(
                _watchlist("005930"),
                duration_seconds=1.0,
                initial_backoff_seconds=0.0,
                max_backoff_seconds=0.0,
            )

        self.assertTrue(summary["recovered"])
        self.assertEqual(summary["disconnects_detected"], 1)

    async def test_connect_failures_use_bounded_exponential_backoff(self):
        first = RecoveryWebSocketClient(
            "first",
            connect_error=TimeoutError("connect timed out"),
        )
        second = RecoveryWebSocketClient("second")
        third = RecoveryWebSocketClient(
            "third",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": 0},
            ],
        )
        sleep = AsyncMock()
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                side_effect=[first, second, third],
            ),
            patch.object(recovery.asyncio, "sleep", sleep),
        ):
            summary = await recovery.run_demo_watchlist_recovery_baseline(
                _watchlist("005930"),
                duration_seconds=1.0,
                max_reconnect_attempts=2,
                initial_backoff_seconds=0.25,
                max_backoff_seconds=0.5,
            )

        self.assertEqual(sleep.await_args_list, [call(0.25), call(0.5)])
        self.assertEqual(summary["connection_failures"], 1)
        self.assertEqual(summary["disconnects_detected"], 1)
        self.assertEqual(summary["connection_attempts"], 3)
        self.assertEqual(summary["reconnect_attempts"], 2)
        self.assertEqual(summary["reconnect_successes"], 2)

    async def test_retry_exhaustion_raises_and_closes_every_client(self):
        first = RecoveryWebSocketClient("first")
        second = RecoveryWebSocketClient("second")
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                side_effect=[first, second],
            ),
        ):
            with self.assertRaises(
                recovery.WatchlistRecoveryExhaustedError
            ) as raised:
                await recovery.run_demo_watchlist_recovery_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                    max_reconnect_attempts=1,
                    initial_backoff_seconds=0.0,
                    max_backoff_seconds=0.0,
                )

        self.assertEqual(raised.exception.attempts, 2)
        self.assertTrue(raised.exception.summary["retry_exhausted"])
        self.assertTrue(raised.exception.summary["closed"])
        self.assertEqual(first.close_calls, 1)
        self.assertEqual(second.close_calls, 1)

    async def test_timeout_is_not_retried_and_closes(self):
        client = RecoveryWebSocketClient(
            "only",
            [{"trnm": "REG", "return_code": 0}],
            hang_after_messages=True,
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                return_value=client,
            ) as factory,
        ):
            with self.assertRaises(TimeoutError):
                await recovery.run_demo_watchlist_recovery_baseline(
                    _watchlist("005930"),
                    duration_seconds=0.01,
                )

        self.assertEqual(factory.call_count, 1)
        self.assertEqual(client.close_calls, 1)

    async def test_cancellation_is_propagated_after_cleanup(self):
        client = RecoveryWebSocketClient(
            "only",
            [{"trnm": "REG", "return_code": 0}],
            hang_after_messages=True,
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(recovery, "get_ws_client", return_value=client),
        ):
            task = asyncio.create_task(
                recovery.run_demo_watchlist_recovery_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                )
            )
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertEqual(client.close_calls, 1)
        self.assertFalse(client.is_connected)

    async def test_server_failure_is_fatal_and_not_retried(self):
        client = RecoveryWebSocketClient(
            "only",
            [{"trnm": "REG", "return_code": -100, "return_msg": "failed"}],
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                return_value=client,
            ) as factory,
        ):
            with self.assertRaises(RealtimeResponseError):
                await recovery.run_demo_watchlist_recovery_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                )

        self.assertEqual(factory.call_count, 1)
        self.assertEqual(client.close_calls, 1)

    async def test_disconnect_after_remove_is_not_reregistered(self):
        client = RecoveryWebSocketClient(
            "only",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
            ],
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                return_value=client,
            ) as factory,
        ):
            with self.assertRaises(StopAsyncIteration):
                await recovery.run_demo_watchlist_recovery_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                )

        self.assertEqual(factory.call_count, 1)
        self.assertEqual(
            [packet["trnm"] for packet in client.sent_packets],
            ["REG", "REMOVE"],
        )
        self.assertEqual(client.close_calls, 1)

    async def test_invalid_options_fail_before_environment_or_client(self):
        invalid_options = (
            ({"duration_seconds": True}, TypeError),
            ({"duration_seconds": 0}, ValueError),
            ({"duration_seconds": float("nan")}, ValueError),
            ({"duration_seconds": float("inf")}, ValueError),
            ({"max_realtime_messages": True}, TypeError),
            ({"max_realtime_messages": 0}, ValueError),
            ({"max_reconnect_attempts": True}, TypeError),
            ({"max_reconnect_attempts": -1}, ValueError),
            ({"initial_backoff_seconds": True}, TypeError),
            ({"initial_backoff_seconds": -1}, ValueError),
            ({"initial_backoff_seconds": float("nan")}, ValueError),
            ({"max_backoff_seconds": float("inf")}, ValueError),
            (
                {
                    "initial_backoff_seconds": 1.0,
                    "max_backoff_seconds": 0.5,
                },
                ValueError,
            ),
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
            ) as environment,
            patch.object(recovery, "get_ws_client") as factory,
        ):
            for options, error_type in invalid_options:
                with self.subTest(options=options):
                    with self.assertRaises(error_type):
                        await recovery.run_demo_watchlist_recovery_baseline(
                            _watchlist("005930"),
                            **options,
                        )

        environment.assert_not_called()
        factory.assert_not_called()

    async def test_empty_watchlist_fails_before_environment_or_client(self):
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
            ) as environment,
            patch.object(recovery, "get_ws_client") as factory,
        ):
            with self.assertRaises(ValueError):
                await recovery.run_demo_watchlist_recovery_baseline(
                    _watchlist(),
                )

        environment.assert_not_called()
        factory.assert_not_called()

    async def test_watchlist_and_request_objects_are_not_mutated(self):
        watchlist = _watchlist("005930", "000660")
        original = copy.deepcopy(watchlist)
        registration = {"trnm": "REG", "data": [{"item": ["005930"]}]}
        unregistration = {
            "trnm": "REMOVE",
            "data": [{"item": ["005930"]}],
        }
        client = RecoveryWebSocketClient(
            "only",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": 0},
            ],
        )
        with (
            patch.object(
                recovery,
                "build_demo_watchlist_registration_request",
                return_value=registration,
            ),
            patch.object(
                recovery,
                "build_demo_watchlist_unregistration_request",
                return_value=unregistration,
            ),
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(recovery, "get_ws_client", return_value=client),
        ):
            await recovery.run_demo_watchlist_recovery_baseline(
                watchlist,
                duration_seconds=1.0,
            )

        self.assertEqual(watchlist, original)
        self.assertIs(client.sent_packets[0], registration)
        self.assertIs(client.sent_packets[1], unregistration)
        self.assertEqual(registration["data"][0]["item"], ["005930"])
        self.assertEqual(unregistration["data"][0]["item"], ["005930"])

    async def test_close_error_is_propagated_without_retry(self):
        client = RecoveryWebSocketClient(
            "only",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": 0},
            ],
            close_error=RuntimeError("close failed"),
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(
                recovery,
                "get_ws_client",
                return_value=client,
            ) as factory,
        ):
            with self.assertRaisesRegex(RuntimeError, "close failed"):
                await recovery.run_demo_watchlist_recovery_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                )

        self.assertEqual(factory.call_count, 1)
        self.assertEqual(client.close_calls, 1)

    async def test_uninterrupted_summary_passes_and_exports_are_public(self):
        client = RecoveryWebSocketClient(
            "only",
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "PING"},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": 0},
            ],
        )
        with (
            patch.object(
                recovery,
                "ensure_demo_websocket_environment",
                return_value=("demo", recovery.DEMO_WS_BASE_URL),
            ),
            patch.object(recovery, "get_ws_client", return_value=client),
        ):
            summary = await recovery.run_demo_watchlist_recovery_baseline(
                _watchlist("005930"),
                duration_seconds=1.0,
            )

        self.assertFalse(summary["recovered"])
        self.assertEqual(summary["reconnect_attempts"], 0)
        self.assertEqual(summary["system_messages"], 3)
        self.assertTrue(
            recovery.demo_watchlist_recovery_baseline_passed(summary)
        )
        self.assertIs(
            websocket_package.run_demo_watchlist_recovery_baseline,
            recovery.run_demo_watchlist_recovery_baseline,
        )
        self.assertIs(
            websocket_package.WatchlistRecoveryExhaustedError,
            recovery.WatchlistRecoveryExhaustedError,
        )


if __name__ == "__main__":
    unittest.main()
