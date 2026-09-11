from __future__ import annotations

import inspect
import unittest
from dataclasses import FrozenInstanceError, fields

import kiwoom_trading_system.orders as orders_package
from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.orders import watchlist_order_permission as permission
from kiwoom_trading_system.risk import watchlist_risk as risk
from kiwoom_trading_system.strategies import watchlist_signal as signal


def _candidate(
    rank: int,
    code: str,
    *,
    signal_decision=signal.WatchlistSignalDecision.ENTRY_CANDIDATE,
    risk_decision=risk.WatchlistRiskDecision.RISK_CLEAR,
    signal_reason_code: str = "SIGNAL_RULE_MATCH",
    risk_reason_code: str | None = "RISK_OK",
    venue=MarketVenue.KRX,
    name: str | None = None,
    exchange_scope: str = "0",
    realtime_type: str = "0B",
):
    if signal_decision is signal.WatchlistSignalDecision.NO_SIGNAL:
        risk_decision = None
        risk_reason_code = None
        venue = None
        signal_reason_code = "NO_SIGNAL"

    return risk.WatchlistCandidateRisk(
        source_rank=rank,
        stock_code=code,
        stock_name=name or f"stock-{rank}",
        exchange_scope=exchange_scope,
        realtime_type=realtime_type,
        signal_decision=signal_decision,
        venue=venue,
        signal_reason_code=signal_reason_code,
        risk_decision=risk_decision,
        risk_reason_code=risk_reason_code,
    )


def _snapshot(*items, realtime_type: str = "0B"):
    no_signal_count = sum(
        item.signal_decision is signal.WatchlistSignalDecision.NO_SIGNAL
        for item in items
    )
    risk_clear_count = sum(
        item.risk_decision is risk.WatchlistRiskDecision.RISK_CLEAR
        for item in items
    )
    risk_blocked_count = sum(
        item.risk_decision is risk.WatchlistRiskDecision.RISK_BLOCKED
        for item in items
    )
    risk_checked_count = risk_clear_count + risk_blocked_count

    return risk.WatchlistRiskSnapshot(
        risks=tuple(items),
        candidate_count=len(items),
        no_signal_count=no_signal_count,
        risk_checked_count=risk_checked_count,
        risk_clear_count=risk_clear_count,
        risk_blocked_count=risk_blocked_count,
        realtime_type=realtime_type,
    )


def _permitted(reason_code: str = "ORDER_POLICY_OK"):
    return permission.WatchlistOrderPermissionEvaluation(
        decision=permission.WatchlistOrderPermissionDecision.ORDER_PERMITTED,
        reason_code=reason_code,
    )


def _denied(reason_code: str = "ORDER_POLICY_DENY"):
    return permission.WatchlistOrderPermissionEvaluation(
        decision=permission.WatchlistOrderPermissionDecision.ORDER_DENIED,
        reason_code=reason_code,
    )


class WatchlistOrderPermissionTests(unittest.TestCase):
    def test_order_permitted_is_preserved(self):
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(_candidate(1, "005930")),
            lambda item: _permitted(),
        )
        self.assertIs(
            result.permissions[0].order_permission_decision,
            permission.WatchlistOrderPermissionDecision.ORDER_PERMITTED,
        )
        self.assertEqual(result.order_permitted_count, 1)
        self.assertEqual(result.order_denied_count, 0)

    def test_order_denied_is_preserved(self):
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(_candidate(1, "005930")),
            lambda item: _denied(),
        )
        self.assertIs(
            result.permissions[0].order_permission_decision,
            permission.WatchlistOrderPermissionDecision.ORDER_DENIED,
        )
        self.assertEqual(result.order_permitted_count, 0)
        self.assertEqual(result.order_denied_count, 1)

    def test_risk_blocked_skips_checker_and_is_not_denied(self):
        calls = []
        blocked = _candidate(
            1,
            "005930",
            risk_decision=risk.WatchlistRiskDecision.RISK_BLOCKED,
            risk_reason_code="RISK_BLOCK",
        )
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(blocked),
            lambda item: calls.append(item),
        )
        self.assertEqual(calls, [])
        self.assertEqual(result.permissions, ())
        self.assertEqual(result.permission_checked_count, 0)
        self.assertEqual(result.order_denied_count, 0)

    def test_no_signal_skips_checker(self):
        calls = []
        item = _candidate(
            1,
            "005930",
            signal_decision=signal.WatchlistSignalDecision.NO_SIGNAL,
        )
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(item),
            lambda candidate: calls.append(candidate),
        )
        self.assertEqual(calls, [])
        self.assertEqual(result.permissions, ())
        self.assertEqual(result.no_signal_count, 1)

    def test_risk_clear_checker_is_called_once(self):
        item = _candidate(1, "005930")
        calls = []

        def checker(candidate):
            calls.append(candidate)
            return _permitted()

        permission.build_watchlist_order_permission_snapshot(
            _snapshot(item),
            checker,
        )
        self.assertEqual(calls, [item])
        self.assertIs(calls[0], item)

    def test_multiple_risk_clear_candidates_each_called_once_in_order(self):
        first = _candidate(2, "000660")
        second = _candidate(1, "005930")
        calls = []

        def checker(candidate):
            calls.append(candidate)
            return _permitted()

        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(first, second),
            checker,
        )
        self.assertEqual(calls, [first, second])
        self.assertEqual(
            tuple(item.stock_code for item in result.permissions),
            ("000660", "005930"),
        )

    def test_mixed_counts_are_correct(self):
        no_signal = _candidate(
            1,
            "005930",
            signal_decision=signal.WatchlistSignalDecision.NO_SIGNAL,
        )
        clear = _candidate(2, "000660")
        blocked = _candidate(
            3,
            "035420",
            risk_decision=risk.WatchlistRiskDecision.RISK_BLOCKED,
            risk_reason_code="RISK_BLOCK",
        )
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(no_signal, clear, blocked),
            lambda item: _permitted(),
        )
        self.assertEqual(result.candidate_count, 3)
        self.assertEqual(result.no_signal_count, 1)
        self.assertEqual(result.risk_checked_count, 2)
        self.assertEqual(result.risk_clear_count, 1)
        self.assertEqual(result.risk_blocked_count, 1)
        self.assertEqual(result.permission_checked_count, 1)

    def test_candidate_metadata_is_preserved(self):
        item = _candidate(
            7,
            "005930",
            name="Samsung Electronics",
            exchange_scope="1",
            realtime_type="0B",
            signal_reason_code="SIGNAL_A",
            risk_reason_code="RISK_B",
            venue=MarketVenue.KRX,
        )
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(item),
            lambda candidate: _permitted("PERMISSION_C"),
        )
        output = result.permissions[0]
        self.assertEqual(output.source_rank, 7)
        self.assertEqual(output.stock_code, "005930")
        self.assertEqual(output.stock_name, "Samsung Electronics")
        self.assertEqual(output.exchange_scope, "1")
        self.assertEqual(output.realtime_type, "0B")
        self.assertIs(output.signal_decision, item.signal_decision)
        self.assertIs(output.venue, MarketVenue.KRX)
        self.assertEqual(output.signal_reason_code, "SIGNAL_A")
        self.assertIs(output.risk_decision, item.risk_decision)
        self.assertEqual(output.risk_reason_code, "RISK_B")
        self.assertEqual(output.order_permission_reason_code, "PERMISSION_C")

    def test_source_order_and_rank_are_preserved_without_reindex(self):
        first = _candidate(9, "000660")
        second = _candidate(3, "005930")
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(first, second),
            lambda item: _permitted(),
        )
        self.assertEqual(
            tuple(item.source_rank for item in result.permissions),
            (9, 3),
        )

    def test_snapshot_realtime_type_is_preserved(self):
        item = _candidate(1, "005930", realtime_type="0B")
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(item, realtime_type="0B"),
            lambda candidate: _permitted(),
        )
        self.assertEqual(result.realtime_type, "0B")

    def test_empty_snapshot_is_supported(self):
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(),
            lambda item: _permitted(),
        )
        self.assertEqual(result.permissions, ())
        self.assertEqual(result.candidate_count, 0)
        self.assertEqual(result.permission_checked_count, 0)

    def test_all_risk_blocked_is_supported(self):
        first = _candidate(
            1,
            "005930",
            risk_decision=risk.WatchlistRiskDecision.RISK_BLOCKED,
            risk_reason_code="BLOCK_A",
        )
        second = _candidate(
            2,
            "000660",
            risk_decision=risk.WatchlistRiskDecision.RISK_BLOCKED,
            risk_reason_code="BLOCK_B",
        )
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(first, second),
            lambda item: self.fail("checker must not run"),
        )
        self.assertEqual(result.permissions, ())
        self.assertEqual(result.risk_blocked_count, 2)
        self.assertEqual(result.permission_checked_count, 0)

    def test_all_risk_clear_is_supported(self):
        first = _candidate(1, "005930")
        second = _candidate(2, "000660")
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(first, second),
            lambda item: _permitted(),
        )
        self.assertEqual(result.risk_clear_count, 2)
        self.assertEqual(result.permission_checked_count, 2)
        self.assertEqual(len(result.permissions), 2)

    def test_permitted_and_denied_mix_counts_are_correct(self):
        first = _candidate(1, "005930")
        second = _candidate(2, "000660")

        def checker(item):
            if item.stock_code == "005930":
                return _permitted()
            return _denied()

        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(first, second),
            checker,
        )
        self.assertEqual(result.permission_checked_count, 2)
        self.assertEqual(result.order_permitted_count, 1)
        self.assertEqual(result.order_denied_count, 1)

    def test_permissions_are_tuple(self):
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(_candidate(1, "005930")),
            lambda item: _permitted(),
        )
        self.assertIsInstance(result.permissions, tuple)

    def test_phase22_dataclasses_are_frozen(self):
        evaluation = _permitted()
        result = permission.build_watchlist_order_permission_snapshot(
            _snapshot(_candidate(1, "005930")),
            lambda item: evaluation,
        )
        with self.assertRaises(FrozenInstanceError):
            evaluation.reason_code = "CHANGED"
        with self.assertRaises(FrozenInstanceError):
            result.permissions[0].stock_code = "000000"
        with self.assertRaises(FrozenInstanceError):
            result.candidate_count = 2

    def test_direct_snapshot_construction_coerces_permissions_to_tuple(self):
        direct = permission.WatchlistOrderPermissionSnapshot(
            permissions=[],
            candidate_count=0,
            no_signal_count=0,
            risk_checked_count=0,
            risk_clear_count=0,
            risk_blocked_count=0,
            permission_checked_count=0,
            order_permitted_count=0,
            order_denied_count=0,
            realtime_type="0B",
        )
        self.assertEqual(direct.permissions, ())
        self.assertIsInstance(direct.permissions, tuple)

    def test_public_export_identity_and_all_are_exact(self):
        expected = (
            "WatchlistOrderPermissionError",
            "WatchlistOrderPermissionDecision",
            "WatchlistOrderPermissionEvaluation",
            "WatchlistCandidateOrderPermission",
            "WatchlistOrderPermissionSnapshot",
            "build_watchlist_order_permission_snapshot",
        )
        self.assertEqual(tuple(orders_package.__all__), expected)
        self.assertEqual(tuple(permission.__all__), expected)
        for name in expected:
            self.assertIs(
                getattr(orders_package, name),
                getattr(permission, name),
            )

    def test_order_permission_decision_values_are_exact(self):
        self.assertEqual(
            {item.value for item in permission.WatchlistOrderPermissionDecision},
            {"ORDER_PERMITTED", "ORDER_DENIED"},
        )

    def test_phase22_dataclass_fields_are_exact(self):
        self.assertEqual(
            tuple(field.name for field in fields(permission.WatchlistOrderPermissionEvaluation)),
            ("decision", "reason_code"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(permission.WatchlistCandidateOrderPermission)),
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
                "order_permission_decision",
                "order_permission_reason_code",
            ),
        )
        self.assertEqual(
            tuple(field.name for field in fields(permission.WatchlistOrderPermissionSnapshot)),
            (
                "permissions",
                "candidate_count",
                "no_signal_count",
                "risk_checked_count",
                "risk_clear_count",
                "risk_blocked_count",
                "permission_checked_count",
                "order_permitted_count",
                "order_denied_count",
                "realtime_type",
            ),
        )

    def test_builder_signature_is_exact(self):
        self.assertEqual(
            tuple(
                inspect.signature(
                    permission.build_watchlist_order_permission_snapshot
                ).parameters
            ),
            ("snapshot", "checker"),
        )

    def test_invalid_snapshot_type_is_rejected(self):
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                object(),
                lambda item: _permitted(),
            )

    def test_non_callable_checker_is_rejected(self):
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(),
                object(),
            )

    def test_invalid_count_types_and_negative_values_are_rejected(self):
        fields_to_values = (
            ("candidate_count", -1),
            ("no_signal_count", True),
            ("risk_checked_count", -1),
            ("risk_clear_count", True),
            ("risk_blocked_count", -1),
        )
        base = _snapshot()
        for field_name, bad_value in fields_to_values:
            values = {
                "risks": base.risks,
                "candidate_count": base.candidate_count,
                "no_signal_count": base.no_signal_count,
                "risk_checked_count": base.risk_checked_count,
                "risk_clear_count": base.risk_clear_count,
                "risk_blocked_count": base.risk_blocked_count,
                "realtime_type": base.realtime_type,
            }
            values[field_name] = bad_value
            malformed = risk.WatchlistRiskSnapshot(**values)
            with self.subTest(field_name=field_name):
                with self.assertRaises(permission.WatchlistOrderPermissionError):
                    permission.build_watchlist_order_permission_snapshot(
                        malformed,
                        lambda item: _permitted(),
                    )

    def test_candidate_count_length_mismatch_is_rejected(self):
        malformed = risk.WatchlistRiskSnapshot(
            risks=(_candidate(1, "005930"),),
            candidate_count=2,
            no_signal_count=0,
            risk_checked_count=1,
            risk_clear_count=1,
            risk_blocked_count=0,
            realtime_type="0B",
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                malformed,
                lambda item: _permitted(),
            )

    def test_no_signal_count_mismatch_is_rejected(self):
        item = _candidate(
            1,
            "005930",
            signal_decision=signal.WatchlistSignalDecision.NO_SIGNAL,
        )
        malformed = risk.WatchlistRiskSnapshot(
            risks=(item,),
            candidate_count=1,
            no_signal_count=0,
            risk_checked_count=0,
            risk_clear_count=0,
            risk_blocked_count=0,
            realtime_type="0B",
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                malformed,
                lambda item: _permitted(),
            )

    def test_risk_checked_count_mismatch_is_rejected(self):
        item = _candidate(1, "005930")
        malformed = risk.WatchlistRiskSnapshot(
            risks=(item,),
            candidate_count=1,
            no_signal_count=0,
            risk_checked_count=0,
            risk_clear_count=1,
            risk_blocked_count=0,
            realtime_type="0B",
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                malformed,
                lambda item: _permitted(),
            )

    def test_risk_clear_count_mismatch_is_rejected(self):
        item = _candidate(1, "005930")
        malformed = risk.WatchlistRiskSnapshot(
            risks=(item,),
            candidate_count=1,
            no_signal_count=0,
            risk_checked_count=1,
            risk_clear_count=0,
            risk_blocked_count=1,
            realtime_type="0B",
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                malformed,
                lambda item: _permitted(),
            )

    def test_risk_blocked_count_mismatch_is_rejected(self):
        item = _candidate(
            1,
            "005930",
            risk_decision=risk.WatchlistRiskDecision.RISK_BLOCKED,
            risk_reason_code="BLOCK",
        )
        malformed = risk.WatchlistRiskSnapshot(
            risks=(item,),
            candidate_count=1,
            no_signal_count=0,
            risk_checked_count=1,
            risk_clear_count=1,
            risk_blocked_count=0,
            realtime_type="0B",
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                malformed,
                lambda item: _permitted(),
            )

    def test_non_candidate_risk_item_is_rejected(self):
        malformed = risk.WatchlistRiskSnapshot(
            risks=(object(),),
            candidate_count=1,
            no_signal_count=0,
            risk_checked_count=1,
            risk_clear_count=1,
            risk_blocked_count=0,
            realtime_type="0B",
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                malformed,
                lambda item: _permitted(),
            )

    def test_source_rank_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "source_rank", "1")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_source_rank_non_positive_is_rejected(self):
        for bad_rank in (0, -1):
            with self.subTest(rank=bad_rank):
                item = _candidate(bad_rank, "005930")
                with self.assertRaises(permission.WatchlistOrderPermissionError):
                    permission.build_watchlist_order_permission_snapshot(
                        _snapshot(item),
                        lambda candidate: _permitted(),
                    )

    def test_duplicate_source_rank_is_rejected(self):
        first = _candidate(1, "005930")
        second = _candidate(1, "000660")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(first, second),
                lambda candidate: _permitted(),
            )

    def test_stock_code_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "stock_code", 5930)
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_stock_name_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "stock_name", 123)
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_exchange_scope_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "exchange_scope", 0)
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_candidate_realtime_type_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "realtime_type", 11)
        malformed = _snapshot(item)
        object.__setattr__(malformed, "realtime_type", "0B")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                malformed,
                lambda candidate: _permitted(),
            )

    def test_candidate_realtime_type_mismatch_is_rejected(self):
        item = _candidate(1, "005930", realtime_type="0B")
        malformed = _snapshot(item, realtime_type="0C")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                malformed,
                lambda candidate: _permitted(),
            )

    def test_signal_decision_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "signal_decision", "ENTRY_CANDIDATE")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_venue_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "venue", "KRX")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_signal_reason_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "signal_reason_code", 123)
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_signal_reason_blank_is_rejected(self):
        item = _candidate(1, "005930", signal_reason_code="  ")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_no_signal_with_risk_decision_is_rejected(self):
        item = _candidate(
            1,
            "005930",
            signal_decision=signal.WatchlistSignalDecision.NO_SIGNAL,
        )
        object.__setattr__(
            item,
            "risk_decision",
            risk.WatchlistRiskDecision.RISK_CLEAR,
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_no_signal_with_risk_reason_is_rejected(self):
        item = _candidate(
            1,
            "005930",
            signal_decision=signal.WatchlistSignalDecision.NO_SIGNAL,
        )
        object.__setattr__(item, "risk_reason_code", "SHOULD_NOT_EXIST")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_entry_risk_decision_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "risk_decision", "RISK_CLEAR")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_entry_risk_reason_wrong_type_is_rejected(self):
        item = _candidate(1, "005930")
        object.__setattr__(item, "risk_reason_code", 123)
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_entry_risk_reason_blank_is_rejected(self):
        item = _candidate(1, "005930", risk_reason_code=" \t")
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(item),
                lambda candidate: _permitted(),
            )

    def test_checker_wrong_return_type_is_rejected(self):
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: None,
            )

    def test_checker_evaluation_subclass_is_rejected(self):
        class DerivedEvaluation(permission.WatchlistOrderPermissionEvaluation):
            pass

        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: DerivedEvaluation(
                    permission.WatchlistOrderPermissionDecision.ORDER_PERMITTED,
                    "OK",
                ),
            )

    def test_evaluation_decision_wrong_type_is_rejected(self):
        evaluation = permission.WatchlistOrderPermissionEvaluation(
            decision="ORDER_PERMITTED",
            reason_code="OK",
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: evaluation,
            )

    def test_evaluation_reason_wrong_type_is_rejected(self):
        evaluation = permission.WatchlistOrderPermissionEvaluation(
            decision=permission.WatchlistOrderPermissionDecision.ORDER_PERMITTED,
            reason_code=123,
        )
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: evaluation,
            )

    def test_evaluation_empty_reason_is_rejected(self):
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: _permitted(""),
            )

    def test_evaluation_whitespace_reason_is_rejected(self):
        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(_candidate(1, "005930")),
                lambda item: _permitted(" \t"),
            )

    def test_checker_exception_is_wrapped_with_cause(self):
        expected = RuntimeError("checker failed")
        calls = []

        def checker(item):
            calls.append(item)
            raise expected

        with self.assertRaises(permission.WatchlistOrderPermissionError) as caught:
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(_candidate(1, "005930")),
                checker,
            )

        self.assertIs(caught.exception.__cause__, expected)
        self.assertEqual(len(calls), 1)

    def test_checker_exception_does_not_retry_or_return_partial_snapshot(self):
        first = _candidate(1, "005930")
        second = _candidate(2, "000660")
        calls = []

        def checker(item):
            calls.append(item)
            if item is second:
                raise RuntimeError("stop")
            return _permitted()

        with self.assertRaises(permission.WatchlistOrderPermissionError):
            permission.build_watchlist_order_permission_snapshot(
                _snapshot(first, second),
                checker,
            )

        self.assertEqual(calls, [first, second])

    def test_evaluation_object_is_not_mutated(self):
        evaluation = _permitted("UNCHANGED")
        before = (evaluation.decision, evaluation.reason_code)
        permission.build_watchlist_order_permission_snapshot(
            _snapshot(_candidate(1, "005930")),
            lambda item: evaluation,
        )
        self.assertEqual(
            (evaluation.decision, evaluation.reason_code),
            before,
        )

    def test_input_snapshot_and_candidate_are_not_mutated(self):
        item = _candidate(1, "005930")
        snapshot = _snapshot(item)
        before_snapshot = snapshot
        before_item = item
        permission.build_watchlist_order_permission_snapshot(
            snapshot,
            lambda candidate: _permitted(),
        )
        self.assertEqual(snapshot, before_snapshot)
        self.assertEqual(item, before_item)
