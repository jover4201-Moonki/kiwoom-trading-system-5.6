from __future__ import annotations

import inspect
import unittest
from dataclasses import FrozenInstanceError, fields

import kiwoom_trading_system.risk as risk_package
from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.risk import watchlist_risk as risk
from kiwoom_trading_system.strategies import watchlist_signal as signal


def _candidate(
    rank: int,
    code: str,
    *,
    decision=signal.WatchlistSignalDecision.ENTRY_CANDIDATE,
    venue=MarketVenue.KRX,
    reason_code: str = "SIGNAL_RULE_MATCH",
    name: str | None = None,
    exchange_scope: str = "0",
    realtime_type: str = "0B",
):
    return signal.WatchlistCandidateSignal(
        source_rank=rank,
        stock_code=code,
        stock_name=name or f"stock-{rank}",
        exchange_scope=exchange_scope,
        realtime_type=realtime_type,
        decision=decision,
        venue=venue,
        reason_code=reason_code,
    )


def _snapshot(*items, realtime_type: str = "0B"):
    no_signal_count = sum(
        item.decision is signal.WatchlistSignalDecision.NO_SIGNAL
        for item in items
    )
    entry_candidate_count = sum(
        item.decision is signal.WatchlistSignalDecision.ENTRY_CANDIDATE
        for item in items
    )
    return signal.WatchlistSignalSnapshot(
        signals=tuple(items),
        candidate_count=len(items),
        no_signal_count=no_signal_count,
        entry_candidate_count=entry_candidate_count,
        realtime_type=realtime_type,
    )


def _clear(reason_code: str = "RISK_OK"):
    return risk.WatchlistRiskEvaluation(
        decision=risk.WatchlistRiskDecision.RISK_CLEAR,
        reason_code=reason_code,
    )


def _blocked(reason_code: str = "RISK_BLOCK"):
    return risk.WatchlistRiskEvaluation(
        decision=risk.WatchlistRiskDecision.RISK_BLOCKED,
        reason_code=reason_code,
    )


class WatchlistRiskTests(unittest.TestCase):
    def test_risk_clear_is_preserved(self):
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(_candidate(1, "005930")),
            lambda item: _clear(),
        )
        self.assertIs(
            result.risks[0].risk_decision,
            risk.WatchlistRiskDecision.RISK_CLEAR,
        )
        self.assertEqual(result.risk_clear_count, 1)
        self.assertEqual(result.risk_blocked_count, 0)

    def test_risk_blocked_is_preserved(self):
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(_candidate(1, "005930")),
            lambda item: _blocked(),
        )
        self.assertIs(
            result.risks[0].risk_decision,
            risk.WatchlistRiskDecision.RISK_BLOCKED,
        )
        self.assertEqual(result.risk_clear_count, 0)
        self.assertEqual(result.risk_blocked_count, 1)

    def test_no_signal_skips_checker(self):
        calls = []
        item = _candidate(
            1,
            "005930",
            decision=signal.WatchlistSignalDecision.NO_SIGNAL,
            venue=None,
            reason_code="NO_SIGNAL",
        )
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(item),
            lambda candidate: calls.append(candidate),
        )
        self.assertEqual(calls, [])
        self.assertIsNone(result.risks[0].risk_decision)
        self.assertIsNone(result.risks[0].risk_reason_code)

    def test_entry_checker_called_once(self):
        item = _candidate(1, "005930")
        calls = []

        def checker(candidate):
            calls.append(candidate)
            return _clear()

        risk.build_watchlist_risk_snapshot(_snapshot(item), checker)
        self.assertEqual(calls, [item])
        self.assertIs(calls[0], item)

    def test_multiple_entry_candidates_each_called_once(self):
        first = _candidate(1, "005930")
        second = _candidate(2, "000660", venue=MarketVenue.NXT)
        calls = []

        def checker(candidate):
            calls.append(candidate)
            return _clear()

        risk.build_watchlist_risk_snapshot(
            _snapshot(first, second),
            checker,
        )
        self.assertEqual(calls, [first, second])

    def test_mixed_counts_are_correct(self):
        no_signal = _candidate(
            1,
            "005930",
            decision=signal.WatchlistSignalDecision.NO_SIGNAL,
            venue=None,
            reason_code="NO_SIGNAL",
        )
        clear = _candidate(2, "000660", venue=MarketVenue.NXT)
        blocked = _candidate(3, "035420", venue=MarketVenue.SOR)

        def checker(candidate):
            if candidate.stock_code == "035420":
                return _blocked()
            return _clear()

        result = risk.build_watchlist_risk_snapshot(
            _snapshot(no_signal, clear, blocked),
            checker,
        )
        self.assertEqual(result.candidate_count, 3)
        self.assertEqual(result.no_signal_count, 1)
        self.assertEqual(result.risk_checked_count, 2)
        self.assertEqual(result.risk_clear_count, 1)
        self.assertEqual(result.risk_blocked_count, 1)

    def test_candidate_order_is_preserved(self):
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(
                _candidate(2, "000660"),
                _candidate(1, "005930"),
            ),
            lambda item: _clear(),
        )
        self.assertEqual(
            tuple(item.stock_code for item in result.risks),
            ("000660", "005930"),
        )

    def test_candidate_metadata_is_preserved(self):
        item = _candidate(
            7,
            "005930",
            name="Samsung Electronics",
            exchange_scope="1",
            realtime_type="0B",
        )
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(item),
            lambda candidate: _clear(),
        )
        output = result.risks[0]
        self.assertEqual(output.source_rank, 7)
        self.assertEqual(output.stock_code, "005930")
        self.assertEqual(output.stock_name, "Samsung Electronics")
        self.assertEqual(output.exchange_scope, "1")
        self.assertEqual(output.realtime_type, "0B")

    def test_krx_venue_is_preserved(self):
        item = _candidate(1, "005930", venue=MarketVenue.KRX)
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(item), lambda candidate: _clear()
        )
        self.assertIs(result.risks[0].venue, MarketVenue.KRX)

    def test_nxt_venue_is_preserved(self):
        item = _candidate(1, "005930", venue=MarketVenue.NXT)
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(item), lambda candidate: _clear()
        )
        self.assertIs(result.risks[0].venue, MarketVenue.NXT)

    def test_sor_venue_is_preserved(self):
        item = _candidate(1, "005930", venue=MarketVenue.SOR)
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(item), lambda candidate: _clear()
        )
        self.assertIs(result.risks[0].venue, MarketVenue.SOR)

    def test_signal_reason_is_preserved(self):
        item = _candidate(1, "005930", reason_code="SIGNAL_A")
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(item), lambda candidate: _clear("RISK_B")
        )
        self.assertEqual(result.risks[0].signal_reason_code, "SIGNAL_A")
        self.assertEqual(result.risks[0].risk_reason_code, "RISK_B")

    def test_realtime_type_is_preserved(self):
        item = _candidate(1, "005930", realtime_type="0B")
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(item, realtime_type="0B"),
            lambda candidate: _clear(),
        )
        self.assertEqual(result.realtime_type, "0B")
        self.assertEqual(result.risks[0].realtime_type, "0B")

    def test_empty_snapshot_is_supported(self):
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(),
            lambda candidate: _clear(),
        )
        self.assertEqual(result.risks, ())
        self.assertEqual(result.candidate_count, 0)
        self.assertEqual(result.no_signal_count, 0)
        self.assertEqual(result.risk_checked_count, 0)

    def test_invalid_snapshot_type_is_rejected(self):
        with self.assertRaises(TypeError):
            risk.build_watchlist_risk_snapshot(object(), lambda item: _clear())

    def test_non_callable_checker_is_rejected(self):
        with self.assertRaises(TypeError):
            risk.build_watchlist_risk_snapshot(_snapshot(), object())

    def test_checker_none_return_is_rejected(self):
        with self.assertRaises(TypeError):
            risk.build_watchlist_risk_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: None,
            )

    def test_checker_mapping_return_is_rejected(self):
        with self.assertRaises(TypeError):
            risk.build_watchlist_risk_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: {"decision": "RISK_CLEAR"},
            )

    def test_checker_evaluation_subclass_is_rejected(self):
        class DerivedEvaluation(risk.WatchlistRiskEvaluation):
            pass

        with self.assertRaises(TypeError):
            risk.build_watchlist_risk_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: DerivedEvaluation(
                    risk.WatchlistRiskDecision.RISK_CLEAR,
                    "RISK_OK",
                ),
            )

    def test_bad_risk_decision_type_is_rejected(self):
        evaluation = risk.WatchlistRiskEvaluation(
            decision="RISK_CLEAR",
            reason_code="RISK_OK",
        )
        with self.assertRaises(TypeError):
            risk.build_watchlist_risk_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: evaluation,
            )

    def test_non_string_risk_reason_is_rejected(self):
        evaluation = risk.WatchlistRiskEvaluation(
            decision=risk.WatchlistRiskDecision.RISK_CLEAR,
            reason_code=123,
        )
        with self.assertRaises(risk.WatchlistRiskError):
            risk.build_watchlist_risk_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: evaluation,
            )

    def test_empty_risk_reason_is_rejected(self):
        with self.assertRaises(risk.WatchlistRiskError):
            risk.build_watchlist_risk_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: _clear(""),
            )

    def test_whitespace_risk_reason_is_rejected(self):
        with self.assertRaises(risk.WatchlistRiskError):
            risk.build_watchlist_risk_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: _clear("   \t"),
            )

    def test_checker_exception_propagates_unchanged(self):
        expected = RuntimeError("checker failed")

        def checker(candidate):
            raise expected

        with self.assertRaises(RuntimeError) as caught:
            risk.build_watchlist_risk_snapshot(
                _snapshot(_candidate(1, "005930")), checker
            )
        self.assertIs(caught.exception, expected)

    def test_checker_evaluation_object_is_not_mutated(self):
        evaluation = _clear("UNCHANGED")
        before = (evaluation.decision, evaluation.reason_code)
        risk.build_watchlist_risk_snapshot(
            _snapshot(_candidate(1, "005930")),
            lambda item: evaluation,
        )
        self.assertEqual(
            (evaluation.decision, evaluation.reason_code), before
        )

    def test_input_snapshot_is_not_mutated(self):
        snapshot = _snapshot(_candidate(1, "005930"))
        before = snapshot
        risk.build_watchlist_risk_snapshot(snapshot, lambda item: _clear())
        self.assertEqual(snapshot, before)

    def test_input_candidate_is_not_mutated(self):
        item = _candidate(1, "005930")
        before = item
        risk.build_watchlist_risk_snapshot(
            _snapshot(item), lambda candidate: _clear()
        )
        self.assertEqual(item, before)

    def test_output_candidate_is_frozen(self):
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(_candidate(1, "005930")), lambda item: _clear()
        )
        with self.assertRaises(FrozenInstanceError):
            result.risks[0].stock_code = "000000"

    def test_output_snapshot_is_frozen(self):
        result = risk.build_watchlist_risk_snapshot(
            _snapshot(_candidate(1, "005930")), lambda item: _clear()
        )
        with self.assertRaises(FrozenInstanceError):
            result.candidate_count = 2

    def test_snapshot_direct_construction_coerces_risks_to_tuple(self):
        direct = risk.WatchlistRiskSnapshot(
            risks=[],
            candidate_count=0,
            no_signal_count=0,
            risk_checked_count=0,
            risk_clear_count=0,
            risk_blocked_count=0,
            realtime_type="0B",
        )
        self.assertEqual(direct.risks, ())
        self.assertIsInstance(direct.risks, tuple)

    def test_public_export_identity(self):
        for name in (
            "WatchlistRiskError",
            "WatchlistRiskDecision",
            "WatchlistRiskEvaluation",
            "WatchlistCandidateRisk",
            "WatchlistRiskSnapshot",
            "build_watchlist_risk_snapshot",
        ):
            self.assertIs(getattr(risk_package, name), getattr(risk, name))

    def test_risk_decision_values_are_exact(self):
        self.assertEqual(
            {item.value for item in risk.WatchlistRiskDecision},
            {"RISK_CLEAR", "RISK_BLOCKED"},
        )

    def test_risk_evaluation_fields_are_exact(self):
        self.assertEqual(
            tuple(field.name for field in fields(risk.WatchlistRiskEvaluation)),
            ("decision", "reason_code"),
        )

    def test_candidate_risk_fields_are_exact(self):
        self.assertEqual(
            tuple(field.name for field in fields(risk.WatchlistCandidateRisk)),
            (
                "source_rank",
                "stock_code",
                "stock_name",
                "exchange_scope",
                "realtime_type",
                "signal_decision",
                "venue",
                "signal_reason_code",
                "risk_decision",
                "risk_reason_code",
            ),
        )

    def test_risk_snapshot_fields_are_exact(self):
        self.assertEqual(
            tuple(field.name for field in fields(risk.WatchlistRiskSnapshot)),
            (
                "risks",
                "candidate_count",
                "no_signal_count",
                "risk_checked_count",
                "risk_clear_count",
                "risk_blocked_count",
                "realtime_type",
            ),
        )

    def test_builder_signature_is_exact(self):
        self.assertEqual(
            tuple(inspect.signature(risk.build_watchlist_risk_snapshot).parameters),
            ("snapshot", "checker"),
        )

    def test_candidate_count_mismatch_is_rejected(self):
        malformed = signal.WatchlistSignalSnapshot(
            signals=(_candidate(1, "005930"),),
            candidate_count=2,
            no_signal_count=0,
            entry_candidate_count=1,
            realtime_type="0B",
        )
        with self.assertRaises(risk.WatchlistRiskError):
            risk.build_watchlist_risk_snapshot(malformed, lambda item: _clear())
