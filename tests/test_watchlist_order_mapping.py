from __future__ import annotations

import inspect
import pathlib
import unittest
from dataclasses import FrozenInstanceError, fields, replace

from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.orders.watchlist_account_validation import (
    WatchlistAccountValidationDecision,
    WatchlistAccountValidationSnapshot,
    WatchlistCandidateAccountValidation,
)
from kiwoom_trading_system.orders.watchlist_order_intent import (
    WatchlistOrderIntentSide,
    WatchlistOrderIntentStyle,
)
from kiwoom_trading_system.orders.watchlist_order_permission import (
    WatchlistOrderPermissionDecision,
)
from kiwoom_trading_system.risk import WatchlistRiskDecision
from kiwoom_trading_system.strategies import WatchlistSignalDecision
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_mapping import (
    KIWOOM_BUY_ORDER_API_ID,
    KIWOOM_ORDER_API_PATH,
    KiwoomBuyOrderRequest,
    KiwoomOrderMappingError,
    WatchlistCandidateKiwoomOrderMapping,
    WatchlistKiwoomOrderMappingSnapshot,
    build_watchlist_kiwoom_order_mapping_snapshot,
)


PHASE25_NAMES = (
    "KIWOOM_BUY_ORDER_API_ID",
    "KIWOOM_ORDER_API_PATH",
    "KiwoomOrderMappingError",
    "KiwoomBuyOrderRequest",
    "WatchlistCandidateKiwoomOrderMapping",
    "WatchlistKiwoomOrderMappingSnapshot",
    "build_watchlist_kiwoom_order_mapping_snapshot",
)


def make_validation(
    rank: int = 1,
    *,
    style: WatchlistOrderIntentStyle = WatchlistOrderIntentStyle.MARKET,
    venue: MarketVenue | None = MarketVenue.KRX,
    quantity: int = 1,
    limit_price: int | None = None,
    decision: WatchlistAccountValidationDecision = (
        WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED
    ),
    reason: str = "ACCOUNT_VALIDATION_OK",
    reservation: int = 1000,
    max_quantity: int = 10,
    remaining_after: int = 9000,
    stock_code: str | None = None,
    exchange_scope: str = "KRX",
) -> WatchlistCandidateAccountValidation:
    if style is WatchlistOrderIntentStyle.LIMIT and limit_price is None:
        limit_price = 12345
    return WatchlistCandidateAccountValidation(
        source_rank=rank,
        stock_code=stock_code or f"{rank:06d}",
        stock_name=f"STOCK-{rank}",
        exchange_scope=exchange_scope,
        realtime_type="REALTIME",
        signal_decision=WatchlistSignalDecision.ENTRY_CANDIDATE,
        venue=venue,
        signal_reason_code=f"SIGNAL-{rank}",
        risk_decision=WatchlistRiskDecision.RISK_CLEAR,
        risk_reason_code=f"RISK-{rank}",
        order_permission_decision=(
            WatchlistOrderPermissionDecision.ORDER_PERMITTED
        ),
        order_permission_reason_code=f"PERMISSION-{rank}",
        order_side=WatchlistOrderIntentSide.BUY,
        order_style=style,
        requested_quantity=quantity,
        limit_price=limit_price,
        order_intent_reason_code=f"INTENT-{rank}",
        account_validation_decision=decision,
        account_validation_reason_code=reason,
        reservation_amount=reservation,
        max_orderable_quantity=max_quantity,
        remaining_buying_power_after=remaining_after,
    )


def make_snapshot(
    validations: tuple[WatchlistCandidateAccountValidation, ...] = (),
    *,
    initial: int = 10000,
    no_signal_count: int = 0,
    risk_blocked_count: int = 0,
    order_denied_count: int = 0,
) -> WatchlistAccountValidationSnapshot:
    passed = sum(
        item.account_validation_decision
        is WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED
        for item in validations
    )
    blocked = len(validations) - passed
    market = sum(
        item.order_style is WatchlistOrderIntentStyle.MARKET
        for item in validations
    )
    limit = sum(
        item.order_style is WatchlistOrderIntentStyle.LIMIT
        for item in validations
    )
    reserved = sum(
        item.reservation_amount
        for item in validations
        if item.account_validation_decision
        is WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED
    )
    remaining = validations[-1].remaining_buying_power_after if validations else initial
    order_permitted = len(validations)
    permission_checked = order_permitted + order_denied_count
    risk_clear = permission_checked
    risk_checked = risk_clear + risk_blocked_count
    candidate_count = no_signal_count + risk_checked

    return WatchlistAccountValidationSnapshot(
        validations=validations,
        candidate_count=candidate_count,
        no_signal_count=no_signal_count,
        risk_checked_count=risk_checked,
        risk_clear_count=risk_clear,
        risk_blocked_count=risk_blocked_count,
        permission_checked_count=permission_checked,
        order_permitted_count=order_permitted,
        order_denied_count=order_denied_count,
        intent_planned_count=order_permitted,
        market_order_count=market,
        limit_order_count=limit,
        validation_checked_count=len(validations),
        validation_passed_count=passed,
        validation_blocked_count=blocked,
        initial_available_buying_power=initial,
        total_reserved_buying_power=reserved,
        remaining_buying_power=remaining,
        account_context_id="ACCOUNT-CONTEXT",
        evidence_snapshot_id="EVIDENCE-SNAPSHOT",
        realtime_type="REALTIME",
    )


class Phase25KiwoomOrderMappingTests(unittest.TestCase):
    def test_public_symbols_exact(self) -> None:
        from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_mapping

        self.assertEqual(tuple(watchlist_order_mapping.__all__), PHASE25_NAMES)

    def test_constants_exact(self) -> None:
        self.assertEqual(KIWOOM_BUY_ORDER_API_ID, "kt10000")
        self.assertEqual(KIWOOM_ORDER_API_PATH, "/api/dostk/ordr")

    def test_builder_signature_exact(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(build_watchlist_kiwoom_order_mapping_snapshot).parameters),
            ("snapshot",),
        )

    def test_request_field_order_exact(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(KiwoomBuyOrderRequest)),
            ("dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"),
        )

    def test_candidate_field_order_exact(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistCandidateKiwoomOrderMapping)),
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
                "request",
            ),
        )

    def test_snapshot_field_order_exact(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(WatchlistKiwoomOrderMappingSnapshot)),
            (
                "mappings",
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
                "mapping_count",
                "initial_available_buying_power",
                "total_reserved_buying_power",
                "remaining_buying_power",
                "account_context_id",
                "evidence_snapshot_id",
                "realtime_type",
            ),
        )

    def test_dataclasses_are_frozen_and_slotted(self) -> None:
        for cls in (
            KiwoomBuyOrderRequest,
            WatchlistCandidateKiwoomOrderMapping,
            WatchlistKiwoomOrderMappingSnapshot,
        ):
            self.assertTrue(cls.__dataclass_params__.frozen)
            self.assertTrue(hasattr(cls, "__slots__"))

    def test_request_is_frozen(self) -> None:
        request = KiwoomBuyOrderRequest("KRX", "005930", "1", "", "3", "")
        with self.assertRaises(FrozenInstanceError):
            request.ord_qty = "2"

    def test_empty_snapshot(self) -> None:
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot())
        self.assertEqual(result.mappings, ())
        self.assertEqual(result.mapping_count, 0)

    def test_one_market_passed(self) -> None:
        item = make_validation()
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))
        self.assertEqual(result.mapping_count, 1)
        request = result.mappings[0].request
        self.assertEqual(
            tuple(getattr(request, f.name) for f in fields(request)),
            ("KRX", "000001", "1", "", "3", ""),
        )

    def test_one_limit_passed(self) -> None:
        item = make_validation(
            style=WatchlistOrderIntentStyle.LIMIT,
            limit_price=12345,
        )
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))
        request = result.mappings[0].request
        self.assertEqual(request.ord_uv, "12345")
        self.assertEqual(request.trde_tp, "0")
        self.assertEqual(request.cond_uv, "")

    def test_all_blocked_returns_no_mappings(self) -> None:
        item = make_validation(
            decision=WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED,
            reason="MAX_ORDERABLE_QUANTITY_INSUFFICIENT",
            quantity=2,
            max_quantity=1,
            remaining_after=10000,
            venue=None,
        )
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))
        self.assertEqual(result.mappings, ())
        self.assertEqual(result.mapping_count, 0)
        self.assertEqual(result.validation_blocked_count, 1)

    def test_mixed_passed_blocked(self) -> None:
        first = make_validation(rank=1, reservation=1000, remaining_after=9000)
        second = make_validation(
            rank=2,
            decision=WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED,
            reason="MAX_ORDERABLE_QUANTITY_INSUFFICIENT",
            quantity=5,
            max_quantity=2,
            reservation=4000,
            remaining_after=9000,
            venue=None,
        )
        third = make_validation(
            rank=3,
            style=WatchlistOrderIntentStyle.LIMIT,
            reservation=2000,
            remaining_after=7000,
        )
        result = build_watchlist_kiwoom_order_mapping_snapshot(
            make_snapshot((first, second, third))
        )
        self.assertEqual([item.source_rank for item in result.mappings], [1, 3])
        self.assertEqual(result.mapping_count, 2)

    def test_passed_relative_order_preserved_without_renumbering(self) -> None:
        first = make_validation(rank=8, reservation=1000, remaining_after=9000)
        second = make_validation(rank=3, reservation=2000, remaining_after=7000)
        result = build_watchlist_kiwoom_order_mapping_snapshot(
            make_snapshot((first, second))
        )
        self.assertEqual([item.source_rank for item in result.mappings], [8, 3])

    def test_duplicate_source_rank_rejected(self) -> None:
        first = make_validation(rank=1, reservation=1000, remaining_after=9000)
        second = make_validation(rank=1, reservation=2000, remaining_after=7000)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(
                make_snapshot((first, second))
            )

    def test_krx_mapping(self) -> None:
        item = make_validation(venue=MarketVenue.KRX)
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))
        self.assertEqual(result.mappings[0].request.dmst_stex_tp, "KRX")

    def test_nxt_mapping(self) -> None:
        item = make_validation(venue=MarketVenue.NXT)
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))
        self.assertEqual(result.mappings[0].request.dmst_stex_tp, "NXT")

    def test_sor_mapping(self) -> None:
        item = make_validation(venue=MarketVenue.SOR)
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))
        self.assertEqual(result.mappings[0].request.dmst_stex_tp, "SOR")

    def test_exchange_scope_is_not_routing_source(self) -> None:
        item = make_validation(
            venue=MarketVenue.NXT,
            exchange_scope="KRX",
        )
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))
        self.assertEqual(result.mappings[0].exchange_scope, "KRX")
        self.assertEqual(result.mappings[0].request.dmst_stex_tp, "NXT")

    def test_market_non_none_price_rejected(self) -> None:
        item = make_validation()
        malformed = replace(item, limit_price=1000)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((malformed,)))

    def test_limit_zero_price_rejected(self) -> None:
        item = make_validation(style=WatchlistOrderIntentStyle.LIMIT)
        malformed = replace(item, limit_price=0)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((malformed,)))

    def test_limit_negative_price_rejected(self) -> None:
        item = make_validation(style=WatchlistOrderIntentStyle.LIMIT)
        malformed = replace(item, limit_price=-1)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((malformed,)))

    def test_limit_bool_price_rejected(self) -> None:
        item = make_validation(style=WatchlistOrderIntentStyle.LIMIT)
        malformed = replace(item, limit_price=True)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((malformed,)))

    def test_limit_float_price_rejected(self) -> None:
        item = make_validation(style=WatchlistOrderIntentStyle.LIMIT)
        malformed = replace(item, limit_price=123.0)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((malformed,)))

    def test_limit_string_price_rejected(self) -> None:
        item = make_validation(style=WatchlistOrderIntentStyle.LIMIT)
        malformed = replace(item, limit_price="123")
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((malformed,)))

    def test_quantity_zero_rejected(self) -> None:
        item = replace(make_validation(), requested_quantity=0)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_quantity_negative_rejected(self) -> None:
        item = replace(make_validation(), requested_quantity=-1)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_quantity_bool_rejected(self) -> None:
        item = replace(make_validation(), requested_quantity=True)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_quantity_float_rejected(self) -> None:
        item = replace(make_validation(), requested_quantity=1.0)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_quantity_string_rejected(self) -> None:
        item = replace(make_validation(), requested_quantity="1")
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_ord_qty_length_overflow_rejected(self) -> None:
        item = replace(
            make_validation(),
            requested_quantity=10**12,
            max_orderable_quantity=10**12,
        )
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_ord_uv_length_overflow_rejected(self) -> None:
        item = replace(
            make_validation(style=WatchlistOrderIntentStyle.LIMIT),
            limit_price=10**12,
        )
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_stock_code_length_overflow_rejected_for_passed(self) -> None:
        item = make_validation(stock_code="1234567890123")
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_wrong_snapshot_type_rejected(self) -> None:
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(object())

    def test_malformed_validation_count_rejected(self) -> None:
        snapshot = make_snapshot((make_validation(),))
        malformed = replace(snapshot, validation_checked_count=2)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(malformed)

    def test_malformed_phase20_count_rejected(self) -> None:
        snapshot = make_snapshot((make_validation(),))
        malformed = replace(snapshot, candidate_count=99)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(malformed)

    def test_malformed_phase21_count_rejected(self) -> None:
        snapshot = make_snapshot((make_validation(),))
        malformed = replace(snapshot, risk_checked_count=2)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(malformed)

    def test_malformed_phase22_count_rejected(self) -> None:
        snapshot = make_snapshot((make_validation(),))
        malformed = replace(snapshot, permission_checked_count=2)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(malformed)

    def test_malformed_phase23_count_rejected(self) -> None:
        snapshot = make_snapshot((make_validation(),))
        malformed = replace(snapshot, intent_planned_count=2)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(malformed)

    def test_invalid_side_type_rejected(self) -> None:
        item = replace(make_validation(), order_side="BUY")
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_invalid_style_type_rejected(self) -> None:
        item = replace(make_validation(), order_style="MARKET")
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_passed_venue_none_rejected(self) -> None:
        item = make_validation(venue=None)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_unsupported_venue_type_rejected(self) -> None:
        item = replace(make_validation(), venue="KRX")
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_invalid_account_decision_type_rejected(self) -> None:
        item = replace(
            make_validation(),
            account_validation_decision="ACCOUNT_VALIDATION_PASSED",
        )
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_passed_reason_mismatch_rejected(self) -> None:
        item = replace(
            make_validation(),
            account_validation_reason_code="WRONG",
        )
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_blocked_quantity_reason_mismatch_rejected(self) -> None:
        item = make_validation(
            decision=WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED,
            reason="BUYING_POWER_INSUFFICIENT",
            quantity=5,
            max_quantity=1,
            remaining_after=10000,
            venue=None,
        )
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))

    def test_blocked_buying_power_reason(self) -> None:
        item = make_validation(
            decision=WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED,
            reason="BUYING_POWER_INSUFFICIENT",
            reservation=11000,
            max_quantity=10,
            remaining_after=10000,
            venue=None,
        )
        result = build_watchlist_kiwoom_order_mapping_snapshot(make_snapshot((item,)))
        self.assertEqual(result.mapping_count, 0)

    def test_blocked_does_not_consume_buying_power(self) -> None:
        item = make_validation(
            decision=WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED,
            reason="MAX_ORDERABLE_QUANTITY_INSUFFICIENT",
            quantity=2,
            max_quantity=1,
            remaining_after=9000,
            venue=None,
        )
        snapshot = make_snapshot((item,), initial=10000)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(snapshot)

    def test_passed_remaining_mismatch_rejected(self) -> None:
        item = replace(make_validation(), remaining_buying_power_after=8000)
        snapshot = make_snapshot((item,), initial=10000)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(snapshot)

    def test_buying_power_summary_mismatch_rejected(self) -> None:
        snapshot = make_snapshot((make_validation(),))
        malformed = replace(snapshot, total_reserved_buying_power=500)
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(malformed)

    def test_request_identity_exact(self) -> None:
        item = make_validation()
        mapping = build_watchlist_kiwoom_order_mapping_snapshot(
            make_snapshot((item,))
        ).mappings[0]
        self.assertEqual(mapping.venue.value, mapping.request.dmst_stex_tp)
        self.assertEqual(mapping.stock_code, mapping.request.stk_cd)
        self.assertEqual(str(mapping.requested_quantity), mapping.request.ord_qty)

    def test_candidate_request_identity_mismatch_rejected(self) -> None:
        item = make_validation()
        mapping = build_watchlist_kiwoom_order_mapping_snapshot(
            make_snapshot((item,))
        ).mappings[0]
        wrong = replace(mapping.request, stk_cd="999999")
        with self.assertRaises(KiwoomOrderMappingError):
            replace(mapping, request=wrong)

    def test_provider_body_exact_field_order(self) -> None:
        request = build_watchlist_kiwoom_order_mapping_snapshot(
            make_snapshot((make_validation(),))
        ).mappings[0].request
        self.assertEqual(
            tuple(field.name for field in fields(request)),
            ("dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"),
        )

    def test_trde_tp_values_fit_length_two(self) -> None:
        market = build_watchlist_kiwoom_order_mapping_snapshot(
            make_snapshot((make_validation(),))
        ).mappings[0].request
        limit_item = make_validation(
            style=WatchlistOrderIntentStyle.LIMIT,
            limit_price=1000,
        )
        limit = build_watchlist_kiwoom_order_mapping_snapshot(
            make_snapshot((limit_item,))
        ).mappings[0].request
        self.assertLessEqual(len(market.trde_tp), 2)
        self.assertLessEqual(len(limit.trde_tp), 2)
        self.assertEqual((market.trde_tp, limit.trde_tp), ("3", "0"))

    def test_snapshot_summary_is_preserved(self) -> None:
        snapshot = make_snapshot(
            (make_validation(),),
            no_signal_count=2,
            risk_blocked_count=3,
            order_denied_count=4,
        )
        result = build_watchlist_kiwoom_order_mapping_snapshot(snapshot)
        for name in (
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
        ):
            self.assertEqual(getattr(result, name), getattr(snapshot, name))

    def test_input_snapshot_and_candidate_not_mutated(self) -> None:
        item = make_validation()
        snapshot = make_snapshot((item,))
        before_item = item
        before_snapshot = snapshot
        build_watchlist_kiwoom_order_mapping_snapshot(snapshot)
        self.assertEqual(item, before_item)
        self.assertEqual(snapshot, before_snapshot)

    def test_failure_does_not_mutate_input(self) -> None:
        first = make_validation(rank=1, reservation=1000, remaining_after=9000)
        second = make_validation(rank=2, reservation=2000, remaining_after=7000)
        malformed_second = replace(second, venue=None)
        snapshot = make_snapshot((first, malformed_second))
        before = snapshot
        with self.assertRaises(KiwoomOrderMappingError):
            build_watchlist_kiwoom_order_mapping_snapshot(snapshot)
        self.assertEqual(snapshot, before)

    def test_source_has_no_submission_or_authentication_calls(self) -> None:
        path = pathlib.Path(
            inspect.getsourcefile(build_watchlist_kiwoom_order_mapping_snapshot)
        )
        source = path.read_text(encoding="utf-8").lower()
        for marker in (
            "get_client(",
            "fetch_page(",
            "requests",
            "httpx",
            "aiohttp",
            "websockets",
            "socket",
            "authorization",
            "oauth",
            "dotenv",
            "keyring",
            "win32cred",
            "ord_no",
            "return_code",
            "return_msg",
            "retry",
            "timeout",
            "backoff",
        ):
            self.assertNotIn(marker, source)

    def test_source_imports_no_external_network_dependency(self) -> None:
        path = pathlib.Path(
            inspect.getsourcefile(build_watchlist_kiwoom_order_mapping_snapshot)
        )
        source = path.read_text(encoding="utf-8")
        allowed_prefixes = (
            "from __future__ ",
            "from dataclasses ",
            "from kiwoom_trading_system.",
        )
        import_lines = [
            line.strip()
            for line in source.splitlines()
            if line.startswith("import ") or line.startswith("from ")
        ]
        self.assertTrue(all(line.startswith(allowed_prefixes) for line in import_lines))


if __name__ == "__main__":
    unittest.main()
