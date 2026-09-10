from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

import kiwoom_trading_system.strategies as strategies_package
from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.strategies import (
    watchlist_observation as observation,
)
from kiwoom_trading_system.strategies import (
    watchlist_signal as signal,
)


def _observation(
    rank: int,
    code: str,
    *,
    name: str | None = None,
    exchange_scope: str = "0",
    realtime_type: str = "0B",
    venues: tuple[MarketVenue, ...] = (),
) -> observation.WatchlistCandidateObservation:
    return observation.WatchlistCandidateObservation(
        source_rank=rank,
        stock_code=code,
        stock_name=name or f"stock-{rank}",
        exchange_scope=exchange_scope,
        realtime_type=realtime_type,
        states={
            venue: object()
            for venue in venues
        },
    )


def _snapshot(
    *items: observation.WatchlistCandidateObservation,
    realtime_type: str = "0B",
) -> observation.WatchlistObservationSnapshot:
    observed = sum(bool(item.states) for item in items)

    return observation.WatchlistObservationSnapshot(
        observations=tuple(items),
        candidate_count=len(items),
        observed_candidate_count=observed,
        unobserved_candidate_count=len(items) - observed,
        state_count=sum(len(item.states) for item in items),
        realtime_type=realtime_type,
    )


def _no_signal(
    reason_code: str = "NO_RULE_MATCH",
    *,
    venue=None,
) -> signal.WatchlistSignalEvaluation:
    return signal.WatchlistSignalEvaluation(
        decision=signal.WatchlistSignalDecision.NO_SIGNAL,
        venue=venue,
        reason_code=reason_code,
    )


def _entry(
    venue,
    reason_code: str = "RULE_MATCH",
) -> signal.WatchlistSignalEvaluation:
    return signal.WatchlistSignalEvaluation(
        decision=signal.WatchlistSignalDecision.ENTRY_CANDIDATE,
        venue=venue,
        reason_code=reason_code,
    )


class WatchlistSignalTests(unittest.TestCase):
    def test_no_signal_is_preserved(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _no_signal(),
        )

        self.assertEqual(result.candidate_count, 1)
        self.assertEqual(result.no_signal_count, 1)
        self.assertEqual(result.entry_candidate_count, 0)
        self.assertIs(
            result.signals[0].decision,
            signal.WatchlistSignalDecision.NO_SIGNAL,
        )
        self.assertIsNone(result.signals[0].venue)

    def test_entry_candidate_krx_is_preserved(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                venues=(MarketVenue.KRX,),
            )
        )

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _entry(MarketVenue.KRX),
        )

        self.assertEqual(result.entry_candidate_count, 1)
        self.assertIs(
            result.signals[0].venue,
            MarketVenue.KRX,
        )

    def test_entry_candidate_nxt_is_preserved(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                venues=(MarketVenue.NXT,),
            )
        )

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _entry(MarketVenue.NXT),
        )

        self.assertIs(
            result.signals[0].venue,
            MarketVenue.NXT,
        )

    def test_entry_candidate_sor_is_preserved(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                venues=(MarketVenue.SOR,),
            )
        )

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _entry(MarketVenue.SOR),
        )

        self.assertIs(
            result.signals[0].venue,
            MarketVenue.SOR,
        )

    def test_mixed_decisions_have_correct_counts(self):
        first = _observation(
            1,
            "005930",
            venues=(MarketVenue.KRX,),
        )
        second = _observation(2, "000660")
        snapshot = _snapshot(first, second)

        def evaluator(item):
            if item.stock_code == "005930":
                return _entry(MarketVenue.KRX)

            return _no_signal()

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            evaluator,
        )

        self.assertEqual(result.candidate_count, 2)
        self.assertEqual(result.entry_candidate_count, 1)
        self.assertEqual(result.no_signal_count, 1)

    def test_candidate_order_is_preserved(self):
        snapshot = _snapshot(
            _observation(2, "000660"),
            _observation(1, "005930"),
        )

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _no_signal(),
        )

        self.assertEqual(
            tuple(item.stock_code for item in result.signals),
            ("000660", "005930"),
        )

    def test_candidate_metadata_is_preserved(self):
        snapshot = _snapshot(
            _observation(
                7,
                "005930",
                name="Samsung Electronics",
                exchange_scope="1",
            )
        )

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _no_signal("NO_ENTRY"),
        )

        candidate = result.signals[0]
        self.assertEqual(candidate.source_rank, 7)
        self.assertEqual(candidate.stock_code, "005930")
        self.assertEqual(
            candidate.stock_name,
            "Samsung Electronics",
        )
        self.assertEqual(candidate.exchange_scope, "1")
        self.assertEqual(candidate.reason_code, "NO_ENTRY")

    def test_realtime_type_is_preserved(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                realtime_type="0B",
            ),
            realtime_type="0B",
        )

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _no_signal(),
        )

        self.assertEqual(result.realtime_type, "0B")
        self.assertEqual(result.signals[0].realtime_type, "0B")

    def test_evaluator_is_called_once_per_candidate(self):
        snapshot = _snapshot(
            _observation(1, "005930"),
            _observation(2, "000660"),
            _observation(3, "035420"),
        )
        calls = []

        def evaluator(item):
            calls.append(item.stock_code)
            return _no_signal()

        signal.build_watchlist_signal_snapshot(
            snapshot,
            evaluator,
        )

        self.assertEqual(
            calls,
            ["005930", "000660", "035420"],
        )

    def test_evaluator_receives_original_observation(self):
        item = _observation(1, "005930")
        snapshot = _snapshot(item)
        received = []

        def evaluator(candidate):
            received.append(candidate)
            return _no_signal()

        signal.build_watchlist_signal_snapshot(
            snapshot,
            evaluator,
        )

        self.assertEqual(len(received), 1)
        self.assertIs(received[0], item)

    def test_empty_snapshot_does_not_call_evaluator(self):
        snapshot = _snapshot()
        calls = []

        def evaluator(item):
            calls.append(item)
            return _no_signal()

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            evaluator,
        )

        self.assertEqual(calls, [])
        self.assertEqual(result.signals, ())
        self.assertEqual(result.candidate_count, 0)
        self.assertEqual(result.no_signal_count, 0)
        self.assertEqual(result.entry_candidate_count, 0)

    def test_wrong_snapshot_type_raises_type_error(self):
        with self.assertRaisesRegex(TypeError, "snapshot"):
            signal.build_watchlist_signal_snapshot(
                object(),
                lambda item: _no_signal(),
            )

    def test_non_callable_evaluator_raises_type_error(self):
        with self.assertRaisesRegex(TypeError, "evaluator"):
            signal.build_watchlist_signal_snapshot(
                _snapshot(),
                object(),
            )

    def test_wrong_evaluator_return_type_raises_type_error(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )

        with self.assertRaisesRegex(
            TypeError,
            "WatchlistSignalEvaluation",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: object(),
            )

    def test_evaluator_exception_is_propagated(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )
        expected = RuntimeError("evaluator failed")

        def evaluator(item):
            raise expected

        with self.assertRaises(RuntimeError) as context:
            signal.build_watchlist_signal_snapshot(
                snapshot,
                evaluator,
            )

        self.assertIs(context.exception, expected)

    def test_no_signal_rejects_non_none_venue(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                venues=(MarketVenue.KRX,),
            )
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "NO_SIGNAL",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: _no_signal(
                    "NO_ENTRY",
                    venue=MarketVenue.KRX,
                ),
            )

    def test_entry_candidate_requires_venue(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                venues=(MarketVenue.KRX,),
            )
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "MarketVenue",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: _entry(None),
            )

    def test_unobserved_candidate_cannot_enter(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "observed state",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: _entry(MarketVenue.KRX),
            )

    def test_entry_candidate_rejects_unobserved_venue(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                venues=(MarketVenue.KRX,),
            )
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "observation.states",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: _entry(MarketVenue.NXT),
            )

    def test_empty_reason_code_is_rejected(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "reason_code",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: _no_signal(""),
            )

    def test_whitespace_reason_code_is_rejected(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "reason_code",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: _no_signal("   "),
            )

    def test_reason_code_must_be_string(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )
        evaluation = signal.WatchlistSignalEvaluation(
            decision=signal.WatchlistSignalDecision.NO_SIGNAL,
            venue=None,
            reason_code=object(),
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "string",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: evaluation,
            )

    def test_decision_must_be_signal_decision(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )
        evaluation = signal.WatchlistSignalEvaluation(
            decision="NO_SIGNAL",
            venue=None,
            reason_code="NO_ENTRY",
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "decision",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: evaluation,
            )

    def test_entry_venue_must_be_market_venue(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                venues=(MarketVenue.KRX,),
            )
        )
        evaluation = signal.WatchlistSignalEvaluation(
            decision=(
                signal.WatchlistSignalDecision.ENTRY_CANDIDATE
            ),
            venue="KRX",
            reason_code="ENTRY",
        )

        with self.assertRaisesRegex(
            signal.WatchlistSignalError,
            "MarketVenue",
        ):
            signal.build_watchlist_signal_snapshot(
                snapshot,
                lambda item: evaluation,
            )

    def test_no_signal_does_not_auto_select_observed_venue(self):
        snapshot = _snapshot(
            _observation(
                1,
                "005930",
                venues=(
                    MarketVenue.KRX,
                    MarketVenue.NXT,
                    MarketVenue.SOR,
                ),
            )
        )

        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _no_signal("NO_ENTRY"),
        )

        self.assertIsNone(result.signals[0].venue)
        self.assertIs(
            result.signals[0].decision,
            signal.WatchlistSignalDecision.NO_SIGNAL,
        )

    def test_output_dataclasses_are_frozen(self):
        snapshot = _snapshot(
            _observation(1, "005930")
        )
        result = signal.build_watchlist_signal_snapshot(
            snapshot,
            lambda item: _no_signal(),
        )

        self.assertIsInstance(result.signals, tuple)

        with self.assertRaises(FrozenInstanceError):
            result.candidate_count = 99

        with self.assertRaises(FrozenInstanceError):
            result.signals[0].reason_code = "CHANGED"

    def test_public_exports_reference_module_objects(self):
        self.assertIs(
            strategies_package.WatchlistSignalError,
            signal.WatchlistSignalError,
        )
        self.assertIs(
            strategies_package.WatchlistSignalDecision,
            signal.WatchlistSignalDecision,
        )
        self.assertIs(
            strategies_package.WatchlistSignalEvaluation,
            signal.WatchlistSignalEvaluation,
        )
        self.assertIs(
            strategies_package.WatchlistCandidateSignal,
            signal.WatchlistCandidateSignal,
        )
        self.assertIs(
            strategies_package.WatchlistSignalSnapshot,
            signal.WatchlistSignalSnapshot,
        )
        self.assertIs(
            strategies_package.build_watchlist_signal_snapshot,
            signal.build_watchlist_signal_snapshot,
        )


if __name__ == "__main__":
    unittest.main()
