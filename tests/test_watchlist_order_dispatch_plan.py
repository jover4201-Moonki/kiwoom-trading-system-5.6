from __future__ import annotations

import ast
import inspect
import pathlib
import unittest
from dataclasses import FrozenInstanceError, fields
from unittest.mock import patch

from kiwoom_trading_system.brokers.kiwoom import rest as rest_package
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_dispatch_plan as phase26
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_mapping import (
    KIWOOM_BUY_ORDER_API_ID,
    KIWOOM_ORDER_API_PATH,
    KiwoomBuyOrderRequest,
    WatchlistCandidateKiwoomOrderMapping,
    WatchlistKiwoomOrderMappingSnapshot,
)
from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.orders.watchlist_account_validation import (
    WatchlistAccountValidationDecision,
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


EXPECTED_ALL = (
    "KIWOOM_DEMO_ORDER_BASE_URL",
    "KIWOOM_ORDER_HTTP_METHOD",
    "KIWOOM_ORDER_CONTENT_TYPE",
    "KiwoomOrderDispatchPlanError",
    "KiwoomDemoOrderDispatchDecision",
    "KiwoomDemoOrderDispatchBlockReason",
    "KiwoomBuyOrderDispatchPlan",
    "WatchlistCandidateKiwoomOrderDispatchPlan",
    "WatchlistKiwoomOrderDispatchPlanSnapshot",
    "build_watchlist_kiwoom_order_dispatch_plan_snapshot",
)


def _request(
    venue: MarketVenue,
    *,
    stock_code: str,
    quantity: int = 1,
    style: WatchlistOrderIntentStyle = WatchlistOrderIntentStyle.MARKET,
    limit_price: int | None = None,
) -> KiwoomBuyOrderRequest:
    if style is WatchlistOrderIntentStyle.MARKET:
        ord_uv = ""
        trde_tp = "3"
    else:
        ord_uv = str(limit_price)
        trde_tp = "0"
    return KiwoomBuyOrderRequest(
        dmst_stex_tp=venue.value,
        stk_cd=stock_code,
        ord_qty=str(quantity),
        ord_uv=ord_uv,
        trde_tp=trde_tp,
        cond_uv="",
    )


def _mapping(
    rank: int = 1,
    venue: MarketVenue = MarketVenue.KRX,
    *,
    style: WatchlistOrderIntentStyle = WatchlistOrderIntentStyle.MARKET,
) -> WatchlistCandidateKiwoomOrderMapping:
    stock_code = f"{5929 + rank:06d}"
    quantity = rank
    limit_price = None if style is WatchlistOrderIntentStyle.MARKET else 70000
    return WatchlistCandidateKiwoomOrderMapping(
        source_rank=rank,
        stock_code=stock_code,
        stock_name=f"STOCK-{rank}",
        exchange_scope=venue.value,
        realtime_type="REALTIME",
        signal_decision=WatchlistSignalDecision.ENTRY_CANDIDATE,
        venue=venue,
        signal_reason_code="SIGNAL_OK",
        risk_decision=WatchlistRiskDecision.RISK_CLEAR,
        risk_reason_code="RISK_OK",
        order_permission_decision=WatchlistOrderPermissionDecision.ORDER_PERMITTED,
        order_permission_reason_code="PERMISSION_OK",
        order_side=WatchlistOrderIntentSide.BUY,
        order_style=style,
        requested_quantity=quantity,
        limit_price=limit_price,
        order_intent_reason_code="INTENT_OK",
        account_validation_decision=(
            WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED
        ),
        account_validation_reason_code="ACCOUNT_VALIDATION_OK",
        reservation_amount=1000 * rank,
        max_orderable_quantity=100,
        remaining_buying_power_after=1000000 - (1000 * rank),
        request=_request(
            venue,
            stock_code=stock_code,
            quantity=quantity,
            style=style,
            limit_price=limit_price,
        ),
    )


def _snapshot(
    *mappings: WatchlistCandidateKiwoomOrderMapping,
) -> WatchlistKiwoomOrderMappingSnapshot:
    count = len(mappings)
    market_count = sum(
        item.order_style is WatchlistOrderIntentStyle.MARKET for item in mappings
    )
    limit_count = count - market_count
    total_reserved = sum(item.reservation_amount for item in mappings)
    return WatchlistKiwoomOrderMappingSnapshot(
        mappings=tuple(mappings),
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
        validation_checked_count=count,
        validation_passed_count=count,
        validation_blocked_count=0,
        mapping_count=count,
        initial_available_buying_power=1000000,
        total_reserved_buying_power=total_reserved,
        remaining_buying_power=1000000 - total_reserved,
        account_context_id="ACCOUNT-CONTEXT",
        evidence_snapshot_id="EVIDENCE-SNAPSHOT",
        realtime_type="REALTIME",
    )


def _build(*mappings):
    return phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot(
        _snapshot(*mappings)
    )


class Phase26DispatchPlanTests(unittest.TestCase):
    def test_01_public_all_exact(self):
        self.assertEqual(tuple(phase26.__all__), EXPECTED_ALL)


    def test_02_demo_base_url_exact(self):
        self.assertEqual(phase26.KIWOOM_DEMO_ORDER_BASE_URL, "https://mockapi.kiwoom.com")


    def test_03_http_method_exact(self):
        self.assertEqual(phase26.KIWOOM_ORDER_HTTP_METHOD, "POST")


    def test_04_content_type_exact(self):
        self.assertEqual(
            phase26.KIWOOM_ORDER_CONTENT_TYPE,
            "application/json;charset=UTF-8",
        )


    def test_05_phase25_api_id_reused(self):
        result = _build(_mapping())
        self.assertEqual(result.plans[0].dispatch_plan.api_id, KIWOOM_BUY_ORDER_API_ID)


    def test_06_phase25_api_path_reused(self):
        result = _build(_mapping())
        self.assertEqual(result.plans[0].dispatch_plan.api_path, KIWOOM_ORDER_API_PATH)


    def test_07_rest_package_not_reexported(self):
        self.assertFalse(hasattr(rest_package, "KiwoomBuyOrderDispatchPlan"))


    def test_08_builder_signature_exact(self):
        self.assertEqual(
            str(inspect.signature(phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot)),
            "(snapshot: 'WatchlistKiwoomOrderMappingSnapshot') -> 'WatchlistKiwoomOrderDispatchPlanSnapshot'",
        )


    def test_09_public_names_reference_module_objects(self):
        for name in EXPECTED_ALL:
            self.assertIs(getattr(phase26, name), phase26.__dict__[name])


    def test_10_source_has_no_phase26_submission_function(self):
        self.assertFalse(hasattr(phase26, "send_order"))
        self.assertFalse(hasattr(phase26, "submit_order"))


    def test_11_error_is_value_error(self):
        self.assertTrue(issubclass(phase26.KiwoomOrderDispatchPlanError, ValueError))


    def test_12_decision_values_exact(self):
        self.assertEqual(
            tuple(item.value for item in phase26.KiwoomDemoOrderDispatchDecision),
            ("DRY_RUN_SUPPORTED", "DRY_RUN_BLOCKED"),
        )


    def test_13_block_reason_values_exact(self):
        self.assertEqual(
            tuple(item.value for item in phase26.KiwoomDemoOrderDispatchBlockReason),
            ("DEMO_VENUE_UNSUPPORTED",),
        )


    def test_14_plan_rejects_wrong_decision_type(self):
        request = _mapping().request
        with self.assertRaises(TypeError):
            phase26.KiwoomBuyOrderDispatchPlan(
                phase26.KIWOOM_DEMO_ORDER_BASE_URL,
                phase26.KIWOOM_ORDER_HTTP_METHOD,
                KIWOOM_BUY_ORDER_API_ID,
                KIWOOM_ORDER_API_PATH,
                phase26.KIWOOM_ORDER_CONTENT_TYPE,
                request,
                "DRY_RUN_SUPPORTED",
                None,
                False,
            )


    def test_15_plan_rejects_wrong_block_reason_type(self):
        request = _mapping().request
        with self.assertRaises(TypeError):
            phase26.KiwoomBuyOrderDispatchPlan(
                phase26.KIWOOM_DEMO_ORDER_BASE_URL,
                phase26.KIWOOM_ORDER_HTTP_METHOD,
                KIWOOM_BUY_ORDER_API_ID,
                KIWOOM_ORDER_API_PATH,
                phase26.KIWOOM_ORDER_CONTENT_TYPE,
                request,
                phase26.KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED,
                "DEMO_VENUE_UNSUPPORTED",
                False,
            )


    def test_16_supported_plan_rejects_block_reason(self):
        request = _mapping().request
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            phase26.KiwoomBuyOrderDispatchPlan(
                phase26.KIWOOM_DEMO_ORDER_BASE_URL,
                phase26.KIWOOM_ORDER_HTTP_METHOD,
                KIWOOM_BUY_ORDER_API_ID,
                KIWOOM_ORDER_API_PATH,
                phase26.KIWOOM_ORDER_CONTENT_TYPE,
                request,
                phase26.KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED,
                phase26.KiwoomDemoOrderDispatchBlockReason.DEMO_VENUE_UNSUPPORTED,
                False,
            )


    def test_17_blocked_plan_requires_reason(self):
        request = _mapping().request
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            phase26.KiwoomBuyOrderDispatchPlan(
                phase26.KIWOOM_DEMO_ORDER_BASE_URL,
                phase26.KIWOOM_ORDER_HTTP_METHOD,
                KIWOOM_BUY_ORDER_API_ID,
                KIWOOM_ORDER_API_PATH,
                phase26.KIWOOM_ORDER_CONTENT_TYPE,
                request,
                phase26.KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED,
                None,
                False,
            )


    def test_18_plan_fields_exact(self):
        self.assertEqual(
            tuple(item.name for item in fields(phase26.KiwoomBuyOrderDispatchPlan)),
            ("base_url", "http_method", "api_id", "api_path", "content_type", "request", "decision", "block_reason", "send_authorized"),
        )


    def test_19_plan_is_frozen(self):
        plan = _build(_mapping()).plans[0].dispatch_plan
        with self.assertRaises(FrozenInstanceError):
            plan.send_authorized = True


    def test_20_plan_uses_slots(self):
        self.assertTrue(hasattr(phase26.KiwoomBuyOrderDispatchPlan, "__slots__"))


    def test_21_candidate_fields_exact(self):
        self.assertEqual(
            tuple(item.name for item in fields(phase26.WatchlistCandidateKiwoomOrderDispatchPlan)),
            ("source_mapping", "dispatch_plan"),
        )


    def test_22_candidate_is_frozen(self):
        item = _build(_mapping()).plans[0]
        with self.assertRaises(FrozenInstanceError):
            item.source_mapping = _mapping(2)


    def test_23_candidate_uses_slots(self):
        self.assertTrue(hasattr(phase26.WatchlistCandidateKiwoomOrderDispatchPlan, "__slots__"))


    def test_24_snapshot_fields_exact(self):
        self.assertEqual(
            tuple(item.name for item in fields(phase26.WatchlistKiwoomOrderDispatchPlanSnapshot)),
            ("source_snapshot", "plans", "candidate_count", "dry_run_supported_count", "dry_run_blocked_count", "send_authorized_count"),
        )


    def test_25_snapshot_is_frozen(self):
        result = _build(_mapping())
        with self.assertRaises(FrozenInstanceError):
            result.candidate_count = 99


    def test_26_snapshot_uses_slots(self):
        self.assertTrue(hasattr(phase26.WatchlistKiwoomOrderDispatchPlanSnapshot, "__slots__"))


    def test_27_send_authorized_true_rejected(self):
        request = _mapping().request
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            phase26.KiwoomBuyOrderDispatchPlan(
                phase26.KIWOOM_DEMO_ORDER_BASE_URL,
                phase26.KIWOOM_ORDER_HTTP_METHOD,
                KIWOOM_BUY_ORDER_API_ID,
                KIWOOM_ORDER_API_PATH,
                phase26.KIWOOM_ORDER_CONTENT_TYPE,
                request,
                phase26.KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED,
                None,
                True,
            )


    def test_28_candidate_rejects_wrong_source_mapping_type(self):
        plan = _build(_mapping()).plans[0].dispatch_plan
        with self.assertRaises(TypeError):
            phase26.WatchlistCandidateKiwoomOrderDispatchPlan(object(), plan)


    def test_29_candidate_rejects_wrong_dispatch_plan_type(self):
        with self.assertRaises(TypeError):
            phase26.WatchlistCandidateKiwoomOrderDispatchPlan(_mapping(), object())


    def test_30_krx_is_supported(self):
        result = _build(_mapping(venue=MarketVenue.KRX))
        self.assertIs(result.plans[0].dispatch_plan.decision, phase26.KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED)


    def test_31_krx_has_no_block_reason(self):
        result = _build(_mapping(venue=MarketVenue.KRX))
        self.assertIsNone(result.plans[0].dispatch_plan.block_reason)


    def test_32_krx_send_authorized_false(self):
        result = _build(_mapping(venue=MarketVenue.KRX))
        self.assertIs(result.plans[0].dispatch_plan.send_authorized, False)
        self.assertEqual(result.send_authorized_count, 0)


    def test_33_krx_uses_demo_base_url(self):
        self.assertEqual(_build(_mapping()).plans[0].dispatch_plan.base_url, "https://mockapi.kiwoom.com")


    def test_34_krx_transport_metadata_exact(self):
        plan = _build(_mapping()).plans[0].dispatch_plan
        self.assertEqual(
            (plan.http_method, plan.api_id, plan.api_path, plan.content_type),
            ("POST", KIWOOM_BUY_ORDER_API_ID, KIWOOM_ORDER_API_PATH, "application/json;charset=UTF-8"),
        )


    def test_35_krx_request_identity_preserved(self):
        mapping = _mapping()
        result = _build(mapping)
        self.assertIs(result.plans[0].dispatch_plan.request, mapping.request)


    def test_36_krx_mapping_and_snapshot_identity_preserved(self):
        mapping = _mapping()
        snapshot = _snapshot(mapping)
        result = phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot(snapshot)
        self.assertIs(result.source_snapshot, snapshot)
        self.assertIs(result.plans[0].source_mapping, mapping)


    def test_37_nxt_is_blocked(self):
        plan = _build(_mapping(venue=MarketVenue.NXT)).plans[0].dispatch_plan
        self.assertIs(plan.decision, phase26.KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED)


    def test_38_nxt_block_reason_exact(self):
        plan = _build(_mapping(venue=MarketVenue.NXT)).plans[0].dispatch_plan
        self.assertIs(plan.block_reason, phase26.KiwoomDemoOrderDispatchBlockReason.DEMO_VENUE_UNSUPPORTED)


    def test_39_nxt_never_authorizes_send(self):
        plan = _build(_mapping(venue=MarketVenue.NXT)).plans[0].dispatch_plan
        self.assertFalse(plan.send_authorized)


    def test_40_sor_is_blocked(self):
        plan = _build(_mapping(venue=MarketVenue.SOR)).plans[0].dispatch_plan
        self.assertIs(plan.decision, phase26.KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED)


    def test_41_sor_block_reason_exact(self):
        plan = _build(_mapping(venue=MarketVenue.SOR)).plans[0].dispatch_plan
        self.assertIs(plan.block_reason, phase26.KiwoomDemoOrderDispatchBlockReason.DEMO_VENUE_UNSUPPORTED)


    def test_42_all_blocked_snapshot_is_valid(self):
        result = _build(_mapping(1, MarketVenue.NXT), _mapping(2, MarketVenue.SOR))
        self.assertEqual((result.candidate_count, result.dry_run_supported_count, result.dry_run_blocked_count, result.send_authorized_count), (2, 0, 2, 0))


    def test_43_wrong_snapshot_type_rejected(self):
        with self.assertRaises(TypeError):
            phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot(object())


    def test_44_non_tuple_mappings_rejected(self):
        snapshot = _snapshot(_mapping())
        object.__setattr__(snapshot, "mappings", list(snapshot.mappings))
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot(snapshot)


    def test_45_mapping_count_mismatch_rejected(self):
        snapshot = _snapshot(_mapping())
        object.__setattr__(snapshot, "mapping_count", 2)
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot(snapshot)


    def test_46_unknown_venue_rejected(self):
        mapping = _mapping()
        object.__setattr__(mapping, "venue", "UNKNOWN")
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            _build(mapping)


    def test_47_request_venue_mismatch_rejected(self):
        mapping = _mapping(venue=MarketVenue.KRX)
        object.__setattr__(mapping.request, "dmst_stex_tp", "NXT")
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            _build(mapping)


    def test_48_request_stock_mismatch_rejected(self):
        mapping = _mapping()
        object.__setattr__(mapping.request, "stk_cd", "000000")
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            _build(mapping)


    def test_49_input_order_is_preserved(self):
        first = _mapping(1, MarketVenue.KRX)
        second = _mapping(2, MarketVenue.NXT)
        third = _mapping(3, MarketVenue.SOR)
        result = _build(first, second, third)
        self.assertEqual(tuple(item.source_mapping for item in result.plans), (first, second, third))


    def test_50_each_mapping_identity_is_preserved(self):
        mappings = (_mapping(1), _mapping(2, MarketVenue.NXT))
        result = _build(*mappings)
        for expected, actual in zip(mappings, result.plans, strict=True):
            self.assertIs(actual.source_mapping, expected)


    def test_51_each_request_identity_is_preserved(self):
        mappings = (_mapping(1), _mapping(2, MarketVenue.NXT))
        result = _build(*mappings)
        for expected, actual in zip(mappings, result.plans, strict=True):
            self.assertIs(actual.dispatch_plan.request, expected.request)


    def test_52_source_snapshot_identity_is_preserved(self):
        snapshot = _snapshot(_mapping())
        result = phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot(snapshot)
        self.assertIs(result.source_snapshot, snapshot)


    def test_53_inputs_are_not_mutated(self):
        mapping = _mapping()
        snapshot = _snapshot(mapping)
        before = (mapping, mapping.request, tuple(snapshot.mappings), snapshot.mapping_count)
        phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot(snapshot)
        self.assertEqual((mapping, mapping.request, tuple(snapshot.mappings), snapshot.mapping_count), before)


    def test_54_invalid_second_mapping_fails_before_return(self):
        first = _mapping(1)
        second = _mapping(2)
        object.__setattr__(second.request, "ord_qty", "999")
        snapshot = _snapshot(first, second)
        with self.assertRaises(phase26.KiwoomOrderDispatchPlanError):
            phase26.build_watchlist_kiwoom_order_dispatch_plan_snapshot(snapshot)


    def test_55_empty_snapshot_returns_immutable_empty_tuple(self):
        result = _build()
        self.assertEqual(result.plans, ())
        self.assertIsInstance(result.plans, tuple)
        self.assertEqual((result.candidate_count, result.dry_run_supported_count, result.dry_run_blocked_count, result.send_authorized_count), (0, 0, 0, 0))


    def test_56_source_has_no_network_imports(self):
        source = pathlib.Path(inspect.getsourcefile(phase26)).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        for forbidden in ("socket", "requests", "httpx", "urllib", "http.client", "websockets"):
            self.assertFalse(any(item == forbidden or item.startswith(forbidden + ".") for item in imports))


    def test_57_source_has_no_credential_or_dotenv_markers(self):
        source = pathlib.Path(inspect.getsourcefile(phase26)).read_text(encoding="utf-8")
        for marker in ("keyring", "win32cred", "load_dotenv", "dotenv_values", "getenv(", "environ["):
            self.assertNotIn(marker, source)


    def test_58_source_has_no_client_or_submission_calls(self):
        source = pathlib.Path(inspect.getsourcefile(phase26)).read_text(encoding="utf-8")
        for marker in ("get_client(", "fetch_page(", ".post(", ".request(", "submit_order(", "send_order("):
            self.assertNotIn(marker, source)


    def test_59_build_does_not_open_network(self):
        mapping = _mapping()
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            result = _build(mapping)
        self.assertEqual(result.candidate_count, 1)



if __name__ == "__main__":
    unittest.main()
