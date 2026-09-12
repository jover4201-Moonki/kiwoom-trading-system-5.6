from __future__ import annotations

import inspect
import pathlib
import unittest
from dataclasses import FrozenInstanceError, fields, replace

import kiwoom_trading_system.orders as orders
from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.orders.watchlist_account_validation import (
    WatchlistAccountValidationContext,
    WatchlistAccountValidationDecision,
    WatchlistAccountValidationError,
    WatchlistAccountValidationSnapshot,
    WatchlistCandidateAccountValidation,
    WatchlistIntentBuyingPowerEvidence,
    build_watchlist_account_validation_snapshot,
)
from kiwoom_trading_system.orders.watchlist_order_intent import (
    WatchlistCandidateOrderIntent,
    WatchlistOrderIntentSide,
    WatchlistOrderIntentSnapshot,
    WatchlistOrderIntentStyle,
)
from kiwoom_trading_system.orders.watchlist_order_permission import (
    WatchlistOrderPermissionDecision,
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

PHASE24_NAMES = (
    "WatchlistAccountValidationError",
    "WatchlistAccountValidationDecision",
    "WatchlistIntentBuyingPowerEvidence",
    "WatchlistAccountValidationContext",
    "WatchlistCandidateAccountValidation",
    "WatchlistAccountValidationSnapshot",
    "build_watchlist_account_validation_snapshot",
)


def make_intent(
    rank: int = 1,
    *,
    style: WatchlistOrderIntentStyle = WatchlistOrderIntentStyle.MARKET,
    quantity: int = 1,
    limit_price: int | None = None,
) -> WatchlistCandidateOrderIntent:
    if style is WatchlistOrderIntentStyle.LIMIT and limit_price is None:
        limit_price = 10_000
    return WatchlistCandidateOrderIntent(
        source_rank=rank,
        stock_code=f"{rank:06d}",
        stock_name=f"STOCK-{rank}",
        exchange_scope="KRX",
        realtime_type="0B",
        signal_decision=WatchlistSignalDecision.ENTRY_CANDIDATE,
        venue=None,
        signal_reason_code=f"SIGNAL-{rank}",
        risk_decision=WatchlistRiskDecision.RISK_CLEAR,
        risk_reason_code=f"RISK-{rank}",
        order_permission_decision=WatchlistOrderPermissionDecision.ORDER_PERMITTED,
        order_permission_reason_code=f"PERMISSION-{rank}",
        order_side=WatchlistOrderIntentSide.BUY,
        order_style=style,
        requested_quantity=quantity,
        limit_price=limit_price,
        order_intent_reason_code=f"INTENT-{rank}",
    )


def make_snapshot(
    intents: tuple[WatchlistCandidateOrderIntent, ...] = (),
) -> WatchlistOrderIntentSnapshot:
    market_count = sum(
        item.order_style is WatchlistOrderIntentStyle.MARKET for item in intents
    )
    limit_count = sum(
        item.order_style is WatchlistOrderIntentStyle.LIMIT for item in intents
    )
    count = len(intents)
    return WatchlistOrderIntentSnapshot(
        intents=intents,
        candidate_count=count,
        no_signal_count=0,
        risk_checked_count=count,
        risk_clear_count=count,
        risk_blocked_count=0,
        permission_checked_count=count,
        order_permitted_count=count,
        order_denied_count=0,
        intent_planned_count=count,
        market_order_count=market_count,
        limit_order_count=limit_count,
        realtime_type="0B",
    )


def make_evidence(
    intent: WatchlistCandidateOrderIntent,
    *,
    reservation_amount: int = 100,
    max_orderable_quantity: int = 10,
    account_context_id: str = "ACCOUNT-CONTEXT-1",
    evidence_snapshot_id: str = "EVIDENCE-SNAPSHOT-1",
) -> WatchlistIntentBuyingPowerEvidence:
    return WatchlistIntentBuyingPowerEvidence(
        source_rank=intent.source_rank,
        stock_code=intent.stock_code,
        exchange_scope=intent.exchange_scope,
        venue=intent.venue,
        order_side=intent.order_side,
        order_style=intent.order_style,
        requested_quantity=intent.requested_quantity,
        limit_price=intent.limit_price,
        reservation_amount=reservation_amount,
        max_orderable_quantity=max_orderable_quantity,
        account_context_id=account_context_id,
        evidence_snapshot_id=evidence_snapshot_id,
    )


def make_context(
    evidences: tuple[WatchlistIntentBuyingPowerEvidence, ...] = (),
    *,
    available_buying_power: int = 1_000,
    account_context_id: str = "ACCOUNT-CONTEXT-1",
    evidence_snapshot_id: str = "EVIDENCE-SNAPSHOT-1",
) -> WatchlistAccountValidationContext:
    return WatchlistAccountValidationContext(
        account_context_id=account_context_id,
        evidence_snapshot_id=evidence_snapshot_id,
        is_fresh=True,
        available_buying_power=available_buying_power,
        evidences=evidences,
    )


class Phase24ContractTests(unittest.TestCase):
    def test_error_inherits_value_error(self) -> None:
        self.assertTrue(issubclass(WatchlistAccountValidationError, ValueError))

    def test_decision_values_are_exact(self) -> None:
        self.assertEqual(
            tuple(item.value for item in WatchlistAccountValidationDecision),
            ("ACCOUNT_VALIDATION_PASSED", "ACCOUNT_VALIDATION_BLOCKED"),
        )

    def test_module_all_is_exact(self) -> None:
        import kiwoom_trading_system.orders.watchlist_account_validation as module

        self.assertEqual(tuple(module.__all__), PHASE24_NAMES)

    def test_package_all_preserves_phase22_exact_contract(self) -> None:
        self.assertEqual(tuple(orders.__all__), PHASE22_NAMES)

    def test_package_attributes_are_identity_equal(self) -> None:
        import kiwoom_trading_system.orders.watchlist_account_validation as module

        for name in PHASE24_NAMES:
            self.assertIs(getattr(orders, name), getattr(module, name))

    def test_evidence_field_order_is_exact(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistIntentBuyingPowerEvidence)),
            (
                "source_rank",
                "stock_code",
                "exchange_scope",
                "venue",
                "order_side",
                "order_style",
                "requested_quantity",
                "limit_price",
                "reservation_amount",
                "max_orderable_quantity",
                "account_context_id",
                "evidence_snapshot_id",
            ),
        )

    def test_context_field_order_is_exact(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistAccountValidationContext)),
            (
                "account_context_id",
                "evidence_snapshot_id",
                "is_fresh",
                "available_buying_power",
                "evidences",
            ),
        )

    def test_candidate_validation_field_order_is_exact(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistCandidateAccountValidation)),
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
                "account_validation_decision",
                "account_validation_reason_code",
                "reservation_amount",
                "max_orderable_quantity",
                "remaining_buying_power_after",
            ),
        )

    def test_snapshot_field_order_is_exact(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistAccountValidationSnapshot)),
            (
                "validations",
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
                "validation_checked_count",
                "validation_passed_count",
                "validation_blocked_count",
                "initial_available_buying_power",
                "total_reserved_buying_power",
                "remaining_buying_power",
                "account_context_id",
                "evidence_snapshot_id",
                "realtime_type",
            ),
        )

    def test_phase24_dataclasses_are_frozen_and_slotted(self) -> None:
        for cls in (
            WatchlistIntentBuyingPowerEvidence,
            WatchlistAccountValidationContext,
            WatchlistCandidateAccountValidation,
            WatchlistAccountValidationSnapshot,
        ):
            self.assertTrue(cls.__dataclass_params__.frozen)
            self.assertTrue(hasattr(cls, "__slots__"))

    def test_frozen_evidence_rejects_normal_assignment(self) -> None:
        evidence = make_evidence(make_intent())
        with self.assertRaises(FrozenInstanceError):
            evidence.reservation_amount = 999

    def test_builder_signature_is_exact(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(build_watchlist_account_validation_snapshot).parameters),
            ("snapshot", "context"),
        )

    def test_empty_snapshot_context(self) -> None:
        result = build_watchlist_account_validation_snapshot(
            make_snapshot(),
            make_context(),
        )
        self.assertEqual(result.validations, ())
        self.assertEqual(result.validation_checked_count, 0)
        self.assertEqual(result.validation_passed_count, 0)
        self.assertEqual(result.validation_blocked_count, 0)
        self.assertEqual(result.total_reserved_buying_power, 0)
        self.assertEqual(result.remaining_buying_power, 1_000)

    def test_market_pass(self) -> None:
        intent = make_intent(quantity=2)
        evidence = make_evidence(intent, reservation_amount=300, max_orderable_quantity=2)
        result = build_watchlist_account_validation_snapshot(
            make_snapshot((intent,)),
            make_context((evidence,), available_buying_power=500),
        )
        item = result.validations[0]
        self.assertIs(
            item.account_validation_decision,
            WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED,
        )
        self.assertEqual(item.account_validation_reason_code, "ACCOUNT_VALIDATION_OK")
        self.assertEqual(item.remaining_buying_power_after, 200)
        self.assertEqual(result.total_reserved_buying_power, 300)
        self.assertEqual(result.remaining_buying_power, 200)

    def test_limit_pass(self) -> None:
        intent = make_intent(
            style=WatchlistOrderIntentStyle.LIMIT,
            quantity=3,
            limit_price=20_000,
        )
        evidence = make_evidence(intent, reservation_amount=600, max_orderable_quantity=3)
        result = build_watchlist_account_validation_snapshot(
            make_snapshot((intent,)),
            make_context((evidence,), available_buying_power=600),
        )
        self.assertEqual(result.validation_passed_count, 1)
        self.assertEqual(result.remaining_buying_power, 0)

    def test_exact_buying_power_boundary_passes(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent, reservation_amount=1_000)
        result = build_watchlist_account_validation_snapshot(
            make_snapshot((intent,)),
            make_context((evidence,), available_buying_power=1_000),
        )
        self.assertEqual(result.validation_passed_count, 1)
        self.assertEqual(result.remaining_buying_power, 0)

    def test_max_orderable_quantity_insufficient_blocks_without_reservation(self) -> None:
        intent = make_intent(quantity=2)
        evidence = make_evidence(intent, reservation_amount=100, max_orderable_quantity=1)
        result = build_watchlist_account_validation_snapshot(
            make_snapshot((intent,)),
            make_context((evidence,), available_buying_power=500),
        )
        item = result.validations[0]
        self.assertIs(
            item.account_validation_decision,
            WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED,
        )
        self.assertEqual(
            item.account_validation_reason_code,
            "MAX_ORDERABLE_QUANTITY_INSUFFICIENT",
        )
        self.assertEqual(item.remaining_buying_power_after, 500)
        self.assertEqual(result.total_reserved_buying_power, 0)

    def test_buying_power_insufficient_blocks_without_reservation(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent, reservation_amount=501)
        result = build_watchlist_account_validation_snapshot(
            make_snapshot((intent,)),
            make_context((evidence,), available_buying_power=500),
        )
        item = result.validations[0]
        self.assertEqual(item.account_validation_reason_code, "BUYING_POWER_INSUFFICIENT")
        self.assertEqual(item.remaining_buying_power_after, 500)
        self.assertEqual(result.total_reserved_buying_power, 0)

    def test_all_pass(self) -> None:
        intents = (make_intent(1), make_intent(2))
        evidences = tuple(make_evidence(item, reservation_amount=100) for item in intents)
        result = build_watchlist_account_validation_snapshot(
            make_snapshot(intents),
            make_context(evidences, available_buying_power=200),
        )
        self.assertEqual(result.validation_passed_count, 2)
        self.assertEqual(result.validation_blocked_count, 0)
        self.assertEqual(result.total_reserved_buying_power, 200)

    def test_all_blocked(self) -> None:
        intents = (make_intent(1, quantity=2), make_intent(2, quantity=2))
        evidences = tuple(
            make_evidence(item, reservation_amount=100, max_orderable_quantity=1)
            for item in intents
        )
        result = build_watchlist_account_validation_snapshot(
            make_snapshot(intents),
            make_context(evidences, available_buying_power=200),
        )
        self.assertEqual(result.validation_passed_count, 0)
        self.assertEqual(result.validation_blocked_count, 2)
        self.assertEqual(result.total_reserved_buying_power, 0)
        self.assertEqual(result.remaining_buying_power, 200)

    def test_mixed_pass_and_block(self) -> None:
        intents = (make_intent(1), make_intent(2))
        evidences = (
            make_evidence(intents[0], reservation_amount=400),
            make_evidence(intents[1], reservation_amount=700),
        )
        result = build_watchlist_account_validation_snapshot(
            make_snapshot(intents),
            make_context(evidences, available_buying_power=1_000),
        )
        self.assertEqual(result.validation_passed_count, 1)
        self.assertEqual(result.validation_blocked_count, 1)
        self.assertEqual(result.remaining_buying_power, 600)

    def test_cumulative_oversubscription_700k_plus_700k(self) -> None:
        intents = (make_intent(1), make_intent(2))
        evidences = (
            make_evidence(intents[0], reservation_amount=700_000),
            make_evidence(intents[1], reservation_amount=700_000),
        )
        result = build_watchlist_account_validation_snapshot(
            make_snapshot(intents),
            make_context(evidences, available_buying_power=1_000_000),
        )
        self.assertEqual(result.validation_passed_count, 1)
        self.assertEqual(result.validation_blocked_count, 1)
        self.assertEqual(result.total_reserved_buying_power, 700_000)
        self.assertEqual(result.remaining_buying_power, 300_000)

    def test_blocked_intent_does_not_reserve_before_later_pass(self) -> None:
        intents = (make_intent(1, quantity=2), make_intent(2))
        evidences = (
            make_evidence(intents[0], reservation_amount=900, max_orderable_quantity=1),
            make_evidence(intents[1], reservation_amount=800),
        )
        result = build_watchlist_account_validation_snapshot(
            make_snapshot(intents),
            make_context(evidences, available_buying_power=800),
        )
        self.assertEqual(result.validation_blocked_count, 1)
        self.assertEqual(result.validation_passed_count, 1)
        self.assertEqual(result.total_reserved_buying_power, 800)
        self.assertEqual(result.remaining_buying_power, 0)

    def test_input_tuple_order_is_preserved_without_sorting(self) -> None:
        intents = (make_intent(5), make_intent(2))
        evidences = tuple(make_evidence(item) for item in intents)
        result = build_watchlist_account_validation_snapshot(
            make_snapshot(intents),
            make_context(evidences),
        )
        self.assertEqual(tuple(item.source_rank for item in result.validations), (5, 2))

    def test_output_preserves_phase23_candidate_fields(self) -> None:
        intent = make_intent(7, style=WatchlistOrderIntentStyle.LIMIT, limit_price=12_345)
        result = build_watchlist_account_validation_snapshot(
            make_snapshot((intent,)),
            make_context((make_evidence(intent),)),
        )
        item = result.validations[0]
        for field_name in (
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
        ):
            self.assertEqual(getattr(item, field_name), getattr(intent, field_name))

    def test_identity_source_rank_mismatch_is_error(self) -> None:
        intent = make_intent(1)
        evidence = replace(make_evidence(intent), source_rank=2)
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)), make_context((evidence,))
            )

    def test_identity_stock_code_mismatch_is_error(self) -> None:
        intent = make_intent()
        evidence = replace(make_evidence(intent), stock_code="999999")
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)), make_context((evidence,))
            )

    def test_identity_exchange_scope_mismatch_is_error(self) -> None:
        intent = make_intent()
        evidence = replace(make_evidence(intent), exchange_scope="NXT")
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)), make_context((evidence,))
            )

    def test_identity_venue_mismatch_is_error(self) -> None:
        intent = make_intent()
        evidence = replace(make_evidence(intent), venue=MarketVenue.KRX)
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)), make_context((evidence,))
            )

    def test_identity_order_side_wrong_type_is_error(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent)
        object.__setattr__(evidence, "order_side", "BUY")
        context = make_context((make_evidence(intent),))
        object.__setattr__(context, "evidences", (evidence,))
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(make_snapshot((intent,)), context)

    def test_identity_order_style_mismatch_is_error(self) -> None:
        intent = make_intent(
            style=WatchlistOrderIntentStyle.LIMIT,
            limit_price=10_000,
        )
        evidence = replace(
            make_evidence(intent),
            order_style=WatchlistOrderIntentStyle.MARKET,
            limit_price=None,
        )
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)), make_context((evidence,))
            )

    def test_identity_requested_quantity_mismatch_is_error(self) -> None:
        intent = make_intent(quantity=1)
        evidence = replace(make_evidence(intent), requested_quantity=2)
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)), make_context((evidence,))
            )

    def test_identity_limit_price_mismatch_is_error(self) -> None:
        intent = make_intent(
            style=WatchlistOrderIntentStyle.LIMIT,
            limit_price=10_000,
        )
        evidence = replace(make_evidence(intent), limit_price=10_001)
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)), make_context((evidence,))
            )

    def test_account_context_id_mismatch_is_error(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent, account_context_id="OTHER")
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)),
                make_context((evidence,), account_context_id="ACCOUNT-CONTEXT-1"),
            )

    def test_evidence_snapshot_id_mismatch_is_error(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent, evidence_snapshot_id="OTHER")
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)),
                make_context((evidence,), evidence_snapshot_id="EVIDENCE-SNAPSHOT-1"),
            )

    def test_missing_evidence_is_error(self) -> None:
        intent = make_intent()
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot((intent,)), make_context()
            )

    def test_extra_evidence_is_error(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent)
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                make_snapshot(), make_context((evidence,))
            )

    def test_duplicate_evidence_source_rank_is_error(self) -> None:
        intents = (make_intent(1), make_intent(2))
        first = make_evidence(intents[0])
        second = make_evidence(intents[1])
        object.__setattr__(second, "source_rank", 1)
        context = make_context((first, make_evidence(intents[1])))
        object.__setattr__(context, "evidences", (first, second))
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(make_snapshot(intents), context)

    def test_stale_context_is_contract_error(self) -> None:
        context = make_context()
        object.__setattr__(context, "is_fresh", False)
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(make_snapshot(), context)

    def test_wrong_snapshot_type_is_error(self) -> None:
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(object(), make_context())

    def test_wrong_context_type_is_error(self) -> None:
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(make_snapshot(), object())

    def test_wrong_evidence_type_is_error(self) -> None:
        context = make_context()
        object.__setattr__(context, "evidences", (object(),))
        snapshot = make_snapshot((make_intent(),))
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(snapshot, context)

    def test_context_evidences_must_be_tuple(self) -> None:
        with self.assertRaises(WatchlistAccountValidationError):
            WatchlistAccountValidationContext(
                account_context_id="A",
                evidence_snapshot_id="E",
                is_fresh=True,
                available_buying_power=0,
                evidences=[],
            )

    def test_bool_numeric_values_are_rejected(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent)
        for field_name in (
            "source_rank",
            "requested_quantity",
            "reservation_amount",
            "max_orderable_quantity",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(WatchlistAccountValidationError):
                    replace(evidence, **{field_name: True})
        with self.assertRaises(WatchlistAccountValidationError):
            WatchlistAccountValidationContext(
                account_context_id="A",
                evidence_snapshot_id="E",
                is_fresh=True,
                available_buying_power=True,
                evidences=(),
            )

    def test_float_and_string_numeric_values_are_rejected(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent)
        for value in (1.0, "1"):
            with self.subTest(value=value):
                with self.assertRaises(WatchlistAccountValidationError):
                    replace(evidence, reservation_amount=value)

    def test_zero_and_negative_numeric_boundaries(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent)
        with self.assertRaises(WatchlistAccountValidationError):
            replace(evidence, reservation_amount=0)
        with self.assertRaises(WatchlistAccountValidationError):
            replace(evidence, max_orderable_quantity=-1)
        with self.assertRaises(WatchlistAccountValidationError):
            make_context(available_buying_power=-1)

    def test_zero_available_buying_power_is_valid_and_blocks(self) -> None:
        intent = make_intent()
        result = build_watchlist_account_validation_snapshot(
            make_snapshot((intent,)),
            make_context((make_evidence(intent),), available_buying_power=0),
        )
        self.assertEqual(result.validation_blocked_count, 1)
        self.assertEqual(result.remaining_buying_power, 0)

    def test_zero_max_orderable_quantity_is_valid_and_blocks(self) -> None:
        intent = make_intent()
        result = build_watchlist_account_validation_snapshot(
            make_snapshot((intent,)),
            make_context((make_evidence(intent, max_orderable_quantity=0),)),
        )
        self.assertEqual(result.validation_blocked_count, 1)
        self.assertEqual(
            result.validations[0].account_validation_reason_code,
            "MAX_ORDERABLE_QUANTITY_INSUFFICIENT",
        )

    def test_market_evidence_requires_none_limit_price(self) -> None:
        intent = make_intent()
        with self.assertRaises(WatchlistAccountValidationError):
            replace(make_evidence(intent), limit_price=1)

    def test_limit_evidence_requires_positive_exact_int_price(self) -> None:
        intent = make_intent(style=WatchlistOrderIntentStyle.LIMIT, limit_price=100)
        evidence = make_evidence(intent)
        for value in (None, 0, True, 1.0, "1"):
            with self.subTest(value=value):
                with self.assertRaises(WatchlistAccountValidationError):
                    replace(evidence, limit_price=value)

    def test_blank_ids_are_rejected(self) -> None:
        with self.assertRaises(WatchlistAccountValidationError):
            make_context(account_context_id="   ")
        with self.assertRaises(WatchlistAccountValidationError):
            make_context(evidence_snapshot_id="")

    def test_malformed_upstream_count_is_error(self) -> None:
        intent = make_intent()
        malformed = replace(make_snapshot((intent,)), candidate_count=2)
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(
                malformed,
                make_context((make_evidence(intent),)),
            )

    def test_malformed_upstream_intent_type_is_error(self) -> None:
        snapshot = make_snapshot((make_intent(),))
        object.__setattr__(snapshot, "intents", (object(),))
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(snapshot, make_context())

    def test_duplicate_upstream_source_rank_is_error(self) -> None:
        first = make_intent(1)
        second = make_intent(2)
        object.__setattr__(second, "source_rank", 1)
        snapshot = make_snapshot((first, second))
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(snapshot, make_context())

    def test_structural_error_occurs_before_cumulative_output(self) -> None:
        intents = (make_intent(1), make_intent(2))
        first = make_evidence(intents[0], reservation_amount=100)
        second = replace(make_evidence(intents[1]), stock_code="999999")
        context = make_context((first, second), available_buying_power=1_000)
        snapshot = make_snapshot(intents)
        with self.assertRaises(WatchlistAccountValidationError):
            build_watchlist_account_validation_snapshot(snapshot, context)
        self.assertEqual(context.available_buying_power, 1_000)
        self.assertEqual(snapshot.intents, intents)

    def test_inputs_are_not_mutated(self) -> None:
        intent = make_intent()
        evidence = make_evidence(intent, reservation_amount=100)
        snapshot = make_snapshot((intent,))
        context = make_context((evidence,), available_buying_power=500)
        before_snapshot = repr(snapshot)
        before_context = repr(context)
        build_watchlist_account_validation_snapshot(snapshot, context)
        self.assertEqual(repr(snapshot), before_snapshot)
        self.assertEqual(repr(context), before_context)

    def test_snapshot_accounting_invariant(self) -> None:
        intents = (make_intent(1), make_intent(2))
        evidences = (
            make_evidence(intents[0], reservation_amount=200),
            make_evidence(intents[1], reservation_amount=300),
        )
        result = build_watchlist_account_validation_snapshot(
            make_snapshot(intents),
            make_context(evidences, available_buying_power=1_000),
        )
        self.assertEqual(
            result.initial_available_buying_power,
            result.total_reserved_buying_power + result.remaining_buying_power,
        )
        self.assertEqual(result.validation_checked_count, result.intent_planned_count)
        self.assertEqual(
            result.validation_checked_count,
            result.validation_passed_count + result.validation_blocked_count,
        )

    def test_source_has_no_broker_network_or_credential_tokens(self) -> None:
        import kiwoom_trading_system.orders.watchlist_account_validation as module

        source = pathlib.Path(module.__file__).read_text(encoding="utf-8")
        forbidden = (
            "kt00010",
            "kt00011",
            "kt10000",
            "kt10001",
            "kt10002",
            "kt10003",
            "api.kiwoom.com",
            "mockapi.kiwoom.com",
            "requests",
            "websocket",
            "keyring",
            "Credential Manager",
            "trde_tp",
            "IOC",
            "FOK",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_no_provider_specific_price_proxy_logic(self) -> None:
        import kiwoom_trading_system.orders.watchlist_account_validation as module

        source = pathlib.Path(module.__file__).read_text(encoding="utf-8")
        for token in (
            "upper_limit",
            "ask_price",
            "current_price",
            "fee_rate",
            "tax_rate",
            "margin_rate",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
