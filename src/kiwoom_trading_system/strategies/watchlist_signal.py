"""Build an immutable Phase 20 watchlist entry-signal candidate snapshot."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from kiwoom_trading_system.market_data import MarketVenue

from .watchlist_observation import (
    WatchlistCandidateObservation,
    WatchlistObservationSnapshot,
)


class WatchlistSignalError(ValueError):
    """Raised when a Phase 20 signal evaluation violates the contract."""


class WatchlistSignalDecision(str, Enum):
    """Allowed Phase 20 candidate decisions."""

    NO_SIGNAL = "NO_SIGNAL"
    ENTRY_CANDIDATE = "ENTRY_CANDIDATE"


@dataclass(frozen=True, slots=True)
class WatchlistSignalEvaluation:
    """Immutable evaluator output for one candidate observation."""

    decision: WatchlistSignalDecision
    venue: MarketVenue | None
    reason_code: str


@dataclass(frozen=True, slots=True)
class WatchlistCandidateSignal:
    """Immutable Phase 20 result for one watchlist candidate."""

    source_rank: int
    stock_code: str
    stock_name: str
    exchange_scope: str
    realtime_type: str
    decision: WatchlistSignalDecision
    venue: MarketVenue | None
    reason_code: str


@dataclass(frozen=True, slots=True)
class WatchlistSignalSnapshot:
    """Immutable ordered Phase 20 signal snapshot."""

    signals: tuple[WatchlistCandidateSignal, ...]
    candidate_count: int
    no_signal_count: int
    entry_candidate_count: int
    realtime_type: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "signals",
            tuple(self.signals),
        )


def build_watchlist_signal_snapshot(
    snapshot: WatchlistObservationSnapshot,
    evaluator: Callable[
        [WatchlistCandidateObservation],
        WatchlistSignalEvaluation,
    ],
) -> WatchlistSignalSnapshot:
    """Evaluate each Phase 19 observation exactly once without trading."""

    if not isinstance(snapshot, WatchlistObservationSnapshot):
        raise TypeError(
            "snapshot must be WatchlistObservationSnapshot."
        )

    if not callable(evaluator):
        raise TypeError("evaluator must be callable.")

    signals: list[WatchlistCandidateSignal] = []

    for observation in snapshot.observations:
        evaluation = evaluator(observation)

        if not isinstance(
            evaluation,
            WatchlistSignalEvaluation,
        ):
            raise TypeError(
                "evaluator must return WatchlistSignalEvaluation."
            )

        if not isinstance(
            evaluation.decision,
            WatchlistSignalDecision,
        ):
            raise WatchlistSignalError(
                "evaluation decision must be WatchlistSignalDecision."
            )

        if not isinstance(evaluation.reason_code, str):
            raise WatchlistSignalError(
                "reason_code must be a string."
            )

        if not evaluation.reason_code.strip():
            raise WatchlistSignalError(
                "reason_code must not be empty or whitespace."
            )

        if (
            evaluation.decision
            is WatchlistSignalDecision.NO_SIGNAL
        ):
            if evaluation.venue is not None:
                raise WatchlistSignalError(
                    "NO_SIGNAL requires venue=None."
                )
        else:
            if not isinstance(
                evaluation.venue,
                MarketVenue,
            ):
                raise WatchlistSignalError(
                    "ENTRY_CANDIDATE venue must be MarketVenue."
                )

            if not observation.states:
                raise WatchlistSignalError(
                    "ENTRY_CANDIDATE requires an observed state."
                )

            if evaluation.venue not in observation.states:
                raise WatchlistSignalError(
                    "ENTRY_CANDIDATE venue must exist in "
                    "observation.states."
                )

        signals.append(
            WatchlistCandidateSignal(
                source_rank=observation.source_rank,
                stock_code=observation.stock_code,
                stock_name=observation.stock_name,
                exchange_scope=observation.exchange_scope,
                realtime_type=observation.realtime_type,
                decision=evaluation.decision,
                venue=evaluation.venue,
                reason_code=evaluation.reason_code,
            )
        )

    signal_tuple = tuple(signals)

    no_signal_count = sum(
        signal.decision is WatchlistSignalDecision.NO_SIGNAL
        for signal in signal_tuple
    )

    entry_candidate_count = sum(
        signal.decision
        is WatchlistSignalDecision.ENTRY_CANDIDATE
        for signal in signal_tuple
    )

    return WatchlistSignalSnapshot(
        signals=signal_tuple,
        candidate_count=snapshot.candidate_count,
        no_signal_count=no_signal_count,
        entry_candidate_count=entry_candidate_count,
        realtime_type=snapshot.realtime_type,
    )


__all__ = [
    "WatchlistSignalError",
    "WatchlistSignalDecision",
    "WatchlistSignalEvaluation",
    "WatchlistCandidateSignal",
    "WatchlistSignalSnapshot",
    "build_watchlist_signal_snapshot",
]
