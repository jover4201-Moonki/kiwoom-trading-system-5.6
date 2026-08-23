from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from kiwoom import describe_selection, get_ws_base_url, get_ws_client
from kiwoom.realtime import build_reg_packet


API_URL = "/api/dostk/websocket"
DEMO_WS_BASE_URL = "wss://mockapi.kiwoom.com:10000"
DEFAULT_STOCK_CODE = "005930"
DEFAULT_REALTIME_TYPE = "0B"


class DemoWebSocketEnvironmentRequiredError(RuntimeError):
    """Raised when Phase 5 isn't using the demo WebSocket server."""


class RealtimeResponseError(RuntimeError):
    """Raised when Kiwoom returns a failed realtime response."""

    def __init__(self, return_code: object, return_msg: object) -> None:
        super().__init__(
            "Kiwoom realtime request failed: "
            f"return_code={return_code!r}, return_msg={return_msg!r}"
        )
        self.return_code = return_code
        self.return_msg = return_msg


def _mode_text(value: object) -> str:
    return str(getattr(value, "value", value)).strip().lower()


def _is_success_return_code(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value == 0

    text = str(value).strip()
    if not text:
        return False

    try:
        return int(text) == 0
    except ValueError:
        return False


def _normalize_stock_code(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("stk_cd must be a string.")

    code = value.strip()
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        raise ValueError("stk_cd must contain exactly six ASCII digits.")

    return code


def _normalize_realtime_type(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("realtime_type must be a string.")

    realtime_type = value.strip().upper()
    if not realtime_type:
        raise ValueError("realtime_type is required.")

    return realtime_type


def _message_type(message: Any) -> str:
    if isinstance(message, dict):
        value = str(message.get("trnm", "")).strip().upper()
        return value or "MESSAGE"
    return type(message).__name__.upper()


def _validate_response(message: Any) -> None:
    if not isinstance(message, dict):
        return
    if "return_code" not in message:
        return

    return_code = message.get("return_code")
    if not _is_success_return_code(return_code):
        raise RealtimeResponseError(
            return_code,
            message.get("return_msg"),
        )


def ensure_demo_websocket_environment() -> tuple[str, str]:
    """Require the current demo profile and official mock WS URL."""

    selection = describe_selection()
    mode = _mode_text(selection.mode)
    ws_base_url = get_ws_base_url().rstrip("/")

    if mode != "demo":
        raise DemoWebSocketEnvironmentRequiredError(
            f"Phase 5 requires demo mode, current mode={mode!r}."
        )

    if ws_base_url != DEMO_WS_BASE_URL:
        raise DemoWebSocketEnvironmentRequiredError(
            "Phase 5 requires the Kiwoom mock WebSocket server, "
            f"current ws_base_url={ws_base_url!r}."
        )

    return mode, ws_base_url


async def run_demo_realtime_baseline(
    stk_cd: str = DEFAULT_STOCK_CODE,
    *,
    realtime_type: str = DEFAULT_REALTIME_TYPE,
    duration_seconds: float = 10.0,
    max_messages: int = 3,
) -> dict[str, Any]:
    """Run a bounded demo login, registration, receive and close check."""

    code = _normalize_stock_code(stk_cd)
    normalized_type = _normalize_realtime_type(realtime_type)

    if isinstance(duration_seconds, bool) or not isinstance(
        duration_seconds,
        (int, float),
    ):
        raise TypeError("duration_seconds must be a number.")
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero.")

    if isinstance(max_messages, bool) or not isinstance(max_messages, int):
        raise TypeError("max_messages must be an integer.")
    if max_messages <= 0:
        raise ValueError("max_messages must be greater than zero.")

    mode, ws_base_url = ensure_demo_websocket_environment()
    client = get_ws_client()

    registration = build_reg_packet(
        [code],
        [normalized_type],
        group_no="1",
        refresh="1",
    )

    summary: dict[str, Any] = {
        "mode": mode,
        "ws_base_url": ws_base_url,
        "api_url": API_URL,
        "stock_code": code,
        "realtime_type": normalized_type,
        "connected": False,
        "registration_sent": False,
        "registration_acknowledged": False,
        "messages_received": 0,
        "realtime_messages": 0,
        "system_messages": 0,
        "message_types": [],
        "timed_out": False,
        "closed": False,
    }

    try:
        await client.connect(api_url=API_URL)
        summary["connected"] = bool(client.is_connected)

        await client.send(registration)
        summary["registration_sent"] = True

        try:
            async with asyncio.timeout(float(duration_seconds)):
                async for message in client.iter_messages():
                    _validate_response(message)
                    message_type = _message_type(message)

                    summary["messages_received"] += 1
                    if message_type not in summary["message_types"]:
                        summary["message_types"].append(message_type)

                    if message_type == "REAL":
                        summary["realtime_messages"] += 1
                        summary["registration_acknowledged"] = True
                    else:
                        summary["system_messages"] += 1
                        if message_type == "REG":
                            summary["registration_acknowledged"] = True

                    if summary["messages_received"] >= max_messages:
                        break
        except TimeoutError:
            summary["timed_out"] = True
    finally:
        await client.close()
        summary["closed"] = not bool(client.is_connected)

    return summary


def _baseline_passed(summary: dict[str, Any]) -> bool:
    return bool(
        summary.get("mode") == "demo"
        and summary.get("ws_base_url") == DEMO_WS_BASE_URL
        and summary.get("connected")
        and summary.get("registration_sent")
        and summary.get("registration_acknowledged")
        and summary.get("closed")
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 5 Kiwoom demo WebSocket baseline."
    )
    parser.add_argument("--code", default=DEFAULT_STOCK_CODE)
    parser.add_argument("--type", dest="realtime_type", default="0B")
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--max-messages", type=int, default=3)
    args = parser.parse_args()

    summary = asyncio.run(
        run_demo_realtime_baseline(
            args.code,
            realtime_type=args.realtime_type,
            duration_seconds=args.duration,
            max_messages=args.max_messages,
        )
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))

    if _baseline_passed(summary):
        print("PHASE5_DEMO_WEBSOCKET_BASELINE=PASS")
        return 0

    print("PHASE5_DEMO_WEBSOCKET_BASELINE=HOLD")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())