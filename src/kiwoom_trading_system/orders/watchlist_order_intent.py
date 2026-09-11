"""Build an immutable Phase 23 watchlist Order Intent snapshot."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.orders.watchlist_order_permission import (
    WatchlistCandidateOrderPermission,
    WatchlistOrderPermissionDecision,
    WatchlistOrderPermissionSnapshot,
)
from kiwoom_trading_system.risk import WatchlistRiskDecision
from kiwoom_trading_system.strategies import WatchlistSignalDecision


class WatchlistOrderIntentError(ValueError):
    """Raised when a Phase 23 Order Intent evaluation violates the contract."""


class WatchlistOrderIntentSide(str, Enum):
    """Allowed Phase 23 order sides."""

    BUY = "BUY"


class WatchlistOrderIntentStyle(str, Enum):
    """Broker-neutral Phase 23 order styles."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise WatchlistOrderIntentError(
            f"{field_name} must be a string."
        )

    if not value.strip():
        raise WatchlistOrderIntentError(
            f"{field_name} must not be empty or whitespace."
        )


def _validate_nonnegative_count(value: object, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise WatchlistOrderIntentError(
            f"{field_name} must be a non-negative integer."
        )


def _validate_positive_integer(value: object, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise WatchlistOrderIntentError(
            f"{field_name} must be a positive integer."
        )


@dataclass(frozen=True, slots=True)
class WatchlistOrderIntentEvaluation:
    """Immutable planner output for one ORDER_PERMITTED candidate."""

    order_side: WatchlistOrderIntentSide
    order_style: WatchlistOrderIntentStyle
    requested_quantity: int
    limit_price: int | None
    reason_code: str

    def __post_init__(self) -> None:
        if type(self.order_side) is not WatchlistOrderIntentSide:
            raise WatchlistOrderIntentError(
                "order_side must be WatchlistOrderIntentSide."
            )

        if self.order_side is not WatchlistOrderIntentSide.BUY:
            raise WatchlistOrderIntentError(
                "order_side must be BUY."
            )

        if type(self.order_style) is not WatchlistOrderIntentStyle:
            raise WatchlistOrderIntentError(
                "order_style must be WatchlistOrderIntentStyle."
            )

        _validate_positive_integer(
            self.requested_quantity,
            "requested_quantity",
        )

        if self.order_style is WatchlistOrderIntentStyle.MARKET:
            if self.limit_price is not None:
                raise WatchlistOrderIntentError(
                    "MARKET limit_price must be None."
                )
        elif self.order_style is WatchlistOrderIntentStyle.LIMIT:
            _validate_positive_integer(
                self.limit_price,
                "LIMIT limit_price",
            )
        else:
            raise WatchlistOrderIntentError(
                "order_style is not supported."
            )

        _require_nonempty_string(
            self.reason_code,
            "reason_code",
        )


@dataclass(frozen=True, slots=True)
class WatchlistCandidateOrderIntent:
    """Immutable Phase 23 intent for one ORDER_PERMITTED candidate."""

    source_rank: int
    stock_code: str
    stock_name: str
    exchange_scope: str
    realtime_type: str
    signal_decision: WatchlistSignalDecision
    venue: MarketVenue | None
    signal_reason_code: str
    risk_decision: WatchlistRiskDecision
    risk_reason_code: str
    order_permission_decision: WatchlistOrderPermissionDecision
    order_permission_reason_code: str
    order_side: WatchlistOrderIntentSide
    order_style: WatchlistOrderIntentStyle
    requested_quantity: int
    limit_price: int | None
    order_intent_reason_code: str


@dataclass(frozen=True, slots=True)
class WatchlistOrderIntentSnapshot:
    """Immutable ordered Phase 23 Order Intent snapshot."""

    intents: tuple[WatchlistCandidateOrderIntent, ...]
    candidate_count: int
    no_signal_count: int
    risk_checked_count: int
    risk_clear_count: int
    risk_blocked_count: int
    permission_checked_count: int
    order_permitted_count: int
    order_denied_count: int
    intent_planned_count: int
    market_order_count: int
    limit_order_count: int
    realtime_type: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "intents", tuple(self.intents))


def _validate_permission_snapshot(
    snapshot: WatchlistOrderPermissionSnapshot,
) -> None:
    for field_name in (
        "candidate_count",
        "no_signal_count",
        "risk_checked_count",
        "risk_clear_count",
        "risk_blocked_count",
        "permission_checked_count",
        "order_permitted_count",
        "order_denied_count",
    ):
        _validate_nonnegative_count(
            getattr(snapshot, field_name),
            f"snapshot {field_name}",
        )

    _require_nonempty_string(
        snapshot.realtime_type,
        "snapshot realtime_type",
    )

    if len(snapshot.permissions) != snapshot.permission_checked_count:
        raise WatchlistOrderIntentError(
            "snapshot permission_checked_count must match the permissions tuple length."
        )

    if snapshot.candidate_count != (
        snapshot.no_signal_count + snapshot.risk_checked_count
    ):
        raise WatchlistOrderIntentError(
            "candidate_count must equal no_signal_count plus risk_checked_count."
        )

    if snapshot.risk_checked_count != (
        snapshot.risk_clear_count + snapshot.risk_blocked_count
    ):
        raise WatchlistOrderIntentError(
            "risk_checked_count must equal risk_clear_count plus risk_blocked_count."
        )

    if snapshot.permission_checked_count != snapshot.risk_clear_count:
        raise WatchlistOrderIntentError(
            "permission_checked_count must equal risk_clear_count."
        )

    if snapshot.permission_checked_count != (
        snapshot.order_permitted_count + snapshot.order_denied_count
    ):
        raise WatchlistOrderIntentError(
            "permission_checked_count must equal order_permitted_count plus order_denied_count."
        )

    permitted_count = 0
    denied_count = 0
    seen_source_ranks: set[int] = set()

    for candidate in snapshot.permissions:
        if not isinstance(candidate, WatchlistCandidateOrderPermission):
            raise WatchlistOrderIntentError(
                "snapshot permissions must contain WatchlistCandidateOrderPermission."
            )

        _validate_positive_integer(
            candidate.source_rank,
            "candidate source_rank",
        )

        if candidate.source_rank in seen_source_ranks:
            raise WatchlistOrderIntentError(
                "candidate source_rank values must be unique."
            )
        seen_source_ranks.add(candidate.source_rank)

        for field_name in (
            "stock_code",
            "stock_name",
            "exchange_scope",
            "realtime_type",
            "signal_reason_code",
            "risk_reason_code",
            "order_permission_reason_code",
        ):
            _require_nonempty_string(
                getattr(candidate, field_name),
                f"candidate {field_name}",
            )

        if candidate.realtime_type != snapshot.realtime_type:
            raise WatchlistOrderIntentError(
                "candidate realtime_type must match snapshot realtime_type."
            )

        if (
            type(candidate.signal_decision)
            is not WatchlistSignalDecision
            or candidate.signal_decision
            is not WatchlistSignalDecision.ENTRY_CANDIDATE
        ):
            raise WatchlistOrderIntentError(
                "candidate signal_decision must be ENTRY_CANDIDATE."
            )

        if (
            candidate.venue is not None
            and not isinstance(candidate.venue, MarketVenue)
        ):
            raise WatchlistOrderIntentError(
                "candidate venue must be MarketVenue or None."
            )

        if (
            type(candidate.risk_decision)
            is not WatchlistRiskDecision
            or candidate.risk_decision
            is not WatchlistRiskDecision.RISK_CLEAR
        ):
            raise WatchlistOrderIntentError(
                "candidate risk_decision must be RISK_CLEAR."
            )

        if (
            type(candidate.order_permission_decision)
            is not WatchlistOrderPermissionDecision
        ):
            raise WatchlistOrderIntentError(
                "candidate order_permission_decision must be WatchlistOrderPermissionDecision."
            )

        if (
            candidate.order_permission_decision
            is WatchlistOrderPermissionDecision.ORDER_PERMITTED
        ):
            permitted_count += 1
        elif (
            candidate.order_permission_decision
            is WatchlistOrderPermissionDecision.ORDER_DENIED
        ):
            denied_count += 1
        else:
            raise WatchlistOrderIntentError(
                "candidate order_permission_decision is not supported."
            )

    if permitted_count != snapshot.order_permitted_count:
        raise WatchlistOrderIntentError(
            "snapshot order_permitted_count does not match its permissions."
        )

    if denied_count != snapshot.order_denied_count:
        raise WatchlistOrderIntentError(
            "snapshot order_denied_count does not match its permissions."
        )


def _planner_is_async(planner: object) -> bool:
    if inspect.iscoroutinefunction(planner) or inspect.isasyncgenfunction(planner):
        return True

    call = getattr(planner, "__call__", None)
    return (
        inspect.iscoroutinefunction(call)
        or inspect.isasyncgenfunction(call)
    )


def _close_awaitable(value: object) -> None:
    if inspect.iscoroutine(value):
        value.close()


def build_watchlist_order_intent_snapshot(
    snapshot: WatchlistOrderPermissionSnapshot,
    planner: Callable[
        [WatchlistCandidateOrderPermission],
        WatchlistOrderIntentEvaluation,
    ],
) -> WatchlistOrderIntentSnapshot:
    """Plan one broker-neutral intent for each ORDER_PERMITTED candidate."""

    if not isinstance(snapshot, WatchlistOrderPermissionSnapshot):
        raise WatchlistOrderIntentError(
            "snapshot must be WatchlistOrderPermissionSnapshot."
        )

    if not callable(planner):
        raise WatchlistOrderIntentError(
            "planner must be callable."
        )

    if _planner_is_async(planner):
        raise WatchlistOrderIntentError(
            "planner must be synchronous."
        )

    _validate_permission_snapshot(snapshot)

    intents: list[WatchlistCandidateOrderIntent] = []
    market_order_count = 0
    limit_order_count = 0

    for candidate in snapshot.permissions:
        if (
            candidate.order_permission_decision
            is WatchlistOrderPermissionDecision.ORDER_DENIED
        ):
            continue

        try:
            evaluation = planner(candidate)
        except Exception as exc:
            raise WatchlistOrderIntentError(
                "planner raised an exception."
            ) from exc

        if inspect.isawaitable(evaluation):
            _close_awaitable(evaluation)
            raise WatchlistOrderIntentError(
                "planner must not return an awaitable."
            )

        if type(evaluation) is not WatchlistOrderIntentEvaluation:
            raise WatchlistOrderIntentError(
                "planner must return WatchlistOrderIntentEvaluation."
            )

        if evaluation.order_style is WatchlistOrderIntentStyle.MARKET:
            market_order_count += 1
        elif evaluation.order_style is WatchlistOrderIntentStyle.LIMIT:
            limit_order_count += 1
        else:
            raise WatchlistOrderIntentError(
                "evaluation order_style is not supported."
            )

        intents.append(
            WatchlistCandidateOrderIntent(
                source_rank=candidate.source_rank,
                stock_code=candidate.stock_code,
                stock_name=candidate.stock_name,
                exchange_scope=candidate.exchange_scope,
                realtime_type=candidate.realtime_type,
                signal_decision=candidate.signal_decision,
                venue=candidate.venue,
                signal_reason_code=candidate.signal_reason_code,
                risk_decision=candidate.risk_decision,
                risk_reason_code=candidate.risk_reason_code,
                order_permission_decision=candidate.order_permission_decision,
                order_permission_reason_code=candidate.order_permission_reason_code,
                order_side=evaluation.order_side,
                order_style=evaluation.order_style,
                requested_quantity=evaluation.requested_quantity,
                limit_price=evaluation.limit_price,
                order_intent_reason_code=evaluation.reason_code,
            )
        )

    intent_tuple = tuple(intents)
    intent_planned_count = len(intent_tuple)

    if intent_planned_count != snapshot.order_permitted_count:
        raise WatchlistOrderIntentError(
            "intent_planned_count must equal order_permitted_count."
        )

    if (
        market_order_count + limit_order_count
        != intent_planned_count
    ):
        raise WatchlistOrderIntentError(
            "market_order_count plus limit_order_count must equal intent_planned_count."
        )

    return WatchlistOrderIntentSnapshot(
        intents=intent_tuple,
        candidate_count=snapshot.candidate_count,
        no_signal_count=snapshot.no_signal_count,
        risk_checked_count=snapshot.risk_checked_count,
        risk_clear_count=snapshot.risk_clear_count,
        risk_blocked_count=snapshot.risk_blocked_count,
        permission_checked_count=snapshot.permission_checked_count,
        order_permitted_count=snapshot.order_permitted_count,
        order_denied_count=snapshot.order_denied_count,
        intent_planned_count=intent_planned_count,
        market_order_count=market_order_count,
        limit_order_count=limit_order_count,
        realtime_type=snapshot.realtime_type,
    )


__all__ = [
    "WatchlistOrderIntentError",
    "WatchlistOrderIntentSide",
    "WatchlistOrderIntentStyle",
    "WatchlistOrderIntentEvaluation",
    "WatchlistCandidateOrderIntent",
    "WatchlistOrderIntentSnapshot",
    "build_watchlist_order_intent_snapshot",
]
