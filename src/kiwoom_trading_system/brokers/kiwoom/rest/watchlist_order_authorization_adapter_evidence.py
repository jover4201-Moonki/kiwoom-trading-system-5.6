from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import inspect
import json
import re
import types
from typing import Protocol

from .watchlist_order_authorization_consumption_claim import (
    KiwoomOrderAuthorizationConsumptionClaimContext,
    WatchlistOrderAuthorizationConsumptionClaimSnapshot,
)
from .watchlist_order_send_request import WatchlistOrderSendRequestSnapshot

__all__ = [
    "WatchlistOrderAuthorizationAdapterEvidenceError",
    "KiwoomOrderAuthorizationAuthorityAdapter",
    "KiwoomOrderAuthorizationAuthorityReportedResult",
    "WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot",
    "check_and_consume_demo_watchlist_order_authorization_adapter_evidence",
]


class WatchlistOrderAuthorizationAdapterEvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class KiwoomOrderAuthorizationAuthorityReportedResult:
    authorization_claim_identity: tuple[str, str, str, str]
    authorization_replay_guard: tuple[str, str]
    claim_fingerprint: str
    asserted_authority_approval_reference: str
    asserted_authority_conformance_reference: str
    authority_result_reference: str | None
    decision: str
    block_reason: str | None
    indeterminate_reason: str | None
    consumption_reference: str | None
    authority_reported_authorization_consumption_committed: bool | None
    authority_reported_replay_guard_consumption_committed: bool | None
    commit_state_known: bool


class KiwoomOrderAuthorizationAuthorityAdapter(Protocol):
    def check_and_consume(
        self,
        *,
        authorization_claim_identity: tuple[str, str, str, str],
        authorization_replay_guard: tuple[str, str],
        claim_fingerprint: str,
        asserted_authority_approval_reference: str,
        asserted_authority_conformance_reference: str,
    ) -> KiwoomOrderAuthorizationAuthorityReportedResult:
        ...


@dataclass(frozen=True)
class WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot:
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot
    asserted_authority_approval_reference: str
    asserted_authority_conformance_reference: str
    authority_result: KiwoomOrderAuthorizationAuthorityReportedResult | None
    decision: str
    block_reason: str | None
    indeterminate_reason: str | None
    authority_result_reference: str | None
    consumption_reference: str | None
    evidence_fingerprint: str
    authority_reported_authorization_consumption_committed: bool | None
    authority_reported_replay_guard_consumption_committed: bool | None
    commit_state_known: bool
    consumption_evidence_candidate_ready: bool
    authority_trust_independently_verified: bool
    automatic_retry_permitted: bool
    reconciliation_required: bool
    authority_invocation_attempted: bool
    phase32_direct_credential_accessed: bool
    phase32_direct_network_performed: bool
    phase32_direct_account_accessed: bool
    phase32_direct_order_submitted: bool


_MISSING = object()
_PROVIDER_BODY_KEYS = frozenset(
    {"dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"}
)
_LOWER_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_DECISION_CONSUMED = "AUTHORITY_REPORTED_CONSUMED"
_DECISION_BLOCKED = "AUTHORITY_REPORTED_BLOCKED"
_DECISION_INDETERMINATE = "INDETERMINATE"
_BLOCK_REASONS = frozenset(
    {
        "CLAIM_ALREADY_CONSUMED",
        "REPLAY_GUARD_ALREADY_CONSUMED",
        "AUTHORITY_NAMESPACE_MISMATCH",
        "EVIDENCE_SNAPSHOT_MISMATCH",
        "SUBMISSION_ATTEMPT_MISMATCH",
        "SEND_AUTHORIZATION_MISMATCH",
        "GRANT_ATTEMPT_BINDING_INVALID",
        "AUTHORIZATION_REVOKED",
        "AUTHORIZATION_STALE",
        "AUTHORIZATION_INVALID",
    }
)
_INDETERMINATE_AUTHORITY_REPORTED = "AUTHORITY_REPORTED_INDETERMINATE"
_INDETERMINATE_TIMEOUT = "AUTHORITY_TIMEOUT"
_INDETERMINATE_EXCEPTION = "AUTHORITY_EXCEPTION"
_INDETERMINATE_CONTRACT = "AUTHORITY_RESULT_CONTRACT_VIOLATION"


def _raise(reason: str) -> None:
    raise WatchlistOrderAuthorizationAdapterEvidenceError(reason)


def _is_exact_opaque_reference(value: object) -> bool:
    if type(value) is not str:
        return False
    if not 1 <= len(value) <= 128:
        return False
    if not value or value != value.strip():
        return False
    return not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _is_binding_reference(value: object) -> bool:
    if type(value) is not str:
        return False
    if not 1 <= len(value) <= 128:
        return False
    if not value.strip():
        return False
    return not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _is_exact_bool(value: object, expected: bool | None = None) -> bool:
    if type(value) is not bool:
        return False
    return expected is None or value is expected


def _exact_tuple_of_exact_str(value: object, length: int) -> bool:
    return (
        type(value) is tuple
        and len(value) == length
        and all(type(item) is str for item in value)
    )


def _phase31_structure_and_safety_valid(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    if type(source_snapshot.context) is not KiwoomOrderAuthorizationConsumptionClaimContext:
        return False
    if not _exact_tuple_of_exact_str(source_snapshot.authorization_claim_identity, 4):
        return False
    if not _exact_tuple_of_exact_str(source_snapshot.authorization_replay_guard, 2):
        return False
    if type(source_snapshot.claim_fingerprint) is not str:
        return False
    if _LOWER_HEX_64.fullmatch(source_snapshot.claim_fingerprint) is None:
        return False
    expected_flags = (
        (source_snapshot.claim_prepared, True),
        (source_snapshot.authorization_consumption_committed, False),
        (source_snapshot.post_permitted, False),
        (source_snapshot.automatic_retry_permitted, False),
        (source_snapshot.network_performed, False),
        (source_snapshot.order_submitted, False),
    )
    if not all(_is_exact_bool(value, expected) for value, expected in expected_flags):
        return False

    context = source_snapshot.context
    expected_claim_identity = (
        context.authorization_authority_reference,
        context.authorization_evidence_snapshot_id,
        context.submission_attempt_reference,
        context.send_authorization_reference,
    )
    expected_replay_guard = (
        context.authorization_authority_reference,
        context.send_authorization_reference,
    )
    return (
        source_snapshot.authorization_claim_identity == expected_claim_identity
        and source_snapshot.authorization_replay_guard == expected_replay_guard
    )


def _phase30_request_and_materialization_binding_valid(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    phase30 = source_snapshot.source_snapshot
    if type(phase30) is not WatchlistOrderSendRequestSnapshot:
        return False
    if phase30.environment != "demo":
        return False
    if phase30.side != "BUY":
        return False
    if phase30.exchange != "KRX":
        return False
    if phase30.api_id != "kt10000":
        return False
    if phase30.http_method != "POST":
        return False
    if phase30.api_path != "/api/dostk/ordr":
        return False

    body = phase30.body
    if not isinstance(body, Mapping):
        return False
    try:
        keys = set(body.keys())
        values = tuple(body.values())
    except (AttributeError, TypeError):
        return False
    if keys != _PROVIDER_BODY_KEYS:
        return False
    if any(type(key) is not str for key in body.keys()):
        return False
    if any(type(value) is not str for value in values):
        return False
    if body["dmst_stex_tp"] != "KRX" or body["cond_uv"] != "":
        return False
    if body["trde_tp"] == "0":
        if body["ord_uv"] == "":
            return False
    elif body["trde_tp"] == "3":
        if body["ord_uv"] != "":
            return False
    else:
        return False

    if not _is_binding_reference(phase30.source_attempt_ref):
        return False
    if not _is_binding_reference(phase30.authorization_evidence_ref):
        return False
    if type(phase30.materialization_fingerprint) is not str:
        return False
    if _LOWER_HEX_64.fullmatch(phase30.materialization_fingerprint) is None:
        return False

    safety = (
        phase30.transport_allowed,
        phase30.credential_accessed,
        phase30.network_performed,
        phase30.account_accessed,
        phase30.order_submitted,
    )
    if not all(_is_exact_bool(value, False) for value in safety):
        return False

    context = source_snapshot.context
    if context.submission_attempt_reference != phase30.source_attempt_ref:
        return False
    if context.authorization_evidence_snapshot_id != phase30.authorization_evidence_ref:
        return False

    envelope = {
        "environment": phase30.environment,
        "side": phase30.side,
        "exchange": phase30.exchange,
        "api_id": phase30.api_id,
        "http_method": phase30.http_method,
        "api_path": phase30.api_path,
        "body": dict(phase30.body),
        "source_attempt_ref": phase30.source_attempt_ref,
        "authorization_evidence_ref": phase30.authorization_evidence_ref,
    }
    canonical = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return phase30.materialization_fingerprint == hashlib.sha256(canonical).hexdigest()


def _phase31_claim_fingerprint_valid(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    envelope = {
        "materialization_fingerprint": source_snapshot.source_snapshot.materialization_fingerprint,
        "authorization_claim_identity": source_snapshot.authorization_claim_identity,
        "authorization_replay_guard": source_snapshot.authorization_replay_guard,
    }
    canonical = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return source_snapshot.claim_fingerprint == hashlib.sha256(canonical).hexdigest()


def _validated_authority_surface(authority: object) -> types.FunctionType:
    class_surface = inspect.getattr_static(type(authority), "check_and_consume", _MISSING)
    instance_surface = inspect.getattr_static(authority, "check_and_consume", _MISSING)
    if class_surface is _MISSING or instance_surface is _MISSING:
        _raise("AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID")
    if instance_surface is not class_surface:
        _raise("AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID")
    if type(class_surface) is not types.FunctionType:
        _raise("AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID")
    if inspect.iscoroutinefunction(class_surface):
        _raise("AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID")
    if inspect.isgeneratorfunction(class_surface):
        _raise("AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID")
    if inspect.isasyncgenfunction(class_surface):
        _raise("AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID")
    return class_surface


def _evidence_fingerprint(
    *,
    claim_fingerprint: str,
    asserted_authority_approval_reference: str,
    asserted_authority_conformance_reference: str,
    decision: str,
    block_reason: str | None,
    indeterminate_reason: str | None,
    authority_result_reference: str | None,
    consumption_reference: str | None,
    authority_reported_authorization_consumption_committed: bool | None,
    authority_reported_replay_guard_consumption_committed: bool | None,
    commit_state_known: bool,
    consumption_evidence_candidate_ready: bool,
    authority_trust_independently_verified: bool,
    automatic_retry_permitted: bool,
    reconciliation_required: bool,
    authority_invocation_attempted: bool,
    phase32_direct_credential_accessed: bool,
    phase32_direct_network_performed: bool,
    phase32_direct_account_accessed: bool,
    phase32_direct_order_submitted: bool,
) -> str:
    envelope = {
        "claim_fingerprint": claim_fingerprint,
        "asserted_authority_approval_reference": asserted_authority_approval_reference,
        "asserted_authority_conformance_reference": asserted_authority_conformance_reference,
        "decision": decision,
        "block_reason": block_reason,
        "indeterminate_reason": indeterminate_reason,
        "authority_result_reference": authority_result_reference,
        "consumption_reference": consumption_reference,
        "authority_reported_authorization_consumption_committed": authority_reported_authorization_consumption_committed,
        "authority_reported_replay_guard_consumption_committed": authority_reported_replay_guard_consumption_committed,
        "commit_state_known": commit_state_known,
        "consumption_evidence_candidate_ready": consumption_evidence_candidate_ready,
        "authority_trust_independently_verified": authority_trust_independently_verified,
        "automatic_retry_permitted": automatic_retry_permitted,
        "reconciliation_required": reconciliation_required,
        "authority_invocation_attempted": authority_invocation_attempted,
        "phase32_direct_credential_accessed": phase32_direct_credential_accessed,
        "phase32_direct_network_performed": phase32_direct_network_performed,
        "phase32_direct_account_accessed": phase32_direct_account_accessed,
        "phase32_direct_order_submitted": phase32_direct_order_submitted,
    }
    canonical = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _snapshot(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
    asserted_authority_approval_reference: str,
    asserted_authority_conformance_reference: str,
    *,
    authority_result: KiwoomOrderAuthorizationAuthorityReportedResult | None,
    decision: str,
    block_reason: str | None,
    indeterminate_reason: str | None,
    authority_result_reference: str | None,
    consumption_reference: str | None,
    authority_reported_authorization_consumption_committed: bool | None,
    authority_reported_replay_guard_consumption_committed: bool | None,
    commit_state_known: bool,
    consumption_evidence_candidate_ready: bool,
    reconciliation_required: bool,
) -> WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot:
    values = {
        "claim_fingerprint": source_snapshot.claim_fingerprint,
        "asserted_authority_approval_reference": asserted_authority_approval_reference,
        "asserted_authority_conformance_reference": asserted_authority_conformance_reference,
        "decision": decision,
        "block_reason": block_reason,
        "indeterminate_reason": indeterminate_reason,
        "authority_result_reference": authority_result_reference,
        "consumption_reference": consumption_reference,
        "authority_reported_authorization_consumption_committed": authority_reported_authorization_consumption_committed,
        "authority_reported_replay_guard_consumption_committed": authority_reported_replay_guard_consumption_committed,
        "commit_state_known": commit_state_known,
        "consumption_evidence_candidate_ready": consumption_evidence_candidate_ready,
        "authority_trust_independently_verified": False,
        "automatic_retry_permitted": False,
        "reconciliation_required": reconciliation_required,
        "authority_invocation_attempted": True,
        "phase32_direct_credential_accessed": False,
        "phase32_direct_network_performed": False,
        "phase32_direct_account_accessed": False,
        "phase32_direct_order_submitted": False,
    }
    return WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot(
        source_snapshot=source_snapshot,
        asserted_authority_approval_reference=asserted_authority_approval_reference,
        asserted_authority_conformance_reference=asserted_authority_conformance_reference,
        authority_result=authority_result,
        decision=decision,
        block_reason=block_reason,
        indeterminate_reason=indeterminate_reason,
        authority_result_reference=authority_result_reference,
        consumption_reference=consumption_reference,
        evidence_fingerprint=_evidence_fingerprint(**values),
        authority_reported_authorization_consumption_committed=authority_reported_authorization_consumption_committed,
        authority_reported_replay_guard_consumption_committed=authority_reported_replay_guard_consumption_committed,
        commit_state_known=commit_state_known,
        consumption_evidence_candidate_ready=consumption_evidence_candidate_ready,
        authority_trust_independently_verified=False,
        automatic_retry_permitted=False,
        reconciliation_required=reconciliation_required,
        authority_invocation_attempted=True,
        phase32_direct_credential_accessed=False,
        phase32_direct_network_performed=False,
        phase32_direct_account_accessed=False,
        phase32_direct_order_submitted=False,
    )


def _indeterminate_snapshot(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
    asserted_authority_approval_reference: str,
    asserted_authority_conformance_reference: str,
    reason: str,
) -> WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot:
    return _snapshot(
        source_snapshot,
        asserted_authority_approval_reference,
        asserted_authority_conformance_reference,
        authority_result=None,
        decision=_DECISION_INDETERMINATE,
        block_reason=None,
        indeterminate_reason=reason,
        authority_result_reference=None,
        consumption_reference=None,
        authority_reported_authorization_consumption_committed=None,
        authority_reported_replay_guard_consumption_committed=None,
        commit_state_known=False,
        consumption_evidence_candidate_ready=False,
        reconciliation_required=True,
    )


def _result_matches_exact_echoes(
    result: KiwoomOrderAuthorizationAuthorityReportedResult,
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
    asserted_authority_approval_reference: str,
    asserted_authority_conformance_reference: str,
) -> bool:
    return (
        _exact_tuple_of_exact_str(result.authorization_claim_identity, 4)
        and _exact_tuple_of_exact_str(result.authorization_replay_guard, 2)
        and result.authorization_claim_identity == source_snapshot.authorization_claim_identity
        and result.authorization_replay_guard == source_snapshot.authorization_replay_guard
        and type(result.claim_fingerprint) is str
        and result.claim_fingerprint == source_snapshot.claim_fingerprint
        and type(result.asserted_authority_approval_reference) is str
        and result.asserted_authority_approval_reference == asserted_authority_approval_reference
        and type(result.asserted_authority_conformance_reference) is str
        and result.asserted_authority_conformance_reference == asserted_authority_conformance_reference
    )


def _normalize_reported_result(
    result: object,
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
    asserted_authority_approval_reference: str,
    asserted_authority_conformance_reference: str,
) -> WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot:
    if type(result) is not KiwoomOrderAuthorizationAuthorityReportedResult:
        return _indeterminate_snapshot(
            source_snapshot,
            asserted_authority_approval_reference,
            asserted_authority_conformance_reference,
            _INDETERMINATE_CONTRACT,
        )
    if not _result_matches_exact_echoes(
        result,
        source_snapshot,
        asserted_authority_approval_reference,
        asserted_authority_conformance_reference,
    ):
        return _indeterminate_snapshot(
            source_snapshot,
            asserted_authority_approval_reference,
            asserted_authority_conformance_reference,
            _INDETERMINATE_CONTRACT,
        )

    if type(result.decision) is not str:
        return _indeterminate_snapshot(source_snapshot, asserted_authority_approval_reference, asserted_authority_conformance_reference, _INDETERMINATE_CONTRACT)
    if result.authority_result_reference is not None and not _is_exact_opaque_reference(result.authority_result_reference):
        return _indeterminate_snapshot(source_snapshot, asserted_authority_approval_reference, asserted_authority_conformance_reference, _INDETERMINATE_CONTRACT)
    if result.consumption_reference is not None and not _is_exact_opaque_reference(result.consumption_reference):
        return _indeterminate_snapshot(source_snapshot, asserted_authority_approval_reference, asserted_authority_conformance_reference, _INDETERMINATE_CONTRACT)

    if result.decision == _DECISION_CONSUMED:
        valid = (
            _is_exact_opaque_reference(result.authority_result_reference)
            and _is_exact_opaque_reference(result.consumption_reference)
            and result.block_reason is None
            and result.indeterminate_reason is None
            and _is_exact_bool(result.commit_state_known, True)
            and _is_exact_bool(result.authority_reported_authorization_consumption_committed, True)
            and _is_exact_bool(result.authority_reported_replay_guard_consumption_committed, True)
        )
        if valid:
            return _snapshot(
                source_snapshot,
                asserted_authority_approval_reference,
                asserted_authority_conformance_reference,
                authority_result=result,
                decision=_DECISION_CONSUMED,
                block_reason=None,
                indeterminate_reason=None,
                authority_result_reference=result.authority_result_reference,
                consumption_reference=result.consumption_reference,
                authority_reported_authorization_consumption_committed=True,
                authority_reported_replay_guard_consumption_committed=True,
                commit_state_known=True,
                consumption_evidence_candidate_ready=True,
                reconciliation_required=False,
            )
    elif result.decision == _DECISION_BLOCKED:
        valid = (
            _is_exact_opaque_reference(result.authority_result_reference)
            and type(result.block_reason) is str
            and result.block_reason in _BLOCK_REASONS
            and result.indeterminate_reason is None
            and result.consumption_reference is None
            and _is_exact_bool(result.commit_state_known, True)
            and _is_exact_bool(result.authority_reported_authorization_consumption_committed, False)
            and _is_exact_bool(result.authority_reported_replay_guard_consumption_committed, False)
        )
        if valid:
            return _snapshot(
                source_snapshot,
                asserted_authority_approval_reference,
                asserted_authority_conformance_reference,
                authority_result=result,
                decision=_DECISION_BLOCKED,
                block_reason=result.block_reason,
                indeterminate_reason=None,
                authority_result_reference=result.authority_result_reference,
                consumption_reference=None,
                authority_reported_authorization_consumption_committed=False,
                authority_reported_replay_guard_consumption_committed=False,
                commit_state_known=True,
                consumption_evidence_candidate_ready=False,
                reconciliation_required=False,
            )
    elif result.decision == _DECISION_INDETERMINATE:
        valid = (
            _is_exact_opaque_reference(result.authority_result_reference)
            and result.block_reason is None
            and result.indeterminate_reason == _INDETERMINATE_AUTHORITY_REPORTED
            and type(result.indeterminate_reason) is str
            and result.consumption_reference is None
            and _is_exact_bool(result.commit_state_known, False)
            and result.authority_reported_authorization_consumption_committed is None
            and result.authority_reported_replay_guard_consumption_committed is None
        )
        if valid:
            return _snapshot(
                source_snapshot,
                asserted_authority_approval_reference,
                asserted_authority_conformance_reference,
                authority_result=result,
                decision=_DECISION_INDETERMINATE,
                block_reason=None,
                indeterminate_reason=_INDETERMINATE_AUTHORITY_REPORTED,
                authority_result_reference=result.authority_result_reference,
                consumption_reference=None,
                authority_reported_authorization_consumption_committed=None,
                authority_reported_replay_guard_consumption_committed=None,
                commit_state_known=False,
                consumption_evidence_candidate_ready=False,
                reconciliation_required=True,
            )

    return _indeterminate_snapshot(
        source_snapshot,
        asserted_authority_approval_reference,
        asserted_authority_conformance_reference,
        _INDETERMINATE_CONTRACT,
    )


def check_and_consume_demo_watchlist_order_authorization_adapter_evidence(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
    authority: KiwoomOrderAuthorizationAuthorityAdapter,
    *,
    asserted_authority_approval_reference: str,
    asserted_authority_conformance_reference: str,
) -> WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot:
    if type(source_snapshot) is not WatchlistOrderAuthorizationConsumptionClaimSnapshot:
        _raise("SOURCE_SNAPSHOT_TYPE_INVALID")
    if not _phase31_structure_and_safety_valid(source_snapshot):
        _raise("SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID")
    if not _phase30_request_and_materialization_binding_valid(source_snapshot):
        _raise("PHASE30_REQUEST_OR_MATERIALIZATION_BINDING_INVALID")
    if not _phase31_claim_fingerprint_valid(source_snapshot):
        _raise("PHASE31_CLAIM_FINGERPRINT_INVALID")
    if not _is_exact_opaque_reference(asserted_authority_approval_reference):
        _raise("ASSERTED_AUTHORITY_APPROVAL_REFERENCE_INVALID")
    if not _is_exact_opaque_reference(asserted_authority_conformance_reference):
        _raise("ASSERTED_AUTHORITY_CONFORMANCE_REFERENCE_INVALID")

    class_surface = _validated_authority_surface(authority)
    bound_operation = types.MethodType(class_surface, authority)

    try:
        result = bound_operation(
            authorization_claim_identity=source_snapshot.authorization_claim_identity,
            authorization_replay_guard=source_snapshot.authorization_replay_guard,
            claim_fingerprint=source_snapshot.claim_fingerprint,
            asserted_authority_approval_reference=asserted_authority_approval_reference,
            asserted_authority_conformance_reference=asserted_authority_conformance_reference,
        )
    except TimeoutError:
        return _indeterminate_snapshot(
            source_snapshot,
            asserted_authority_approval_reference,
            asserted_authority_conformance_reference,
            _INDETERMINATE_TIMEOUT,
        )
    except Exception:
        return _indeterminate_snapshot(
            source_snapshot,
            asserted_authority_approval_reference,
            asserted_authority_conformance_reference,
            _INDETERMINATE_EXCEPTION,
        )

    return _normalize_reported_result(
        result,
        source_snapshot,
        asserted_authority_approval_reference,
        asserted_authority_conformance_reference,
    )
