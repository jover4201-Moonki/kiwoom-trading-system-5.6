import asyncio
import copy
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
        connect_error: Exception | None = None,
        send_error: Exception | None = None,
        close_error: Exception | None = None,
    ):
        self.messages = tuple(messages)
        self.connect_error = connect_error
        self.send_error = send_error
        self.close_error = close_error
        self.is_connected = False
        self.connect_calls = []
        self.sent_packets = []
        self.close_calls = 0

    async def connect(self, *, api_url: str) -> None:
        self.connect_calls.append(api_url)
        if self.connect_error is not None:
            raise self.connect_error
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
        if self.close_error is not None:
            raise self.close_error


class HangingWebSocketClient(FakeWebSocketClient):
    async def iter_messages(self):
        await asyncio.Event().wait()
        if False:
            yield None




class LifecycleWebSocketClient(FakeWebSocketClient):
    def __init__(
        self,
        messages=(),
        *,
        connect_error: Exception | None = None,
        send_errors=(),
        close_error: Exception | None = None,
        hang_after_messages: bool = False,
    ):
        super().__init__(
            messages,
            connect_error=connect_error,
            close_error=close_error,
        )
        self.send_errors = tuple(send_errors)
        self.hang_after_messages = hang_after_messages
        self.send_calls = 0
        self.iter_messages_calls = 0
        self.events = []

    async def connect(self, *, api_url: str) -> None:
        self.events.append("connect")
        await super().connect(api_url=api_url)

    async def send(self, packet) -> None:
        self.events.append(f"send:{packet.get('trnm')}")
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
            self.events.append(f"receive:{message.get('trnm')}")
            yield message
        if self.hang_after_messages:
            await asyncio.Event().wait()
            if False:
                yield None

    async def close(self) -> None:
        self.events.append("close")
        await super().close()


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

    async def test_unregistration_success_sends_remove_and_closes(self):
        client = FakeWebSocketClient(
            [{"trnm": "REMOVE", "return_code": 0}]
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            summary = (
                await baseline.run_demo_watchlist_unregistration_baseline(
                    _watchlist("035420", "005930"),
                    duration_seconds=1.0,
                    max_messages=1,
                )
            )

        self.assertEqual(client.connect_calls, [baseline.API_URL])
        self.assertEqual(
            client.sent_packets,
            [
                {
                    "trnm": "REMOVE",
                    "grp_no": "1",
                    "data": [
                        {
                            "item": ["035420", "005930"],
                            "type": ["0B"],
                        }
                    ],
                }
            ],
        )
        self.assertEqual(summary["stock_codes"], ("035420", "005930"))
        self.assertEqual(summary["unregistered_item_count"], 2)
        self.assertEqual(summary["messages_received"], 1)
        self.assertEqual(summary["realtime_messages"], 0)
        self.assertEqual(summary["system_messages"], 1)
        self.assertEqual(summary["message_types"], ["REMOVE"])
        self.assertTrue(summary["unregistration_sent"])
        self.assertTrue(summary["unregistration_acknowledged"])
        self.assertFalse(summary["timed_out"])
        self.assertTrue(summary["closed"])
        self.assertEqual(client.close_calls, 1)

    async def test_unregistration_preserves_watchlist_and_request(self):
        watchlist = _watchlist("005930", "000660")
        stock_codes_before = watchlist.stock_codes
        candidates_before = watchlist.candidates
        metrics_before = watchlist.metrics
        request = {
            "trnm": "REMOVE",
            "grp_no": "1",
            "data": [
                {
                    "item": ["005930", "000660"],
                    "type": ["0B"],
                }
            ],
        }
        request_before = copy.deepcopy(request)
        client = FakeWebSocketClient(
            [{"trnm": "REMOVE", "return_code": 0}]
        )

        with (
            patch.object(
                baseline,
                "build_demo_watchlist_unregistration_request",
                return_value=request,
            ) as builder,
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            await baseline.run_demo_watchlist_unregistration_baseline(
                watchlist,
                duration_seconds=1.0,
                max_messages=1,
            )

        builder.assert_called_once_with(watchlist)
        self.assertIs(client.sent_packets[0], request)
        self.assertEqual(request, request_before)
        self.assertEqual(watchlist.stock_codes, stock_codes_before)
        self.assertIs(watchlist.candidates, candidates_before)
        self.assertIs(watchlist.metrics, metrics_before)

    async def test_unregistration_server_failure_closes_client(self):
        client = FakeWebSocketClient(
            [
                {
                    "trnm": "REMOVE",
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
                await baseline.run_demo_watchlist_unregistration_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                    max_messages=1,
                )

        self.assertEqual(client.close_calls, 1)
        self.assertFalse(client.is_connected)

    async def test_unregistration_send_error_closes_client(self):
        client = FakeWebSocketClient(
            send_error=RuntimeError("remove send failed")
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "remove send failed",
            ):
                await baseline.run_demo_watchlist_unregistration_baseline(
                    _watchlist("005930")
                )

        self.assertEqual(client.close_calls, 1)
        self.assertFalse(client.is_connected)

    async def test_unregistration_timeout_closes_client(self):
        client = HangingWebSocketClient()
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            summary = (
                await baseline.run_demo_watchlist_unregistration_baseline(
                    _watchlist("005930"),
                    duration_seconds=0.01,
                    max_messages=1,
                )
            )

        self.assertTrue(summary["timed_out"])
        self.assertFalse(summary["unregistration_acknowledged"])
        self.assertTrue(summary["closed"])
        self.assertEqual(client.close_calls, 1)

    async def test_unregistration_connect_error_still_closes_client(self):
        client = FakeWebSocketClient(
            connect_error=RuntimeError("connect failed")
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "connect failed"):
                await baseline.run_demo_watchlist_unregistration_baseline(
                    _watchlist("005930")
                )

        self.assertEqual(client.close_calls, 1)
        self.assertFalse(client.is_connected)

    async def test_unregistration_close_error_is_propagated(self):
        client = FakeWebSocketClient(
            [{"trnm": "REMOVE", "return_code": 0}],
            close_error=RuntimeError("close failed"),
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "close failed"):
                await baseline.run_demo_watchlist_unregistration_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                    max_messages=1,
                )

        self.assertEqual(client.close_calls, 1)
        self.assertFalse(client.is_connected)

    async def test_unregistration_invalid_inputs_before_environment(self):
        invalid_watchlists = (
            (object(), TypeError),
            (_watchlist(), ValueError),
            (_watchlist("005930", realtime_type="0C"), ValueError),
        )
        with patch.object(
            baseline,
            "ensure_demo_websocket_environment",
        ) as environment:
            for watchlist, expected_error in invalid_watchlists:
                with self.subTest(watchlist=watchlist):
                    with self.assertRaises(expected_error):
                        await (
                            baseline
                            .run_demo_watchlist_unregistration_baseline(
                                watchlist
                            )
                        )

        environment.assert_not_called()

    async def test_unregistration_invalid_limits_before_environment(self):
        invalid_cases = (
            ({"duration_seconds": True}, TypeError),
            ({"duration_seconds": 0}, ValueError),
            ({"max_messages": True}, TypeError),
            ({"max_messages": 0}, ValueError),
        )
        with patch.object(
            baseline,
            "ensure_demo_websocket_environment",
        ) as environment:
            for kwargs, expected_error in invalid_cases:
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(expected_error):
                        await (
                            baseline
                            .run_demo_watchlist_unregistration_baseline(
                                _watchlist("005930"),
                                **kwargs,
                            )
                        )

        environment.assert_not_called()

    async def test_unregistration_builder_error_before_environment(self):
        with (
            patch.object(
                baseline,
                "build_demo_watchlist_unregistration_request",
                side_effect=RuntimeError("builder failed"),
            ),
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
            ) as environment,
        ):
            with self.assertRaisesRegex(RuntimeError, "builder failed"):
                await baseline.run_demo_watchlist_unregistration_baseline(
                    _watchlist("005930")
                )

        environment.assert_not_called()

    def test_unregistration_decision_requires_complete_summary(self):
        summary = {
            "mode": "demo",
            "ws_base_url": baseline.DEMO_WS_BASE_URL,
            "unregistered_item_count": 2,
            "connected": True,
            "unregistration_sent": True,
            "unregistration_acknowledged": True,
            "closed": True,
        }
        self.assertTrue(
            baseline.demo_watchlist_unregistration_baseline_passed(
                summary
            )
        )

        for key in tuple(summary):
            with self.subTest(key=key):
                incomplete = dict(summary)
                incomplete.pop(key)
                self.assertFalse(
                    baseline.demo_watchlist_unregistration_baseline_passed(
                        incomplete
                    )
                )

    def test_public_package_exports_phase15_contract(self):
        self.assertIs(
            websocket_package.run_demo_watchlist_unregistration_baseline,
            baseline.run_demo_watchlist_unregistration_baseline,
        )
        self.assertIs(
            websocket_package
            .demo_watchlist_unregistration_baseline_passed,
            baseline.demo_watchlist_unregistration_baseline_passed,
        )

    async def test_lifecycle_success_order(self):
        client = LifecycleWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL", "data": [{"item": "005930"}]},
                {"trnm": "REMOVE", "return_code": 0},
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
            summary = await baseline.run_demo_watchlist_lifecycle_baseline(
                _watchlist("005930"),
                duration_seconds=1.0,
            )

        self.assertEqual(
            client.events,
            [
                "connect",
                "send:REG",
                "receive:REG",
                "receive:REAL",
                "send:REMOVE",
                "receive:REMOVE",
                "close",
            ],
        )
        self.assertTrue(
            baseline.demo_watchlist_lifecycle_baseline_passed(summary)
        )

    async def test_lifecycle_uses_one_client_and_connection(self):
        client = LifecycleWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": 0},
            ]
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(
                baseline,
                "get_ws_client",
                return_value=client,
            ) as client_factory,
        ):
            await baseline.run_demo_watchlist_lifecycle_baseline(
                _watchlist("005930"),
                duration_seconds=1.0,
            )

        client_factory.assert_called_once_with()
        self.assertEqual(client.connect_calls, [baseline.API_URL])
        self.assertEqual(client.iter_messages_calls, 1)
        self.assertEqual(client.send_calls, 2)
        self.assertEqual(client.close_calls, 1)

    async def test_lifecycle_preserves_watchlist_and_requests(self):
        watchlist = _watchlist("005930", "000660")
        stock_codes_before = watchlist.stock_codes
        candidates_before = watchlist.candidates
        metrics_before = watchlist.metrics
        registration = {
            "trnm": "REG",
            "grp_no": "1",
            "refresh": "1",
            "data": [{"item": ["005930", "000660"], "type": ["0B"]}],
        }
        unregistration = {
            "trnm": "REMOVE",
            "grp_no": "1",
            "data": [{"item": ["005930", "000660"], "type": ["0B"]}],
        }
        requests_before = copy.deepcopy((registration, unregistration))
        client = LifecycleWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": 0},
            ]
        )
        with (
            patch.object(
                baseline,
                "build_demo_watchlist_registration_request",
                return_value=registration,
            ) as registration_builder,
            patch.object(
                baseline,
                "build_demo_watchlist_unregistration_request",
                return_value=unregistration,
            ) as unregistration_builder,
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            await baseline.run_demo_watchlist_lifecycle_baseline(
                watchlist,
                duration_seconds=1.0,
            )

        registration_builder.assert_called_once_with(watchlist)
        unregistration_builder.assert_called_once_with(watchlist)
        self.assertIs(client.sent_packets[0], registration)
        self.assertIs(client.sent_packets[1], unregistration)
        self.assertEqual((registration, unregistration), requests_before)
        self.assertEqual(watchlist.stock_codes, stock_codes_before)
        self.assertIs(watchlist.candidates, candidates_before)
        self.assertIs(watchlist.metrics, metrics_before)

    async def test_lifecycle_separates_system_and_limits_realtime(self):
        client = LifecycleWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "PING"},
                {"trnm": "REAL"},
                {"trnm": "REAL"},
                {"trnm": "NOTICE"},
                {"trnm": "REMOVE", "return_code": 0},
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
            summary = await baseline.run_demo_watchlist_lifecycle_baseline(
                _watchlist("005930"),
                duration_seconds=1.0,
                max_realtime_messages=1,
            )

        self.assertEqual(summary["realtime_messages"], 1)
        self.assertEqual(summary["ignored_realtime_messages"], 1)
        self.assertEqual(summary["system_messages"], 4)
        self.assertEqual(summary["messages_received"], 6)
        self.assertEqual(
            summary["message_types"],
            ["REG", "PING", "REAL", "NOTICE", "REMOVE"],
        )

    async def test_lifecycle_registration_server_failure_closes(self):
        client = LifecycleWebSocketClient(
            [{"trnm": "REG", "return_code": -100, "return_msg": "failed"}]
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
                await baseline.run_demo_watchlist_lifecycle_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                )

        self.assertEqual(client.close_calls, 1)
        self.assertEqual([packet["trnm"] for packet in client.sent_packets], ["REG"])

    async def test_lifecycle_unregistration_server_failure_closes(self):
        client = LifecycleWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": -100, "return_msg": "failed"},
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
                await baseline.run_demo_watchlist_lifecycle_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                )

        self.assertEqual(client.close_calls, 1)
        self.assertEqual(
            [packet["trnm"] for packet in client.sent_packets],
            ["REG", "REMOVE"],
        )

    async def test_lifecycle_registration_send_error_closes(self):
        client = LifecycleWebSocketClient(
            send_errors=(RuntimeError("REG send failed"),)
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "REG send failed"):
                await baseline.run_demo_watchlist_lifecycle_baseline(
                    _watchlist("005930")
                )

        self.assertEqual(client.close_calls, 1)
        self.assertEqual(client.send_calls, 1)

    async def test_lifecycle_unregistration_send_error_closes(self):
        client = LifecycleWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
            ],
            send_errors=(None, RuntimeError("REMOVE send failed")),
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "REMOVE send failed"):
                await baseline.run_demo_watchlist_lifecycle_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                )

        self.assertEqual(client.close_calls, 1)
        self.assertEqual(client.send_calls, 2)

    async def test_lifecycle_registration_timeout_closes(self):
        client = LifecycleWebSocketClient(hang_after_messages=True)
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaises(TimeoutError):
                await baseline.run_demo_watchlist_lifecycle_baseline(
                    _watchlist("005930"),
                    duration_seconds=0.01,
                )

        self.assertEqual(client.close_calls, 1)

    async def test_lifecycle_unregistration_timeout_closes(self):
        client = LifecycleWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
            ],
            hang_after_messages=True,
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaises(TimeoutError):
                await baseline.run_demo_watchlist_lifecycle_baseline(
                    _watchlist("005930"),
                    duration_seconds=0.01,
                )

        self.assertEqual(client.close_calls, 1)
        self.assertEqual(client.send_calls, 2)

    async def test_lifecycle_connect_error_closes(self):
        client = LifecycleWebSocketClient(
            connect_error=RuntimeError("connect failed")
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "connect failed"):
                await baseline.run_demo_watchlist_lifecycle_baseline(
                    _watchlist("005930")
                )

        self.assertEqual(client.close_calls, 1)
        self.assertFalse(client.is_connected)

    async def test_lifecycle_close_error_is_propagated(self):
        client = LifecycleWebSocketClient(
            [
                {"trnm": "REG", "return_code": 0},
                {"trnm": "REAL"},
                {"trnm": "REMOVE", "return_code": 0},
            ],
            close_error=RuntimeError("close failed"),
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
                return_value=("demo", baseline.DEMO_WS_BASE_URL),
            ),
            patch.object(baseline, "get_ws_client", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "close failed"):
                await baseline.run_demo_watchlist_lifecycle_baseline(
                    _watchlist("005930"),
                    duration_seconds=1.0,
                )

        self.assertEqual(client.close_calls, 1)

    async def test_lifecycle_invalid_input_before_environment(self):
        invalid_cases = (
            (object(), TypeError),
            (_watchlist(), ValueError),
            (_watchlist("005930", realtime_type="0C"), ValueError),
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
            ) as environment,
            patch.object(baseline, "get_ws_client") as client_factory,
        ):
            for watchlist, expected_error in invalid_cases:
                with self.subTest(watchlist=watchlist):
                    with self.assertRaises(expected_error):
                        await baseline.run_demo_watchlist_lifecycle_baseline(
                            watchlist
                        )

        environment.assert_not_called()
        client_factory.assert_not_called()

    async def test_lifecycle_invalid_limits_before_environment(self):
        invalid_cases = (
            ({"duration_seconds": True}, TypeError),
            ({"duration_seconds": 0}, ValueError),
            ({"max_realtime_messages": True}, TypeError),
            ({"max_realtime_messages": 0}, ValueError),
        )
        with (
            patch.object(
                baseline,
                "ensure_demo_websocket_environment",
            ) as environment,
            patch.object(baseline, "get_ws_client") as client_factory,
        ):
            for kwargs, expected_error in invalid_cases:
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(expected_error):
                        await baseline.run_demo_watchlist_lifecycle_baseline(
                            _watchlist("005930"),
                            **kwargs,
                        )

        environment.assert_not_called()
        client_factory.assert_not_called()

    async def test_lifecycle_builder_error_before_environment_and_client(self):
        for builder_name in (
            "build_demo_watchlist_registration_request",
            "build_demo_watchlist_unregistration_request",
        ):
            with self.subTest(builder_name=builder_name):
                with (
                    patch.object(
                        baseline,
                        builder_name,
                        side_effect=RuntimeError(f"{builder_name} failed"),
                    ),
                    patch.object(
                        baseline,
                        "ensure_demo_websocket_environment",
                    ) as environment,
                    patch.object(
                        baseline,
                        "get_ws_client",
                    ) as client_factory,
                ):
                    with self.assertRaisesRegex(RuntimeError, "failed"):
                        await baseline.run_demo_watchlist_lifecycle_baseline(
                            _watchlist("005930")
                        )

                environment.assert_not_called()
                client_factory.assert_not_called()

    def test_lifecycle_decision_and_phase16_exports(self):
        summary = {
            "mode": "demo",
            "ws_base_url": baseline.DEMO_WS_BASE_URL,
            "registered_item_count": 1,
            "unregistered_item_count": 1,
            "max_realtime_messages": 1,
            "connected": True,
            "registration_sent": True,
            "registration_acknowledged": True,
            "messages_received": 3,
            "realtime_messages": 1,
            "ignored_realtime_messages": 0,
            "system_messages": 2,
            "unregistration_sent": True,
            "unregistration_acknowledged": True,
            "closed": True,
        }
        self.assertTrue(
            baseline.demo_watchlist_lifecycle_baseline_passed(summary)
        )
        for key in tuple(summary):
            with self.subTest(key=key):
                incomplete = dict(summary)
                incomplete.pop(key)
                self.assertFalse(
                    baseline.demo_watchlist_lifecycle_baseline_passed(
                        incomplete
                    )
                )

        self.assertIs(
            websocket_package.run_demo_watchlist_lifecycle_baseline,
            baseline.run_demo_watchlist_lifecycle_baseline,
        )
        self.assertIs(
            websocket_package.demo_watchlist_lifecycle_baseline_passed,
            baseline.demo_watchlist_lifecycle_baseline_passed,
        )


if __name__ == "__main__":
    unittest.main()
