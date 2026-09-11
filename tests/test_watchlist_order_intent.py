from __future__ import annotations

import asyncio
import inspect
import pathlib
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from unittest.mock import Mock

import kiwoom_trading_system.orders as orders
from kiwoom_trading_system.orders.watchlist_order_intent import (
    WatchlistCandidateOrderIntent,
    WatchlistOrderIntentError,
    WatchlistOrderIntentEvaluation,
    WatchlistOrderIntentSide,
    WatchlistOrderIntentSnapshot,
    WatchlistOrderIntentStyle,
    build_watchlist_order_intent_snapshot,
)
from kiwoom_trading_system.orders.watchlist_order_permission import (
    WatchlistCandidateOrderPermission,
    WatchlistOrderPermissionDecision,
    WatchlistOrderPermissionSnapshot,
)
from kiwoom_trading_system.risk import WatchlistRiskDecision
from kiwoom_trading_system.strategies import WatchlistSignalDecision


PHASE22_NAMES = (
    "WatchlistOrderPermissionError",
    "WatchlistOrderPermissionDecision",
    "WatchlistOrderPermissionEvaluation",
    "WatchlistCandidateOrderPermission",
    "WatchlistOrderPermissionSnapshot",
    "build_watchlist_order_permission_snapshot",
)

PHASE23_NAMES = (
    "WatchlistOrderIntentError",
    "WatchlistOrderIntentSide",
    "WatchlistOrderIntentStyle",
    "WatchlistOrderIntentEvaluation",
    "WatchlistCandidateOrderIntent",
    "WatchlistOrderIntentSnapshot",
    "build_watchlist_order_intent_snapshot",
)


def make_permission(
    rank: int,
    decision: WatchlistOrderPermissionDecision,
) -> WatchlistCandidateOrderPermission:
    return WatchlistCandidateOrderPermission(
        source_rank=rank,
        stock_code=f"{rank:06d}",
        stock_name=f"STOCK-{rank}",
        exchange_scope="KRX",
        realtime_type="REALTIME",
        signal_decision=WatchlistSignalDecision.ENTRY_CANDIDATE,
        venue=None,
        signal_reason_code=f"SIGNAL-{rank}",
        risk_decision=WatchlistRiskDecision.RISK_CLEAR,
        risk_reason_code=f"RISK-{rank}",
        order_permission_decision=decision,
        order_permission_reason_code=f"PERMISSION-{rank}",
    )


def make_snapshot(
    permissions: tuple[WatchlistCandidateOrderPermission, ...] = (),
    *,
    no_signal_count: int = 0,
    risk_blocked_count: int = 0,
) -> WatchlistOrderPermissionSnapshot:
    permitted = sum(
        item.order_permission_decision
        is WatchlistOrderPermissionDecision.ORDER_PERMITTED
        for item in permissions
    )
    denied = sum(
        item.order_permission_decision
        is WatchlistOrderPermissionDecision.ORDER_DENIED
        for item in permissions
    )
    risk_clear_count = len(permissions)
    risk_checked_count = risk_clear_count + risk_blocked_count

    return WatchlistOrderPermissionSnapshot(
        permissions=permissions,
        candidate_count=no_signal_count + risk_checked_count,
        no_signal_count=no_signal_count,
        risk_checked_count=risk_checked_count,
        risk_clear_count=risk_clear_count,
        risk_blocked_count=risk_blocked_count,
        permission_checked_count=risk_clear_count,
        order_permitted_count=permitted,
        order_denied_count=denied,
        realtime_type="REALTIME",
    )


def market_evaluation(reason: str = "INTENT-MARKET") -> WatchlistOrderIntentEvaluation:
    return WatchlistOrderIntentEvaluation(
        order_side=WatchlistOrderIntentSide.BUY,
        order_style=WatchlistOrderIntentStyle.MARKET,
        requested_quantity=3,
        limit_price=None,
        reason_code=reason,
    )


def limit_evaluation(reason: str = "INTENT-LIMIT") -> WatchlistOrderIntentEvaluation:
    return WatchlistOrderIntentEvaluation(
        order_side=WatchlistOrderIntentSide.BUY,
        order_style=WatchlistOrderIntentStyle.LIMIT,
        requested_quantity=4,
        limit_price=12345,
        reason_code=reason,
    )


class Phase23OrderIntentTests(unittest.TestCase):
    def test_package_all_preserves_phase22_exact_contract(self) -> None:
        self.assertEqual(tuple(orders.__all__), PHASE22_NAMES)

    def test_package_exports_are_identity_equal(self) -> None:
        for name in PHASE23_NAMES:
            self.assertIs(getattr(orders, name), globals()[name])

    def test_builder_signature_is_snapshot_planner(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(build_watchlist_order_intent_snapshot).parameters),
            ("snapshot", "planner"),
        )

    def test_side_enum_exact_values(self) -> None:
        self.assertEqual(
            [item.value for item in WatchlistOrderIntentSide],
            ["BUY"],
        )

    def test_style_enum_exact_values(self) -> None:
        self.assertEqual(
            [item.value for item in WatchlistOrderIntentStyle],
            ["MARKET", "LIMIT"],
        )

    def test_evaluation_field_order(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistOrderIntentEvaluation)),
            (
                "order_side",
                "order_style",
                "requested_quantity",
                "limit_price",
                "reason_code",
            ),
        )

    def test_candidate_field_order(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistCandidateOrderIntent)),
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
                "order_side",
                "order_style",
                "requested_quantity",
                "limit_price",
                "order_intent_reason_code",
            ),
        )

    def test_snapshot_field_order(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistOrderIntentSnapshot)),
            (
                "intents",
                "candidate_count",
                "no_signal_count",
                "risk_checked_count",
                "risk_clear_count",
                "risk_blocked_count",
                "permission_checked_count",
                "order_permitted_count",
                "order_denied_count",
                "intent_planned_count",
                "market_order_count",
                "limit_order_count",
                "realtime_type",
            ),
        )

    def test_dataclasses_are_frozen_and_slotted(self) -> None:
        for cls in (
            WatchlistOrderIntentEvaluation,
            WatchlistCandidateOrderIntent,
            WatchlistOrderIntentSnapshot,
        ):
            self.assertTrue(cls.__dataclass_params__.frozen)
            self.assertTrue(hasattr(cls, "__slots__"))

    def test_evaluation_is_frozen(self) -> None:
        item = market_evaluation()
        with self.assertRaises(FrozenInstanceError):
            item.requested_quantity = 9

    def test_empty_snapshot(self) -> None:
        planner = Mock()
        result = build_watchlist_order_intent_snapshot(make_snapshot(), planner)
        self.assertEqual(result.intents, ())
        self.assertEqual(result.intent_planned_count, 0)
        self.assertEqual(result.market_order_count, 0)
        self.assertEqual(result.limit_order_count, 0)
        planner.assert_not_called()

    def test_all_denied_calls_planner_zero_times(self) -> None:
        snapshot = make_snapshot(
            (
                make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),
                make_permission(2, WatchlistOrderPermissionDecision.ORDER_DENIED),
            )
        )
        planner = Mock()
        result = build_watchlist_order_intent_snapshot(snapshot, planner)
        self.assertEqual(result.intents, ())
        self.assertEqual(result.intent_planned_count, 0)
        planner.assert_not_called()

    def test_all_permitted_calls_planner_once_each(self) -> None:
        snapshot = make_snapshot(
            (
                make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
                make_permission(2, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
            )
        )
        planner = Mock(side_effect=(market_evaluation(), limit_evaluation()))
        result = build_watchlist_order_intent_snapshot(snapshot, planner)
        self.assertEqual(planner.call_count, 2)
        self.assertEqual(result.intent_planned_count, 2)

    def test_mixed_snapshot_calls_only_permitted(self) -> None:
        first = make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED)
        second = make_permission(2, WatchlistOrderPermissionDecision.ORDER_DENIED)
        third = make_permission(3, WatchlistOrderPermissionDecision.ORDER_PERMITTED)
        calls = []

        def planner(candidate):
            calls.append(candidate.source_rank)
            return market_evaluation(str(candidate.source_rank))

        result = build_watchlist_order_intent_snapshot(
            make_snapshot((first, second, third)),
            planner,
        )
        self.assertEqual(calls, [1, 3])
        self.assertEqual([item.source_rank for item in result.intents], [1, 3])

    def test_preserves_first_twelve_upstream_fields(self) -> None:
        candidate = make_permission(
            7,
            WatchlistOrderPermissionDecision.ORDER_PERMITTED,
        )
        result = build_watchlist_order_intent_snapshot(
            make_snapshot((candidate,)),
            lambda _: limit_evaluation(),
        )
        intent = result.intents[0]
        source_values = tuple(
            getattr(candidate, name)
            for name in (
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
            )
        )
        intent_values = tuple(
            getattr(intent, name)
            for name in (
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
            )
        )
        self.assertEqual(intent_values, source_values)

    def test_market_counts(self) -> None:
        snapshot = make_snapshot(
            (
                make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
                make_permission(2, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
            )
        )
        result = build_watchlist_order_intent_snapshot(
            snapshot,
            lambda _: market_evaluation(),
        )
        self.assertEqual(result.market_order_count, 2)
        self.assertEqual(result.limit_order_count, 0)

    def test_limit_counts(self) -> None:
        snapshot = make_snapshot(
            (
                make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
                make_permission(2, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
            )
        )
        result = build_watchlist_order_intent_snapshot(
            snapshot,
            lambda _: limit_evaluation(),
        )
        self.assertEqual(result.market_order_count, 0)
        self.assertEqual(result.limit_order_count, 2)

    def test_mixed_style_counts(self) -> None:
        snapshot = make_snapshot(
            (
                make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
                make_permission(2, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
            )
        )
        evaluations = iter((market_evaluation(), limit_evaluation()))
        result = build_watchlist_order_intent_snapshot(
            snapshot,
            lambda _: next(evaluations),
        )
        self.assertEqual(result.market_order_count, 1)
        self.assertEqual(result.limit_order_count, 1)

    def test_copies_all_upstream_counts(self) -> None:
        snapshot = make_snapshot(
            (make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),),
            no_signal_count=2,
            risk_blocked_count=3,
        )
        result = build_watchlist_order_intent_snapshot(snapshot, Mock())
        self.assertEqual(result.candidate_count, snapshot.candidate_count)
        self.assertEqual(result.no_signal_count, snapshot.no_signal_count)
        self.assertEqual(result.risk_checked_count, snapshot.risk_checked_count)
        self.assertEqual(result.risk_clear_count, snapshot.risk_clear_count)
        self.assertEqual(result.risk_blocked_count, snapshot.risk_blocked_count)
        self.assertEqual(
            result.permission_checked_count,
            snapshot.permission_checked_count,
        )
        self.assertEqual(
            result.order_permitted_count,
            snapshot.order_permitted_count,
        )
        self.assertEqual(result.order_denied_count, snapshot.order_denied_count)
        self.assertEqual(result.realtime_type, snapshot.realtime_type)

    def test_market_evaluation_accepts_none_price(self) -> None:
        item = market_evaluation()
        self.assertIsNone(item.limit_price)

    def test_limit_evaluation_accepts_positive_integer_price(self) -> None:
        item = limit_evaluation()
        self.assertEqual(item.limit_price, 12345)

    def test_side_rejects_string_coercion(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                order_side="BUY",
                order_style=WatchlistOrderIntentStyle.MARKET,
                requested_quantity=1,
                limit_price=None,
                reason_code="OK",
            )

    def test_style_rejects_string_coercion(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                order_side=WatchlistOrderIntentSide.BUY,
                order_style="MARKET",
                requested_quantity=1,
                limit_price=None,
                reason_code="OK",
            )

    def test_quantity_rejects_zero(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.MARKET,
                0,
                None,
                "OK",
            )

    def test_quantity_rejects_negative(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.MARKET,
                -1,
                None,
                "OK",
            )

    def test_quantity_rejects_bool(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.MARKET,
                True,
                None,
                "OK",
            )

    def test_quantity_rejects_float(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.MARKET,
                1.0,
                None,
                "OK",
            )

    def test_market_rejects_limit_price(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.MARKET,
                1,
                1000,
                "OK",
            )

    def test_limit_rejects_none_price(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.LIMIT,
                1,
                None,
                "OK",
            )

    def test_limit_rejects_zero_price(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.LIMIT,
                1,
                0,
                "OK",
            )

    def test_limit_rejects_bool_price(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.LIMIT,
                1,
                True,
                "OK",
            )

    def test_reason_rejects_empty(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.MARKET,
                1,
                None,
                "",
            )

    def test_reason_rejects_whitespace_only(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            WatchlistOrderIntentEvaluation(
                WatchlistOrderIntentSide.BUY,
                WatchlistOrderIntentStyle.MARKET,
                1,
                None,
                "   ",
            )

    def test_reason_is_not_trimmed(self) -> None:
        item = WatchlistOrderIntentEvaluation(
            WatchlistOrderIntentSide.BUY,
            WatchlistOrderIntentStyle.MARKET,
            1,
            None,
            "  KEEP  ",
        )
        self.assertEqual(item.reason_code, "  KEEP  ")

    def test_wrong_snapshot_type_rejected(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(object(), lambda _: market_evaluation())

    def test_noncallable_planner_rejected(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(make_snapshot(), None)

    def test_async_function_planner_rejected_before_call(self) -> None:
        async def planner(candidate):
            return market_evaluation()

        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot(
                    (make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),)
                ),
                planner,
            )

    def test_async_callable_object_rejected_before_call(self) -> None:
        class Planner:
            async def __call__(self, candidate):
                return market_evaluation()

        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot(
                    (make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),)
                ),
                Planner(),
            )

    def test_awaitable_return_rejected(self) -> None:
        async def produce():
            return market_evaluation()

        def planner(candidate):
            return produce()

        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot(
                    (make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),)
                ),
                planner,
            )

    def test_wrong_return_type_rejected(self) -> None:
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot(
                    (make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),)
                ),
                lambda _: object(),
            )

    def test_planner_exception_preserves_cause(self) -> None:
        cause = RuntimeError("planner boom")

        def planner(candidate):
            raise cause

        with self.assertRaises(WatchlistOrderIntentError) as caught:
            build_watchlist_order_intent_snapshot(
                make_snapshot(
                    (make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),)
                ),
                planner,
            )
        self.assertIs(caught.exception.__cause__, cause)

    def test_atomic_failure_returns_no_partial_snapshot(self) -> None:
        snapshot = make_snapshot(
            (
                make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
                make_permission(2, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
            )
        )
        calls = []

        def planner(candidate):
            calls.append(candidate.source_rank)
            if candidate.source_rank == 2:
                raise RuntimeError("fail")
            return market_evaluation()

        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(snapshot, planner)
        self.assertEqual(calls, [1, 2])

    def test_candidate_count_invariant_rejected(self) -> None:
        snapshot = replace(make_snapshot(), candidate_count=1)
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(snapshot, Mock())

    def test_risk_checked_invariant_rejected(self) -> None:
        snapshot = replace(make_snapshot(), risk_checked_count=1)
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(snapshot, Mock())

    def test_permission_checked_invariant_rejected(self) -> None:
        snapshot = make_snapshot(
            (make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),)
        )
        snapshot = replace(snapshot, permission_checked_count=0)
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(snapshot, Mock())

    def test_permission_decision_counts_rejected(self) -> None:
        snapshot = make_snapshot(
            (make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),)
        )
        snapshot = replace(snapshot, order_denied_count=0, order_permitted_count=1)
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(snapshot, Mock())

    def test_duplicate_source_rank_rejected(self) -> None:
        one = make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED)
        two = replace(one, stock_code="000002", stock_name="STOCK-2")
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot((one, two)),
                Mock(),
            )

    def test_invalid_permission_decision_type_rejected(self) -> None:
        candidate = replace(
            make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),
            order_permission_decision="ORDER_DENIED",
        )
        snapshot = WatchlistOrderPermissionSnapshot(
            permissions=(candidate,),
            candidate_count=1,
            no_signal_count=0,
            risk_checked_count=1,
            risk_clear_count=1,
            risk_blocked_count=0,
            permission_checked_count=1,
            order_permitted_count=0,
            order_denied_count=1,
            realtime_type="REALTIME",
        )
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(snapshot, Mock())

    def test_invalid_upstream_reason_rejected(self) -> None:
        candidate = replace(
            make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),
            order_permission_reason_code=" ",
        )
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot((candidate,)),
                Mock(),
            )

    def test_invalid_upstream_realtime_type_rejected(self) -> None:
        candidate = replace(
            make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),
            realtime_type="OTHER",
        )
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot((candidate,)),
                Mock(),
            )

    def test_invalid_upstream_risk_decision_rejected(self) -> None:
        candidate = replace(
            make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),
            risk_decision=WatchlistRiskDecision.RISK_BLOCKED,
        )
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot((candidate,)),
                Mock(),
            )

    def test_invalid_upstream_signal_decision_rejected(self) -> None:
        candidate = replace(
            make_permission(1, WatchlistOrderPermissionDecision.ORDER_DENIED),
            signal_decision=WatchlistSignalDecision.NO_SIGNAL,
        )
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(
                make_snapshot((candidate,)),
                Mock(),
            )

    def test_bool_snapshot_count_rejected(self) -> None:
        snapshot = replace(make_snapshot(), candidate_count=False)
        with self.assertRaises(WatchlistOrderIntentError):
            build_watchlist_order_intent_snapshot(snapshot, Mock())

    def test_snapshot_permissions_are_tuple_in_result_context(self) -> None:
        snapshot = make_snapshot(
            (make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),)
        )
        result = build_watchlist_order_intent_snapshot(
            snapshot,
            lambda _: market_evaluation(),
        )
        self.assertIsInstance(result.intents, tuple)

    def test_intent_planned_equals_order_permitted(self) -> None:
        snapshot = make_snapshot(
            (
                make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),
                make_permission(2, WatchlistOrderPermissionDecision.ORDER_DENIED),
            )
        )
        result = build_watchlist_order_intent_snapshot(
            snapshot,
            lambda _: market_evaluation(),
        )
        self.assertEqual(
            result.intent_planned_count,
            result.order_permitted_count,
        )

    def test_style_counts_sum_to_intent_planned(self) -> None:
        snapshot = make_snapshot(
            (make_permission(1, WatchlistOrderPermissionDecision.ORDER_PERMITTED),)
        )
        result = build_watchlist_order_intent_snapshot(
            snapshot,
            lambda _: limit_evaluation(),
        )
        self.assertEqual(
            result.market_order_count + result.limit_order_count,
            result.intent_planned_count,
        )

    def test_source_contains_no_kiwoom_order_api_ids(self) -> None:
        source = pathlib.Path(inspect.getsourcefile(WatchlistOrderIntentEvaluation)).read_text(
            encoding="utf-8"
        )
        for marker in ("kt00011", "kt10000", "kt10001", "kt10002", "kt10003"):
            self.assertNotIn(marker, source)

    def test_source_contains_no_network_or_credential_imports(self) -> None:
        source = pathlib.Path(inspect.getsourcefile(WatchlistOrderIntentEvaluation)).read_text(
            encoding="utf-8"
        )
        for marker in (
            "import socket",
            "import requests",
            "import httpx",
            "import websockets",
            "import keyring",
            "kiwoomcli",
            "api.kiwoom.com",
            "mockapi.kiwoom.com",
        ):
            self.assertNotIn(marker, source)

    def test_phase22_exports_remain_identity_equal(self) -> None:
        from kiwoom_trading_system.orders import watchlist_order_permission as permission

        for name in PHASE22_NAMES:
            self.assertIs(getattr(orders, name), getattr(permission, name))


if __name__ == "__main__":
    unittest.main()
