from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from kiwoom_trading_system.brokers.kiwoom.websocket import demo_baseline


class FakeWebSocketClient:
    def __init__(self, messages: list[object]) -> None:
        self.messages = messages
        self.is_connected = False
        self.connected_api_url: str | None = None
        self.sent_packets: list[object] = []
        self.close_calls = 0

    async def connect(self, *, api_url: str) -> None:
        self.connected_api_url = api_url
        self.is_connected = True

    async def send(self, payload: object) -> None:
        if not self.is_connected:
            raise RuntimeError("not connected")
        self.sent_packets.append(payload)

    async def iter_messages(self):
        for message in self.messages:
            yield message

    async def close(self) -> None:
        self.close_calls += 1
        self.is_connected = False


class ReturnCodeTests(unittest.TestCase):
    def test_success_values(self) -> None:
        for value in (None, 0, "0"):
            with self.subTest(value=value):
                self.assertTrue(
                    demo_baseline._is_success_return_code(value)
                )

    def test_failure_values(self) -> None:
        for value in (True, -1, "", "invalid"):
            with self.subTest(value=value):
                self.assertFalse(
                    demo_baseline._is_success_return_code(value)
                )


class InputValidationTests(unittest.TestCase):
    def test_valid_values_are_normalized(self) -> None:
        self.assertEqual(
            demo_baseline._normalize_stock_code(" 005930 "),
            "005930",
        )
        self.assertEqual(
            demo_baseline._normalize_realtime_type(" 0b "),
            "0B",
        )

    def test_invalid_stock_codes_are_rejected(self) -> None:
        for value in ("", "5930", "A005930", "００５９３０", "00593A"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    demo_baseline._normalize_stock_code(value)


class DemoEnvironmentTests(unittest.TestCase):
    def test_demo_environment_passes(self) -> None:
        with (
            patch.object(
                demo_baseline,
                "describe_selection",
                return_value=SimpleNamespace(mode="demo"),
            ),
            patch.object(
                demo_baseline,
                "get_ws_base_url",
                return_value=demo_baseline.DEMO_WS_BASE_URL,
            ),
        ):
            result = demo_baseline.ensure_demo_websocket_environment()

        self.assertEqual(
            result,
            ("demo", demo_baseline.DEMO_WS_BASE_URL),
        )

    def test_real_environment_is_blocked(self) -> None:
        with (
            patch.object(
                demo_baseline,
                "describe_selection",
                return_value=SimpleNamespace(mode="real"),
            ),
            patch.object(
                demo_baseline,
                "get_ws_base_url",
                return_value="wss://api.kiwoom.com:10000",
            ),
        ):
            with self.assertRaises(
                demo_baseline.DemoWebSocketEnvironmentRequiredError
            ):
                demo_baseline.ensure_demo_websocket_environment()

    def test_wrong_demo_url_is_blocked(self) -> None:
        with (
            patch.object(
                demo_baseline,
                "describe_selection",
                return_value=SimpleNamespace(mode="demo"),
            ),
            patch.object(
                demo_baseline,
                "get_ws_base_url",
                return_value="wss://example.invalid:10000",
            ),
        ):
            with self.assertRaises(
                demo_baseline.DemoWebSocketEnvironmentRequiredError
            ):
                demo_baseline.ensure_demo_websocket_environment()


class DemoRealtimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_registration_receive_and_close(self) -> None:
        client = FakeWebSocketClient(
            [
                {
                    "trnm": "REG",
                    "return_code": 0,
                    "return_msg": "success",
                },
                {
                    "trnm": "REAL",
                    "data": [],
                },
            ]
        )

        with (
            patch.object(
                demo_baseline,
                "ensure_demo_websocket_environment",
                return_value=(
                    "demo",
                    demo_baseline.DEMO_WS_BASE_URL,
                ),
            ),
            patch.object(
                demo_baseline,
                "get_ws_client",
                return_value=client,
            ),
        ):
            summary = await demo_baseline.run_demo_realtime_baseline(
                "005930",
                duration_seconds=1,
                max_messages=2,
            )

        self.assertEqual(
            client.connected_api_url,
            demo_baseline.API_URL,
        )
        self.assertEqual(
            client.sent_packets,
            [
                {
                    "trnm": "REG",
                    "grp_no": "1",
                    "refresh": "1",
                    "data": [
                        {
                            "item": ["005930"],
                            "type": ["0B"],
                        }
                    ],
                }
            ],
        )
        self.assertTrue(summary["connected"])
        self.assertTrue(summary["registration_sent"])
        self.assertTrue(summary["registration_acknowledged"])
        self.assertEqual(summary["messages_received"], 2)
        self.assertEqual(summary["realtime_messages"], 1)
        self.assertEqual(summary["system_messages"], 1)
        self.assertEqual(summary["message_types"], ["REG", "REAL"])
        self.assertTrue(summary["closed"])
        self.assertEqual(client.close_calls, 1)


    async def test_realtime_handler_receives_only_real(
        self,
    ) -> None:
        real_message = {
            "trnm": "REAL",
            "data": [],
        }
        client = FakeWebSocketClient(
            [
                {
                    "trnm": "REG",
                    "return_code": 0,
                    "return_msg": "success",
                },
                real_message,
            ]
        )
        received = []

        async def handler(message):
            received.append(message)

        with (
            patch.object(
                demo_baseline,
                "ensure_demo_websocket_environment",
                return_value=(
                    "demo",
                    demo_baseline.DEMO_WS_BASE_URL,
                ),
            ),
            patch.object(
                demo_baseline,
                "get_ws_client",
                return_value=client,
            ),
        ):
            await demo_baseline.run_demo_realtime_baseline(
                "005930",
                duration_seconds=1,
                max_messages=2,
                on_realtime_message=handler,
            )

        self.assertEqual(received, [real_message])
        self.assertEqual(client.close_calls, 1)

    async def test_invalid_realtime_handler_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            await demo_baseline.run_demo_realtime_baseline(
                "005930",
                on_realtime_message=object(),
            )

    async def test_failed_response_closes_client(self) -> None:
        client = FakeWebSocketClient(
            [
                {
                    "trnm": "REG",
                    "return_code": -100,
                    "return_msg": "test error",
                }
            ]
        )

        with (
            patch.object(
                demo_baseline,
                "ensure_demo_websocket_environment",
                return_value=(
                    "demo",
                    demo_baseline.DEMO_WS_BASE_URL,
                ),
            ),
            patch.object(
                demo_baseline,
                "get_ws_client",
                return_value=client,
            ),
        ):
            with self.assertRaises(
                demo_baseline.RealtimeResponseError
            ):
                await demo_baseline.run_demo_realtime_baseline(
                    "005930",
                    duration_seconds=1,
                    max_messages=1,
                )

        self.assertFalse(client.is_connected)
        self.assertEqual(client.close_calls, 1)

    async def test_invalid_limits_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            await demo_baseline.run_demo_realtime_baseline(
                "005930",
                duration_seconds=0,
            )

        with self.assertRaises(ValueError):
            await demo_baseline.run_demo_realtime_baseline(
                "005930",
                max_messages=0,
            )


class BaselineDecisionTests(unittest.TestCase):
    def test_complete_summary_passes(self) -> None:
        summary = {
            "mode": "demo",
            "ws_base_url": demo_baseline.DEMO_WS_BASE_URL,
            "connected": True,
            "registration_sent": True,
            "registration_acknowledged": True,
            "closed": True,
        }
        self.assertTrue(demo_baseline._baseline_passed(summary))

    def test_missing_ack_holds(self) -> None:
        summary = {
            "mode": "demo",
            "ws_base_url": demo_baseline.DEMO_WS_BASE_URL,
            "connected": True,
            "registration_sent": True,
            "registration_acknowledged": False,
            "closed": True,
        }
        self.assertFalse(demo_baseline._baseline_passed(summary))


if __name__ == "__main__":
    unittest.main()