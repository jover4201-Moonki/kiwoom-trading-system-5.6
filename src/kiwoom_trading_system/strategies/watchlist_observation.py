"""Build an immutable strategy-input observation snapshot from Phase 18 state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.screening import RealtimeWatchlist
from kiwoom_trading_system.state import (
    RealtimeTradeState,
    WatchlistRecoveryStatePipelineResult,
)


class WatchlistObservationError(ValueError):
    """Raised when Phase 18 state conflicts with watchlist metadata."""


@dataclass(frozen=True, slots=True)
class WatchlistCandidateObservation:
    """Immutable observation for one watchlist candidate."""

    source_rank: int
    stock_code: str
    stock_name: str
    exchange_scope: str
    realtime_type: str
    states: Mapping[MarketVenue, RealtimeTradeState]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "states",
            MappingProxyType(dict(self.states)),
        )


@dataclass(frozen=True, slots=True)
class WatchlistObservationSnapshot:
    """Immutable ordered strategy-input snapshot for one watchlist."""

    observations: tuple[WatchlistCandidateObservation, ...]
    candidate_count: int
    observed_candidate_count: int
    unobserved_candidate_count: int
    state_count: int
    realtime_type: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observations",
            tuple(self.observations),
        )


def build_watchlist_observation_snapshot(
    watchlist: RealtimeWatchlist,
    result: WatchlistRecoveryStatePipelineResult,
) -> WatchlistObservationSnapshot:
    """Combine watchlist metadata with already-computed Phase 18 states."""

    if not isinstance(watchlist, RealtimeWatchlist):
        raise TypeError("watchlist must be RealtimeWatchlist.")

    if not isinstance(result, WatchlistRecoveryStatePipelineResult):
        raise TypeError(
            "result must be WatchlistRecoveryStatePipelineResult."
        )

    if not isinstance(result.states, Mapping):
        raise WatchlistObservationError(
            "result states must be a mapping."
        )

    candidate_codes = {
        candidate.stock_code
        for candidate in watchlist.candidates
    }
    states_by_code: dict[
        str,
        dict[MarketVenue, RealtimeTradeState],
    ] = {
        candidate.stock_code: {}
        for candidate in watchlist.candidates
    }

    for key, state in result.states.items():
        if not isinstance(key, tuple) or len(key) != 2:
            raise WatchlistObservationError(
                "state key must be (stock_code, venue)."
            )

        stock_code, venue = key

        if stock_code not in candidate_codes:
            raise WatchlistObservationError(
                f"state stock code is not in watchlist: {stock_code!r}."
            )

        if not isinstance(venue, MarketVenue):
            raise WatchlistObservationError(
                "state key venue must be MarketVenue."
            )

        if not isinstance(state, RealtimeTradeState):
            raise WatchlistObservationError(
                "state value must be RealtimeTradeState."
            )

        if state.instrument_code != stock_code:
            raise WatchlistObservationError(
                "state key stock code does not match state instrument code."
            )

        if state.venue != venue:
            raise WatchlistObservationError(
                "state key venue does not match state venue."
            )

        states_by_code[stock_code][venue] = state

    observations = tuple(
        WatchlistCandidateObservation(
            source_rank=candidate.source_rank,
            stock_code=candidate.stock_code,
            stock_name=candidate.stock_name,
            exchange_scope=candidate.exchange_scope,
            realtime_type=watchlist.realtime_type,
            states=states_by_code[candidate.stock_code],
        )
        for candidate in watchlist.candidates
    )
    observed_candidate_count = sum(
        bool(observation.states)
        for observation in observations
    )
    candidate_count = len(observations)

    return WatchlistObservationSnapshot(
        observations=observations,
        candidate_count=candidate_count,
        observed_candidate_count=observed_candidate_count,
        unobserved_candidate_count=(
            candidate_count - observed_candidate_count
        ),
        state_count=sum(
            len(observation.states)
            for observation in observations
        ),
        realtime_type=watchlist.realtime_type,
    )


__all__ = [
    "WatchlistObservationError",
    "WatchlistCandidateObservation",
    "WatchlistObservationSnapshot",
    "build_watchlist_observation_snapshot",
]
