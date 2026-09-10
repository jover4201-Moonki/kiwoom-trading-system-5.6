"""Build an immutable Phase 21 watchlist Risk Check snapshot."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.strategies import (
    WatchlistCandidateSignal,
    WatchlistSignalDecision,
    WatchlistSignalSnapshot,
)


class WatchlistRiskError(ValueError):
    """Raised when a Phase 21 risk evaluation violates the contract."""


class WatchlistRiskDecision(str, Enum):
    """Allowed Phase 21 Risk Check decisions."""

    RISK_CLEAR = "RISK_CLEAR"
    RISK_BLOCKED = "RISK_BLOCKED"


@dataclass(frozen=True, slots=True)
class WatchlistRiskEvaluation:
    """Immutable checker output for one entry candidate."""

    decision: WatchlistRiskDecision
    reason_code: str


@dataclass(frozen=True, slots=True)
class WatchlistCandidateRisk:
    """Immutable Phase 21 result for one Phase 20 signal candidate."""

    source_rank: int
    stock_code: str
    stock_name: str
    exchange_scope: str
    realtime_type: str
    signal_decision: WatchlistSignalDecision
    venue: MarketVenue | None
    signal_reason_code: str
    risk_decision: WatchlistRiskDecision | None
    risk_reason_code: str | None


@dataclass(frozen=True, slots=True)
class WatchlistRiskSnapshot:
    """Immutable ordered Phase 21 Risk Check snapshot."""

    risks: tuple[WatchlistCandidateRisk, ...]
    candidate_count: int
    no_signal_count: int
    risk_checked_count: int
    risk_clear_count: int
    risk_blocked_count: int
    realtime_type: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "risks", tuple(self.risks))


def _validate_signal_snapshot(snapshot: WatchlistSignalSnapshot) -> None:
    if len(snapshot.signals) != snapshot.candidate_count:
        raise WatchlistRiskError(
            "snapshot candidate_count must match the signal tuple length."
        )

    no_signal_count = 0
    entry_candidate_count = 0

    for candidate in snapshot.signals:
        if not isinstance(candidate, WatchlistCandidateSignal):
            raise TypeError(
                "snapshot signals must contain WatchlistCandidateSignal."
            )

        if not isinstance(candidate.decision, WatchlistSignalDecision):
            raise TypeError(
                "candidate signal_decision must be WatchlistSignalDecision."
            )

        if candidate.decision is WatchlistSignalDecision.NO_SIGNAL:
            no_signal_count += 1
        elif candidate.decision is WatchlistSignalDecision.ENTRY_CANDIDATE:
            entry_candidate_count += 1

    if snapshot.no_signal_count != no_signal_count:
        raise WatchlistRiskError(
            "snapshot no_signal_count does not match its signals."
        )

    if snapshot.entry_candidate_count != entry_candidate_count:
        raise WatchlistRiskError(
            "snapshot entry_candidate_count does not match its signals."
        )

    if snapshot.candidate_count != no_signal_count + entry_candidate_count:
        raise WatchlistRiskError(
            "snapshot counts violate the Phase 20 arithmetic invariant."
        )


def build_watchlist_risk_snapshot(
    snapshot: WatchlistSignalSnapshot,
    checker: Callable[[WatchlistCandidateSignal], WatchlistRiskEvaluation],
) -> WatchlistRiskSnapshot:
    """Risk Check every Phase 20 entry candidate exactly once."""

    if not isinstance(snapshot, WatchlistSignalSnapshot):
        raise TypeError("snapshot must be WatchlistSignalSnapshot.")

    if not callable(checker):
        raise TypeError("checker must be callable.")

    _validate_signal_snapshot(snapshot)

    risks: list[WatchlistCandidateRisk] = []
    risk_clear_count = 0
    risk_blocked_count = 0

    for candidate in snapshot.signals:
        if candidate.decision is WatchlistSignalDecision.NO_SIGNAL:
            risk_decision = None
            risk_reason_code = None
        else:
            evaluation = checker(candidate)

            if type(evaluation) is not WatchlistRiskEvaluation:
                raise TypeError(
                    "checker must return WatchlistRiskEvaluation."
                )

            if type(evaluation.decision) is not WatchlistRiskDecision:
                raise TypeError(
                    "evaluation decision must be WatchlistRiskDecision."
                )

            if not isinstance(evaluation.reason_code, str):
                raise WatchlistRiskError("reason_code must be a string.")

            if not evaluation.reason_code.strip():
                raise WatchlistRiskError(
                    "reason_code must not be empty or whitespace."
                )

            risk_decision = evaluation.decision
            risk_reason_code = evaluation.reason_code

            if risk_decision is WatchlistRiskDecision.RISK_CLEAR:
                risk_clear_count += 1
            else:
                risk_blocked_count += 1

        risks.append(
            WatchlistCandidateRisk(
                source_rank=candidate.source_rank,
                stock_code=candidate.stock_code,
                stock_name=candidate.stock_name,
                exchange_scope=candidate.exchange_scope,
                realtime_type=candidate.realtime_type,
                signal_decision=candidate.decision,
                venue=candidate.venue,
                signal_reason_code=candidate.reason_code,
                risk_decision=risk_decision,
                risk_reason_code=risk_reason_code,
            )
        )

    risk_tuple = tuple(risks)
    no_signal_count = sum(
        item.signal_decision is WatchlistSignalDecision.NO_SIGNAL
        for item in risk_tuple
    )
    risk_checked_count = risk_clear_count + risk_blocked_count

    if snapshot.entry_candidate_count != risk_checked_count:
        raise WatchlistRiskError(
            "Phase 20 entry_candidate_count must equal risk_checked_count."
        )

    if snapshot.candidate_count != no_signal_count + risk_checked_count:
        raise WatchlistRiskError(
            "candidate_count must equal no_signal_count plus risk_checked_count."
        )

    return WatchlistRiskSnapshot(
        risks=risk_tuple,
        candidate_count=snapshot.candidate_count,
        no_signal_count=no_signal_count,
        risk_checked_count=risk_checked_count,
        risk_clear_count=risk_clear_count,
        risk_blocked_count=risk_blocked_count,
        realtime_type=snapshot.realtime_type,
    )


__all__ = [
    "WatchlistRiskError",
    "WatchlistRiskDecision",
    "WatchlistRiskEvaluation",
    "WatchlistCandidateRisk",
    "WatchlistRiskSnapshot",
    "build_watchlist_risk_snapshot",
]
