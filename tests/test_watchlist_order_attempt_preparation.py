from __future__ import annotations

import ast
import hashlib
import inspect
import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_attempt_preparation as subject
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_submission_safety as safety
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
    / "watchlist_order_attempt_preparation.py"
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
    "KiwoomOrderAttemptPreparationError",
    "KiwoomOrderPreparationConfirmationState",
    "KiwoomOrderAttemptPreparationDecision",
    "KiwoomOrderAttemptPreparationBlockReason",
    "KiwoomOrderAttemptPreparationContext",
    "WatchlistCandidateKiwoomOrderAttemptPreparation",
    "WatchlistKiwoomOrderAttemptPreparationSnapshot",
    "build_watchlist_kiwoom_order_attempt_preparation_snapshot",
)

PHASE27_PUBLIC_API = (
    "KiwoomOrderSubmissionSafetyError",
    "KiwoomPriorSubmissionState",
    "KiwoomOrderSubmissionSafetyDecision",
    "KiwoomOrderSubmissionSafetyBlockReason",
    "KiwoomOrderSubmissionSafetyContext",
    "WatchlistCandidateKiwoomOrderSubmissionSafety",
    "WatchlistKiwoomOrderSubmissionSafetySnapshot",
    "build_watchlist_kiwoom_order_submission_safety_snapshot",
)

PHASE26_PUBLIC_API = (
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

PHASE25_PUBLIC_API = (
    "KIWOOM_BUY_ORDER_API_ID",
    "KIWOOM_ORDER_API_PATH",
    "KiwoomOrderMappingError",
    "KiwoomBuyOrderRequest",
    "WatchlistCandidateKiwoomOrderMapping",
    "WatchlistKiwoomOrderMappingSnapshot",
    "build_watchlist_kiwoom_order_mapping_snapshot",
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
) -> WatchlistCandidateKiwoomOrderMapping:
    stock_code = f"{5929 + rank:06d}"
    request = _request(venue, stock_code=stock_code, quantity=rank)
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
        request=request,
    )


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


def _dispatch_snapshot(
    plans: tuple[WatchlistCandidateKiwoomOrderDispatchPlan, ...],
) -> WatchlistKiwoomOrderDispatchPlanSnapshot:
    mappings = tuple(plan.source_mapping for plan in plans)
    supported = sum(
        plan.dispatch_plan.decision
        is KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED
        for plan in plans
    )
    return WatchlistKiwoomOrderDispatchPlanSnapshot(
        source_snapshot=_mapping_snapshot(mappings),
        plans=plans,
        candidate_count=len(plans),
        dry_run_supported_count=supported,
        dry_run_blocked_count=len(plans) - supported,
        send_authorized_count=0,
    )


def _safety_context(
    rank: int,
    state: safety.KiwoomPriorSubmissionState,
) -> safety.KiwoomOrderSubmissionSafetyContext:
    if state is safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED:
        return safety.KiwoomOrderSubmissionSafetyContext(rank, state)
    if state is safety.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED:
        return safety.KiwoomOrderSubmissionSafetyContext(
            rank,
            state,
            prior_attempt_reference=f"PRIOR-{rank}",
        )
    return safety.KiwoomOrderSubmissionSafetyContext(
        rank,
        state,
        prior_attempt_reference=f"PRIOR-{rank}",
        reconciliation_reference=f"RECON-{rank}",
    )


def _safety_snapshot(
    states: tuple[safety.KiwoomPriorSubmissionState, ...],
    venues: tuple[MarketVenue, ...] | None = None,
    ranks: tuple[int, ...] | None = None,
) -> safety.WatchlistKiwoomOrderSubmissionSafetySnapshot:
    if venues is None:
        venues = tuple(MarketVenue.KRX for _ in states)
    if ranks is None:
        ranks = tuple(range(1, len(states) + 1))
    plans = tuple(
        _source_plan(rank, venue)
        for rank, venue in zip(ranks, venues, strict=True)
    )
    contexts = tuple(
        _safety_context(rank, state)
        for rank, state in zip(ranks, states, strict=True)
    )
    return safety.build_watchlist_kiwoom_order_submission_safety_snapshot(
        _dispatch_snapshot(plans),
        contexts,
    )


def _prep_context(
    rank: int,
    *,
    confirmed: bool,
    confirmation_reference: str | None = None,
    submission_attempt_reference: str | None = None,
) -> subject.KiwoomOrderAttemptPreparationContext:
    if confirmed:
        if confirmation_reference is None:
            confirmation_reference = f"CONFIRM-{rank}"
        if submission_attempt_reference is None:
            submission_attempt_reference = f"ATTEMPT-{rank}"
        state = subject.KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION
    else:
        state = subject.KiwoomOrderPreparationConfirmationState.NOT_CONFIRMED
    return subject.KiwoomOrderAttemptPreparationContext(
        source_rank=rank,
        confirmation_state=state,
        confirmation_reference=confirmation_reference,
        submission_attempt_reference=submission_attempt_reference,
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


def _build(
    source_snapshot: safety.WatchlistKiwoomOrderSubmissionSafetySnapshot,
    contexts: tuple[subject.KiwoomOrderAttemptPreparationContext, ...],
) -> subject.WatchlistKiwoomOrderAttemptPreparationSnapshot:
    return subject.build_watchlist_kiwoom_order_attempt_preparation_snapshot(
        source_snapshot,
        contexts,
    )


def _count_test_methods(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


class Phase28PublicApiTests(unittest.TestCase):
    def test_public_api_exact_eight(self):
        self.assertEqual(subject.__all__, PUBLIC_API)

    def test_error_base(self):
        self.assertTrue(issubclass(subject.KiwoomOrderAttemptPreparationError, RuntimeError))

    def test_confirmation_state_enum_exact(self):
        self.assertEqual(
            [(item.name, item.value) for item in subject.KiwoomOrderPreparationConfirmationState],
            [
                ("NOT_CONFIRMED", "NOT_CONFIRMED"),
                ("CONFIRMED_FOR_PREPARATION", "CONFIRMED_FOR_PREPARATION"),
            ],
        )

    def test_decision_enum_exact(self):
        self.assertEqual(
            [(item.name, item.value) for item in subject.KiwoomOrderAttemptPreparationDecision],
            [
                ("ATTEMPT_PREPARED", "ATTEMPT_PREPARED"),
                ("ATTEMPT_BLOCKED", "ATTEMPT_BLOCKED"),
            ],
        )

    def test_block_reason_enum_exact(self):
        self.assertEqual(
            [(item.name, item.value) for item in subject.KiwoomOrderAttemptPreparationBlockReason],
            [
                ("UPSTREAM_SUBMISSION_BLOCKED", "UPSTREAM_SUBMISSION_BLOCKED"),
                ("CONFIRMATION_REQUIRED", "CONFIRMATION_REQUIRED"),
            ],
        )

    def test_context_dataclass_contract(self):
        cls = subject.KiwoomOrderAttemptPreparationContext
        self.assertTrue(cls.__dataclass_params__.frozen)
        self.assertTrue(hasattr(cls, "__slots__"))
        self.assertEqual(
            [field.name for field in fields(cls)],
            [
                "source_rank",
                "confirmation_state",
                "confirmation_reference",
                "submission_attempt_reference",
            ],
        )

    def test_candidate_dataclass_contract(self):
        cls = subject.WatchlistCandidateKiwoomOrderAttemptPreparation
        self.assertTrue(cls.__dataclass_params__.frozen)
        self.assertTrue(hasattr(cls, "__slots__"))
        self.assertEqual(
            [field.name for field in fields(cls)],
            [
                "source_evaluation",
                "context",
                "decision",
                "block_reason",
                "single_attempt_prepared",
                "automatic_retry_permitted",
            ],
        )

    def test_snapshot_dataclass_contract(self):
        cls = subject.WatchlistKiwoomOrderAttemptPreparationSnapshot
        self.assertTrue(cls.__dataclass_params__.frozen)
        self.assertTrue(hasattr(cls, "__slots__"))
        self.assertEqual(
            [field.name for field in fields(cls)],
            [
                "source_snapshot",
                "preparations",
                "candidate_count",
                "prepared_count",
                "blocked_count",
                "confirmation_required_count",
                "automatic_retry_permitted_count",
            ],
        )

    def test_builder_signature_exact(self):
        signature = inspect.signature(
            subject.build_watchlist_kiwoom_order_attempt_preparation_snapshot
        )
        self.assertEqual(list(signature.parameters), ["source_snapshot", "contexts"])
        self.assertEqual(
            str(signature.return_annotation),
            "WatchlistKiwoomOrderAttemptPreparationSnapshot",
        )

    def test_public_definitions_exact(self):
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        names = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and not node.name.startswith("_")
        ]
        self.assertEqual(tuple(names), PUBLIC_API)


class Phase28UpstreamIdentityTests(unittest.TestCase):
    def test_source_snapshot_identity_preserved(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        result = _build(upstream, (_prep_context(1, confirmed=False),))
        self.assertIs(result.source_snapshot, upstream)

    def test_source_evaluation_identity_preserved(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        result = _build(upstream, (_prep_context(1, confirmed=False),))
        self.assertIs(result.preparations[0].source_evaluation, upstream.evaluations[0])

    def test_context_identity_preserved(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        context = _prep_context(1, confirmed=False)
        result = _build(upstream, (context,))
        self.assertIs(result.preparations[0].context, context)

    def test_relative_order_is_preserved(self):
        ranks = (3, 1, 2)
        upstream = _safety_snapshot(
            tuple(safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED for _ in ranks),
            ranks=ranks,
        )
        contexts = tuple(_prep_context(rank, confirmed=False) for rank in ranks)
        result = _build(upstream, contexts)
        self.assertEqual(
            [item.context.source_rank for item in result.preparations],
            [3, 1, 2],
        )

    def test_missing_context_fails_closed(self):
        upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
            )
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(upstream, (_prep_context(1, confirmed=False),))

    def test_extra_context_fails_closed(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(
                upstream,
                (
                    _prep_context(1, confirmed=False),
                    _prep_context(2, confirmed=False),
                ),
            )

    def test_source_rank_pairing_mismatch_fails_closed(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(upstream, (_prep_context(2, confirmed=False),))

    def test_duplicate_context_rank_fails_closed(self):
        upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
            )
        )
        contexts = (
            _prep_context(1, confirmed=False),
            _unsafe_replace(_prep_context(2, confirmed=False), source_rank=1),
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(upstream, contexts)

    def test_phase27_evaluation_order_identity_mismatch_fails_closed(self):
        upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
            )
        )
        malformed = _unsafe_replace(
            upstream,
            evaluations=(upstream.evaluations[1], upstream.evaluations[0]),
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(
                malformed,
                (
                    _prep_context(1, confirmed=False),
                    _prep_context(2, confirmed=False),
                ),
            )

    def test_phase25_request_identity_mismatch_fails_closed(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        plan = upstream.evaluations[0].source_plan
        bad_dispatch = _unsafe_replace(
            plan.dispatch_plan,
            request=_request(MarketVenue.KRX, stock_code="999999"),
        )
        bad_plan = _unsafe_replace(plan, dispatch_plan=bad_dispatch)
        phase26 = upstream.source_snapshot
        bad_phase26 = _unsafe_replace(phase26, plans=(bad_plan,))
        malformed = _unsafe_replace(
            upstream,
            source_snapshot=bad_phase26,
            evaluations=(
                _unsafe_replace(upstream.evaluations[0], source_plan=bad_plan),
            ),
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(malformed, (_prep_context(1, confirmed=False),))


class Phase28ReferenceInvariantTests(unittest.TestCase):
    def setUp(self):
        self.upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
            )
        )

    def test_not_confirmed_requires_both_references_none(self):
        result = _build(self.upstream, (_prep_context(1, confirmed=False), _prep_context(2, confirmed=False)))
        self.assertTrue(all(item.context.confirmation_reference is None for item in result.preparations))

    def test_not_confirmed_confirmation_reference_rejected(self):
        context = subject.KiwoomOrderAttemptPreparationContext(
            1,
            subject.KiwoomOrderPreparationConfirmationState.NOT_CONFIRMED,
            confirmation_reference="C",
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_not_confirmed_submission_reference_rejected(self):
        context = subject.KiwoomOrderAttemptPreparationContext(
            1,
            subject.KiwoomOrderPreparationConfirmationState.NOT_CONFIRMED,
            submission_attempt_reference="A",
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_confirmed_requires_confirmation_reference(self):
        context = subject.KiwoomOrderAttemptPreparationContext(
            1,
            subject.KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION,
            submission_attempt_reference="A",
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_confirmed_requires_submission_reference(self):
        context = subject.KiwoomOrderAttemptPreparationContext(
            1,
            subject.KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION,
            confirmation_reference="C",
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_confirmation_reference_type_rejected(self):
        context = subject.KiwoomOrderAttemptPreparationContext(
            1,
            subject.KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION,
            confirmation_reference=123,
            submission_attempt_reference="A",
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_submission_reference_type_rejected(self):
        context = subject.KiwoomOrderAttemptPreparationContext(
            1,
            subject.KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION,
            confirmation_reference="C",
            submission_attempt_reference=123,
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_blank_confirmation_reference_rejected(self):
        context = _prep_context(1, confirmed=True, confirmation_reference="   ")
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_blank_submission_reference_rejected(self):
        context = _prep_context(1, confirmed=True, submission_attempt_reference="\t")
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_duplicate_confirmation_reference_rejected(self):
        contexts = (
            _prep_context(1, confirmed=True, confirmation_reference="SAME"),
            _prep_context(2, confirmed=True, confirmation_reference="SAME"),
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(self.upstream, contexts)

    def test_duplicate_submission_reference_rejected(self):
        contexts = (
            _prep_context(1, confirmed=True, submission_attempt_reference="SAME"),
            _prep_context(2, confirmed=True, submission_attempt_reference="SAME"),
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(self.upstream, contexts)

    def test_same_context_reference_collision_rejected(self):
        context = _prep_context(
            1,
            confirmed=True,
            confirmation_reference="SAME",
            submission_attempt_reference="SAME",
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(_safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,)), (context,))

    def test_submission_reference_must_differ_from_prior_attempt(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED,))
        context = _prep_context(1, confirmed=True, submission_attempt_reference="PRIOR-1")
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(upstream, (context,))

    def test_reference_values_are_preserved_without_trimming(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        context = _prep_context(
            1,
            confirmed=True,
            confirmation_reference="  CONFIRM  ",
            submission_attempt_reference="  ATTEMPT  ",
        )
        result = _build(upstream, (context,))
        self.assertEqual(result.preparations[0].context.confirmation_reference, "  CONFIRM  ")
        self.assertEqual(result.preparations[0].context.submission_attempt_reference, "  ATTEMPT  ")


class Phase28DecisionMatrixTests(unittest.TestCase):
    def test_ready_confirmed_becomes_prepared(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        item = _build(upstream, (_prep_context(1, confirmed=True),)).preparations[0]
        self.assertIs(item.decision, subject.KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED)
        self.assertIsNone(item.block_reason)
        self.assertTrue(item.single_attempt_prepared)

    def test_ready_not_confirmed_requires_confirmation(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        item = _build(upstream, (_prep_context(1, confirmed=False),)).preparations[0]
        self.assertIs(item.decision, subject.KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED)
        self.assertIs(item.block_reason, subject.KiwoomOrderAttemptPreparationBlockReason.CONFIRMATION_REQUIRED)
        self.assertFalse(item.single_attempt_prepared)

    def test_upstream_blocked_not_confirmed_stays_blocked(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,))
        item = _build(upstream, (_prep_context(1, confirmed=False),)).preparations[0]
        self.assertIs(item.block_reason, subject.KiwoomOrderAttemptPreparationBlockReason.UPSTREAM_SUBMISSION_BLOCKED)

    def test_upstream_blocked_confirmed_fails_closed(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,))
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(upstream, (_prep_context(1, confirmed=True),))

    def test_upstream_blocked_reference_injection_fails_closed(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,))
        context = subject.KiwoomOrderAttemptPreparationContext(
            1,
            subject.KiwoomOrderPreparationConfirmationState.NOT_CONFIRMED,
            confirmation_reference="INJECTED",
        )
        with self.assertRaises(subject.KiwoomOrderAttemptPreparationError):
            _build(upstream, (context,))

    def test_prepared_iff_single_attempt_prepared_true(self):
        upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
            )
        )
        result = _build(
            upstream,
            (
                _prep_context(1, confirmed=True),
                _prep_context(2, confirmed=False),
            ),
        )
        for item in result.preparations:
            self.assertEqual(
                item.decision is subject.KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED,
                item.single_attempt_prepared,
            )

    def test_automatic_retry_is_false_for_every_candidate(self):
        upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,
            )
        )
        result = _build(upstream, (_prep_context(1, confirmed=True), _prep_context(2, confirmed=False)))
        self.assertTrue(all(item.automatic_retry_permitted is False for item in result.preparations))

    def test_confirmed_accepted_never_promoted_to_prepared(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,))
        item = _build(upstream, (_prep_context(1, confirmed=False),)).preparations[0]
        self.assertIs(item.decision, subject.KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED)

    def test_ambiguous_unresolved_never_promoted_to_prepared(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED,))
        item = _build(upstream, (_prep_context(1, confirmed=False),)).preparations[0]
        self.assertIs(item.decision, subject.KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED)
        self.assertIs(item.block_reason, subject.KiwoomOrderAttemptPreparationBlockReason.UPSTREAM_SUBMISSION_BLOCKED)

    def test_demo_unsupported_candidate_never_promoted_to_prepared(self):
        upstream = _safety_snapshot(
            (safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,),
            venues=(MarketVenue.NXT,),
        )
        item = _build(upstream, (_prep_context(1, confirmed=False),)).preparations[0]
        self.assertIs(item.decision, subject.KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED)


class Phase28SnapshotAggregateTests(unittest.TestCase):
    def test_empty_snapshot_counts_zero(self):
        upstream = _safety_snapshot(())
        result = _build(upstream, ())
        self.assertEqual(
            (
                result.candidate_count,
                result.prepared_count,
                result.blocked_count,
                result.confirmation_required_count,
                result.automatic_retry_permitted_count,
            ),
            (0, 0, 0, 0, 0),
        )

    def test_all_prepared_counts(self):
        upstream = _safety_snapshot(
            tuple(safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED for _ in range(3))
        )
        result = _build(upstream, tuple(_prep_context(i, confirmed=True) for i in range(1, 4)))
        self.assertEqual((result.candidate_count, result.prepared_count, result.blocked_count), (3, 3, 0))

    def test_all_confirmation_required_counts(self):
        upstream = _safety_snapshot(
            tuple(safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED for _ in range(3))
        )
        result = _build(upstream, tuple(_prep_context(i, confirmed=False) for i in range(1, 4)))
        self.assertEqual((result.blocked_count, result.confirmation_required_count), (3, 3))

    def test_mixed_snapshot_counts(self):
        upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,
            )
        )
        result = _build(
            upstream,
            (
                _prep_context(1, confirmed=True),
                _prep_context(2, confirmed=False),
                _prep_context(3, confirmed=False),
            ),
        )
        self.assertEqual(
            (result.candidate_count, result.prepared_count, result.blocked_count, result.confirmation_required_count),
            (3, 1, 2, 1),
        )

    def test_candidate_count_equals_preparations_length(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        result = _build(upstream, (_prep_context(1, confirmed=True),))
        self.assertEqual(result.candidate_count, len(result.preparations))

    def test_prepared_plus_blocked_equals_candidate_count(self):
        upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,
            )
        )
        result = _build(upstream, (_prep_context(1, confirmed=True), _prep_context(2, confirmed=False)))
        self.assertEqual(result.prepared_count + result.blocked_count, result.candidate_count)

    def test_automatic_retry_permitted_count_is_zero(self):
        upstream = _safety_snapshot(
            (
                safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
                safety.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,
            )
        )
        result = _build(upstream, (_prep_context(1, confirmed=True), _prep_context(2, confirmed=False)))
        self.assertEqual(result.automatic_retry_permitted_count, 0)

    def test_result_dataclasses_are_frozen(self):
        upstream = _safety_snapshot((safety.KiwoomPriorSubmissionState.NEVER_ATTEMPTED,))
        result = _build(upstream, (_prep_context(1, confirmed=True),))
        with self.assertRaises(FrozenInstanceError):
            result.candidate_count = 99
        with self.assertRaises(FrozenInstanceError):
            result.preparations[0].single_attempt_prepared = False


class Phase28ForbiddenSideEffectTests(unittest.TestCase):
    def test_source_has_no_network_library_imports(self):
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertTrue(roots.isdisjoint({"requests", "httpx", "socket", "websockets", "urllib", "aiohttp"}))

    def test_source_has_no_provider_client_or_oauth_symbols(self):
        text = SOURCE_PATH.read_text(encoding="utf-8")
        for token in ("get_client", "get_ws_client", "OAuth", "oauth"):
            self.assertNotIn(token, text)

    def test_source_has_no_credential_or_dotenv_access_symbols(self):
        text = SOURCE_PATH.read_text(encoding="utf-8")
        for token in ("KIWOOM_APP_KEY", "KIWOOM_APP_SECRET", "ACCESS_TOKEN", "dotenv", 'open(".env"'):
            self.assertNotIn(token, text)

    def test_source_has_no_http_submission_calls(self):
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        call_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    call_names.add(node.func.attr)
        self.assertTrue(call_names.isdisjoint({"post", "request", "send", "connect"}))

    def test_rest_init_remains_empty(self):
        self.assertEqual(REST_INIT_PATH.read_bytes(), b"")

    def test_dependency_files_match_approved_hashes(self):
        expected = {
            "pyproject.toml": "19F7833CBBF81A182EAF0C2C8BEB9C0BCB6701B967B94F2A90236F3F26146A06",
            "uv.lock": "EFD171C3ED130E37C9A30DB7E19BBF0942F83C7BD9329440F6FD3C3CF1C81114",
        }
        for relative, expected_sha in expected.items():
            with self.subTest(relative=relative):
                actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest().upper()
                self.assertEqual(actual, expected_sha)


class Phase28CompatibilityBoundaryTests(unittest.TestCase):
    def test_phase27_public_api_exact(self):
        self.assertEqual(safety.__all__, PHASE27_PUBLIC_API)

    def test_phase26_public_api_exact(self):
        from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_dispatch_plan as phase26
        self.assertEqual(tuple(phase26.__all__), PHASE26_PUBLIC_API)

    def test_phase25_public_api_exact(self):
        from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_mapping as phase25
        self.assertEqual(tuple(phase25.__all__), PHASE25_PUBLIC_API)

    def test_phase27_26_25_static_test_counts_exact(self):
        self.assertEqual(_count_test_methods(ROOT / "tests/test_watchlist_order_submission_safety.py"), 72)
        self.assertEqual(_count_test_methods(ROOT / "tests/test_watchlist_order_dispatch_plan.py"), 59)
        self.assertEqual(_count_test_methods(ROOT / "tests/test_watchlist_order_mapping.py"), 59)

    def test_phase27_26_25_source_and_test_hashes_exact(self):
        expected = {
            "src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_submission_safety.py": "D544CCDCB8421DB424175D4251009C1A9B4798090402854DD54D2E74D04595AC",
            "tests/test_watchlist_order_submission_safety.py": "C625B785337F03D2413785D0FB3AD93F2CFFEE4DB13B957FD5B2988559DEBE20",
            "src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_dispatch_plan.py": "CE004F1619ACFD78FAB4CF25CD476C2421AEE8FCA9F822AB76C90C1F02DFDE56",
            "tests/test_watchlist_order_dispatch_plan.py": "0E553A13A77524BF108C769090BD1F91EEDF80C3EA156911581054FFFF7D21A5",
            "src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_mapping.py": "A2D50E769E89AC1902598791A88189155E7BC7637CECAE70D4A8D40FFB9DFBD0",
            "tests/test_watchlist_order_mapping.py": "256056BF1D03E3014A18E4D290753146543679FD730CE7A2B4AA0A98AA42C7C0",
        }
        for relative, expected_sha in expected.items():
            with self.subTest(relative=relative):
                actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest().upper()
                self.assertEqual(actual, expected_sha)

    def test_no_phase28_rest_package_reexport(self):
        init_text = REST_INIT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("KiwoomOrderAttemptPreparation", init_text)
        self.assertNotIn("watchlist_order_attempt_preparation", init_text)


if __name__ == "__main__":
    unittest.main()
