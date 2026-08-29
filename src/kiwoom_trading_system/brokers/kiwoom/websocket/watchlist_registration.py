"""Pure conversion from a demo realtime watchlist to a REG request."""

from __future__ import annotations

from typing import Any

from kiwoom.realtime import build_reg_packet

from kiwoom_trading_system.screening import (
    DEFAULT_REALTIME_TYPE,
    RealtimeWatchlist,
)

DEMO_REGISTRATION_GROUP_NO = "1"
DEMO_REGISTRATION_REFRESH = "1"


def build_demo_watchlist_registration_request(
    watchlist: RealtimeWatchlist,
) -> dict[str, Any]:
    """Build one demo ``REG`` request without connecting or sending."""

    if not isinstance(watchlist, RealtimeWatchlist):
        raise TypeError("watchlist must be a RealtimeWatchlist.")

    if watchlist.realtime_type != DEFAULT_REALTIME_TYPE:
        raise ValueError(
            f"watchlist.realtime_type must be {DEFAULT_REALTIME_TYPE!r}."
        )

    return build_reg_packet(
        list(watchlist.stock_codes),
        [DEFAULT_REALTIME_TYPE],
        group_no=DEMO_REGISTRATION_GROUP_NO,
        refresh=DEMO_REGISTRATION_REFRESH,
    )
