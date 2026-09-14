from __future__ import annotations

from dataclasses import dataclass as _dataclass
from enum import Enum as _Enum
from typing import TYPE_CHECKING as _TYPE_CHECKING

from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_dispatch_plan import (
    KiwoomBuyOrderDispatchPlan as _KiwoomBuyOrderDispatchPlan,
    WatchlistCandidateKiwoomOrderDispatchPlan as _WatchlistCandidateKiwoomOrderDispatchPlan,
    WatchlistKiwoomOrderDispatchPlanSnapshot as _WatchlistKiwoomOrderDispatchPlanSnapshot,
)
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_mapping import (
    WatchlistCandidateKiwoomOrderMapping as _WatchlistCandidateKiwoomOrderMapping,
    WatchlistKiwoomOrderMappingSnapshot as _WatchlistKiwoomOrderMappingSnapshot,
)
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_submission_safety import (
    KiwoomOrderSubmissionSafetyBlockReason as _KiwoomOrderSubmissionSafetyBlockReason,
    KiwoomOrderSubmissionSafetyContext as _KiwoomOrderSubmissionSafetyContext,
    KiwoomOrderSubmissionSafetyDecision as _KiwoomOrderSubmissionSafetyDecision,
    WatchlistCandidateKiwoomOrderSubmissionSafety as _WatchlistCandidateKiwoomOrderSubmissionSafety,
    WatchlistKiwoomOrderSubmissionSafetySnapshot as _WatchlistKiwoomOrderSubmissionSafetySnapshot,
)

if _TYPE_CHECKING:
    from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_submission_safety import (
        WatchlistCandidateKiwoomOrderSubmissionSafety,
        WatchlistKiwoomOrderSubmissionSafetySnapshot,
    )

__all__ = (
    "KiwoomOrderAttemptPreparationError",
    "KiwoomOrderPreparationConfirmationState",
    "KiwoomOrderAttemptPreparationDecision",
    "KiwoomOrderAttemptPreparationBlockReason",
    "KiwoomOrderAttemptPreparationContext",
    "WatchlistCandidateKiwoomOrderAttemptPreparation",
    "WatchlistKiwoomOrderAttemptPreparationSnapshot",
    "build_watchlist_kiwoom_order_attempt_preparation_snapshot",
)


class KiwoomOrderAttemptPreparationError(RuntimeError):
    """Raised when Phase28 preparation input violates the approved contract."""


class KiwoomOrderPreparationConfirmationState(str, _Enum):
    NOT_CONFIRMED = "NOT_CONFIRMED"
    CONFIRMED_FOR_PREPARATION = "CONFIRMED_FOR_PREPARATION"


class KiwoomOrderAttemptPreparationDecision(str, _Enum):
    ATTEMPT_PREPARED = "ATTEMPT_PREPARED"
    ATTEMPT_BLOCKED = "ATTEMPT_BLOCKED"


class KiwoomOrderAttemptPreparationBlockReason(str, _Enum):
    UPSTREAM_SUBMISSION_BLOCKED = "UPSTREAM_SUBMISSION_BLOCKED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"


@_dataclass(frozen=True, slots=True)
class KiwoomOrderAttemptPreparationContext:
    source_rank: int
    confirmation_state: KiwoomOrderPreparationConfirmationState
    confirmation_reference: str | None = None
    submission_attempt_reference: str | None = None


@_dataclass(frozen=True, slots=True)
class WatchlistCandidateKiwoomOrderAttemptPreparation:
    source_evaluation: WatchlistCandidateKiwoomOrderSubmissionSafety
    context: KiwoomOrderAttemptPreparationContext
    decision: KiwoomOrderAttemptPreparationDecision
    block_reason: KiwoomOrderAttemptPreparationBlockReason | None
    single_attempt_prepared: bool
    automatic_retry_permitted: bool


@_dataclass(frozen=True, slots=True)
class WatchlistKiwoomOrderAttemptPreparationSnapshot:
    source_snapshot: WatchlistKiwoomOrderSubmissionSafetySnapshot
    preparations: tuple[WatchlistCandidateKiwoomOrderAttemptPreparation, ...]
    candidate_count: int
    prepared_count: int
    blocked_count: int
    confirmation_required_count: int
    automatic_retry_permitted_count: int


def _error(message: str) -> KiwoomOrderAttemptPreparationError:
    return KiwoomOrderAttemptPreparationError(message)


def _validate_reference(value: object, field_name: str, *, required: bool) -> None:
    if value is None:
        if required:
            raise _error(f"{field_name} is required for CONFIRMED_FOR_PREPARATION.")
        return
    if type(value) is not str:
        raise _error(f"{field_name} must be str or None.")
    if value.strip() == "":
        raise _error(f"{field_name} must not be blank.")


def _validate_context(
    context: object,
) -> KiwoomOrderAttemptPreparationContext:
    if type(context) is not KiwoomOrderAttemptPreparationContext:
        raise _error("Every context must be KiwoomOrderAttemptPreparationContext.")
    if type(context.source_rank) is not int:
        raise _error("context.source_rank must be an int.")
    if type(context.confirmation_state) is not KiwoomOrderPreparationConfirmationState:
        raise _error("context.confirmation_state is invalid.")

    if context.confirmation_state is KiwoomOrderPreparationConfirmationState.NOT_CONFIRMED:
        if context.confirmation_reference is not None:
            raise _error("NOT_CONFIRMED requires confirmation_reference to be None.")
        if context.submission_attempt_reference is not None:
            raise _error("NOT_CONFIRMED requires submission_attempt_reference to be None.")
        return context

    if (
        context.confirmation_state
        is KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION
    ):
        _validate_reference(
            context.confirmation_reference,
            "confirmation_reference",
            required=True,
        )
        _validate_reference(
            context.submission_attempt_reference,
            "submission_attempt_reference",
            required=True,
        )
        if context.confirmation_reference == context.submission_attempt_reference:
            raise _error(
                "confirmation_reference and submission_attempt_reference must differ."
            )
        return context

    raise _error("Unsupported preparation confirmation state.")


def _validate_source_snapshot(
    source_snapshot: object,
) -> tuple[
    tuple[_WatchlistCandidateKiwoomOrderSubmissionSafety, ...],
    tuple[int, ...],
]:
    if type(source_snapshot) is not _WatchlistKiwoomOrderSubmissionSafetySnapshot:
        raise _error("source_snapshot must be WatchlistKiwoomOrderSubmissionSafetySnapshot.")

    dispatch_snapshot = source_snapshot.source_snapshot
    if type(dispatch_snapshot) is not _WatchlistKiwoomOrderDispatchPlanSnapshot:
        raise _error("Phase27 source_snapshot has an invalid Phase26 snapshot type.")
    mapping_snapshot = dispatch_snapshot.source_snapshot
    if type(mapping_snapshot) is not _WatchlistKiwoomOrderMappingSnapshot:
        raise _error("Phase26 source_snapshot has an invalid Phase25 snapshot type.")

    evaluations = source_snapshot.evaluations
    plans = dispatch_snapshot.plans
    mappings = mapping_snapshot.mappings
    if type(evaluations) is not tuple:
        raise _error("source_snapshot.evaluations must be a tuple.")
    if type(plans) is not tuple:
        raise _error("Phase26 plans must be a tuple.")
    if type(mappings) is not tuple:
        raise _error("Phase25 mappings must be a tuple.")

    for label, value in (
        ("Phase27 candidate_count", source_snapshot.candidate_count),
        ("Phase27 ready_for_confirmation_count", source_snapshot.ready_for_confirmation_count),
        ("Phase27 blocked_count", source_snapshot.blocked_count),
        (
            "Phase27 reconciliation_required_count",
            source_snapshot.reconciliation_required_count,
        ),
        (
            "Phase27 automatic_retry_permitted_count",
            source_snapshot.automatic_retry_permitted_count,
        ),
        ("Phase26 candidate_count", dispatch_snapshot.candidate_count),
        ("Phase26 dry_run_supported_count", dispatch_snapshot.dry_run_supported_count),
        ("Phase26 dry_run_blocked_count", dispatch_snapshot.dry_run_blocked_count),
        ("Phase26 send_authorized_count", dispatch_snapshot.send_authorized_count),
        ("Phase25 mapping_count", mapping_snapshot.mapping_count),
    ):
        if type(value) is not int:
            raise _error(f"{label} must be an int.")

    count = len(evaluations)
    if source_snapshot.candidate_count != count:
        raise _error("Phase27 candidate_count does not match evaluations.")
    if dispatch_snapshot.candidate_count != len(plans) or len(plans) != count:
        raise _error("Phase26 plans count does not match Phase27 evaluations.")
    if (
        dispatch_snapshot.dry_run_supported_count
        + dispatch_snapshot.dry_run_blocked_count
        != len(plans)
    ):
        raise _error("Phase26 dry-run counts do not match plans.")
    if dispatch_snapshot.send_authorized_count != 0:
        raise _error("Phase26 send_authorized_count must remain zero.")
    if mapping_snapshot.mapping_count != len(mappings) or len(mappings) != count:
        raise _error("Phase25 mappings count does not match Phase27 evaluations.")
    if source_snapshot.automatic_retry_permitted_count != 0:
        raise _error("Phase27 automatic_retry_permitted_count must remain zero.")

    ready_count = 0
    blocked_count = 0
    reconciliation_count = 0
    ranks: list[int] = []
    seen_ranks: set[int] = set()

    for index, evaluation in enumerate(evaluations):
        if type(evaluation) is not _WatchlistCandidateKiwoomOrderSubmissionSafety:
            raise _error("Every Phase27 evaluation has an invalid type.")
        if evaluation.source_plan is not plans[index]:
            raise _error("Phase27 evaluation/source plan identity or order changed.")
        source_plan = evaluation.source_plan
        if type(source_plan) is not _WatchlistCandidateKiwoomOrderDispatchPlan:
            raise _error("Phase27 source_plan has an invalid type.")
        if source_plan.source_mapping is not mappings[index]:
            raise _error("Phase26 source mapping identity or order changed.")
        if type(source_plan.source_mapping) is not _WatchlistCandidateKiwoomOrderMapping:
            raise _error("Phase25 source mapping has an invalid type.")
        if type(source_plan.dispatch_plan) is not _KiwoomBuyOrderDispatchPlan:
            raise _error("Phase26 dispatch plan has an invalid type.")
        if source_plan.dispatch_plan.request is not source_plan.source_mapping.request:
            raise _error("Phase25 request identity is not preserved by Phase26.")

        rank = source_plan.source_mapping.source_rank
        if type(rank) is not int:
            raise _error("Phase25 source_rank must be an int.")
        if rank in seen_ranks:
            raise _error("Duplicate source_rank exists in Phase27 upstream.")
        seen_ranks.add(rank)
        ranks.append(rank)

        if type(evaluation.context) is not _KiwoomOrderSubmissionSafetyContext:
            raise _error("Phase27 evaluation context has an invalid type.")
        if evaluation.context.source_rank != rank:
            raise _error("Phase27 evaluation context/source_rank pairing is inconsistent.")
        if type(evaluation.decision) is not _KiwoomOrderSubmissionSafetyDecision:
            raise _error("Phase27 evaluation decision has an invalid type.")
        if evaluation.automatic_retry_permitted is not False:
            raise _error("Phase27 automatic_retry_permitted must remain False.")

        if evaluation.decision is _KiwoomOrderSubmissionSafetyDecision.READY_FOR_CONFIRMATION:
            ready_count += 1
            if evaluation.block_reason is not None:
                raise _error("READY_FOR_CONFIRMATION must not have a block reason.")
        elif evaluation.decision is _KiwoomOrderSubmissionSafetyDecision.SUBMISSION_BLOCKED:
            blocked_count += 1
            if type(evaluation.block_reason) is not _KiwoomOrderSubmissionSafetyBlockReason:
                raise _error("SUBMISSION_BLOCKED requires an exact Phase27 block reason.")
            if (
                evaluation.block_reason
                is _KiwoomOrderSubmissionSafetyBlockReason.RECONCILIATION_REQUIRED
            ):
                reconciliation_count += 1
        else:
            raise _error("Unsupported Phase27 evaluation decision.")

    if source_snapshot.ready_for_confirmation_count != ready_count:
        raise _error("Phase27 ready_for_confirmation_count is inconsistent.")
    if source_snapshot.blocked_count != blocked_count:
        raise _error("Phase27 blocked_count is inconsistent.")
    if source_snapshot.reconciliation_required_count != reconciliation_count:
        raise _error("Phase27 reconciliation_required_count is inconsistent.")

    return evaluations, tuple(ranks)


def build_watchlist_kiwoom_order_attempt_preparation_snapshot(
    source_snapshot: WatchlistKiwoomOrderSubmissionSafetySnapshot,
    contexts: tuple[KiwoomOrderAttemptPreparationContext, ...],
) -> WatchlistKiwoomOrderAttemptPreparationSnapshot:
    evaluations, upstream_ranks = _validate_source_snapshot(source_snapshot)
    if type(contexts) is not tuple:
        raise _error("contexts must be a tuple.")
    if len(contexts) != len(evaluations):
        raise _error("contexts count must exactly match Phase27 evaluations.")

    validated_contexts: list[KiwoomOrderAttemptPreparationContext] = []
    seen_context_ranks: set[int] = set()
    confirmation_references: set[str] = set()
    submission_references: set[str] = set()

    for index, raw_context in enumerate(contexts):
        context = _validate_context(raw_context)
        expected_rank = upstream_ranks[index]
        if context.source_rank in seen_context_ranks:
            raise _error("Duplicate context source_rank is prohibited.")
        seen_context_ranks.add(context.source_rank)
        if context.source_rank != expected_rank:
            raise _error("Context order/source_rank pairing does not match Phase27 evaluations.")

        if context.confirmation_reference is not None:
            if context.confirmation_reference in confirmation_references:
                raise _error("Duplicate confirmation_reference is prohibited.")
            confirmation_references.add(context.confirmation_reference)
        if context.submission_attempt_reference is not None:
            if context.submission_attempt_reference in submission_references:
                raise _error("Duplicate submission_attempt_reference is prohibited.")
            submission_references.add(context.submission_attempt_reference)

        evaluation = evaluations[index]
        if (
            evaluation.decision
            is _KiwoomOrderSubmissionSafetyDecision.SUBMISSION_BLOCKED
            and context.confirmation_state
            is not KiwoomOrderPreparationConfirmationState.NOT_CONFIRMED
        ):
            raise _error("SUBMISSION_BLOCKED candidates cannot be confirmation-injected.")

        if (
            context.confirmation_state
            is KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION
        ):
            prior_reference = evaluation.context.prior_attempt_reference
            if (
                prior_reference is not None
                and context.submission_attempt_reference == prior_reference
            ):
                raise _error(
                    "submission_attempt_reference must differ from prior_attempt_reference."
                )

        validated_contexts.append(context)

    preparations: list[WatchlistCandidateKiwoomOrderAttemptPreparation] = []
    for evaluation, context in zip(evaluations, validated_contexts, strict=True):
        if evaluation.decision is _KiwoomOrderSubmissionSafetyDecision.READY_FOR_CONFIRMATION:
            if (
                context.confirmation_state
                is KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION
            ):
                decision = KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED
                block_reason = None
                single_attempt_prepared = True
            else:
                decision = KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED
                block_reason = KiwoomOrderAttemptPreparationBlockReason.CONFIRMATION_REQUIRED
                single_attempt_prepared = False
        else:
            decision = KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED
            block_reason = KiwoomOrderAttemptPreparationBlockReason.UPSTREAM_SUBMISSION_BLOCKED
            single_attempt_prepared = False

        preparations.append(
            WatchlistCandidateKiwoomOrderAttemptPreparation(
                source_evaluation=evaluation,
                context=context,
                decision=decision,
                block_reason=block_reason,
                single_attempt_prepared=single_attempt_prepared,
                automatic_retry_permitted=False,
            )
        )

    preparation_tuple = tuple(preparations)
    prepared_count = sum(
        item.decision is KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED
        for item in preparation_tuple
    )
    blocked_count = len(preparation_tuple) - prepared_count
    confirmation_required_count = sum(
        item.block_reason is KiwoomOrderAttemptPreparationBlockReason.CONFIRMATION_REQUIRED
        for item in preparation_tuple
    )

    return WatchlistKiwoomOrderAttemptPreparationSnapshot(
        source_snapshot=source_snapshot,
        preparations=preparation_tuple,
        candidate_count=len(preparation_tuple),
        prepared_count=prepared_count,
        blocked_count=blocked_count,
        confirmation_required_count=confirmation_required_count,
        automatic_retry_permitted_count=0,
    )
