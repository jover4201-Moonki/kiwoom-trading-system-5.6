from __future__ import annotations

from dataclasses import dataclass as _dataclass
from enum import Enum as _Enum
from typing import TYPE_CHECKING as _TYPE_CHECKING

from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_dispatch_plan import (
    KIWOOM_DEMO_ORDER_BASE_URL as _KIWOOM_DEMO_ORDER_BASE_URL,
    KIWOOM_ORDER_CONTENT_TYPE as _KIWOOM_ORDER_CONTENT_TYPE,
    KIWOOM_ORDER_HTTP_METHOD as _KIWOOM_ORDER_HTTP_METHOD,
    KiwoomBuyOrderDispatchPlan as _KiwoomBuyOrderDispatchPlan,
    KiwoomDemoOrderDispatchBlockReason as _KiwoomDemoOrderDispatchBlockReason,
    KiwoomDemoOrderDispatchDecision as _KiwoomDemoOrderDispatchDecision,
    WatchlistCandidateKiwoomOrderDispatchPlan as _WatchlistCandidateKiwoomOrderDispatchPlan,
    WatchlistKiwoomOrderDispatchPlanSnapshot as _WatchlistKiwoomOrderDispatchPlanSnapshot,
)
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_mapping import (
    KIWOOM_BUY_ORDER_API_ID as _KIWOOM_BUY_ORDER_API_ID,
    KIWOOM_ORDER_API_PATH as _KIWOOM_ORDER_API_PATH,
    KiwoomBuyOrderRequest as _KiwoomBuyOrderRequest,
    WatchlistCandidateKiwoomOrderMapping as _WatchlistCandidateKiwoomOrderMapping,
    WatchlistKiwoomOrderMappingSnapshot as _WatchlistKiwoomOrderMappingSnapshot,
)
from kiwoom_trading_system.market_data import MarketVenue as _MarketVenue

if _TYPE_CHECKING:
    from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_dispatch_plan import (
        WatchlistCandidateKiwoomOrderDispatchPlan,
        WatchlistKiwoomOrderDispatchPlanSnapshot,
    )

__all__ = (
    "KiwoomOrderSubmissionSafetyError",
    "KiwoomPriorSubmissionState",
    "KiwoomOrderSubmissionSafetyDecision",
    "KiwoomOrderSubmissionSafetyBlockReason",
    "KiwoomOrderSubmissionSafetyContext",
    "WatchlistCandidateKiwoomOrderSubmissionSafety",
    "WatchlistKiwoomOrderSubmissionSafetySnapshot",
    "build_watchlist_kiwoom_order_submission_safety_snapshot",
)


class KiwoomOrderSubmissionSafetyError(RuntimeError):
    """Raised when Phase27 submission-readiness input violates the approved contract."""


class KiwoomPriorSubmissionState(str, _Enum):
    NEVER_ATTEMPTED = "NEVER_ATTEMPTED"
    CONFIRMED_NOT_ACCEPTED = "CONFIRMED_NOT_ACCEPTED"
    CONFIRMED_ACCEPTED = "CONFIRMED_ACCEPTED"
    AMBIGUOUS_UNRESOLVED = "AMBIGUOUS_UNRESOLVED"


class KiwoomOrderSubmissionSafetyDecision(str, _Enum):
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    SUBMISSION_BLOCKED = "SUBMISSION_BLOCKED"


class KiwoomOrderSubmissionSafetyBlockReason(str, _Enum):
    DEMO_VENUE_UNSUPPORTED = "DEMO_VENUE_UNSUPPORTED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    ALREADY_ACCEPTED = "ALREADY_ACCEPTED"


@_dataclass(frozen=True, slots=True)
class KiwoomOrderSubmissionSafetyContext:
    source_rank: int
    prior_submission_state: KiwoomPriorSubmissionState
    prior_attempt_reference: str | None = None
    reconciliation_reference: str | None = None


@_dataclass(frozen=True, slots=True)
class WatchlistCandidateKiwoomOrderSubmissionSafety:
    source_plan: WatchlistCandidateKiwoomOrderDispatchPlan
    context: KiwoomOrderSubmissionSafetyContext
    decision: KiwoomOrderSubmissionSafetyDecision
    block_reason: KiwoomOrderSubmissionSafetyBlockReason | None
    automatic_retry_permitted: bool


@_dataclass(frozen=True, slots=True)
class WatchlistKiwoomOrderSubmissionSafetySnapshot:
    source_snapshot: WatchlistKiwoomOrderDispatchPlanSnapshot
    evaluations: tuple[WatchlistCandidateKiwoomOrderSubmissionSafety, ...]
    candidate_count: int
    ready_for_confirmation_count: int
    blocked_count: int
    reconciliation_required_count: int
    automatic_retry_permitted_count: int


def _error(message: str) -> KiwoomOrderSubmissionSafetyError:
    return KiwoomOrderSubmissionSafetyError(message)


def _validate_reference(value: object, field_name: str, required: bool) -> None:
    if value is None:
        if required:
            raise _error(f"{field_name} is required for the selected prior submission state.")
        return
    if type(value) is not str:
        raise _error(f"{field_name} must be str or None.")
    if value == "":
        raise _error(f"{field_name} must not be an empty string.")


def _validate_context(context: object) -> KiwoomOrderSubmissionSafetyContext:
    if type(context) is not KiwoomOrderSubmissionSafetyContext:
        raise _error("Every context must be KiwoomOrderSubmissionSafetyContext.")
    if type(context.source_rank) is not int:
        raise _error("context.source_rank must be an int.")
    if not isinstance(context.prior_submission_state, KiwoomPriorSubmissionState):
        raise _error("context.prior_submission_state is invalid.")

    state = context.prior_submission_state
    prior = context.prior_attempt_reference
    reconciliation = context.reconciliation_reference

    if state is KiwoomPriorSubmissionState.NEVER_ATTEMPTED:
        if prior is not None or reconciliation is not None:
            raise _error("NEVER_ATTEMPTED requires both references to be None.")
        return context

    if state is KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED:
        _validate_reference(prior, "prior_attempt_reference", required=True)
        _validate_reference(reconciliation, "reconciliation_reference", required=False)
        return context

    if state in (
        KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED,
        KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,
    ):
        _validate_reference(prior, "prior_attempt_reference", required=True)
        _validate_reference(reconciliation, "reconciliation_reference", required=True)
        return context

    raise _error("Unsupported prior submission state.")


def _validate_source_plan(
    source_plan: object,
) -> tuple[_MarketVenue, int]:
    if type(source_plan) is not _WatchlistCandidateKiwoomOrderDispatchPlan:
        raise _error("Every source plan must be WatchlistCandidateKiwoomOrderDispatchPlan.")

    source_mapping = source_plan.source_mapping
    dispatch_plan = source_plan.dispatch_plan

    if type(source_mapping) is not _WatchlistCandidateKiwoomOrderMapping:
        raise _error("source_plan.source_mapping has an invalid type.")
    if type(dispatch_plan) is not _KiwoomBuyOrderDispatchPlan:
        raise _error("source_plan.dispatch_plan has an invalid type.")

    source_rank = source_mapping.source_rank
    if type(source_rank) is not int:
        raise _error("source_mapping.source_rank must be an int.")

    venue = source_mapping.venue
    if type(venue) is not _MarketVenue:
        raise _error("source_mapping.venue has an invalid type.")
    if venue not in (_MarketVenue.KRX, _MarketVenue.NXT, _MarketVenue.SOR):
        raise _error("source_mapping.venue is unsupported.")

    if type(source_mapping.request) is not _KiwoomBuyOrderRequest:
        raise _error("source_mapping.request has an invalid type.")
    if type(dispatch_plan.request) is not _KiwoomBuyOrderRequest:
        raise _error("dispatch_plan.request has an invalid type.")
    if dispatch_plan.request is not source_mapping.request:
        raise _error("dispatch_plan.request must preserve source_mapping.request identity.")
    if dispatch_plan.send_authorized is not False:
        raise _error("Phase26 send_authorized must remain False.")

    if dispatch_plan.base_url != _KIWOOM_DEMO_ORDER_BASE_URL:
        raise _error("Phase26 demo base URL is inconsistent.")
    if dispatch_plan.http_method != _KIWOOM_ORDER_HTTP_METHOD:
        raise _error("Phase26 HTTP method is inconsistent.")
    if dispatch_plan.api_id != _KIWOOM_BUY_ORDER_API_ID:
        raise _error("Phase26 API ID is inconsistent.")
    if dispatch_plan.api_path != _KIWOOM_ORDER_API_PATH:
        raise _error("Phase26 API path is inconsistent.")
    if dispatch_plan.content_type != _KIWOOM_ORDER_CONTENT_TYPE:
        raise _error("Phase26 content type is inconsistent.")

    request_venue = getattr(dispatch_plan.request, "dmst_stex_tp", None)
    if request_venue != venue.value:
        raise _error("Mapped request venue is inconsistent with source_mapping.venue.")
    if dispatch_plan.request.stk_cd != source_mapping.stock_code:
        raise _error("Mapped request stock code is inconsistent with source_mapping.")
    if dispatch_plan.request.ord_qty != str(source_mapping.requested_quantity):
        raise _error("Mapped request quantity is inconsistent with source_mapping.")

    if venue is _MarketVenue.KRX:
        if dispatch_plan.decision is not _KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED:
            raise _error("KRX requires Phase26 DRY_RUN_SUPPORTED.")
        if dispatch_plan.block_reason is not None:
            raise _error("KRX supported Phase26 plan must not have a block reason.")
    else:
        if dispatch_plan.decision is not _KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED:
            raise _error("NXT/SOR requires Phase26 DRY_RUN_BLOCKED.")
        if (
            dispatch_plan.block_reason
            is not _KiwoomDemoOrderDispatchBlockReason.DEMO_VENUE_UNSUPPORTED
        ):
            raise _error("NXT/SOR requires Phase26 DEMO_VENUE_UNSUPPORTED.")

    return venue, source_rank


def _decision_for(
    venue: _MarketVenue,
    state: KiwoomPriorSubmissionState,
) -> tuple[
    KiwoomOrderSubmissionSafetyDecision,
    KiwoomOrderSubmissionSafetyBlockReason | None,
]:
    if venue in (_MarketVenue.NXT, _MarketVenue.SOR):
        return (
            KiwoomOrderSubmissionSafetyDecision.SUBMISSION_BLOCKED,
            KiwoomOrderSubmissionSafetyBlockReason.DEMO_VENUE_UNSUPPORTED,
        )

    if state in (
        KiwoomPriorSubmissionState.NEVER_ATTEMPTED,
        KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED,
    ):
        return (
            KiwoomOrderSubmissionSafetyDecision.READY_FOR_CONFIRMATION,
            None,
        )

    if state is KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED:
        return (
            KiwoomOrderSubmissionSafetyDecision.SUBMISSION_BLOCKED,
            KiwoomOrderSubmissionSafetyBlockReason.ALREADY_ACCEPTED,
        )

    if state is KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED:
        return (
            KiwoomOrderSubmissionSafetyDecision.SUBMISSION_BLOCKED,
            KiwoomOrderSubmissionSafetyBlockReason.RECONCILIATION_REQUIRED,
        )

    raise _error("Unsupported prior submission state.")


def build_watchlist_kiwoom_order_submission_safety_snapshot(
    source_snapshot: WatchlistKiwoomOrderDispatchPlanSnapshot,
    contexts: tuple[KiwoomOrderSubmissionSafetyContext, ...],
) -> WatchlistKiwoomOrderSubmissionSafetySnapshot:
    if type(source_snapshot) is not _WatchlistKiwoomOrderDispatchPlanSnapshot:
        raise _error("source_snapshot must be WatchlistKiwoomOrderDispatchPlanSnapshot.")
    if type(contexts) is not tuple:
        raise _error("contexts must be a tuple.")

    mapping_snapshot = source_snapshot.source_snapshot
    if type(mapping_snapshot) is not _WatchlistKiwoomOrderMappingSnapshot:
        raise _error("Phase26 source_snapshot.source_snapshot has an invalid type.")
    if type(mapping_snapshot.mappings) is not tuple:
        raise _error("Phase25 mapping snapshot mappings must be a tuple.")
    if type(mapping_snapshot.mapping_count) is not int:
        raise _error("Phase25 mapping_count must be an int.")
    if mapping_snapshot.mapping_count != len(mapping_snapshot.mappings):
        raise _error("Phase25 mapping_count does not match mappings.")

    plans = source_snapshot.plans
    if type(plans) is not tuple:
        raise _error("source_snapshot.plans must be a tuple.")
    if type(source_snapshot.candidate_count) is not int:
        raise _error("source_snapshot.candidate_count must be an int.")
    if source_snapshot.candidate_count != len(plans):
        raise _error("source_snapshot.candidate_count does not match plans.")
    if type(source_snapshot.dry_run_supported_count) is not int:
        raise _error("source_snapshot.dry_run_supported_count must be an int.")
    if type(source_snapshot.dry_run_blocked_count) is not int:
        raise _error("source_snapshot.dry_run_blocked_count must be an int.")
    if (
        source_snapshot.dry_run_supported_count
        + source_snapshot.dry_run_blocked_count
        != len(plans)
    ):
        raise _error("Phase26 dry-run counts do not match plans.")
    if type(source_snapshot.send_authorized_count) is not int:
        raise _error("source_snapshot.send_authorized_count must be an int.")
    if source_snapshot.send_authorized_count != 0:
        raise _error("Phase26 send_authorized_count must be zero.")

    if len(mapping_snapshot.mappings) != len(plans):
        raise _error("Phase25 mappings count does not match Phase26 plans.")
    for index, source_plan in enumerate(plans):
        if (
            type(source_plan) is _WatchlistCandidateKiwoomOrderDispatchPlan
            and source_plan.source_mapping is not mapping_snapshot.mappings[index]
        ):
            raise _error("Phase26 plan/source mapping identity or ordering is inconsistent.")

    if len(contexts) != len(plans):
        raise _error("contexts count must exactly match source_snapshot.plans.")

    validated: list[
        tuple[
            WatchlistCandidateKiwoomOrderDispatchPlan,
            KiwoomOrderSubmissionSafetyContext,
            _MarketVenue,
        ]
    ] = []
    upstream_ranks: set[int] = set()
    context_ranks: set[int] = set()

    for source_plan, raw_context in zip(plans, contexts, strict=True):
        venue, source_rank = _validate_source_plan(source_plan)
        context = _validate_context(raw_context)

        if source_rank in upstream_ranks:
            raise _error("Duplicate source_rank exists in Phase26 source plans.")
        upstream_ranks.add(source_rank)

        if context.source_rank in context_ranks:
            raise _error("Duplicate context source_rank is prohibited.")
        context_ranks.add(context.source_rank)

        if context.source_rank != source_rank:
            raise _error("Context order/source_rank pairing does not match Phase26 plans.")

        validated.append((source_plan, context, venue))

    supported_count = sum(
        venue is _MarketVenue.KRX for _, _, venue in validated
    )
    blocked_count = len(validated) - supported_count
    if source_snapshot.dry_run_supported_count != supported_count:
        raise _error("Phase26 dry_run_supported_count is inconsistent with plans.")
    if source_snapshot.dry_run_blocked_count != blocked_count:
        raise _error("Phase26 dry_run_blocked_count is inconsistent with plans.")

    evaluations: list[WatchlistCandidateKiwoomOrderSubmissionSafety] = []
    for source_plan, context, venue in validated:
        decision, block_reason = _decision_for(
            venue,
            context.prior_submission_state,
        )
        evaluations.append(
            WatchlistCandidateKiwoomOrderSubmissionSafety(
                source_plan=source_plan,
                context=context,
                decision=decision,
                block_reason=block_reason,
                automatic_retry_permitted=False,
            )
        )

    evaluation_tuple = tuple(evaluations)
    ready_count = sum(
        item.decision
        is KiwoomOrderSubmissionSafetyDecision.READY_FOR_CONFIRMATION
        for item in evaluation_tuple
    )
    blocked_count = len(evaluation_tuple) - ready_count
    reconciliation_count = sum(
        item.block_reason
        is KiwoomOrderSubmissionSafetyBlockReason.RECONCILIATION_REQUIRED
        for item in evaluation_tuple
    )

    return WatchlistKiwoomOrderSubmissionSafetySnapshot(
        source_snapshot=source_snapshot,
        evaluations=evaluation_tuple,
        candidate_count=len(evaluation_tuple),
        ready_for_confirmation_count=ready_count,
        blocked_count=blocked_count,
        reconciliation_required_count=reconciliation_count,
        automatic_retry_permitted_count=0,
    )
