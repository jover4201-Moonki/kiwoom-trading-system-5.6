from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields, is_dataclass
from enum import Enum as _Enum
from typing import Any

from .watchlist_order_attempt_preparation import (
    KiwoomOrderAttemptPreparationBlockReason,
    KiwoomOrderAttemptPreparationContext,
    KiwoomOrderAttemptPreparationDecision,
    WatchlistCandidateKiwoomOrderAttemptPreparation,
    WatchlistKiwoomOrderAttemptPreparationSnapshot,
)


__all__ = [
    "KiwoomOrderSendAuthorizationError",
    "KiwoomOrderSendAuthorizationState",
    "KiwoomOrderSendAuthorizationDecision",
    "KiwoomOrderSendAuthorizationBlockReason",
    "KiwoomOrderSendAuthorizationContext",
    "WatchlistCandidateKiwoomOrderSendAuthorization",
    "WatchlistKiwoomOrderSendAuthorizationSnapshot",
    "build_watchlist_kiwoom_order_send_authorization_snapshot",
]


class KiwoomOrderSendAuthorizationError(RuntimeError):
    pass


class KiwoomOrderSendAuthorizationState(str, _Enum):
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    AUTHORIZED_FOR_SEND = "AUTHORIZED_FOR_SEND"


class KiwoomOrderSendAuthorizationDecision(str, _Enum):
    SEND_AUTHORIZED = "SEND_AUTHORIZED"
    SEND_BLOCKED = "SEND_BLOCKED"


class KiwoomOrderSendAuthorizationBlockReason(str, _Enum):
    UPSTREAM_ATTEMPT_BLOCKED = "UPSTREAM_ATTEMPT_BLOCKED"
    SEND_AUTHORIZATION_REQUIRED = "SEND_AUTHORIZATION_REQUIRED"
    AUTHORIZATION_STALE = "AUTHORIZATION_STALE"


@dataclass(frozen=True, slots=True)
class KiwoomOrderSendAuthorizationContext:
    source_rank: int
    submission_attempt_reference: str | None
    authorization_state: KiwoomOrderSendAuthorizationState
    send_authorization_reference: str | None
    authorization_authority_reference: str
    authorization_evidence_snapshot_id: str
    is_fresh: bool


@dataclass(frozen=True, slots=True)
class WatchlistCandidateKiwoomOrderSendAuthorization:
    source_preparation: WatchlistCandidateKiwoomOrderAttemptPreparation
    context: KiwoomOrderSendAuthorizationContext
    decision: KiwoomOrderSendAuthorizationDecision
    block_reason: KiwoomOrderSendAuthorizationBlockReason | None
    send_authorized: bool
    automatic_retry_permitted: bool


@dataclass(frozen=True, slots=True)
class WatchlistKiwoomOrderSendAuthorizationSnapshot:
    source_snapshot: WatchlistKiwoomOrderAttemptPreparationSnapshot
    authorizations: tuple[WatchlistCandidateKiwoomOrderSendAuthorization, ...]
    candidate_count: int
    send_authorized_count: int
    send_blocked_count: int
    authorization_required_count: int
    authorization_stale_count: int
    upstream_blocked_count: int
    automatic_retry_permitted_count: int


_MISSING = object()

_PHASE28_CONTEXT_FIELDS = (
    "source_rank",
    "confirmation_state",
    "confirmation_reference",
    "submission_attempt_reference",
)
_PHASE28_PREPARATION_FIELDS = (
    "source_evaluation",
    "context",
    "decision",
    "block_reason",
    "single_attempt_prepared",
    "automatic_retry_permitted",
)
_PHASE28_SNAPSHOT_FIELDS = (
    "source_snapshot",
    "preparations",
    "candidate_count",
    "prepared_count",
    "blocked_count",
    "confirmation_required_count",
    "automatic_retry_permitted_count",
)


def _error(message: str) -> KiwoomOrderSendAuthorizationError:
    return KiwoomOrderSendAuthorizationError(message)


def _exact_nonempty_str(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _walk_named_values(
    root: object,
    name: str,
    *,
    max_depth: int = 5,
) -> list[object]:
    values: list[object] = []
    seen: set[int] = set()

    def visit(value: object, depth: int) -> None:
        if depth > max_depth or value is None:
            return
        if isinstance(value, (str, bytes, int, float, bool, _Enum)):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)

        if hasattr(value, name):
            values.append(getattr(value, name))

        if is_dataclass(value):
            for field in dataclass_fields(value):
                child = getattr(value, field.name)
                if isinstance(child, tuple):
                    for member in child:
                        visit(member, depth + 1)
                else:
                    visit(child, depth + 1)

    visit(root, 0)
    return values


def _coherent_named_value(
    root: object,
    name: str,
    *,
    required: bool,
) -> object:
    values = _walk_named_values(root, name)
    if not values:
        if required:
            raise _error(f"Phase 28 {name} invariant is missing.")
        return _MISSING

    first = values[0]
    for other in values[1:]:
        if type(other) is not type(first) or other != first:
            raise _error(f"Phase 28 {name} identity invariant failed.")
    return first


def _validate_phase28_preparation(
    preparation: WatchlistCandidateKiwoomOrderAttemptPreparation,
) -> tuple[int, str | None]:
    if type(preparation) is not WatchlistCandidateKiwoomOrderAttemptPreparation:
        raise _error(
            "Every Phase 28 preparation must be exact "
            "WatchlistCandidateKiwoomOrderAttemptPreparation."
        )

    if tuple(field.name for field in dataclass_fields(preparation)) != _PHASE28_PREPARATION_FIELDS:
        raise _error("Phase 28 preparation field contract invariant failed.")

    if type(preparation.context) is not KiwoomOrderAttemptPreparationContext:
        raise _error("Phase 28 preparation context type invariant failed.")
    if tuple(field.name for field in dataclass_fields(preparation.context)) != _PHASE28_CONTEXT_FIELDS:
        raise _error("Phase 28 context field contract invariant failed.")

    if type(preparation.decision) is not KiwoomOrderAttemptPreparationDecision:
        raise _error("Phase 28 preparation decision type invariant failed.")

    if preparation.decision is KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED:
        if preparation.block_reason is not None:
            raise _error("Phase 28 prepared decision/block invariant failed.")
    elif preparation.decision is KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED:
        if type(preparation.block_reason) is not KiwoomOrderAttemptPreparationBlockReason:
            raise _error("Phase 28 blocked decision/block invariant failed.")
        if preparation.block_reason not in (
            KiwoomOrderAttemptPreparationBlockReason.CONFIRMATION_REQUIRED,
            KiwoomOrderAttemptPreparationBlockReason.UPSTREAM_SUBMISSION_BLOCKED,
        ):
            raise _error("Phase 28 blocked reason invariant failed.")
    else:
        raise _error("Phase 28 decision invariant failed.")

    if type(preparation.automatic_retry_permitted) is not bool:
        raise _error("Phase 28 automatic_retry_permitted must be exact bool.")
    if preparation.automatic_retry_permitted is not False:
        raise _error("Phase 28 automatic_retry_permitted must be False.")

    source_rank = _coherent_named_value(preparation, "source_rank", required=True)
    if type(source_rank) is not int or type(source_rank) is bool:
        raise _error("Phase 28 source_rank must be exact int.")
    if source_rank < 1:
        raise _error("Phase 28 source_rank must be positive.")

    submission_reference = _coherent_named_value(
        preparation,
        "submission_attempt_reference",
        required=True,
    )
    if preparation.decision is KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED:
        if not _exact_nonempty_str(submission_reference):
            raise _error(
                "Phase 28 prepared submission_attempt_reference invariant failed."
            )
    else:
        if submission_reference is not None:
            raise _error(
                "Phase 28 blocked submission_attempt_reference invariant failed."
            )

    return source_rank, submission_reference


def _expected_phase28_counts(
    preparations: tuple[WatchlistCandidateKiwoomOrderAttemptPreparation, ...],
) -> dict[str, int]:
    prepared_count = sum(
        item.decision is KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED
        for item in preparations
    )
    blocked_count = len(preparations) - prepared_count
    confirmation_required_count = sum(
        item.block_reason
        is KiwoomOrderAttemptPreparationBlockReason.CONFIRMATION_REQUIRED
        for item in preparations
    )
    upstream_blocked_count = sum(
        item.block_reason
        is KiwoomOrderAttemptPreparationBlockReason.UPSTREAM_SUBMISSION_BLOCKED
        for item in preparations
    )
    retry_count = sum(item.automatic_retry_permitted is True for item in preparations)

    return {
        "candidate_count": len(preparations),
        "attempt_prepared_count": prepared_count,
        "prepared_count": prepared_count,
        "attempt_blocked_count": blocked_count,
        "blocked_count": blocked_count,
        "confirmation_required_count": confirmation_required_count,
        "upstream_submission_blocked_count": upstream_blocked_count,
        "upstream_blocked_count": upstream_blocked_count,
        "automatic_retry_permitted_count": retry_count,
    }


def _validate_phase28_snapshot(
    source_snapshot: WatchlistKiwoomOrderAttemptPreparationSnapshot,
) -> tuple[
    tuple[WatchlistCandidateKiwoomOrderAttemptPreparation, ...],
    tuple[tuple[int, str | None], ...],
]:
    if type(source_snapshot) is not WatchlistKiwoomOrderAttemptPreparationSnapshot:
        raise _error(
            "source_snapshot must be exact "
            "WatchlistKiwoomOrderAttemptPreparationSnapshot."
        )

    if tuple(field.name for field in dataclass_fields(source_snapshot)) != _PHASE28_SNAPSHOT_FIELDS:
        raise _error("Phase 28 snapshot field contract invariant failed.")

    if type(source_snapshot.preparations) is not tuple:
        raise _error("Phase 28 preparations must be exact tuple.")

    preparations = source_snapshot.preparations
    identities: list[tuple[int, str | None]] = []
    for preparation in preparations:
        identities.append(_validate_phase28_preparation(preparation))

    if type(source_snapshot.candidate_count) is not int:
        raise _error("Phase 28 candidate_count must be exact int.")
    if source_snapshot.candidate_count != len(preparations):
        raise _error("Phase 28 candidate_count length invariant failed.")

    expected = _expected_phase28_counts(preparations)
    known_count_fields = 0
    for field in dataclass_fields(source_snapshot):
        if not field.name.endswith("_count"):
            continue
        if field.name not in expected:
            raise _error(
                f"Unsupported Phase 28 aggregate count field: {field.name}."
            )
        actual = getattr(source_snapshot, field.name)
        if type(actual) is not int or type(actual) is bool:
            raise _error(f"Phase 28 {field.name} must be exact int.")
        if actual != expected[field.name]:
            raise _error(f"Phase 28 {field.name} aggregate invariant failed.")
        known_count_fields += 1

    if known_count_fields == 0:
        raise _error("Phase 28 aggregate count invariants are missing.")

    if not hasattr(source_snapshot, "automatic_retry_permitted_count"):
        raise _error("Phase 28 retry aggregate invariant is missing.")
    if source_snapshot.automatic_retry_permitted_count != 0:
        raise _error("Phase 28 automatic_retry_permitted_count must be 0.")

    # Source/context/reference positional identity is validated without rebuilding
    # or recalculating any Phase 28 decision. For each position, every reachable
    # Phase 28 source_rank and submission_attempt_reference must already agree.
    # The loop above performs that fail-closed identity check directly on the
    # supplied immutable Phase 28 object graph and preserves its order.
    return preparations, tuple(identities)


def _validate_authorization_state_reference(
    context: KiwoomOrderSendAuthorizationContext,
) -> None:
    if type(context.authorization_state) is not KiwoomOrderSendAuthorizationState:
        raise _error("authorization_state must be exact enum.")

    if context.authorization_state is KiwoomOrderSendAuthorizationState.AUTHORIZED_FOR_SEND:
        if not _exact_nonempty_str(context.send_authorization_reference):
            raise _error(
                "AUTHORIZED_FOR_SEND requires a non-empty exact string "
                "send_authorization_reference."
            )
    elif context.authorization_state is KiwoomOrderSendAuthorizationState.NOT_AUTHORIZED:
        if context.send_authorization_reference is not None:
            raise _error(
                "NOT_AUTHORIZED requires send_authorization_reference=None."
            )
    else:
        raise _error("Unsupported authorization_state.")


def _validate_authority_reference(
    context: KiwoomOrderSendAuthorizationContext,
) -> None:
    if not _exact_nonempty_str(context.authorization_authority_reference):
        raise _error(
            "authorization_authority_reference must be a non-empty exact string."
        )


def _validate_evidence_snapshot_id(
    context: KiwoomOrderSendAuthorizationContext,
) -> None:
    if not _exact_nonempty_str(context.authorization_evidence_snapshot_id):
        raise _error(
            "authorization_evidence_snapshot_id must be a non-empty exact string."
        )


def build_watchlist_kiwoom_order_send_authorization_snapshot(
    source_snapshot: WatchlistKiwoomOrderAttemptPreparationSnapshot,
    contexts: tuple[KiwoomOrderSendAuthorizationContext, ...],
) -> WatchlistKiwoomOrderSendAuthorizationSnapshot:
    # 1. Phase 28 upstream exact type/structure/aggregate/reference/decision.
    preparations, upstream_identities = _validate_phase28_snapshot(source_snapshot)

    # 2. Phase 29 context exact type/count/positional order.
    if type(contexts) is not tuple:
        raise _error("contexts must be exact tuple.")
    if len(contexts) != len(preparations):
        raise _error("contexts count must equal Phase 28 preparations count.")
    for context in contexts:
        if type(context) is not KiwoomOrderSendAuthorizationContext:
            raise _error(
                "Every context must be exact KiwoomOrderSendAuthorizationContext."
            )

    # 3. source_rank exact pairwise identity.
    for context, (source_rank, _) in zip(contexts, upstream_identities, strict=True):
        if type(context.source_rank) is not type(source_rank):
            raise _error("source_rank exact type identity mismatch.")
        if context.source_rank != source_rank:
            raise _error("source_rank pairwise identity mismatch.")

    # 4. submission_attempt_reference exact binding.
    for context, (_, submission_reference) in zip(
        contexts,
        upstream_identities,
        strict=True,
    ):
        if type(context.submission_attempt_reference) is not type(
            submission_reference
        ):
            raise _error("submission_attempt_reference exact type mismatch.")
        if context.submission_attempt_reference != submission_reference:
            raise _error("submission_attempt_reference exact binding mismatch.")

    # 5. authorization state/reference structural invariant.
    for context in contexts:
        _validate_authorization_state_reference(context)

    # 6. authorization_authority_reference validity.
    for context in contexts:
        _validate_authority_reference(context)

    # 7. authorization_evidence_snapshot_id validity.
    for context in contexts:
        _validate_evidence_snapshot_id(context)

    # 8. non-empty batch authority/snapshot/freshness coherence.
    if contexts:
        authority = contexts[0].authorization_authority_reference
        snapshot_id = contexts[0].authorization_evidence_snapshot_id
        freshness = contexts[0].is_fresh
        for context in contexts[1:]:
            if context.authorization_authority_reference != authority:
                raise _error("Mixed authorization authority batch is invalid.")
            if context.authorization_evidence_snapshot_id != snapshot_id:
                raise _error("Mixed authorization evidence snapshot batch is invalid.")
            if context.is_fresh != freshness:
                raise _error("Mixed freshness batch is invalid.")

    # 9. is_fresh exact bool.
    for context in contexts:
        if type(context.is_fresh) is not bool:
            raise _error("is_fresh must be exact bool.")

    # 10. duplicate non-None send_authorization_reference.
    seen_send_references: set[str] = set()
    for context in contexts:
        reference = context.send_authorization_reference
        if reference is None:
            continue
        if reference in seen_send_references:
            raise _error("Duplicate non-None send_authorization_reference.")
        seen_send_references.add(reference)

    # 11. decision evaluation.
    authorizations: list[WatchlistCandidateKiwoomOrderSendAuthorization] = []
    for preparation, context in zip(preparations, contexts, strict=True):
        if preparation.decision is KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED:
            decision = KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED
            block_reason = (
                KiwoomOrderSendAuthorizationBlockReason.UPSTREAM_ATTEMPT_BLOCKED
            )
        elif context.is_fresh is False:
            decision = KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED
            block_reason = KiwoomOrderSendAuthorizationBlockReason.AUTHORIZATION_STALE
        elif (
            context.authorization_state
            is KiwoomOrderSendAuthorizationState.NOT_AUTHORIZED
        ):
            decision = KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED
            block_reason = (
                KiwoomOrderSendAuthorizationBlockReason.SEND_AUTHORIZATION_REQUIRED
            )
        else:
            decision = KiwoomOrderSendAuthorizationDecision.SEND_AUTHORIZED
            block_reason = None

        authorizations.append(
            WatchlistCandidateKiwoomOrderSendAuthorization(
                source_preparation=preparation,
                context=context,
                decision=decision,
                block_reason=block_reason,
                send_authorized=(
                    decision is KiwoomOrderSendAuthorizationDecision.SEND_AUTHORIZED
                ),
                automatic_retry_permitted=False,
            )
        )

    authorizations_tuple = tuple(authorizations)
    send_authorized_count = sum(
        item.decision is KiwoomOrderSendAuthorizationDecision.SEND_AUTHORIZED
        for item in authorizations_tuple
    )
    send_blocked_count = len(authorizations_tuple) - send_authorized_count
    authorization_required_count = sum(
        item.block_reason
        is KiwoomOrderSendAuthorizationBlockReason.SEND_AUTHORIZATION_REQUIRED
        for item in authorizations_tuple
    )
    authorization_stale_count = sum(
        item.block_reason is KiwoomOrderSendAuthorizationBlockReason.AUTHORIZATION_STALE
        for item in authorizations_tuple
    )
    upstream_blocked_count = sum(
        item.block_reason
        is KiwoomOrderSendAuthorizationBlockReason.UPSTREAM_ATTEMPT_BLOCKED
        for item in authorizations_tuple
    )

    if send_blocked_count != (
        authorization_required_count
        + authorization_stale_count
        + upstream_blocked_count
    ):
        raise _error("Phase 29 blocked aggregate invariant failed.")

    return WatchlistKiwoomOrderSendAuthorizationSnapshot(
        source_snapshot=source_snapshot,
        authorizations=authorizations_tuple,
        candidate_count=len(authorizations_tuple),
        send_authorized_count=send_authorized_count,
        send_blocked_count=send_blocked_count,
        authorization_required_count=authorization_required_count,
        authorization_stale_count=authorization_stale_count,
        upstream_blocked_count=upstream_blocked_count,
        automatic_retry_permitted_count=0,
    )
