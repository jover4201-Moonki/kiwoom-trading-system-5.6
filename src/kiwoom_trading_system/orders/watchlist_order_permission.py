"""Build an immutable Phase 22 watchlist Order Permission snapshot."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.risk import (
    WatchlistCandidateRisk,
    WatchlistRiskDecision,
    WatchlistRiskSnapshot,
)
from kiwoom_trading_system.strategies import WatchlistSignalDecision


class WatchlistOrderPermissionError(ValueError):
    """Raised when a Phase 22 Order Permission evaluation violates the contract."""


class WatchlistOrderPermissionDecision(str, Enum):
    """Allowed Phase 22 Order Permission decisions."""

    ORDER_PERMITTED = "ORDER_PERMITTED"
    ORDER_DENIED = "ORDER_DENIED"


@dataclass(frozen=True, slots=True)
class WatchlistOrderPermissionEvaluation:
    """Immutable checker output for one Risk Clear candidate."""

    decision: WatchlistOrderPermissionDecision
    reason_code: str


@dataclass(frozen=True, slots=True)
class WatchlistCandidateOrderPermission:
    """Immutable Phase 22 result for one Phase 21 Risk Clear candidate."""

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


@dataclass(frozen=True, slots=True)
class WatchlistOrderPermissionSnapshot:
    """Immutable ordered Phase 22 Order Permission snapshot."""

    permissions: tuple[WatchlistCandidateOrderPermission, ...]
    candidate_count: int
    no_signal_count: int
    risk_checked_count: int
    risk_clear_count: int
    risk_blocked_count: int
    permission_checked_count: int
    order_permitted_count: int
    order_denied_count: int
    realtime_type: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "permissions", tuple(self.permissions))


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise WatchlistOrderPermissionError(
            f"{field_name} must be a string."
        )

    if not value.strip():
        raise WatchlistOrderPermissionError(
            f"{field_name} must not be empty or whitespace."
        )


def _validate_nonnegative_count(value: object, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise WatchlistOrderPermissionError(
            f"{field_name} must be a non-negative integer."
        )


def _validate_risk_snapshot(snapshot: WatchlistRiskSnapshot) -> None:
    for field_name in (
        "candidate_count",
        "no_signal_count",
        "risk_checked_count",
        "risk_clear_count",
        "risk_blocked_count",
    ):
        _validate_nonnegative_count(
            getattr(snapshot, field_name),
            f"snapshot {field_name}",
        )

    _require_nonempty_string(snapshot.realtime_type, "snapshot realtime_type")

    if len(snapshot.risks) != snapshot.candidate_count:
        raise WatchlistOrderPermissionError(
            "snapshot candidate_count must match the risk tuple length."
        )

    no_signal_count = 0
    risk_checked_count = 0
    risk_clear_count = 0
    risk_blocked_count = 0
    seen_source_ranks: set[int] = set()

    for candidate in snapshot.risks:
        if not isinstance(candidate, WatchlistCandidateRisk):
            raise WatchlistOrderPermissionError(
                "snapshot risks must contain WatchlistCandidateRisk."
            )

        if type(candidate.source_rank) is not int or candidate.source_rank <= 0:
            raise WatchlistOrderPermissionError(
                "candidate source_rank must be a positive integer."
            )

        if candidate.source_rank in seen_source_ranks:
            raise WatchlistOrderPermissionError(
                "candidate source_rank values must be unique."
            )
        seen_source_ranks.add(candidate.source_rank)

        for field_name in (
            "stock_code",
            "stock_name",
            "exchange_scope",
            "realtime_type",
            "signal_reason_code",
        ):
            _require_nonempty_string(
                getattr(candidate, field_name),
                f"candidate {field_name}",
            )

        if candidate.realtime_type != snapshot.realtime_type:
            raise WatchlistOrderPermissionError(
                "candidate realtime_type must match snapshot realtime_type."
            )

        if type(candidate.signal_decision) is not WatchlistSignalDecision:
            raise WatchlistOrderPermissionError(
                "candidate signal_decision must be WatchlistSignalDecision."
            )

        if (
            candidate.venue is not None
            and not isinstance(candidate.venue, MarketVenue)
        ):
            raise WatchlistOrderPermissionError(
                "candidate venue must be MarketVenue or None."
            )

        if candidate.signal_decision is WatchlistSignalDecision.NO_SIGNAL:
            no_signal_count += 1

            if candidate.risk_decision is not None:
                raise WatchlistOrderPermissionError(
                    "NO_SIGNAL candidate risk_decision must be None."
                )

            if candidate.risk_reason_code is not None:
                raise WatchlistOrderPermissionError(
                    "NO_SIGNAL candidate risk_reason_code must be None."
                )

            continue

        if candidate.signal_decision is not WatchlistSignalDecision.ENTRY_CANDIDATE:
            raise WatchlistOrderPermissionError(
                "candidate signal_decision is not supported."
            )

        risk_checked_count += 1

        if type(candidate.risk_decision) is not WatchlistRiskDecision:
            raise WatchlistOrderPermissionError(
                "entry candidate risk_decision must be WatchlistRiskDecision."
            )

        _require_nonempty_string(
            candidate.risk_reason_code,
            "candidate risk_reason_code",
        )

        if candidate.risk_decision is WatchlistRiskDecision.RISK_CLEAR:
            risk_clear_count += 1
        elif candidate.risk_decision is WatchlistRiskDecision.RISK_BLOCKED:
            risk_blocked_count += 1
        else:
            raise WatchlistOrderPermissionError(
                "candidate risk_decision is not supported."
            )

    if snapshot.no_signal_count != no_signal_count:
        raise WatchlistOrderPermissionError(
            "snapshot no_signal_count does not match its risks."
        )

    if snapshot.risk_checked_count != risk_checked_count:
        raise WatchlistOrderPermissionError(
            "snapshot risk_checked_count does not match its risks."
        )

    if snapshot.risk_clear_count != risk_clear_count:
        raise WatchlistOrderPermissionError(
            "snapshot risk_clear_count does not match its risks."
        )

    if snapshot.risk_blocked_count != risk_blocked_count:
        raise WatchlistOrderPermissionError(
            "snapshot risk_blocked_count does not match its risks."
        )

    if snapshot.risk_checked_count != (
        snapshot.risk_clear_count + snapshot.risk_blocked_count
    ):
        raise WatchlistOrderPermissionError(
            "risk_checked_count must equal risk_clear_count plus risk_blocked_count."
        )

    if snapshot.candidate_count != (
        snapshot.no_signal_count + snapshot.risk_checked_count
    ):
        raise WatchlistOrderPermissionError(
            "candidate_count must equal no_signal_count plus risk_checked_count."
        )


def build_watchlist_order_permission_snapshot(
    snapshot: WatchlistRiskSnapshot,
    checker: Callable[
        [WatchlistCandidateRisk],
        WatchlistOrderPermissionEvaluation,
    ],
) -> WatchlistOrderPermissionSnapshot:
    """Evaluate every Phase 21 Risk Clear candidate exactly once."""

    if not isinstance(snapshot, WatchlistRiskSnapshot):
        raise WatchlistOrderPermissionError(
            "snapshot must be WatchlistRiskSnapshot."
        )

    if not callable(checker):
        raise WatchlistOrderPermissionError(
            "checker must be callable."
        )

    _validate_risk_snapshot(snapshot)

    permissions: list[WatchlistCandidateOrderPermission] = []
    order_permitted_count = 0
    order_denied_count = 0

    for candidate in snapshot.risks:
        if candidate.risk_decision is not WatchlistRiskDecision.RISK_CLEAR:
            continue

        try:
            evaluation = checker(candidate)
        except Exception as exc:
            raise WatchlistOrderPermissionError(
                "checker raised an exception."
            ) from exc

        if type(evaluation) is not WatchlistOrderPermissionEvaluation:
            raise WatchlistOrderPermissionError(
                "checker must return WatchlistOrderPermissionEvaluation."
            )

        if type(evaluation.decision) is not WatchlistOrderPermissionDecision:
            raise WatchlistOrderPermissionError(
                "evaluation decision must be WatchlistOrderPermissionDecision."
            )

        _require_nonempty_string(
            evaluation.reason_code,
            "reason_code",
        )

        if (
            evaluation.decision
            is WatchlistOrderPermissionDecision.ORDER_PERMITTED
        ):
            order_permitted_count += 1
        elif (
            evaluation.decision
            is WatchlistOrderPermissionDecision.ORDER_DENIED
        ):
            order_denied_count += 1
        else:
            raise WatchlistOrderPermissionError(
                "evaluation decision is not supported."
            )

        permissions.append(
            WatchlistCandidateOrderPermission(
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
                order_permission_decision=evaluation.decision,
                order_permission_reason_code=evaluation.reason_code,
            )
        )

    permission_tuple = tuple(permissions)
    permission_checked_count = len(permission_tuple)

    if permission_checked_count != snapshot.risk_clear_count:
        raise WatchlistOrderPermissionError(
            "permission_checked_count must equal risk_clear_count."
        )

    if permission_checked_count != (
        order_permitted_count + order_denied_count
    ):
        raise WatchlistOrderPermissionError(
            "permission_checked_count must equal order_permitted_count plus order_denied_count."
        )

    return WatchlistOrderPermissionSnapshot(
        permissions=permission_tuple,
        candidate_count=snapshot.candidate_count,
        no_signal_count=snapshot.no_signal_count,
        risk_checked_count=snapshot.risk_checked_count,
        risk_clear_count=snapshot.risk_clear_count,
        risk_blocked_count=snapshot.risk_blocked_count,
        permission_checked_count=permission_checked_count,
        order_permitted_count=order_permitted_count,
        order_denied_count=order_denied_count,
        realtime_type=snapshot.realtime_type,
    )


__all__ = [
    "WatchlistOrderPermissionError",
    "WatchlistOrderPermissionDecision",
    "WatchlistOrderPermissionEvaluation",
    "WatchlistCandidateOrderPermission",
    "WatchlistOrderPermissionSnapshot",
    "build_watchlist_order_permission_snapshot",
]
