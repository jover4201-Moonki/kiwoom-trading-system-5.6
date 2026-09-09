from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from types import MappingProxyType

import kiwoom_trading_system.strategies as strategies_package
from kiwoom_trading_system.market_data import (
    MarketVenue,
    normalize_trade_packet,
)
from kiwoom_trading_system.screening import (
    RealtimeWatchCandidate,
    RealtimeWatchlist,
    RealtimeWatchlistMetrics,
)
from kiwoom_trading_system.state import (
    WatchlistRecoveryStatePipelineMetrics,
    WatchlistRecoveryStatePipelineResult,
    update_realtime_trade_state,
)
from kiwoom_trading_system.strategies import (
    watchlist_observation as observation,
)


NOW = datetime(2026, 8, 31, tzinfo=UTC)


def _candidate(
    rank: int,
    code: str,
    *,
    name: str | None = None,
    exchange_scope: str = "0",
) -> RealtimeWatchCandidate:
    return RealtimeWatchCandidate(
        source_rank=rank,
        stock_code=code,
        stock_name=name or f"stock-{rank}",
        exchange_scope=exchange_scope,
    )


def _watchlist(
    *candidates: RealtimeWatchCandidate,
) -> RealtimeWatchlist:
    return RealtimeWatchlist(
        candidates=tuple(candidates),
        metrics=RealtimeWatchlistMetrics(
            input_candidate_count=len(candidates),
            accepted_candidate_count=len(candidates),
            invalid_code_count=0,
            duplicate_code_count=0,
        ),
    )


def _state(item: str):
    packet = {
        "trnm": "REAL",
        "data": [
            {
                "type": "0B",
                "name": "stock trade",
                "item": item,
                "values": {
                    "20": "090000",
                    "10": "+100",
                    "15": "+1",
                },
            }
        ],
    }
    trade = normalize_trade_packet(
        packet,
        received_at=NOW,
    )[0]
    return update_realtime_trade_state(
        None,
        trade,
    )


def _result(states):
    return WatchlistRecoveryStatePipelineResult(
        baseline_summary=MappingProxyType(
            {"mode": "demo"}
        ),
        states=MappingProxyType(states),
        metrics=WatchlistRecoveryStatePipelineMetrics(
            realtime_packets=0,
            normalized_trades=0,
            normalization_errors=0,
            normalization_error_messages=(),
            state_updates=0,
            state_errors=0,
            state_error_messages=(),
        ),
    )


class WatchlistObservationTests(unittest.TestCase):
    def test_single_candidate_krx_snapshot_counts(self):
        watchlist = _watchlist(
            _candidate(1, "005930")
        )
        state = _state("005930")
        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({
                ("005930", MarketVenue.KRX): state
            }),
        )

        self.assertEqual(snapshot.candidate_count, 1)
        self.assertEqual(snapshot.observed_candidate_count, 1)
        self.assertEqual(snapshot.unobserved_candidate_count, 0)
        self.assertEqual(snapshot.state_count, 1)
        self.assertIs(
            snapshot.observations[0].states[MarketVenue.KRX],
            state,
        )

    def test_multiple_candidates_preserve_order(self):
        watchlist = _watchlist(
            _candidate(2, "000660"),
            _candidate(1, "005930"),
        )
        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({}),
        )

        self.assertEqual(
            tuple(item.stock_code for item in snapshot.observations),
            ("000660", "005930"),
        )

    def test_source_rank_is_preserved(self):
        watchlist = _watchlist(
            _candidate(7, "005930")
        )
        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({}),
        )

        self.assertEqual(snapshot.observations[0].source_rank, 7)

    def test_stock_name_is_preserved(self):
        watchlist = _watchlist(
            _candidate(
                1,
                "005930",
                name="Samsung Electronics",
            )
        )
        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({}),
        )

        self.assertEqual(
            snapshot.observations[0].stock_name,
            "Samsung Electronics",
        )

    def test_exchange_scope_is_preserved(self):
        watchlist = _watchlist(
            _candidate(
                1,
                "005930",
                exchange_scope="1",
            )
        )
        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({}),
        )

        self.assertEqual(
            snapshot.observations[0].exchange_scope,
            "1",
        )

    def test_realtime_type_is_preserved(self):
        watchlist = _watchlist(
            _candidate(1, "005930")
        )
        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({}),
        )

        self.assertEqual(
            snapshot.realtime_type,
            watchlist.realtime_type,
        )
        self.assertEqual(
            snapshot.observations[0].realtime_type,
            watchlist.realtime_type,
        )

    def test_krx_nxt_sor_states_are_separated(self):
        watchlist = _watchlist(
            _candidate(1, "005930")
        )
        krx = _state("005930")
        nxt = _state("005930_NX")
        sor = _state("005930_AL")

        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({
                ("005930", MarketVenue.KRX): krx,
                ("005930", MarketVenue.NXT): nxt,
                ("005930", MarketVenue.SOR): sor,
            }),
        )

        states = snapshot.observations[0].states
        self.assertEqual(
            set(states),
            {
                MarketVenue.KRX,
                MarketVenue.NXT,
                MarketVenue.SOR,
            },
        )
        self.assertEqual(snapshot.state_count, 3)

    def test_candidate_without_state_is_retained(self):
        watchlist = _watchlist(
            _candidate(1, "005930"),
            _candidate(2, "000660"),
        )
        state = _state("005930")

        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({
                ("005930", MarketVenue.KRX): state
            }),
        )

        self.assertEqual(snapshot.candidate_count, 2)
        self.assertEqual(snapshot.observed_candidate_count, 1)
        self.assertEqual(snapshot.unobserved_candidate_count, 1)
        self.assertEqual(dict(snapshot.observations[1].states), {})

    def test_unexpected_state_instrument_is_rejected(self):
        watchlist = _watchlist(
            _candidate(1, "005930")
        )
        state = _state("000660")

        with self.assertRaisesRegex(
            observation.WatchlistObservationError,
            "not in watchlist",
        ):
            observation.build_watchlist_observation_snapshot(
                watchlist,
                _result({
                    ("000660", MarketVenue.KRX): state
                }),
            )

    def test_state_key_code_mismatch_is_rejected(self):
        watchlist = _watchlist(
            _candidate(1, "005930"),
            _candidate(2, "000660"),
        )
        state = _state("000660")

        with self.assertRaisesRegex(
            observation.WatchlistObservationError,
            "stock code",
        ):
            observation.build_watchlist_observation_snapshot(
                watchlist,
                _result({
                    ("005930", MarketVenue.KRX): state
                }),
            )

    def test_state_key_venue_mismatch_is_rejected(self):
        watchlist = _watchlist(
            _candidate(1, "005930")
        )
        state = _state("005930_NX")

        with self.assertRaisesRegex(
            observation.WatchlistObservationError,
            "venue",
        ):
            observation.build_watchlist_observation_snapshot(
                watchlist,
                _result({
                    ("005930", MarketVenue.KRX): state
                }),
            )

    def test_wrong_watchlist_type_raises_type_error(self):
        with self.assertRaisesRegex(
            TypeError,
            "watchlist",
        ):
            observation.build_watchlist_observation_snapshot(
                object(),
                _result({}),
            )

    def test_wrong_result_type_raises_type_error(self):
        watchlist = _watchlist(
            _candidate(1, "005930")
        )

        with self.assertRaisesRegex(
            TypeError,
            "result",
        ):
            observation.build_watchlist_observation_snapshot(
                watchlist,
                object(),
            )

    def test_inputs_are_not_mutated(self):
        watchlist = _watchlist(
            _candidate(1, "005930")
        )
        state = _state("005930")
        source_states = {
            ("005930", MarketVenue.KRX): state
        }
        result = _result(source_states)
        candidates_before = tuple(watchlist.candidates)
        states_before = dict(result.states)

        observation.build_watchlist_observation_snapshot(
            watchlist,
            result,
        )

        self.assertEqual(
            tuple(watchlist.candidates),
            candidates_before,
        )
        self.assertEqual(
            dict(result.states),
            states_before,
        )

    def test_outputs_are_immutable(self):
        watchlist = _watchlist(
            _candidate(1, "005930")
        )
        state = _state("005930")
        snapshot = observation.build_watchlist_observation_snapshot(
            watchlist,
            _result({
                ("005930", MarketVenue.KRX): state
            }),
        )
        candidate = snapshot.observations[0]

        self.assertIsInstance(snapshot.observations, tuple)
        with self.assertRaises(FrozenInstanceError):
            snapshot.candidate_count = 99
        with self.assertRaises(TypeError):
            candidate.states[MarketVenue.NXT] = state

    def test_public_exports_reference_module_objects(self):
        self.assertIs(
            strategies_package.WatchlistObservationError,
            observation.WatchlistObservationError,
        )
        self.assertIs(
            strategies_package.WatchlistCandidateObservation,
            observation.WatchlistCandidateObservation,
        )
        self.assertIs(
            strategies_package.WatchlistObservationSnapshot,
            observation.WatchlistObservationSnapshot,
        )
        self.assertIs(
            strategies_package.build_watchlist_observation_snapshot,
            observation.build_watchlist_observation_snapshot,
        )


if __name__ == "__main__":
    unittest.main()
