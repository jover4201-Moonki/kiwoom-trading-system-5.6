"""Bounded demo WebSocket baselines for a realtime watchlist."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from kiwoom import get_ws_client

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


class EmptyRealtimeWatchlistError(ValueError):
    """Raised when a registration watchlist has no stock codes."""


def _validate_run_options(
    duration_seconds: float,
    max_messages: int,
    on_realtime_message: Callable[[Any], Awaitable[None]] | None,
) -> None:
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

    if on_realtime_message is not None and not callable(
        on_realtime_message
    ):
        raise TypeError("on_realtime_message must be callable.")


async def _run_demo_watchlist_request_baseline(
    request: dict[str, Any],
    summary: dict[str, Any],
    *,
    sent_key: str,
    acknowledged_key: str,
    acknowledgement_types: frozenset[str],
    duration_seconds: float,
    max_messages: int,
    on_realtime_message: Callable[[Any], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """Send one request and receive bounded messages with guaranteed cleanup."""

    client = get_ws_client()
    try:
        await client.connect(api_url=API_URL)
        summary["connected"] = bool(client.is_connected)

        await client.send(request)
        summary[sent_key] = True

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
                        if on_realtime_message is not None:
                            await on_realtime_message(message)
                    else:
                        summary["system_messages"] += 1

                    if message_type in acknowledgement_types:
                        summary[acknowledged_key] = True

                    if summary["messages_received"] >= max_messages:
                        break
        except TimeoutError:
            summary["timed_out"] = True
    finally:
        await client.close()
        summary["closed"] = not bool(client.is_connected)

    return summary


async def run_demo_watchlist_realtime_baseline(
    watchlist: RealtimeWatchlist,
    *,
    duration_seconds: float = 10.0,
    max_messages: int = 3,
    on_realtime_message: Callable[[Any], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """Register one watchlist and receive a bounded set of demo messages."""

    registration = build_demo_watchlist_registration_request(watchlist)
    stock_codes = watchlist.stock_codes
    if not stock_codes:
        raise EmptyRealtimeWatchlistError(
            "watchlist must contain at least one stock code."
        )

    _validate_run_options(
        duration_seconds,
        max_messages,
        on_realtime_message,
    )

    mode, ws_base_url = ensure_demo_websocket_environment()
    summary: dict[str, Any] = {
        "mode": mode,
        "ws_base_url": ws_base_url,
        "api_url": API_URL,
        "stock_codes": stock_codes,
        "registered_item_count": len(stock_codes),
        "realtime_type": watchlist.realtime_type,
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

    return await _run_demo_watchlist_request_baseline(
        registration,
        summary,
        sent_key="registration_sent",
        acknowledged_key="registration_acknowledged",
        acknowledgement_types=frozenset({"REG", "REAL"}),
        duration_seconds=duration_seconds,
        max_messages=max_messages,
        on_realtime_message=on_realtime_message,
    )


async def run_demo_watchlist_unregistration_baseline(
    watchlist: RealtimeWatchlist,
    *,
    duration_seconds: float = 10.0,
    max_messages: int = 3,
) -> dict[str, Any]:
    """Unregister one watchlist and receive bounded demo messages."""

    unregistration = build_demo_watchlist_unregistration_request(watchlist)
    stock_codes = watchlist.stock_codes

    _validate_run_options(duration_seconds, max_messages, None)

    mode, ws_base_url = ensure_demo_websocket_environment()
    summary: dict[str, Any] = {
        "mode": mode,
        "ws_base_url": ws_base_url,
        "api_url": API_URL,
        "stock_codes": stock_codes,
        "unregistered_item_count": len(stock_codes),
        "realtime_type": watchlist.realtime_type,
        "connected": False,
        "unregistration_sent": False,
        "unregistration_acknowledged": False,
        "messages_received": 0,
        "realtime_messages": 0,
        "system_messages": 0,
        "message_types": [],
        "timed_out": False,
        "closed": False,
    }

    return await _run_demo_watchlist_request_baseline(
        unregistration,
        summary,
        sent_key="unregistration_sent",
        acknowledged_key="unregistration_acknowledged",
        acknowledgement_types=frozenset({"REMOVE"}),
        duration_seconds=duration_seconds,
        max_messages=max_messages,
    )


def demo_watchlist_baseline_passed(summary: dict[str, Any]) -> bool:
    """Return whether the bounded demo watchlist baseline completed."""

    return bool(
        summary.get("mode") == "demo"
        and summary.get("ws_base_url") == DEMO_WS_BASE_URL
        and summary.get("registered_item_count", 0) > 0
        and summary.get("connected")
        and summary.get("registration_sent")
        and summary.get("registration_acknowledged")
        and summary.get("closed")
    )


def demo_watchlist_unregistration_baseline_passed(
    summary: dict[str, Any],
) -> bool:
    """Return whether demo watchlist unregistration completed."""

    return bool(
        summary.get("mode") == "demo"
        and summary.get("ws_base_url") == DEMO_WS_BASE_URL
        and summary.get("unregistered_item_count", 0) > 0
        and summary.get("connected")
        and summary.get("unregistration_sent")
        and summary.get("unregistration_acknowledged")
        and summary.get("closed")
    )


__all__ = [
    "EmptyRealtimeWatchlistError",
    "run_demo_watchlist_realtime_baseline",
    "demo_watchlist_baseline_passed",
    "run_demo_watchlist_unregistration_baseline",
    "demo_watchlist_unregistration_baseline_passed",
]
