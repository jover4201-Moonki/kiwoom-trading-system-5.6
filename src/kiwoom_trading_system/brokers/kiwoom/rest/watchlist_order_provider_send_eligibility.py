from collections.abc import Mapping as _Mapping
from dataclasses import dataclass as _dataclass
from enum import Enum as _Enum
import hashlib as _hashlib
import json as _json
import re as _re

from .watchlist_order_authorization_adapter_evidence import (
    KiwoomOrderAuthorizationAuthorityReportedResult as _KiwoomOrderAuthorizationAuthorityReportedResult,
    WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot as _WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
)
from .watchlist_order_authorization_consumption_claim import (
    KiwoomOrderAuthorizationConsumptionClaimContext as _KiwoomOrderAuthorizationConsumptionClaimContext,
    WatchlistOrderAuthorizationConsumptionClaimSnapshot as _WatchlistOrderAuthorizationConsumptionClaimSnapshot,
)
from .watchlist_order_authorization_durable_authority import (
    KiwoomOrderAuthorizationDurableLedgerRecord as _KiwoomOrderAuthorizationDurableLedgerRecord,
    WatchlistOrderAuthorizationDurableVerificationSnapshot as _WatchlistOrderAuthorizationDurableVerificationSnapshot,
)
from .watchlist_order_send_request import (
    WatchlistOrderSendRequestSnapshot as _WatchlistOrderSendRequestSnapshot,
)


__all__ = (
    "WatchlistOrderProviderSendEligibilityError",
    "KiwoomOrderProviderSendEligibilityDecision",
    "KiwoomOrderProviderSendEligibilityIndeterminateReason",
    "WatchlistOrderProviderSendEligibilityCandidateSnapshot",
    "build_demo_watchlist_order_provider_send_eligibility_candidate_snapshot",
)


class WatchlistOrderProviderSendEligibilityError(RuntimeError):
    pass


class KiwoomOrderProviderSendEligibilityDecision(str, _Enum):
    PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY = "PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY"
    INDETERMINATE = "INDETERMINATE"


class KiwoomOrderProviderSendEligibilityIndeterminateReason(str, _Enum):
    SOURCE_DURABLE_VERIFICATION_INDETERMINATE = "SOURCE_DURABLE_VERIFICATION_INDETERMINATE"


@_dataclass(frozen=True)
class WatchlistOrderProviderSendEligibilityCandidateSnapshot:
    source_snapshot: _WatchlistOrderAuthorizationDurableVerificationSnapshot
    request_snapshot: _WatchlistOrderSendRequestSnapshot
    decision: KiwoomOrderProviderSendEligibilityDecision
    indeterminate_reason: KiwoomOrderProviderSendEligibilityIndeterminateReason | None
    request_materialization_verified: bool
    authorization_claim_binding_verified: bool
    durable_consumption_verified: bool
    provider_request_contract_verified: bool
    authority_approval_provenance_verified: bool
    authority_conformance_provenance_verified: bool
    provider_send_eligibility_candidate_ready: bool
    provider_send_eligibility_authorized: bool
    production_authority_use_authorized: bool
    transport_allowed: bool
    credential_accessed: bool
    network_performed: bool
    account_accessed: bool
    order_submitted: bool
    automatic_retry_permitted: bool
    reconciliation_required: bool
    eligibility_fingerprint: str


_PUBLIC_ERROR_CODES = (
    "SOURCE_SNAPSHOT_TYPE_INVALID",
    "PHASE33_DECISION_INVALID",
    "PHASE32_SOURCE_SNAPSHOT_TYPE_INVALID",
    "PHASE31_SOURCE_SNAPSHOT_TYPE_INVALID",
    "PHASE31_CONTEXT_TYPE_INVALID",
    "PHASE30_REQUEST_SNAPSHOT_TYPE_INVALID",
    "PHASE33_STATE_INVARIANT_INVALID",
    "PHASE32_STATE_OR_RESULT_INVALID",
    "PHASE31_STATE_OR_REFERENCE_INVALID",
    "PHASE31_CLAIM_IDENTITY_INVALID",
    "PHASE31_REPLAY_GUARD_INVALID",
    "PHASE30_REQUEST_STRUCTURE_INVALID",
    "PHASE30_REQUEST_SAFETY_INVALID",
    "PHASE30_CONTEXT_BINDING_INVALID",
    "PHASE30_MATERIALIZATION_FINGERPRINT_INVALID",
    "PHASE31_CLAIM_FINGERPRINT_INVALID",
    "PHASE32_AUTHORITY_RESULT_BINDING_INVALID",
    "PHASE32_EVIDENCE_FINGERPRINT_INVALID",
    "PHASE33_DURABLE_RECORD_STRUCTURE_INVALID",
    "PHASE33_DURABLE_RECORD_FINGERPRINT_INVALID",
    "PHASE33_DURABLE_RECORD_REFERENCE_SELF_BINDING_INVALID",
    "PHASE33_DURABLE_RECORD_SOURCE_BINDING_INVALID",
    "PHASE33_VERIFICATION_FINGERPRINT_INVALID",
    "PROVIDER_REQUEST_CONTRACT_INVALID",
)

_PROVIDER_BODY_KEYS = frozenset(
    {"dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"}
)
_LOWER_HEX_64 = _re.compile(r"^[0-9a-f]{64}$")
_RESULT_REFERENCE_RE = _re.compile(r"^phase33-result-[0-9a-f]{64}$")
_CONSUMPTION_REFERENCE_RE = _re.compile(r"^phase33-consume-[0-9a-f]{64}$")
_PHASE33_SUCCESS = "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED"
_PHASE33_INDETERMINATE = "INDETERMINATE"
_PHASE33_INDETERMINATE_REASONS = frozenset(
    {
        "LEDGER_READ_ERROR",
        "LEDGER_SCHEMA_MISMATCH",
        "SQLITE_DURABILITY_PROFILE_MISMATCH",
        "BACKEND_IDENTITY_MISMATCH",
        "LEDGER_RECORD_NOT_FOUND",
        "LEDGER_RECORD_BINDING_MISMATCH",
        "LEDGER_RECORD_FINGERPRINT_MISMATCH",
        "LEDGER_STATE_AMBIGUOUS",
    }
)
_PHASE32_CONSUMED = "AUTHORITY_REPORTED_CONSUMED"
_SCHEMA_ID = "kiwoom-watchlist-order-authorization-durable-ledger-v1"
_LEDGER_SCHEMA_REFERENCE = _SCHEMA_ID
_TRANSACTION_PROFILE_ID = "sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1"
_DURABILITY_PROFILE_ID = "sqlite-main-wal-synchronous-full-v1"


def _raise(code: str) -> None:
    raise WatchlistOrderProviderSendEligibilityError(code)


def _is_lower_hex_64(value: object) -> bool:
    return type(value) is str and _LOWER_HEX_64.fullmatch(value) is not None


def _strict_utf8(value: str) -> bool:
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        return False
    return True


def _has_phase31_control(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _has_phase30_control(value: str) -> bool:
    return any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in value)


def _is_phase30_reference(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and bool(value.strip())
        and not _has_phase30_control(value)
    )


def _is_phase31_opaque_reference(value: object) -> bool:
    return type(value) is str and bool(value) and bool(value.strip())


def _is_phase31_binding_reference(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and bool(value.strip())
        and not _has_phase31_control(value)
    )


def _is_phase32_opaque_reference(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and bool(value)
        and value == value.strip()
        and not _has_phase31_control(value)
    )


def _is_phase33_config_reference(value: object) -> bool:
    return _is_phase32_opaque_reference(value) and _strict_utf8(value)


def _is_exact_bool(value: object, expected: bool | None = None) -> bool:
    return type(value) is bool and (expected is None or value is expected)


def _is_exact_tuple_of_exact_str(value: object, length: int) -> bool:
    return (
        type(value) is tuple
        and len(value) == length
        and all(type(item) is str for item in value)
    )


def _canonical_sha256(envelope: dict[str, object]) -> str:
    canonical = _json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return _hashlib.sha256(canonical).hexdigest()


def _phase33_branch_state_valid(
    source_snapshot: _WatchlistOrderAuthorizationDurableVerificationSnapshot,
) -> bool:
    if not _is_phase33_config_reference(source_snapshot.backend_instance_reference):
        return False
    if type(source_snapshot.ledger_schema_reference) is not str:
        return False
    if source_snapshot.ledger_schema_reference != _LEDGER_SCHEMA_REFERENCE:
        return False
    if not _is_lower_hex_64(source_snapshot.verification_fingerprint):
        return False

    common_false = (
        source_snapshot.authority_approval_provenance_verified,
        source_snapshot.authority_conformance_provenance_verified,
        source_snapshot.provider_send_eligibility_authorized,
        source_snapshot.production_authority_use_authorized,
    )
    if not all(_is_exact_bool(value, False) for value in common_false):
        return False

    verification_flags = (
        source_snapshot.concrete_sqlite_authority_identity_verified,
        source_snapshot.ledger_schema_verified,
        source_snapshot.sqlite_connection_surface_verified,
        source_snapshot.sqlite_durability_profile_verified,
        source_snapshot.durable_record_present,
        source_snapshot.exact_binding_verified,
        source_snapshot.durable_consumption_record_verified,
    )

    if source_snapshot.verification_decision == _PHASE33_SUCCESS:
        if source_snapshot.indeterminate_reason is not None:
            return False
        if type(source_snapshot.durable_record) is not _KiwoomOrderAuthorizationDurableLedgerRecord:
            return False
        if not all(_is_exact_bool(value, True) for value in verification_flags):
            return False
        return _is_exact_bool(source_snapshot.reconciliation_required, False)

    if source_snapshot.verification_decision == _PHASE33_INDETERMINATE:
        if (
            type(source_snapshot.indeterminate_reason) is not str
            or source_snapshot.indeterminate_reason not in _PHASE33_INDETERMINATE_REASONS
        ):
            return False
        if source_snapshot.durable_record is not None:
            return False
        if not all(_is_exact_bool(value, False) for value in verification_flags):
            return False
        return _is_exact_bool(source_snapshot.reconciliation_required, True)

    return False


def _phase32_state_valid(
    phase32_snapshot: _WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
) -> bool:
    if not _is_lower_hex_64(phase32_snapshot.evidence_fingerprint):
        return False
    if type(phase32_snapshot.decision) is not str or phase32_snapshot.decision != _PHASE32_CONSUMED:
        return False
    if phase32_snapshot.block_reason is not None or phase32_snapshot.indeterminate_reason is not None:
        return False
    if type(phase32_snapshot.authority_result) is not _KiwoomOrderAuthorizationAuthorityReportedResult:
        return False

    for value in (
        phase32_snapshot.asserted_authority_approval_reference,
        phase32_snapshot.asserted_authority_conformance_reference,
        phase32_snapshot.authority_result_reference,
        phase32_snapshot.consumption_reference,
    ):
        if not _is_phase32_opaque_reference(value) or not _strict_utf8(value):
            return False

    expected_bools = (
        (phase32_snapshot.authority_reported_authorization_consumption_committed, True),
        (phase32_snapshot.authority_reported_replay_guard_consumption_committed, True),
        (phase32_snapshot.commit_state_known, True),
        (phase32_snapshot.consumption_evidence_candidate_ready, True),
        (phase32_snapshot.authority_trust_independently_verified, False),
        (phase32_snapshot.automatic_retry_permitted, False),
        (phase32_snapshot.reconciliation_required, False),
        (phase32_snapshot.authority_invocation_attempted, True),
        (phase32_snapshot.phase32_direct_credential_accessed, False),
        (phase32_snapshot.phase32_direct_network_performed, False),
        (phase32_snapshot.phase32_direct_account_accessed, False),
        (phase32_snapshot.phase32_direct_order_submitted, False),
    )
    return all(_is_exact_bool(value, expected) for value, expected in expected_bools)


def _phase31_state_and_reference_valid(
    phase31_snapshot: _WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    context = phase31_snapshot.context
    if not _is_exact_tuple_of_exact_str(phase31_snapshot.authorization_claim_identity, 4):
        return False
    if not _is_exact_tuple_of_exact_str(phase31_snapshot.authorization_replay_guard, 2):
        return False
    if not _is_lower_hex_64(phase31_snapshot.claim_fingerprint):
        return False

    expected_bools = (
        (phase31_snapshot.claim_prepared, True),
        (phase31_snapshot.authorization_consumption_committed, False),
        (phase31_snapshot.post_permitted, False),
        (phase31_snapshot.automatic_retry_permitted, False),
        (phase31_snapshot.network_performed, False),
        (phase31_snapshot.order_submitted, False),
    )
    if not all(_is_exact_bool(value, expected) for value, expected in expected_bools):
        return False

    if not _is_phase31_opaque_reference(context.authorization_authority_reference):
        return False
    if not _is_phase31_binding_reference(context.authorization_evidence_snapshot_id):
        return False
    if not _is_phase31_binding_reference(context.submission_attempt_reference):
        return False
    if not _is_phase31_opaque_reference(context.send_authorization_reference):
        return False

    if not _is_phase33_config_reference(context.authorization_authority_reference):
        return False
    for value in (
        context.authorization_evidence_snapshot_id,
        context.submission_attempt_reference,
        context.send_authorization_reference,
    ):
        if not _strict_utf8(value):
            return False

    return True


def _phase30_structure_copy(
    request_snapshot: _WatchlistOrderSendRequestSnapshot,
) -> dict[str, str] | None:
    for value in (
        request_snapshot.environment,
        request_snapshot.side,
        request_snapshot.exchange,
        request_snapshot.api_id,
        request_snapshot.http_method,
        request_snapshot.api_path,
    ):
        if type(value) is not str:
            return None

    body = request_snapshot.body
    if not isinstance(body, _Mapping):
        return None

    try:
        raw_keys = tuple(body.keys())
        raw_values = tuple(body.values())
        if set(raw_keys) != _PROVIDER_BODY_KEYS:
            return None
        if any(type(key) is not str for key in raw_keys):
            return None
        if any(type(value) is not str for value in raw_values):
            return None
        body_copy = {key: body[key] for key in _PROVIDER_BODY_KEYS}
        if any(type(value) is not str for value in body_copy.values()):
            return None
    except (AttributeError, KeyError, TypeError):
        return None

    if not _is_phase30_reference(request_snapshot.source_attempt_ref):
        return None
    if not _is_phase30_reference(request_snapshot.authorization_evidence_ref):
        return None
    if not _is_lower_hex_64(request_snapshot.materialization_fingerprint):
        return None
    return body_copy


def _phase30_safety_valid(request_snapshot: _WatchlistOrderSendRequestSnapshot) -> bool:
    return all(
        _is_exact_bool(value, False)
        for value in (
            request_snapshot.transport_allowed,
            request_snapshot.credential_accessed,
            request_snapshot.network_performed,
            request_snapshot.account_accessed,
            request_snapshot.order_submitted,
        )
    )


def _phase30_materialization_fingerprint(
    request_snapshot: _WatchlistOrderSendRequestSnapshot,
    body_copy: dict[str, str],
) -> str:
    return _canonical_sha256(
        {
            "environment": request_snapshot.environment,
            "side": request_snapshot.side,
            "exchange": request_snapshot.exchange,
            "api_id": request_snapshot.api_id,
            "http_method": request_snapshot.http_method,
            "api_path": request_snapshot.api_path,
            "body": body_copy,
            "source_attempt_ref": request_snapshot.source_attempt_ref,
            "authorization_evidence_ref": request_snapshot.authorization_evidence_ref,
        }
    )


def _phase31_claim_fingerprint(
    request_snapshot: _WatchlistOrderSendRequestSnapshot,
    phase31_snapshot: _WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> str:
    return _canonical_sha256(
        {
            "materialization_fingerprint": request_snapshot.materialization_fingerprint,
            "authorization_claim_identity": phase31_snapshot.authorization_claim_identity,
            "authorization_replay_guard": phase31_snapshot.authorization_replay_guard,
        }
    )


def _phase32_authority_result_binding_valid(
    phase32_snapshot: _WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
    phase31_snapshot: _WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    result = phase32_snapshot.authority_result
    if type(result) is not _KiwoomOrderAuthorizationAuthorityReportedResult:
        return False
    if not _is_exact_tuple_of_exact_str(result.authorization_claim_identity, 4):
        return False
    if result.authorization_claim_identity != phase31_snapshot.authorization_claim_identity:
        return False
    if not _is_exact_tuple_of_exact_str(result.authorization_replay_guard, 2):
        return False
    if result.authorization_replay_guard != phase31_snapshot.authorization_replay_guard:
        return False
    if not _is_lower_hex_64(result.claim_fingerprint):
        return False
    if result.claim_fingerprint != phase31_snapshot.claim_fingerprint:
        return False

    pairs = (
        (result.asserted_authority_approval_reference, phase32_snapshot.asserted_authority_approval_reference),
        (result.asserted_authority_conformance_reference, phase32_snapshot.asserted_authority_conformance_reference),
        (result.authority_result_reference, phase32_snapshot.authority_result_reference),
        (result.consumption_reference, phase32_snapshot.consumption_reference),
    )
    for actual, expected in pairs:
        if not _is_phase32_opaque_reference(actual) or actual != expected:
            return False

    if type(result.decision) is not str or result.decision != _PHASE32_CONSUMED:
        return False
    if result.block_reason is not None or result.indeterminate_reason is not None:
        return False
    return all(
        _is_exact_bool(value, True)
        for value in (
            result.authority_reported_authorization_consumption_committed,
            result.authority_reported_replay_guard_consumption_committed,
            result.commit_state_known,
        )
    )


def _phase32_evidence_fingerprint(
    phase32_snapshot: _WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
    phase31_snapshot: _WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> str:
    return _canonical_sha256(
        {
            "claim_fingerprint": phase31_snapshot.claim_fingerprint,
            "asserted_authority_approval_reference": phase32_snapshot.asserted_authority_approval_reference,
            "asserted_authority_conformance_reference": phase32_snapshot.asserted_authority_conformance_reference,
            "decision": phase32_snapshot.decision,
            "block_reason": phase32_snapshot.block_reason,
            "indeterminate_reason": phase32_snapshot.indeterminate_reason,
            "authority_result_reference": phase32_snapshot.authority_result_reference,
            "consumption_reference": phase32_snapshot.consumption_reference,
            "authority_reported_authorization_consumption_committed": phase32_snapshot.authority_reported_authorization_consumption_committed,
            "authority_reported_replay_guard_consumption_committed": phase32_snapshot.authority_reported_replay_guard_consumption_committed,
            "commit_state_known": phase32_snapshot.commit_state_known,
            "consumption_evidence_candidate_ready": phase32_snapshot.consumption_evidence_candidate_ready,
            "authority_trust_independently_verified": phase32_snapshot.authority_trust_independently_verified,
            "automatic_retry_permitted": phase32_snapshot.automatic_retry_permitted,
            "reconciliation_required": phase32_snapshot.reconciliation_required,
            "authority_invocation_attempted": phase32_snapshot.authority_invocation_attempted,
            "phase32_direct_credential_accessed": phase32_snapshot.phase32_direct_credential_accessed,
            "phase32_direct_network_performed": phase32_snapshot.phase32_direct_network_performed,
            "phase32_direct_account_accessed": phase32_snapshot.phase32_direct_account_accessed,
            "phase32_direct_order_submitted": phase32_snapshot.phase32_direct_order_submitted,
        }
    )


def _durable_record_structure_valid(record: _KiwoomOrderAuthorizationDurableLedgerRecord) -> bool:
    if not _is_phase33_config_reference(record.backend_instance_reference):
        return False
    if not _is_phase31_opaque_reference(record.authorization_authority_reference):
        return False
    if not _is_phase33_config_reference(record.authorization_authority_reference):
        return False
    if not _is_phase31_binding_reference(record.authorization_evidence_snapshot_id):
        return False
    if not _strict_utf8(record.authorization_evidence_snapshot_id):
        return False
    if not _is_phase31_binding_reference(record.submission_attempt_reference):
        return False
    if not _strict_utf8(record.submission_attempt_reference):
        return False
    if not _is_phase31_opaque_reference(record.send_authorization_reference):
        return False
    if not _strict_utf8(record.send_authorization_reference):
        return False
    if not _is_lower_hex_64(record.claim_fingerprint):
        return False
    if not _is_phase32_opaque_reference(record.authority_approval_reference):
        return False
    if not _strict_utf8(record.authority_approval_reference):
        return False
    if not _is_phase32_opaque_reference(record.authority_conformance_reference):
        return False
    if not _strict_utf8(record.authority_conformance_reference):
        return False
    if type(record.authority_result_reference) is not str or _RESULT_REFERENCE_RE.fullmatch(record.authority_result_reference) is None:
        return False
    if type(record.consumption_reference) is not str or _CONSUMPTION_REFERENCE_RE.fullmatch(record.consumption_reference) is None:
        return False
    if type(record.sqlite_journal_mode) is not str or record.sqlite_journal_mode != "wal":
        return False
    if type(record.sqlite_synchronous_level) is not int or record.sqlite_synchronous_level != 2:
        return False
    return _is_lower_hex_64(record.record_fingerprint)


def _durable_record_fingerprint(record: _KiwoomOrderAuthorizationDurableLedgerRecord) -> str:
    return _canonical_sha256(
        {
            "domain": "phase33-durable-record-v1",
            "schema_id": _SCHEMA_ID,
            "transaction_profile_id": _TRANSACTION_PROFILE_ID,
            "durability_profile_id": _DURABILITY_PROFILE_ID,
            "backend_instance_reference": record.backend_instance_reference,
            "authorization_authority_reference": record.authorization_authority_reference,
            "authorization_evidence_snapshot_id": record.authorization_evidence_snapshot_id,
            "submission_attempt_reference": record.submission_attempt_reference,
            "send_authorization_reference": record.send_authorization_reference,
            "claim_fingerprint": record.claim_fingerprint,
            "authority_approval_reference": record.authority_approval_reference,
            "authority_conformance_reference": record.authority_conformance_reference,
            "authority_result_reference": record.authority_result_reference,
            "consumption_reference": record.consumption_reference,
            "sqlite_journal_mode": record.sqlite_journal_mode,
            "sqlite_synchronous_level": record.sqlite_synchronous_level,
        }
    )


def _durable_authority_result_reference(record: _KiwoomOrderAuthorizationDurableLedgerRecord) -> str:
    identity = (
        record.authorization_authority_reference,
        record.authorization_evidence_snapshot_id,
        record.submission_attempt_reference,
        record.send_authorization_reference,
    )
    replay = (
        record.authorization_authority_reference,
        record.send_authorization_reference,
    )
    return "phase33-result-" + _canonical_sha256(
        {
            "domain": "phase33-authority-result-v1",
            "schema_id": _SCHEMA_ID,
            "transaction_profile_id": _TRANSACTION_PROFILE_ID,
            "durability_profile_id": _DURABILITY_PROFILE_ID,
            "backend_instance_reference": record.backend_instance_reference,
            "authorization_claim_identity": identity,
            "authorization_replay_guard": replay,
            "claim_fingerprint": record.claim_fingerprint,
            "authority_approval_reference": record.authority_approval_reference,
            "authority_conformance_reference": record.authority_conformance_reference,
        }
    )


def _durable_consumption_reference(record: _KiwoomOrderAuthorizationDurableLedgerRecord) -> str:
    identity = (
        record.authorization_authority_reference,
        record.authorization_evidence_snapshot_id,
        record.submission_attempt_reference,
        record.send_authorization_reference,
    )
    replay = (
        record.authorization_authority_reference,
        record.send_authorization_reference,
    )
    return "phase33-consume-" + _canonical_sha256(
        {
            "domain": "phase33-consumption-v1",
            "schema_id": _SCHEMA_ID,
            "transaction_profile_id": _TRANSACTION_PROFILE_ID,
            "durability_profile_id": _DURABILITY_PROFILE_ID,
            "backend_instance_reference": record.backend_instance_reference,
            "authorization_claim_identity": identity,
            "authorization_replay_guard": replay,
            "claim_fingerprint": record.claim_fingerprint,
            "authority_approval_reference": record.authority_approval_reference,
            "authority_conformance_reference": record.authority_conformance_reference,
            "authority_result_reference": record.authority_result_reference,
        }
    )


def _durable_record_source_binding_valid(
    record: _KiwoomOrderAuthorizationDurableLedgerRecord,
    source_snapshot: _WatchlistOrderAuthorizationDurableVerificationSnapshot,
    phase32_snapshot: _WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
    phase31_snapshot: _WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    context = phase31_snapshot.context
    return (
        record.backend_instance_reference == source_snapshot.backend_instance_reference
        and record.authorization_authority_reference == context.authorization_authority_reference
        and record.authorization_evidence_snapshot_id == context.authorization_evidence_snapshot_id
        and record.submission_attempt_reference == context.submission_attempt_reference
        and record.send_authorization_reference == context.send_authorization_reference
        and record.claim_fingerprint == phase31_snapshot.claim_fingerprint
        and record.authority_approval_reference == phase32_snapshot.asserted_authority_approval_reference
        and record.authority_conformance_reference == phase32_snapshot.asserted_authority_conformance_reference
        and record.authority_result_reference == phase32_snapshot.authority_result_reference
        and record.consumption_reference == phase32_snapshot.consumption_reference
    )


def _phase33_verification_fingerprint(
    source_snapshot: _WatchlistOrderAuthorizationDurableVerificationSnapshot,
    phase32_snapshot: _WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
    durable_record_fingerprint: str | None,
) -> str:
    return _canonical_sha256(
        {
            "domain": "phase33-local-durable-verification-v1",
            "source_evidence_fingerprint": phase32_snapshot.evidence_fingerprint,
            "durable_record_fingerprint": durable_record_fingerprint,
            "backend_instance_reference": source_snapshot.backend_instance_reference,
            "ledger_schema_reference": _LEDGER_SCHEMA_REFERENCE,
            "verification_decision": source_snapshot.verification_decision,
            "indeterminate_reason": source_snapshot.indeterminate_reason,
            "concrete_sqlite_authority_identity_verified": source_snapshot.concrete_sqlite_authority_identity_verified,
            "ledger_schema_verified": source_snapshot.ledger_schema_verified,
            "sqlite_connection_surface_verified": source_snapshot.sqlite_connection_surface_verified,
            "sqlite_durability_profile_verified": source_snapshot.sqlite_durability_profile_verified,
            "durable_record_present": source_snapshot.durable_record_present,
            "exact_binding_verified": source_snapshot.exact_binding_verified,
            "durable_consumption_record_verified": source_snapshot.durable_consumption_record_verified,
            "authority_approval_provenance_verified": source_snapshot.authority_approval_provenance_verified,
            "authority_conformance_provenance_verified": source_snapshot.authority_conformance_provenance_verified,
            "provider_send_eligibility_authorized": source_snapshot.provider_send_eligibility_authorized,
            "production_authority_use_authorized": source_snapshot.production_authority_use_authorized,
            "reconciliation_required": source_snapshot.reconciliation_required,
        }
    )


def _provider_request_contract_valid(
    request_snapshot: _WatchlistOrderSendRequestSnapshot,
    body_copy: dict[str, str],
) -> bool:
    if request_snapshot.environment != "demo":
        return False
    if request_snapshot.side != "BUY":
        return False
    if request_snapshot.exchange != "KRX":
        return False
    if request_snapshot.api_id != "kt10000":
        return False
    if request_snapshot.http_method != "POST":
        return False
    if request_snapshot.api_path != "/api/dostk/ordr":
        return False
    if body_copy["dmst_stex_tp"] != "KRX" or body_copy["cond_uv"] != "":
        return False
    if body_copy["trde_tp"] == "0":
        return body_copy["ord_uv"] != ""
    if body_copy["trde_tp"] == "3":
        return body_copy["ord_uv"] == ""
    return False


def _eligibility_envelope(
    snapshot: WatchlistOrderProviderSendEligibilityCandidateSnapshot,
) -> dict[str, object]:
    return {
        "domain": "phase34-provider-send-eligibility-candidate-v1",
        "phase33_verification_fingerprint": snapshot.source_snapshot.verification_fingerprint,
        "phase32_evidence_fingerprint": snapshot.source_snapshot.source_snapshot.evidence_fingerprint,
        "phase31_claim_fingerprint": snapshot.source_snapshot.source_snapshot.source_snapshot.claim_fingerprint,
        "phase30_materialization_fingerprint": snapshot.request_snapshot.materialization_fingerprint,
        "source_attempt_ref": snapshot.request_snapshot.source_attempt_ref,
        "authorization_evidence_ref": snapshot.request_snapshot.authorization_evidence_ref,
        "decision": snapshot.decision.value,
        "indeterminate_reason": None if snapshot.indeterminate_reason is None else snapshot.indeterminate_reason.value,
        "request_materialization_verified": snapshot.request_materialization_verified,
        "authorization_claim_binding_verified": snapshot.authorization_claim_binding_verified,
        "durable_consumption_verified": snapshot.durable_consumption_verified,
        "provider_request_contract_verified": snapshot.provider_request_contract_verified,
        "authority_approval_provenance_verified": snapshot.authority_approval_provenance_verified,
        "authority_conformance_provenance_verified": snapshot.authority_conformance_provenance_verified,
        "provider_send_eligibility_candidate_ready": snapshot.provider_send_eligibility_candidate_ready,
        "provider_send_eligibility_authorized": snapshot.provider_send_eligibility_authorized,
        "production_authority_use_authorized": snapshot.production_authority_use_authorized,
        "transport_allowed": snapshot.transport_allowed,
        "credential_accessed": snapshot.credential_accessed,
        "network_performed": snapshot.network_performed,
        "account_accessed": snapshot.account_accessed,
        "order_submitted": snapshot.order_submitted,
        "automatic_retry_permitted": snapshot.automatic_retry_permitted,
        "reconciliation_required": snapshot.reconciliation_required,
    }


def _eligibility_fingerprint(
    snapshot: WatchlistOrderProviderSendEligibilityCandidateSnapshot,
) -> str:
    return _canonical_sha256(_eligibility_envelope(snapshot))


def _assert_internal_safety_state(
    snapshot: WatchlistOrderProviderSendEligibilityCandidateSnapshot,
) -> None:
    defect = False
    if type(snapshot.source_snapshot) is not _WatchlistOrderAuthorizationDurableVerificationSnapshot:
        defect = True
    elif type(snapshot.request_snapshot) is not _WatchlistOrderSendRequestSnapshot:
        defect = True
    elif snapshot.request_snapshot is not snapshot.source_snapshot.source_snapshot.source_snapshot.source_snapshot:
        defect = True
    elif type(snapshot.decision) is not KiwoomOrderProviderSendEligibilityDecision:
        defect = True
    elif snapshot.indeterminate_reason is not None and type(snapshot.indeterminate_reason) is not KiwoomOrderProviderSendEligibilityIndeterminateReason:
        defect = True
    else:
        bool_fields = (
            snapshot.request_materialization_verified,
            snapshot.authorization_claim_binding_verified,
            snapshot.durable_consumption_verified,
            snapshot.provider_request_contract_verified,
            snapshot.authority_approval_provenance_verified,
            snapshot.authority_conformance_provenance_verified,
            snapshot.provider_send_eligibility_candidate_ready,
            snapshot.provider_send_eligibility_authorized,
            snapshot.production_authority_use_authorized,
            snapshot.transport_allowed,
            snapshot.credential_accessed,
            snapshot.network_performed,
            snapshot.account_accessed,
            snapshot.order_submitted,
            snapshot.automatic_retry_permitted,
            snapshot.reconciliation_required,
        )
        if not all(type(value) is bool for value in bool_fields):
            defect = True
        elif snapshot.request_materialization_verified is not True:
            defect = True
        elif snapshot.authorization_claim_binding_verified is not True:
            defect = True
        elif snapshot.provider_request_contract_verified is not True:
            defect = True
        elif snapshot.authority_approval_provenance_verified is not False:
            defect = True
        elif snapshot.authority_conformance_provenance_verified is not False:
            defect = True
        elif snapshot.provider_send_eligibility_authorized is not False:
            defect = True
        elif snapshot.production_authority_use_authorized is not False:
            defect = True
        elif snapshot.transport_allowed is not False:
            defect = True
        elif snapshot.credential_accessed is not False:
            defect = True
        elif snapshot.network_performed is not False:
            defect = True
        elif snapshot.account_accessed is not False:
            defect = True
        elif snapshot.order_submitted is not False:
            defect = True
        elif snapshot.automatic_retry_permitted is not False:
            defect = True
        elif snapshot.decision is KiwoomOrderProviderSendEligibilityDecision.PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY:
            if snapshot.indeterminate_reason is not None:
                defect = True
            elif snapshot.durable_consumption_verified is not True:
                defect = True
            elif snapshot.provider_send_eligibility_candidate_ready is not True:
                defect = True
            elif snapshot.reconciliation_required is not False:
                defect = True
        elif snapshot.decision is KiwoomOrderProviderSendEligibilityDecision.INDETERMINATE:
            if snapshot.indeterminate_reason is not KiwoomOrderProviderSendEligibilityIndeterminateReason.SOURCE_DURABLE_VERIFICATION_INDETERMINATE:
                defect = True
            elif snapshot.durable_consumption_verified is not False:
                defect = True
            elif snapshot.provider_send_eligibility_candidate_ready is not False:
                defect = True
            elif snapshot.reconciliation_required is not True:
                defect = True
        else:
            defect = True

    if not defect:
        if not _is_lower_hex_64(snapshot.eligibility_fingerprint):
            defect = True
        elif snapshot.eligibility_fingerprint != _eligibility_fingerprint(snapshot):
            defect = True

    if defect:
        raise AssertionError("PHASE34_INTERNAL_SAFETY_STATE_DEFECT")


def build_demo_watchlist_order_provider_send_eligibility_candidate_snapshot(
    source_snapshot: _WatchlistOrderAuthorizationDurableVerificationSnapshot,
) -> WatchlistOrderProviderSendEligibilityCandidateSnapshot:
    if type(source_snapshot) is not _WatchlistOrderAuthorizationDurableVerificationSnapshot:
        _raise("SOURCE_SNAPSHOT_TYPE_INVALID")

    if (
        type(source_snapshot.verification_decision) is not str
        or source_snapshot.verification_decision not in (_PHASE33_SUCCESS, _PHASE33_INDETERMINATE)
    ):
        _raise("PHASE33_DECISION_INVALID")

    phase32_snapshot = source_snapshot.source_snapshot
    if type(phase32_snapshot) is not _WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot:
        _raise("PHASE32_SOURCE_SNAPSHOT_TYPE_INVALID")

    phase31_snapshot = phase32_snapshot.source_snapshot
    if type(phase31_snapshot) is not _WatchlistOrderAuthorizationConsumptionClaimSnapshot:
        _raise("PHASE31_SOURCE_SNAPSHOT_TYPE_INVALID")

    if type(phase31_snapshot.context) is not _KiwoomOrderAuthorizationConsumptionClaimContext:
        _raise("PHASE31_CONTEXT_TYPE_INVALID")

    request_snapshot = phase31_snapshot.source_snapshot
    if type(request_snapshot) is not _WatchlistOrderSendRequestSnapshot:
        _raise("PHASE30_REQUEST_SNAPSHOT_TYPE_INVALID")

    if not _phase33_branch_state_valid(source_snapshot):
        _raise("PHASE33_STATE_INVARIANT_INVALID")

    if not _phase32_state_valid(phase32_snapshot):
        _raise("PHASE32_STATE_OR_RESULT_INVALID")

    if not _phase31_state_and_reference_valid(phase31_snapshot):
        _raise("PHASE31_STATE_OR_REFERENCE_INVALID")

    context = phase31_snapshot.context
    expected_claim_identity = (
        context.authorization_authority_reference,
        context.authorization_evidence_snapshot_id,
        context.submission_attempt_reference,
        context.send_authorization_reference,
    )
    if phase31_snapshot.authorization_claim_identity != expected_claim_identity:
        _raise("PHASE31_CLAIM_IDENTITY_INVALID")

    expected_replay_guard = (
        context.authorization_authority_reference,
        context.send_authorization_reference,
    )
    if phase31_snapshot.authorization_replay_guard != expected_replay_guard:
        _raise("PHASE31_REPLAY_GUARD_INVALID")

    body_copy = _phase30_structure_copy(request_snapshot)
    if body_copy is None:
        _raise("PHASE30_REQUEST_STRUCTURE_INVALID")

    if not _phase30_safety_valid(request_snapshot):
        _raise("PHASE30_REQUEST_SAFETY_INVALID")

    if (
        context.submission_attempt_reference != request_snapshot.source_attempt_ref
        or context.authorization_evidence_snapshot_id != request_snapshot.authorization_evidence_ref
    ):
        _raise("PHASE30_CONTEXT_BINDING_INVALID")

    if request_snapshot.materialization_fingerprint != _phase30_materialization_fingerprint(request_snapshot, body_copy):
        _raise("PHASE30_MATERIALIZATION_FINGERPRINT_INVALID")

    if phase31_snapshot.claim_fingerprint != _phase31_claim_fingerprint(request_snapshot, phase31_snapshot):
        _raise("PHASE31_CLAIM_FINGERPRINT_INVALID")

    if not _phase32_authority_result_binding_valid(phase32_snapshot, phase31_snapshot):
        _raise("PHASE32_AUTHORITY_RESULT_BINDING_INVALID")

    if phase32_snapshot.evidence_fingerprint != _phase32_evidence_fingerprint(phase32_snapshot, phase31_snapshot):
        _raise("PHASE32_EVIDENCE_FINGERPRINT_INVALID")

    durable_record_fingerprint = None
    if source_snapshot.verification_decision == _PHASE33_SUCCESS:
        durable_record = source_snapshot.durable_record
        if not _durable_record_structure_valid(durable_record):
            _raise("PHASE33_DURABLE_RECORD_STRUCTURE_INVALID")

        durable_record_fingerprint = _durable_record_fingerprint(durable_record)
        if durable_record.record_fingerprint != durable_record_fingerprint:
            _raise("PHASE33_DURABLE_RECORD_FINGERPRINT_INVALID")

        if (
            durable_record.authority_result_reference != _durable_authority_result_reference(durable_record)
            or durable_record.consumption_reference != _durable_consumption_reference(durable_record)
        ):
            _raise("PHASE33_DURABLE_RECORD_REFERENCE_SELF_BINDING_INVALID")

        if not _durable_record_source_binding_valid(
            durable_record,
            source_snapshot,
            phase32_snapshot,
            phase31_snapshot,
        ):
            _raise("PHASE33_DURABLE_RECORD_SOURCE_BINDING_INVALID")

    if source_snapshot.verification_fingerprint != _phase33_verification_fingerprint(
        source_snapshot,
        phase32_snapshot,
        durable_record_fingerprint,
    ):
        _raise("PHASE33_VERIFICATION_FINGERPRINT_INVALID")

    if not _provider_request_contract_valid(request_snapshot, body_copy):
        _raise("PROVIDER_REQUEST_CONTRACT_INVALID")

    success = source_snapshot.verification_decision == _PHASE33_SUCCESS
    decision = (
        KiwoomOrderProviderSendEligibilityDecision.PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY
        if success
        else KiwoomOrderProviderSendEligibilityDecision.INDETERMINATE
    )
    indeterminate_reason = (
        None
        if success
        else KiwoomOrderProviderSendEligibilityIndeterminateReason.SOURCE_DURABLE_VERIFICATION_INDETERMINATE
    )

    common_values = {
        "source_snapshot": source_snapshot,
        "request_snapshot": request_snapshot,
        "decision": decision,
        "indeterminate_reason": indeterminate_reason,
        "request_materialization_verified": True,
        "authorization_claim_binding_verified": True,
        "durable_consumption_verified": source_snapshot.durable_consumption_record_verified,
        "provider_request_contract_verified": True,
        "authority_approval_provenance_verified": source_snapshot.authority_approval_provenance_verified,
        "authority_conformance_provenance_verified": source_snapshot.authority_conformance_provenance_verified,
        "provider_send_eligibility_candidate_ready": success,
        "provider_send_eligibility_authorized": source_snapshot.provider_send_eligibility_authorized,
        "production_authority_use_authorized": source_snapshot.production_authority_use_authorized,
        "transport_allowed": False,
        "credential_accessed": False,
        "network_performed": False,
        "account_accessed": False,
        "order_submitted": False,
        "automatic_retry_permitted": False,
        "reconciliation_required": source_snapshot.reconciliation_required,
    }

    provisional = WatchlistOrderProviderSendEligibilityCandidateSnapshot(
        **common_values,
        eligibility_fingerprint="0" * 64,
    )
    snapshot = WatchlistOrderProviderSendEligibilityCandidateSnapshot(
        **common_values,
        eligibility_fingerprint=_eligibility_fingerprint(provisional),
    )
    _assert_internal_safety_state(snapshot)
    return snapshot
