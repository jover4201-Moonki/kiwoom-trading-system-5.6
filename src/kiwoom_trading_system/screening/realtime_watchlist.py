from __future__ import annotations

from dataclasses import dataclass

from .volume_ranking import VolumeRankingResult


DEFAULT_REALTIME_TYPE = "0B"


@dataclass(frozen=True, slots=True)
class RealtimeWatchCandidate:
    source_rank: int
    stock_code: str
    stock_name: str
    exchange_scope: str


@dataclass(frozen=True, slots=True)
class RealtimeWatchlistMetrics:
    input_candidate_count: int
    accepted_candidate_count: int
    invalid_code_count: int
    duplicate_code_count: int


@dataclass(frozen=True, slots=True)
class RealtimeWatchlist:
    candidates: tuple[RealtimeWatchCandidate, ...]
    metrics: RealtimeWatchlistMetrics
    realtime_type: str = DEFAULT_REALTIME_TYPE

    @property
    def stock_codes(self) -> tuple[str, ...]:
        return tuple(
            candidate.stock_code
            for candidate in self.candidates
        )


def _is_six_ascii_digits(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 6
        and value.isascii()
        and value.isdigit()
    )


def build_realtime_watchlist(
    ranking_result: VolumeRankingResult,
) -> RealtimeWatchlist:
    if not isinstance(ranking_result, VolumeRankingResult):
        raise TypeError(
            "ranking_result must be a VolumeRankingResult."
        )

    accepted: list[RealtimeWatchCandidate] = []
    seen_codes: set[str] = set()
    invalid_code_count = 0
    duplicate_code_count = 0

    for source_rank, candidate in enumerate(
        ranking_result.candidates,
        start=1,
    ):
        stock_code = candidate.stock_code

        if not _is_six_ascii_digits(stock_code):
            invalid_code_count += 1
            continue

        if stock_code in seen_codes:
            duplicate_code_count += 1
            continue

        seen_codes.add(stock_code)
        accepted.append(
            RealtimeWatchCandidate(
                source_rank=source_rank,
                stock_code=stock_code,
                stock_name=candidate.stock_name,
                exchange_scope=candidate.exchange_scope,
            )
        )

    metrics = RealtimeWatchlistMetrics(
        input_candidate_count=len(
            ranking_result.candidates
        ),
        accepted_candidate_count=len(accepted),
        invalid_code_count=invalid_code_count,
        duplicate_code_count=duplicate_code_count,
    )

    return RealtimeWatchlist(
        candidates=tuple(accepted),
        metrics=metrics,
    )


__all__ = [
    "DEFAULT_REALTIME_TYPE",
    "RealtimeWatchCandidate",
    "RealtimeWatchlistMetrics",
    "RealtimeWatchlist",
    "build_realtime_watchlist",
]
