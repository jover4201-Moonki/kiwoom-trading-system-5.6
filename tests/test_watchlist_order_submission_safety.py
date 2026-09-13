from __future__ import annotations

import ast
import hashlib
import inspect
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_submission_safety as subject
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_dispatch_plan import (
    KIWOOM_DEMO_ORDER_BASE_URL,
    KIWOOM_ORDER_CONTENT_TYPE,
    KIWOOM_ORDER_HTTP_METHOD,
    KiwoomBuyOrderDispatchPlan,
    KiwoomDemoOrderDispatchBlockReason,
    KiwoomDemoOrderDispatchDecision,
    WatchlistCandidateKiwoomOrderDispatchPlan,
    WatchlistKiwoomOrderDispatchPlanSnapshot,
)
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


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = (
    ROOT
    / "src"
    / "kiwoom_trading_system"
    / "brokers"
    / "kiwoom"
    / "rest"
    / "watchlist_order_submission_safety.py"
)
REST_INIT_PATH = (
    ROOT
    / "src"
    / "kiwoom_trading_system"
    / "brokers"
    / "kiwoom"
    / "rest"
    / "__init__.py"
)

PUBLIC_API = (
    "KiwoomOrderSubmissionSafetyError",
    "KiwoomPriorSubmissionState",
    "KiwoomOrderSubmissionSafetyDecision",
    "KiwoomOrderSubmissionSafetyBlockReason",
    "KiwoomOrderSubmissionSafetyContext",
    "WatchlistCandidateKiwoomOrderSubmissionSafety",
    "WatchlistKiwoomOrderSubmissionSafetySnapshot",
    "build_watchlist_kiwoom_order_submission_safety_snapshot",
)


def _request(
    venue: MarketVenue,
    *,
    stock_code: str,
    quantity: int = 1,
) -> KiwoomBuyOrderRequest:
    return KiwoomBuyOrderRequest(
        dmst_stex_tp=venue.value,
        stk_cd=stock_code,
        ord_qty=str(quantity),
        ord_uv="",
        trde_tp="3",
        cond_uv="",
    )


def _mapping(
    rank: int,
    venue: MarketVenue = MarketVenue.KRX,
    request: KiwoomBuyOrderRequest | None = None,
) -> WatchlistCandidateKiwoomOrderMapping:
    stock_code = f"{5929 + rank:06d}"
    actual_request = (
        request
        if request is not None
        else _request(venue, stock_code=stock_code, quantity=rank)
    )
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
        order_style=WatchlistOrderIntentStyle.MARKET,
        requested_quantity=rank,
        limit_price=None,
        order_intent_reason_code="INTENT_OK",
        account_validation_decision=(
            WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED
        ),
        account_validation_reason_code="ACCOUNT_VALIDATION_OK",
        reservation_amount=1000 * rank,
        max_orderable_quantity=100,
        remaining_buying_power_after=1_000_000 - (1000 * rank),
        request=actual_request,
    )


def _unsafe_replace(instance, **updates):
    cls = type(instance)
    result = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(
            result,
            field.name,
            updates.get(field.name, getattr(instance, field.name)),
        )
    return result


def _replace_mapping(
    mapping: WatchlistCandidateKiwoomOrderMapping,
    **updates,
) -> WatchlistCandidateKiwoomOrderMapping:
    return _unsafe_replace(mapping, **updates)


def _source_plan(
    rank: int,
    venue: MarketVenue = MarketVenue.KRX,
) -> WatchlistCandidateKiwoomOrderDispatchPlan:
    mapping = _mapping(rank, venue)
    supported = venue is MarketVenue.KRX
    dispatch = KiwoomBuyOrderDispatchPlan(
        base_url=KIWOOM_DEMO_ORDER_BASE_URL,
        http_method=KIWOOM_ORDER_HTTP_METHOD,
        api_id=KIWOOM_BUY_ORDER_API_ID,
        api_path=KIWOOM_ORDER_API_PATH,
        content_type=KIWOOM_ORDER_CONTENT_TYPE,
        request=mapping.request,
        decision=(
            KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED
            if supported
            else KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED
        ),
        block_reason=(
            None
            if supported
            else KiwoomDemoOrderDispatchBlockReason.DEMO_VENUE_UNSUPPORTED
        ),
        send_authorized=False,
    )
    return WatchlistCandidateKiwoomOrderDispatchPlan(
        source_mapping=mapping,
        dispatch_plan=dispatch,
    )


def _mapping_snapshot(
    mappings: tuple[WatchlistCandidateKiwoomOrderMapping, ...],
) -> WatchlistKiwoomOrderMappingSnapshot:
    count = len(mappings)
    total_reserved = sum(item.reservation_amount for item in mappings)
    return WatchlistKiwoomOrderMappingSnapshot(
        mappings=mappings,
        candidate_count=count,
        no_signal_count=0,
        risk_checked_count=count,
        risk_clear_count=count,
        risk_blocked_count=0,
        permission_checked_count=count,
        order_permitted_count=count,
        order_denied_count=0,
        intent_planned_count=count,
        market_order_count=count,
        limit_order_count=0,
        validation_checked_count=count,
        validation_passed_count=count,
        validation_blocked_count=0,
        mapping_count=count,
        initial_available_buying_power=1_000_000,
        total_reserved_buying_power=total_reserved,
        remaining_buying_power=1_000_000 - total_reserved,
        account_context_id="ACCOUNT-CONTEXT",
        evidence_snapshot_id="EVIDENCE-SNAPSHOT",
        realtime_type="REALTIME",
    )


def _snapshot(
    plans: tuple[WatchlistCandidateKiwoomOrderDispatchPlan, ...],
) -> WatchlistKiwoomOrderDispatchPlanSnapshot:
    supported = sum(
        plan.dispatch_plan.decision
        is KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED
        for plan in plans
    )
    mappings = tuple(plan.source_mapping for plan in plans)
    return WatchlistKiwoomOrderDispatchPlanSnapshot(
        source_snapshot=_mapping_snapshot(mappings),
        plans=plans,
        candidate_count=len(plans),
        dry_run_supported_count=supported,
        dry_run_blocked_count=len(plans) - supported,
        send_authorized_count=0,
    )


def _unsafe_mapping_snapshot(
    mappings: tuple[object, ...],
    **updates,
) -> WatchlistKiwoomOrderMappingSnapshot:
    values = {
        "mappings": mappings,
        "candidate_count": len(mappings),
        "no_signal_count": 0,
        "risk_checked_count": len(mappings),
        "risk_clear_count": len(mappings),
        "risk_blocked_count": 0,
        "permission_checked_count": len(mappings),
        "order_permitted_count": len(mappings),
        "order_denied_count": 0,
        "intent_planned_count": len(mappings),
        "market_order_count": len(mappings),
        "limit_order_count": 0,
        "validation_checked_count": len(mappings),
        "validation_passed_count": len(mappings),
        "validation_blocked_count": 0,
        "mapping_count": len(mappings),
        "initial_available_buying_power": 1_000_000,
        "total_reserved_buying_power": 0,
        "remaining_buying_power": 1_000_000,
        "account_context_id": "ACCOUNT-CONTEXT",
        "evidence_snapshot_id": "EVIDENCE-SNAPSHOT",
        "realtime_type": "REALTIME",
    }
    values.update(updates)
    result = object.__new__(WatchlistKiwoomOrderMappingSnapshot)
    for field in fields(WatchlistKiwoomOrderMappingSnapshot):
        object.__setattr__(result, field.name, values[field.name])
    return result


def _unsafe_snapshot(
    plans: tuple[object, ...],
    **updates,
) -> WatchlistKiwoomOrderDispatchPlanSnapshot:
    mappings = tuple(
        plan.source_mapping
        if type(plan) is WatchlistCandidateKiwoomOrderDispatchPlan
        else object()
        for plan in plans
    )
    supported = sum(
        type(plan) is WatchlistCandidateKiwoomOrderDispatchPlan
        and type(plan.dispatch_plan) is KiwoomBuyOrderDispatchPlan
        and plan.dispatch_plan.decision
        is KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED
        for plan in plans
    )
    blocked = sum(
        type(plan) is WatchlistCandidateKiwoomOrderDispatchPlan
        and type(plan.dispatch_plan) is KiwoomBuyOrderDispatchPlan
        and plan.dispatch_plan.decision
        is KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED
        for plan in plans
    )
    values = {
        "source_snapshot": _unsafe_mapping_snapshot(mappings),
        "plans": plans,
        "candidate_count": len(plans),
        "dry_run_supported_count": supported,
        "dry_run_blocked_count": blocked,
        "send_authorized_count": 0,
    }
    values.update(updates)
    result = object.__new__(WatchlistKiwoomOrderDispatchPlanSnapshot)
    for field in fields(WatchlistKiwoomOrderDispatchPlanSnapshot):
        object.__setattr__(result, field.name, values[field.name])
    return result

def _context(
    rank: int,
    state: subject.KiwoomPriorSubmissionState,
    *,
    prior: str | None = None,
    reconciliation: str | None = None,
) -> subject.KiwoomOrderSubmissionSafetyContext:
    if state is subject.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED:
        prior = "attempt" if prior is None else prior
    elif state in (
        subject.KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED,
        subject.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,
    ):
        prior = "attempt" if prior is None else prior
        reconciliation = "reconciliation" if reconciliation is None else reconciliation
    return subject.KiwoomOrderSubmissionSafetyContext(
        source_rank=rank,
        prior_submission_state=state,
        prior_attempt_reference=prior,
        reconciliation_reference=reconciliation,
    )


def _build_one(
    state: subject.KiwoomPriorSubmissionState,
    venue: MarketVenue = MarketVenue.KRX,
) -> subject.WatchlistKiwoomOrderSubmissionSafetySnapshot:
    return subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
        _snapshot((_source_plan(1, venue),)),
        (_context(1, state),),
    )


class Phase27PublicApiTests(unittest.TestCase):
    def test_public_api_exact_eight(self):
        self.assertEqual(subject.__all__, PUBLIC_API)

    def test_error_base(self):
        self.assertTrue(issubclass(subject.KiwoomOrderSubmissionSafetyError, RuntimeError))

    def test_prior_state_enum_exact(self):
        self.assertEqual(
            [(x.name, x.value) for x in subject.KiwoomPriorSubmissionState],
            [
                ("NEVER_ATTEMPTED", "NEVER_ATTEMPTED"),
                ("CONFIRMED_NOT_ACCEPTED", "CONFIRMED_NOT_ACCEPTED"),
                ("CONFIRMED_ACCEPTED", "CONFIRMED_ACCEPTED"),
                ("AMBIGUOUS_UNRESOLVED", "AMBIGUOUS_UNRESOLVED"),
            ],
        )

    def test_decision_enum_exact(self):
        self.assertEqual(
            [(x.name, x.value) for x in subject.KiwoomOrderSubmissionSafetyDecision],
            [
                ("READY_FOR_CONFIRMATION", "READY_FOR_CONFIRMATION"),
                ("SUBMISSION_BLOCKED", "SUBMISSION_BLOCKED"),
            ],
        )

    def test_block_reason_enum_exact(self):
        self.assertEqual(
            [(x.name, x.value) for x in subject.KiwoomOrderSubmissionSafetyBlockReason],
            [
                ("DEMO_VENUE_UNSUPPORTED", "DEMO_VENUE_UNSUPPORTED"),
                ("RECONCILIATION_REQUIRED", "RECONCILIATION_REQUIRED"),
                ("ALREADY_ACCEPTED", "ALREADY_ACCEPTED"),
            ],
        )

    def test_context_dataclass_contract(self):
        cls = subject.KiwoomOrderSubmissionSafetyContext
        self.assertTrue(cls.__dataclass_params__.frozen)
        self.assertTrue(hasattr(cls, "__slots__"))
        self.assertEqual(
            [f.name for f in fields(cls)],
            [
                "source_rank",
                "prior_submission_state",
                "prior_attempt_reference",
                "reconciliation_reference",
            ],
        )

    def test_candidate_dataclass_contract(self):
        cls = subject.WatchlistCandidateKiwoomOrderSubmissionSafety
        self.assertTrue(cls.__dataclass_params__.frozen)
        self.assertTrue(hasattr(cls, "__slots__"))
        self.assertEqual(
            [f.name for f in fields(cls)],
            [
                "source_plan",
                "context",
                "decision",
                "block_reason",
                "automatic_retry_permitted",
            ],
        )

    def test_snapshot_dataclass_contract(self):
        cls = subject.WatchlistKiwoomOrderSubmissionSafetySnapshot
        self.assertTrue(cls.__dataclass_params__.frozen)
        self.assertTrue(hasattr(cls, "__slots__"))
        self.assertEqual(
            [f.name for f in fields(cls)],
            [
                "source_snapshot",
                "evaluations",
                "candidate_count",
                "ready_for_confirmation_count",
                "blocked_count",
                "reconciliation_required_count",
                "automatic_retry_permitted_count",
            ],
        )

    def test_builder_signature_exact(self):
        signature = inspect.signature(
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot
        )
        self.assertEqual(list(signature.parameters), ["source_snapshot", "contexts"])

    def test_concrete_type_annotations_are_not_object_placeholders(self):
        self.assertEqual(
            subject.WatchlistCandidateKiwoomOrderSubmissionSafety.__annotations__[
                "source_plan"
            ],
            "WatchlistCandidateKiwoomOrderDispatchPlan",
        )
        self.assertEqual(
            subject.WatchlistKiwoomOrderSubmissionSafetySnapshot.__annotations__[
                "source_snapshot"
            ],
            "WatchlistKiwoomOrderDispatchPlanSnapshot",
        )


class Phase27ContextInvariantTests(unittest.TestCase):
    def test_contexts_must_be_tuple(self):
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot((_source_plan(1),)),
                [_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED)],
            )

    def test_context_count_missing_fails(self):
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot((_source_plan(1),)),
                (),
            )

    def test_context_count_extra_fails(self):
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot((_source_plan(1),)),
                (
                    _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
                    _context(2, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
                ),
            )

    def test_pairwise_source_rank_mismatch_fails(self):
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot((_source_plan(1),)),
                (_context(2, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_context_order_mismatch_fails(self):
        plans = (_source_plan(1), _source_plan(2))
        contexts = (
            _context(2, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot(plans),
                contexts,
            )

    def test_duplicate_context_rank_fails(self):
        plans = (_source_plan(1), _source_plan(2))
        contexts = (
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot(plans),
                contexts,
            )

    def test_duplicate_upstream_rank_fails(self):
        plans = (_source_plan(1), _source_plan(1))
        contexts = (
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot(plans),
                contexts,
            )

    def test_context_wrong_type_fails(self):
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot((_source_plan(1),)),
                (object(),),
            )

    def test_context_source_rank_bool_fails(self):
        context = replace(
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
            source_rank=True,
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot((_source_plan(1),)),
                (context,),
            )

    def test_prior_state_wrong_type_fails(self):
        context = replace(
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
            prior_submission_state="NEVER_ATTEMPTED",
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot((_source_plan(1),)),
                (context,),
            )


class Phase27ReferenceInvariantTests(unittest.TestCase):
    def _assert_invalid(self, context):
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _snapshot((_source_plan(1),)),
                (context,),
            )

    def test_never_attempted_requires_prior_none(self):
        self._assert_invalid(
            _context(
                1,
                subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                prior="attempt",
            )
        )

    def test_never_attempted_requires_reconciliation_none(self):
        self._assert_invalid(
            _context(
                1,
                subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                reconciliation="reconciliation",
            )
        )

    def test_ambiguous_requires_prior_reference(self):
        context = subject.KiwoomOrderSubmissionSafetyContext(
            source_rank=1,
            prior_submission_state=subject.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED,
            prior_attempt_reference=None,
            reconciliation_reference=None,
        )
        self._assert_invalid(context)

    def test_ambiguous_allows_none_reconciliation(self):
        result = _build_one(subject.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED)
        self.assertEqual(result.reconciliation_required_count, 1)

    def test_confirmed_not_accepted_requires_prior(self):
        context = subject.KiwoomOrderSubmissionSafetyContext(
            1,
            subject.KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED,
            None,
            "reconciliation",
        )
        self._assert_invalid(context)

    def test_confirmed_not_accepted_requires_reconciliation(self):
        context = subject.KiwoomOrderSubmissionSafetyContext(
            1,
            subject.KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED,
            "attempt",
            None,
        )
        self._assert_invalid(context)

    def test_confirmed_accepted_requires_prior(self):
        context = subject.KiwoomOrderSubmissionSafetyContext(
            1,
            subject.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,
            None,
            "reconciliation",
        )
        self._assert_invalid(context)

    def test_confirmed_accepted_requires_reconciliation(self):
        context = subject.KiwoomOrderSubmissionSafetyContext(
            1,
            subject.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,
            "attempt",
            None,
        )
        self._assert_invalid(context)

    def test_non_string_reference_fails(self):
        context = subject.KiwoomOrderSubmissionSafetyContext(
            1,
            subject.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED,
            123,
            None,
        )
        self._assert_invalid(context)

    def test_empty_reference_fails(self):
        context = subject.KiwoomOrderSubmissionSafetyContext(
            1,
            subject.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED,
            "",
            None,
        )
        self._assert_invalid(context)

    def test_reference_is_opaque_and_not_trimmed(self):
        context = subject.KiwoomOrderSubmissionSafetyContext(
            1,
            subject.KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED,
            "  local-attempt  ",
            "  local-reconciliation  ",
        )
        snapshot = subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
            _snapshot((_source_plan(1),)),
            (context,),
        )
        self.assertIs(snapshot.evaluations[0].context, context)
        self.assertEqual(
            snapshot.evaluations[0].context.prior_attempt_reference,
            "  local-attempt  ",
        )


class Phase27DecisionMatrixTests(unittest.TestCase):
    def test_krx_never_attempted_ready(self):
        result = _build_one(subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED)
        item = result.evaluations[0]
        self.assertIs(
            item.decision,
            subject.KiwoomOrderSubmissionSafetyDecision.READY_FOR_CONFIRMATION,
        )
        self.assertIsNone(item.block_reason)

    def test_krx_confirmed_not_accepted_ready(self):
        result = _build_one(subject.KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED)
        item = result.evaluations[0]
        self.assertIs(
            item.decision,
            subject.KiwoomOrderSubmissionSafetyDecision.READY_FOR_CONFIRMATION,
        )
        self.assertIsNone(item.block_reason)

    def test_krx_confirmed_accepted_blocked(self):
        result = _build_one(subject.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED)
        item = result.evaluations[0]
        self.assertIs(
            item.decision,
            subject.KiwoomOrderSubmissionSafetyDecision.SUBMISSION_BLOCKED,
        )
        self.assertIs(
            item.block_reason,
            subject.KiwoomOrderSubmissionSafetyBlockReason.ALREADY_ACCEPTED,
        )

    def test_krx_ambiguous_reconciliation_block(self):
        result = _build_one(subject.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED)
        item = result.evaluations[0]
        self.assertIs(
            item.decision,
            subject.KiwoomOrderSubmissionSafetyDecision.SUBMISSION_BLOCKED,
        )
        self.assertIs(
            item.block_reason,
            subject.KiwoomOrderSubmissionSafetyBlockReason.RECONCILIATION_REQUIRED,
        )

    def test_nxt_all_valid_states_blocked_by_demo_venue(self):
        for state in subject.KiwoomPriorSubmissionState:
            with self.subTest(state=state):
                result = _build_one(state, MarketVenue.NXT)
                item = result.evaluations[0]
                self.assertIs(
                    item.block_reason,
                    subject.KiwoomOrderSubmissionSafetyBlockReason.DEMO_VENUE_UNSUPPORTED,
                )

    def test_sor_all_valid_states_blocked_by_demo_venue(self):
        for state in subject.KiwoomPriorSubmissionState:
            with self.subTest(state=state):
                result = _build_one(state, MarketVenue.SOR)
                item = result.evaluations[0]
                self.assertIs(
                    item.block_reason,
                    subject.KiwoomOrderSubmissionSafetyBlockReason.DEMO_VENUE_UNSUPPORTED,
                )

    def test_automatic_retry_false_always(self):
        plans = (_source_plan(1), _source_plan(2, MarketVenue.NXT))
        contexts = (
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
            _context(2, subject.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED),
        )
        result = subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
            _snapshot(plans),
            contexts,
        )
        self.assertTrue(all(not x.automatic_retry_permitted for x in result.evaluations))
        self.assertEqual(result.automatic_retry_permitted_count, 0)

    def test_mixed_counts(self):
        plans = (
            _source_plan(1),
            _source_plan(2),
            _source_plan(3),
            _source_plan(4, MarketVenue.NXT),
        )
        contexts = (
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
            _context(2, subject.KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED),
            _context(3, subject.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED),
            _context(4, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
        )
        result = subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
            _snapshot(plans),
            contexts,
        )
        self.assertEqual(result.candidate_count, 4)
        self.assertEqual(result.ready_for_confirmation_count, 2)
        self.assertEqual(result.blocked_count, 2)
        self.assertEqual(result.reconciliation_required_count, 1)


class Phase27UpstreamInvariantTests(unittest.TestCase):
    def _assert_plan_error(self, plan):
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _unsafe_snapshot((plan,)),
                (_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_source_snapshot_wrong_type_fails(self):
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                object(),
                (),
            )

    def test_phase25_nested_snapshot_wrong_type_fails(self):
        snap = _unsafe_replace(
            _snapshot((_source_plan(1),)),
            source_snapshot=object(),
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                snap,
                (_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_phase25_mapping_identity_mismatch_fails(self):
        snap = _snapshot((_source_plan(1),))
        alien = _mapping(99)
        bad_phase25 = _mapping_snapshot((alien,))
        bad = _unsafe_replace(snap, source_snapshot=bad_phase25)
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                bad,
                (_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_source_plan_wrong_type_fails(self):
        bad_snapshot = _unsafe_snapshot((object(),))
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                bad_snapshot,
                (_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_source_mapping_wrong_type_fails(self):
        plan = _unsafe_replace(_source_plan(1), source_mapping=object())
        self._assert_plan_error(plan)

    def test_dispatch_plan_wrong_type_fails(self):
        valid = _source_plan(1)
        bad = _unsafe_replace(valid, dispatch_plan=object())
        snap = _unsafe_snapshot((bad,))
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                snap,
                (_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_candidate_count_mismatch_fails(self):
        snap = _unsafe_replace(_snapshot((_source_plan(1),)), candidate_count=2)
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                snap,
                (_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_phase26_dry_run_counts_mismatch_fails(self):
        snap = _unsafe_replace(
            _snapshot((_source_plan(1),)),
            dry_run_supported_count=0,
            dry_run_blocked_count=0,
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                snap,
                (_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_phase26_send_authorized_count_nonzero_fails(self):
        snap = _unsafe_replace(
            _snapshot((_source_plan(1),)),
            send_authorized_count=1,
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                snap,
                (_context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),),
            )

    def test_request_identity_mismatch_fails(self):
        plan = _source_plan(1)
        dispatch = _unsafe_replace(
            plan.dispatch_plan,
            request=_request(MarketVenue.KRX, stock_code="005939", quantity=1),
        )
        self._assert_plan_error(_unsafe_replace(plan, dispatch_plan=dispatch))

    def test_request_type_mismatch_fails(self):
        plan = _source_plan(1)
        mapping = _replace_mapping(plan.source_mapping, request=object())
        dispatch = _unsafe_replace(plan.dispatch_plan, request=mapping.request)
        self._assert_plan_error(
            _unsafe_replace(plan, source_mapping=mapping, dispatch_plan=dispatch)
        )

    def test_request_venue_mismatch_fails(self):
        plan = _source_plan(1)
        wrong = replace(plan.source_mapping.request, dmst_stex_tp="NXT")
        mapping = _replace_mapping(plan.source_mapping, request=wrong)
        dispatch = _unsafe_replace(plan.dispatch_plan, request=wrong)
        self._assert_plan_error(
            _unsafe_replace(plan, source_mapping=mapping, dispatch_plan=dispatch)
        )

    def test_send_authorized_true_fails(self):
        plan = _source_plan(1)
        self._assert_plan_error(
            _unsafe_replace(
                plan,
                dispatch_plan=_unsafe_replace(
                    plan.dispatch_plan,
                    send_authorized=True,
                ),
            )
        )

    def test_demo_base_url_mismatch_fails(self):
        plan = _source_plan(1)
        self._assert_plan_error(
            _unsafe_replace(
                plan,
                dispatch_plan=_unsafe_replace(plan.dispatch_plan, base_url="x"),
            )
        )

    def test_http_method_mismatch_fails(self):
        plan = _source_plan(1)
        self._assert_plan_error(
            _unsafe_replace(
                plan,
                dispatch_plan=_unsafe_replace(plan.dispatch_plan, http_method="GET"),
            )
        )

    def test_api_id_mismatch_fails(self):
        plan = _source_plan(1)
        self._assert_plan_error(
            _unsafe_replace(
                plan,
                dispatch_plan=_unsafe_replace(plan.dispatch_plan, api_id="BAD"),
            )
        )

    def test_api_path_mismatch_fails(self):
        plan = _source_plan(1)
        self._assert_plan_error(
            _unsafe_replace(
                plan,
                dispatch_plan=_unsafe_replace(plan.dispatch_plan, api_path="/bad"),
            )
        )

    def test_content_type_mismatch_fails(self):
        plan = _source_plan(1)
        self._assert_plan_error(
            _unsafe_replace(
                plan,
                dispatch_plan=_unsafe_replace(plan.dispatch_plan, content_type="bad"),
            )
        )

    def test_krx_wrong_phase26_decision_fails(self):
        plan = _source_plan(1)
        dispatch = replace(
            plan.dispatch_plan,
            decision=KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED,
            block_reason=KiwoomDemoOrderDispatchBlockReason.DEMO_VENUE_UNSUPPORTED,
        )
        self._assert_plan_error(_unsafe_replace(plan, dispatch_plan=dispatch))

    def test_nxt_wrong_phase26_decision_fails(self):
        plan = _source_plan(1, MarketVenue.NXT)
        dispatch = replace(
            plan.dispatch_plan,
            decision=KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED,
            block_reason=None,
        )
        self._assert_plan_error(_unsafe_replace(plan, dispatch_plan=dispatch))

    def test_unknown_venue_fails(self):
        plan = _source_plan(1)
        mapping = _replace_mapping(plan.source_mapping, venue="UNKNOWN")
        self._assert_plan_error(_unsafe_replace(plan, source_mapping=mapping))


class Phase27IdentityAtomicityTests(unittest.TestCase):
    def test_empty_snapshot_allowed(self):
        source_snapshot = _snapshot(())
        result = subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
            source_snapshot,
            (),
        )
        self.assertIs(result.source_snapshot, source_snapshot)
        self.assertEqual(result.evaluations, ())
        self.assertEqual(result.candidate_count, 0)

    def test_all_blocked_snapshot_allowed(self):
        plans = (_source_plan(1, MarketVenue.NXT), _source_plan(2, MarketVenue.SOR))
        contexts = (
            _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
            _context(2, subject.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED),
        )
        result = subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
            _snapshot(plans),
            contexts,
        )
        self.assertEqual(result.ready_for_confirmation_count, 0)
        self.assertEqual(result.blocked_count, 2)

    def test_snapshot_plan_context_request_identity_preserved(self):
        plan = _source_plan(1)
        context = _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED)
        source_snapshot = _snapshot((plan,))
        request = plan.dispatch_plan.request
        result = subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
            source_snapshot,
            (context,),
        )
        self.assertIs(result.source_snapshot, source_snapshot)
        self.assertIs(result.evaluations[0].source_plan, plan)
        self.assertIs(result.evaluations[0].context, context)
        self.assertIs(result.evaluations[0].source_plan.dispatch_plan.request, request)

    def test_ordering_preserved(self):
        plans = (_source_plan(3), _source_plan(1), _source_plan(2))
        contexts = tuple(
            _context(p.source_mapping.source_rank, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED)
            for p in plans
        )
        result = subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
            _snapshot(plans),
            contexts,
        )
        self.assertEqual(
            [x.source_plan.source_mapping.source_rank for x in result.evaluations],
            [3, 1, 2],
        )

    def test_error_path_returns_no_partial_snapshot(self):
        plans = (_source_plan(1), _source_plan(2))
        bad_second = _unsafe_replace(
            plans[1],
            dispatch_plan=_unsafe_replace(
                plans[1].dispatch_plan,
                send_authorized=True,
            ),
        )
        with self.assertRaises(subject.KiwoomOrderSubmissionSafetyError):
            subject.build_watchlist_kiwoom_order_submission_safety_snapshot(
                _unsafe_snapshot((plans[0], bad_second)),
                (
                    _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
                    _context(2, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED),
                ),
            )

    def test_context_is_frozen(self):
        context = _context(1, subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED)
        with self.assertRaises(FrozenInstanceError):
            context.source_rank = 2

    def test_candidate_result_is_frozen(self):
        item = _build_one(subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED).evaluations[0]
        with self.assertRaises(FrozenInstanceError):
            item.automatic_retry_permitted = True

    def test_snapshot_result_is_frozen(self):
        result = _build_one(subject.KiwoomPriorSubmissionState.NEVER_ATTEMPTED)
        with self.assertRaises(FrozenInstanceError):
            result.candidate_count = 99


class Phase27SafetyBoundaryTests(unittest.TestCase):
    def test_source_has_no_network_or_provider_client_imports(self):
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        self.assertTrue(
            imported_roots.isdisjoint(
                {"requests", "httpx", "socket", "websockets", "urllib", "aiohttp"}
            )
        )

    def test_source_has_no_client_oauth_or_attempt_id_symbols(self):
        text = SOURCE_PATH.read_text(encoding="utf-8")
        for token in (
            "get_client",
            "get_ws_client",
            "OAuth",
            "oauth",
            "submission_attempt_id",
        ):
            self.assertNotIn(token, text)

    def test_rest_init_is_unchanged_empty_file(self):
        self.assertEqual(REST_INIT_PATH.read_bytes(), b"")

    def test_dependency_files_match_approved_hashes(self):
        expected = {
            "pyproject.toml": "19F7833CBBF81A182EAF0C2C8BEB9C0BCB6701B967B94F2A90236F3F26146A06",
            "uv.lock": "EFD171C3ED130E37C9A30DB7E19BBF0942F83C7BD9329440F6FD3C3CF1C81114",
        }
        for rel, expected_sha in expected.items():
            with self.subTest(rel=rel):
                actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest().upper()
                self.assertEqual(actual, expected_sha)


if __name__ == "__main__":
    unittest.main()
