"""Bounded demo recovery baseline for a realtime watchlist."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from typing import Any

from kiwoom import get_ws_client
from websockets.exceptions import ConnectionClosed

from kiwoom_trading_system.screening import RealtimeWatchlist

from .demo_baseline import (
    API_URL,
    DEMO_WS_BASE_URL,
    _message_type,
    _validate_response,
    ensure_demo_websocket_environment,
)
from .watchlist_registration import (
    build_demo_watchlist_registration_request,
)
from .watchlist_unregistration import (
    build_demo_watchlist_unregistration_request,
)


_RECOVERABLE_DISCONNECTS = (
    ConnectionClosed,
    EOFError,
    OSError,
    StopAsyncIteration,
)


class WatchlistRecoveryExhaustedError(RuntimeError):
    """Raised when the bounded demo reconnect budget is exhausted."""

    def __init__(
        self,
        attempts: int,
        last_error: BaseException,
        summary: dict[str, Any],
    ) -> None:
        super().__init__(
            "demo watchlist recovery exhausted after "
            f"{attempts} connection attempts."
        )
        self.attempts = attempts
        self.last_error = last_error
        self.summary = dict(summary)


class _RecoveryDeadlineExceeded(TimeoutError):
    """Internal marker for the shared recovery deadline."""


class _RealtimeCallbackFailed(Exception):
    """Keep callback failures outside the reconnect error classifier."""

    def __init__(self, error: Exception) -> None:
        super().__init__(str(error))
        self.error = error


def _validate_recovery_options(
    duration_seconds: float,
    max_realtime_messages: int,
    max_reconnect_attempts: int,
    initial_backoff_seconds: float,
    max_backoff_seconds: float,
    on_realtime_message: (
        Callable[[Any], Awaitable[None]] | None
    ),
) -> None:
    if isinstance(duration_seconds, bool) or not isinstance(
        duration_seconds,
        (int, float),
    ):
        raise TypeError("duration_seconds must be a number.")
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero.")
    if not math.isfinite(float(duration_seconds)):
        raise ValueError("duration_seconds must be finite.")

    if isinstance(max_realtime_messages, bool) or not isinstance(
        max_realtime_messages,
        int,
    ):
        raise TypeError("max_realtime_messages must be an integer.")
    if max_realtime_messages <= 0:
        raise ValueError(
            "max_realtime_messages must be greater than zero."
        )

    if isinstance(max_reconnect_attempts, bool) or not isinstance(
        max_reconnect_attempts,
        int,
    ):
        raise TypeError("max_reconnect_attempts must be an integer.")
    if max_reconnect_attempts < 0:
        raise ValueError(
            "max_reconnect_attempts must be zero or greater."
        )

    for name, value in (
        ("initial_backoff_seconds", initial_backoff_seconds),
        ("max_backoff_seconds", max_backoff_seconds),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number.")
        if value < 0:
            raise ValueError(f"{name} must be zero or greater.")
        if not math.isfinite(float(value)):
            raise ValueError(f"{name} must be finite.")

    if max_backoff_seconds < initial_backoff_seconds:
        raise ValueError(
            "max_backoff_seconds must be greater than or equal to "
            "initial_backoff_seconds."
        )

    if (
        on_realtime_message is not None
        and not callable(on_realtime_message)
    ):
        raise TypeError(
            "on_realtime_message must be callable."
        )


async def _call_realtime_callback(
    on_realtime_message: Callable[[Any], Awaitable[None]],
    message: Any,
) -> None:
    try:
        await on_realtime_message(message)
    except Exception as error:
        raise _RealtimeCallbackFailed(error) from error


def _backoff_delay(
    retry_number: int,
    *,
    initial_backoff_seconds: float,
    max_backoff_seconds: float,
) -> float:
    exponent = min(retry_number - 1, 1023)
    return min(
        float(initial_backoff_seconds) * (2.0**exponent),
        float(max_backoff_seconds),
    )


async def _sleep_before_retry(
    retry_number: int,
    *,
    deadline: float,
    initial_backoff_seconds: float,
    max_backoff_seconds: float,
) -> None:
    delay = _backoff_delay(
        retry_number,
        initial_backoff_seconds=initial_backoff_seconds,
        max_backoff_seconds=max_backoff_seconds,
    )
    remaining = deadline - asyncio.get_running_loop().time()
    if remaining <= 0 or delay > remaining:
        raise _RecoveryDeadlineExceeded
    try:
        await asyncio.wait_for(asyncio.sleep(delay), timeout=remaining)
    except TimeoutError as error:
        raise _RecoveryDeadlineExceeded from error


async def _next_recovery_message(
    message_iterator: Any,
    *,
    deadline: float,
) -> Any:
    remaining = deadline - asyncio.get_running_loop().time()
    if remaining <= 0:
        raise _RecoveryDeadlineExceeded
    try:
        return await asyncio.wait_for(
            message_iterator.__anext__(),
            timeout=remaining,
        )
    except TimeoutError as error:
        raise _RecoveryDeadlineExceeded from error


def _record_recovery_message(
    summary: dict[str, Any],
    message: Any,
    *,
    accept_realtime: bool,
) -> str:
    _validate_response(message)
    message_type = _message_type(message)
    summary["messages_received"] += 1
    if message_type not in summary["message_types"]:
        summary["message_types"].append(message_type)
    if message_type == "REAL":
        if accept_realtime:
            summary["realtime_messages"] += 1
        else:
            summary["ignored_realtime_messages"] += 1
    else:
        summary["system_messages"] += 1
    return message_type


async def _receive_recovery_type(
    message_iterator: Any,
    summary: dict[str, Any],
    *,
    expected_type: str,
    deadline: float,
) -> None:
    while True:
        message = await _next_recovery_message(
            message_iterator,
            deadline=deadline,
        )
        if _record_recovery_message(
            summary,
            message,
            accept_realtime=False,
        ) == expected_type:
            return


async def run_demo_watchlist_recovery_baseline(
    watchlist: RealtimeWatchlist,
    *,
    duration_seconds: float = 10.0,
    max_realtime_messages: int = 1,
    max_reconnect_attempts: int = 2,
    initial_backoff_seconds: float = 0.25,
    max_backoff_seconds: float = 2.0,
    on_realtime_message: (
        Callable[[Any], Awaitable[None]] | None
    ) = None,
) -> dict[str, Any]:
    """Recover a bounded demo watchlist after a WebSocket disconnect."""

    registration = build_demo_watchlist_registration_request(watchlist)
    unregistration = build_demo_watchlist_unregistration_request(watchlist)
    _validate_recovery_options(
        duration_seconds,
        max_realtime_messages,
        max_reconnect_attempts,
        initial_backoff_seconds,
        max_backoff_seconds,
        on_realtime_message,
    )

    stock_codes = watchlist.stock_codes
    mode, ws_base_url = ensure_demo_websocket_environment()
    summary: dict[str, Any] = {
        "mode": mode,
        "ws_base_url": ws_base_url,
        "api_url": API_URL,
        "stock_codes": stock_codes,
        "registered_item_count": len(stock_codes),
        "unregistered_item_count": len(stock_codes),
        "realtime_type": watchlist.realtime_type,
        "max_realtime_messages": max_realtime_messages,
        "max_reconnect_attempts": max_reconnect_attempts,
        "connected": False,
        "connection_attempts": 0,
        "successful_connections": 0,
        "connection_failures": 0,
        "disconnects_detected": 0,
        "reconnect_attempts": 0,
        "reconnect_successes": 0,
        "registration_sent": False,
        "registration_acknowledged": False,
        "registrations_sent": 0,
        "registrations_acknowledged": 0,
        "reregistration_sent": False,
        "reregistration_acknowledged": False,
        "messages_received": 0,
        "realtime_messages": 0,
        "ignored_realtime_messages": 0,
        "system_messages": 0,
        "message_types": [],
        "unregistration_sent": False,
        "unregistration_acknowledged": False,
        "retry_exhausted": False,
        "recovered": False,
        "clients_closed": 0,
        "closed": False,
    }

    deadline = (
        asyncio.get_running_loop().time() + float(duration_seconds)
    )
    retry_number = 0

    while True:
        if retry_number > 0:
            summary["reconnect_attempts"] = retry_number
            await _sleep_before_retry(
                retry_number,
                deadline=deadline,
                initial_backoff_seconds=initial_backoff_seconds,
                max_backoff_seconds=max_backoff_seconds,
            )

        client = get_ws_client()
        summary["connection_attempts"] += 1
        connected_this_attempt = False
        shutdown_started = False
        completed = False
        recovery_error: BaseException | None = None

        try:
            await client.connect(api_url=API_URL)
            connected_this_attempt = True
            summary["connected"] = bool(client.is_connected)
            summary["successful_connections"] += 1
            if retry_number > 0:
                summary["reconnect_successes"] += 1

            await client.send(registration)
            summary["registration_sent"] = True
            summary["registrations_sent"] += 1
            if retry_number > 0:
                summary["reregistration_sent"] = True

            message_iterator = client.iter_messages().__aiter__()
            await _receive_recovery_type(
                message_iterator,
                summary,
                expected_type="REG",
                deadline=deadline,
            )
            summary["registration_acknowledged"] = True
            summary["registrations_acknowledged"] += 1
            if retry_number > 0:
                summary["reregistration_acknowledged"] = True

            while (
                summary["realtime_messages"]
                < max_realtime_messages
            ):
                message = await _next_recovery_message(
                    message_iterator,
                    deadline=deadline,
                )
                message_type = _record_recovery_message(
                    summary,
                    message,
                    accept_realtime=True,
                )
                if (
                    message_type == "REAL"
                    and on_realtime_message is not None
                ):
                    await _call_realtime_callback(
                        on_realtime_message,
                        message,
                    )

            await client.send(unregistration)
            shutdown_started = True
            summary["unregistration_sent"] = True
            await _receive_recovery_type(
                message_iterator,
                summary,
                expected_type="REMOVE",
                deadline=deadline,
            )
            summary["unregistration_acknowledged"] = True
            completed = True
        except _RecoveryDeadlineExceeded:
            raise
        except _RealtimeCallbackFailed as failure:
            raise failure.error from failure
        except _RECOVERABLE_DISCONNECTS as error:
            if shutdown_started:
                raise
            recovery_error = error
            if connected_this_attempt:
                summary["disconnects_detected"] += 1
            else:
                summary["connection_failures"] += 1
        finally:
            await client.close()
            summary["clients_closed"] += 1
            summary["closed"] = bool(
                summary["clients_closed"]
                == summary["connection_attempts"]
                and not bool(client.is_connected)
            )

        if completed:
            summary["recovered"] = retry_number > 0
            return summary

        if recovery_error is None:
            raise RuntimeError("recovery attempt ended without a result.")

        if retry_number >= max_reconnect_attempts:
            summary["retry_exhausted"] = True
            raise WatchlistRecoveryExhaustedError(
                summary["connection_attempts"],
                recovery_error,
                summary,
            ) from recovery_error

        retry_number += 1


def demo_watchlist_recovery_baseline_passed(
    summary: dict[str, Any],
) -> bool:
    """Return whether the bounded demo recovery lifecycle completed."""

    realtime_limit = summary.get("max_realtime_messages")
    connection_attempts = summary.get("connection_attempts")
    reconnect_attempts = summary.get("reconnect_attempts")
    registered_count = summary.get("registered_item_count", 0)
    realtime_messages = summary.get("realtime_messages", 0)
    ignored_realtime_messages = summary.get(
        "ignored_realtime_messages"
    )
    system_messages = summary.get("system_messages", 0)

    reconnect_contract_passed = bool(
        reconnect_attempts == 0
        or (
            summary.get("reregistration_sent")
            and summary.get("reregistration_acknowledged")
            and summary.get("recovered")
        )
    )
    return bool(
        summary.get("mode") == "demo"
        and summary.get("ws_base_url") == DEMO_WS_BASE_URL
        and isinstance(realtime_limit, int)
        and not isinstance(realtime_limit, bool)
        and realtime_limit > 0
        and isinstance(connection_attempts, int)
        and not isinstance(connection_attempts, bool)
        and connection_attempts > 0
        and isinstance(reconnect_attempts, int)
        and not isinstance(reconnect_attempts, bool)
        and reconnect_attempts >= 0
        and registered_count > 0
        and summary.get("unregistered_item_count") == registered_count
        and summary.get("connected")
        and summary.get("registration_sent")
        and summary.get("registration_acknowledged")
        and summary.get("registrations_sent", 0) > 0
        and summary.get("registrations_acknowledged", 0) > 0
        and reconnect_contract_passed
        and realtime_messages == realtime_limit
        and isinstance(ignored_realtime_messages, int)
        and not isinstance(ignored_realtime_messages, bool)
        and ignored_realtime_messages >= 0
        and summary.get("unregistration_sent")
        and summary.get("unregistration_acknowledged")
        and not summary.get("retry_exhausted")
        and summary.get("messages_received")
        == realtime_messages + ignored_realtime_messages + system_messages
        and summary.get("clients_closed") == connection_attempts
        and summary.get("closed")
    )


__all__ = [
    "WatchlistRecoveryExhaustedError",
    "run_demo_watchlist_recovery_baseline",
    "demo_watchlist_recovery_baseline_passed",
]
