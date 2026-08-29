"""Pure conversion from a demo realtime watchlist to a REMOVE request."""

from __future__ import annotations

from typing import Any

from kiwoom.realtime import build_remove_packet

from kiwoom_trading_system.screening import (
    DEFAULT_REALTIME_TYPE,
    RealtimeWatchlist,
)

from .watchlist_registration import DEMO_REGISTRATION_GROUP_NO

DEMO_UNREGISTRATION_GROUP_NO = DEMO_REGISTRATION_GROUP_NO


def build_demo_watchlist_unregistration_request(
    watchlist: RealtimeWatchlist,
) -> dict[str, Any]:
    """Build one demo ``REMOVE`` request without connecting or sending."""

    if not isinstance(watchlist, RealtimeWatchlist):
        raise TypeError("watchlist must be a RealtimeWatchlist.")

    if watchlist.realtime_type != DEFAULT_REALTIME_TYPE:
        raise ValueError(
            f"watchlist.realtime_type must be {DEFAULT_REALTIME_TYPE!r}."
        )

    stock_codes = watchlist.stock_codes
    if not stock_codes:
        raise ValueError(
            "watchlist must contain at least one stock code "
            "for unregistration."
        )

    return build_remove_packet(
        list(stock_codes),
        [DEFAULT_REALTIME_TYPE],
        group_no=DEMO_UNREGISTRATION_GROUP_NO,
    )
