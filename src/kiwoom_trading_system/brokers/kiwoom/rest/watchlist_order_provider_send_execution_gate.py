from dataclasses import dataclass as _dataclass, fields as _dataclass_fields
from datetime import datetime as _datetime, timezone as _timezone
from enum import Enum as _Enum
import hashlib as _hashlib
import json as _json
import math as _math
import re as _re
from types import MappingProxyType as _MappingProxyType

from .watchlist_order_provider_send_eligibility import (
    KiwoomOrderProviderSendEligibilityDecision as _Phase34Decision,
    KiwoomOrderProviderSendEligibilityIndeterminateReason as _Phase34IndeterminateReason,
    WatchlistOrderProviderSendEligibilityCandidateSnapshot as _Phase34Snapshot,
)
from .watchlist_order_submission_safety import (
    KiwoomPriorSubmissionState as _PriorSubmissionState,
)


__all__ = (
    "WatchlistOrderProviderSendExecutionGateError",
    "KiwoomOrderProviderSendExecutionReadinessDecision",
    "KiwoomOrderProviderSendExecutionReadinessReason",
    "Phase35ProviderSendApprovalEvidence",
    "Phase35ProviderSendConformanceEvidence",
    "Phase35ExecutionRiskFreshnessEvidence",
    "Phase35ExecutionBuyingPowerFreshnessEvidence",
    "Phase35CredentialOwnershipEvidence",
    "Phase35AccountOwnershipEvidence",
    "Phase35ProviderSendExecutionEvidenceBundle",
    "WatchlistOrderProviderSendExecutionReadinessSnapshot",
    "build_demo_watchlist_order_provider_send_execution_readiness_snapshot",
)


class WatchlistOrderProviderSendExecutionGateError(RuntimeError):
    pass


class KiwoomOrderProviderSendExecutionReadinessDecision(str, _Enum):
    PROVIDER_SEND_EXECUTION_READY = "PROVIDER_SEND_EXECUTION_READY"
    DENIED = "DENIED"
    INDETERMINATE = "INDETERMINATE"


class KiwoomOrderProviderSendExecutionReadinessReason(str, _Enum):
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    PHASE34_SOURCE_INDETERMINATE = "PHASE34_SOURCE_INDETERMINATE"
    TRUST_ANCHOR_UNVERIFIABLE = "TRUST_ANCHOR_UNVERIFIABLE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    EVIDENCE_MALFORMED = "EVIDENCE_MALFORMED"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    CLOCK_REFERENCE_UNVERIFIABLE = "CLOCK_REFERENCE_UNVERIFIABLE"
    PRIOR_SUBMISSION_ALREADY_ACCEPTED = "PRIOR_SUBMISSION_ALREADY_ACCEPTED"
    FRESH_REAUTHORIZATION_REQUIRED = "FRESH_REAUTHORIZATION_REQUIRED"
    RETRY_OR_RETRANSMISSION_REQUESTED = "RETRY_OR_RETRANSMISSION_REQUESTED"
    EXECUTION_RISK_BLOCKED = "EXECUTION_RISK_BLOCKED"
    BUYING_POWER_INSUFFICIENT = "BUYING_POWER_INSUFFICIENT"
    RISK_EVIDENCE_STALE = "RISK_EVIDENCE_STALE"
    BUYING_POWER_EVIDENCE_STALE = "BUYING_POWER_EVIDENCE_STALE"
    APPROVAL_OR_CONFORMANCE_EXPIRED = "APPROVAL_OR_CONFORMANCE_EXPIRED"
    OWNERSHIP_EVIDENCE_EXPIRED = "OWNERSHIP_EVIDENCE_EXPIRED"
    DEMO_BINDING_MISMATCH = "DEMO_BINDING_MISMATCH"
    OWNERSHIP_BINDING_MISMATCH = "OWNERSHIP_BINDING_MISMATCH"
    TRANSPORT_BINDING_MISMATCH = "TRANSPORT_BINDING_MISMATCH"
    SOURCE_BINDING_MISMATCH = "SOURCE_BINDING_MISMATCH"


@_dataclass(frozen=True, slots=True)
class Phase35ProviderSendApprovalEvidence:
    verifier_id: str
    verifier_identity_sha256: str
    evidence_id: str
    issued_at_utc: str
    expires_at_utc: str
    phase34_eligibility_fingerprint: str
    phase30_materialization_fingerprint: str
    source_attempt_ref: str
    authorization_evidence_ref: str
    scope_fingerprint: str
    evidence_fingerprint: str


@_dataclass(frozen=True, slots=True)
class Phase35ProviderSendConformanceEvidence:
    verifier_id: str
    verifier_identity_sha256: str
    evidence_id: str
    issued_at_utc: str
    expires_at_utc: str
    phase34_eligibility_fingerprint: str
    phase30_materialization_fingerprint: str
    source_attempt_ref: str
    authorization_evidence_ref: str
    scope_fingerprint: str
    evidence_fingerprint: str


@_dataclass(frozen=True, slots=True)
class Phase35ExecutionRiskFreshnessEvidence:
    verifier_id: str
    verifier_identity_sha256: str
    evidence_id: str
    issued_at_utc: str
    observed_at_utc: str
    phase34_eligibility_fingerprint: str
    phase30_materialization_fingerprint: str
    source_attempt_ref: str
    risk_decision: str
    scope_fingerprint: str
    evidence_fingerprint: str


@_dataclass(frozen=True, slots=True)
class Phase35ExecutionBuyingPowerFreshnessEvidence:
    verifier_id: str
    verifier_identity_sha256: str
    evidence_id: str
    issued_at_utc: str
    observed_at_utc: str
    phase34_eligibility_fingerprint: str
    phase30_materialization_fingerprint: str
    source_attempt_ref: str
    account_ref_id: str
    buying_power_decision: str
    scope_fingerprint: str
    evidence_fingerprint: str


@_dataclass(frozen=True, slots=True)
class Phase35CredentialOwnershipEvidence:
    verifier_id: str
    verifier_identity_sha256: str
    evidence_id: str
    issued_at_utc: str
    expires_at_utc: str
    credential_ref_id: str
    owner_ref: str
    environment: str
    scope_fingerprint: str
    evidence_fingerprint: str


@_dataclass(frozen=True, slots=True)
class Phase35AccountOwnershipEvidence:
    verifier_id: str
    verifier_identity_sha256: str
    evidence_id: str
    issued_at_utc: str
    expires_at_utc: str
    account_ref_id: str
    account_owner_ref: str
    bound_credential_ref_id: str
    environment: str
    scope_fingerprint: str
    evidence_fingerprint: str


@_dataclass(frozen=True, slots=True)
class Phase35ProviderSendExecutionEvidenceBundle:
    approval_evidence: Phase35ProviderSendApprovalEvidence | None
    conformance_evidence: Phase35ProviderSendConformanceEvidence | None
    risk_evidence: Phase35ExecutionRiskFreshnessEvidence | None
    buying_power_evidence: Phase35ExecutionBuyingPowerFreshnessEvidence | None
    credential_ownership_evidence: Phase35CredentialOwnershipEvidence | None
    account_ownership_evidence: Phase35AccountOwnershipEvidence | None
    prior_submission_state: _PriorSubmissionState | None
    prior_attempt_reference: str | None
    reconciliation_reference: str | None
    automatic_retry_requested: bool
    retransmission_requested: bool


@_dataclass(frozen=True, slots=True)
class WatchlistOrderProviderSendExecutionReadinessSnapshot:
    source_snapshot: _Phase34Snapshot
    decision: KiwoomOrderProviderSendExecutionReadinessDecision
    primary_reason_code: KiwoomOrderProviderSendExecutionReadinessReason | None
    all_reason_codes: tuple[KiwoomOrderProviderSendExecutionReadinessReason, ...]
    evaluated_at_utc: str
    risk_age_seconds: float | None
    buying_power_age_seconds: float | None
    phase34_eligibility_fingerprint: str
    phase33_verification_fingerprint: str
    phase30_materialization_fingerprint: str
    source_attempt_ref: str
    authorization_evidence_ref: str
    scope_fingerprint: str | None
    approval_evidence_fingerprint: str | None
    conformance_evidence_fingerprint: str | None
    risk_evidence_fingerprint: str | None
    buying_power_evidence_fingerprint: str | None
    credential_ownership_evidence_fingerprint: str | None
    account_ownership_evidence_fingerprint: str | None
    prior_submission_state: _PriorSubmissionState | None
    prior_attempt_reference: str | None
    reconciliation_reference: str | None
    reconciliation_required: bool
    provider_send_execution_ready: bool
    transport_authorized: bool
    provider_call_performed: bool
    actual_kt10000_post_performed: bool
    credential_lookup_performed: bool
    account_lookup_performed: bool
    token_acquisition_performed: bool
    automatic_retry_permitted: bool
    retransmission_permitted: bool
    readiness_fingerprint: str


_PHASE34_FIELDS = (
    "source_snapshot",
    "request_snapshot",
    "decision",
    "indeterminate_reason",
    "request_materialization_verified",
    "authorization_claim_binding_verified",
    "durable_consumption_verified",
    "provider_request_contract_verified",
    "authority_approval_provenance_verified",
    "authority_conformance_provenance_verified",
    "provider_send_eligibility_candidate_ready",
    "provider_send_eligibility_authorized",
    "production_authority_use_authorized",
    "transport_allowed",
    "credential_accessed",
    "network_performed",
    "account_accessed",
    "order_submitted",
    "automatic_retry_permitted",
    "reconciliation_required",
    "eligibility_fingerprint",
)

_MAX_RISK_EVIDENCE_AGE_SECONDS = 5.000
_MAX_BUYING_POWER_EVIDENCE_AGE_SECONDS = 5.000
_MAX_FUTURE_CLOCK_SKEW_SECONDS = 1.000

_VERIFIER_IDS = (
    "phase35-explicit-provider-send-approval-verifier-v1",
    "phase35-provider-send-conformance-verifier-v1",
    "phase35-execution-risk-freshness-verifier-v1",
    "phase35-execution-buying-power-freshness-verifier-v1",
    "phase35-demo-credential-ownership-verifier-v1",
    "phase35-demo-account-ownership-verifier-v1",
)

_VERIFIER_REGISTRY = _MappingProxyType(
    {
        "phase35-explicit-provider-send-approval-verifier-v1":
            "4caaa7efb7ef985b98ed3ed8e4aa228df3a9747dae025c2700566978c9401af7",
        "phase35-provider-send-conformance-verifier-v1":
            "d27104d5e61e6592a29135daa240f7d5c546ffd1ffc140281da707528d814947",
        "phase35-execution-risk-freshness-verifier-v1":
            "49333769e15478e16280bd539f3751e00b5cc2597e7b5bfca05fd10c766418a6",
        "phase35-execution-buying-power-freshness-verifier-v1":
            "7e0121363914e113979250bb495fbcabfbef25ef155a18816966257e124b1f57",
        "phase35-demo-credential-ownership-verifier-v1":
            "8cd94990ad8914a834c3c5406641076a10ff59bcb7f9f2725c3212bf34c302d0",
        "phase35-demo-account-ownership-verifier-v1":
            "79feeef34933b768ece50d68e7d1dcf1d526e21783c229c65ade954901bdea18",
    }
)

_EVIDENCE_DOMAIN_BY_TYPE = _MappingProxyType(
    {
        Phase35ProviderSendApprovalEvidence:
            "phase35-explicit-provider-send-approval-evidence-v1",
        Phase35ProviderSendConformanceEvidence:
            "phase35-provider-send-conformance-evidence-v1",
        Phase35ExecutionRiskFreshnessEvidence:
            "phase35-execution-risk-freshness-evidence-v1",
        Phase35ExecutionBuyingPowerFreshnessEvidence:
            "phase35-execution-buying-power-freshness-evidence-v1",
        Phase35CredentialOwnershipEvidence:
            "phase35-demo-credential-ownership-evidence-v1",
        Phase35AccountOwnershipEvidence:
            "phase35-demo-account-ownership-evidence-v1",
    }
)

_EXPECTED_VERIFIER_BY_TYPE = _MappingProxyType(
    {
        Phase35ProviderSendApprovalEvidence:
            "phase35-explicit-provider-send-approval-verifier-v1",
        Phase35ProviderSendConformanceEvidence:
            "phase35-provider-send-conformance-verifier-v1",
        Phase35ExecutionRiskFreshnessEvidence:
            "phase35-execution-risk-freshness-verifier-v1",
        Phase35ExecutionBuyingPowerFreshnessEvidence:
            "phase35-execution-buying-power-freshness-verifier-v1",
        Phase35CredentialOwnershipEvidence:
            "phase35-demo-credential-ownership-verifier-v1",
        Phase35AccountOwnershipEvidence:
            "phase35-demo-account-ownership-verifier-v1",
    }
)

_REASON_PRIORITY = _MappingProxyType(
    {
        KiwoomOrderProviderSendExecutionReadinessReason.RECONCILIATION_REQUIRED: 1000,
        KiwoomOrderProviderSendExecutionReadinessReason.PHASE34_SOURCE_INDETERMINATE: 990,
        KiwoomOrderProviderSendExecutionReadinessReason.TRUST_ANCHOR_UNVERIFIABLE: 980,
        KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_CONFLICT: 970,
        KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED: 960,
        KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MISSING: 950,
        KiwoomOrderProviderSendExecutionReadinessReason.CLOCK_REFERENCE_UNVERIFIABLE: 940,
        KiwoomOrderProviderSendExecutionReadinessReason.PRIOR_SUBMISSION_ALREADY_ACCEPTED: 800,
        KiwoomOrderProviderSendExecutionReadinessReason.FRESH_REAUTHORIZATION_REQUIRED: 790,
        KiwoomOrderProviderSendExecutionReadinessReason.RETRY_OR_RETRANSMISSION_REQUESTED: 780,
        KiwoomOrderProviderSendExecutionReadinessReason.EXECUTION_RISK_BLOCKED: 770,
        KiwoomOrderProviderSendExecutionReadinessReason.BUYING_POWER_INSUFFICIENT: 760,
        KiwoomOrderProviderSendExecutionReadinessReason.RISK_EVIDENCE_STALE: 750,
        KiwoomOrderProviderSendExecutionReadinessReason.BUYING_POWER_EVIDENCE_STALE: 740,
        KiwoomOrderProviderSendExecutionReadinessReason.APPROVAL_OR_CONFORMANCE_EXPIRED: 730,
        KiwoomOrderProviderSendExecutionReadinessReason.OWNERSHIP_EVIDENCE_EXPIRED: 720,
        KiwoomOrderProviderSendExecutionReadinessReason.DEMO_BINDING_MISMATCH: 710,
        KiwoomOrderProviderSendExecutionReadinessReason.OWNERSHIP_BINDING_MISMATCH: 700,
        KiwoomOrderProviderSendExecutionReadinessReason.TRANSPORT_BINDING_MISMATCH: 690,
        KiwoomOrderProviderSendExecutionReadinessReason.SOURCE_BINDING_MISMATCH: 680,
    }
)

_INDETERMINATE_REASONS = frozenset(
    (
        KiwoomOrderProviderSendExecutionReadinessReason.RECONCILIATION_REQUIRED,
        KiwoomOrderProviderSendExecutionReadinessReason.PHASE34_SOURCE_INDETERMINATE,
        KiwoomOrderProviderSendExecutionReadinessReason.TRUST_ANCHOR_UNVERIFIABLE,
        KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_CONFLICT,
        KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED,
        KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MISSING,
        KiwoomOrderProviderSendExecutionReadinessReason.CLOCK_REFERENCE_UNVERIFIABLE,
    )
)

_LOWER_HEX_64 = _re.compile(r"^[0-9a-f]{64}$")
_CREDENTIAL_REF = _re.compile(r"^credref:[A-Za-z0-9._-]{1,96}$")
_OWNER_REF = _re.compile(r"^ownerref:[A-Za-z0-9._-]{1,96}$")
_ACCOUNT_REF = _re.compile(r"^acctref:[A-Za-z0-9._-]{1,96}$")


def _canonical_sha256(envelope: dict[str, object]) -> str:
    raw = _json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return _hashlib.sha256(raw).hexdigest()


def _utc_now() -> _datetime:
    return _datetime.now(_timezone.utc)


def _canonical_utc_text(value: _datetime) -> str:
    if type(value) is not _datetime:
        raise AssertionError("PHASE35_INTERNAL_CLOCK_TYPE_DEFECT")
    if value.tzinfo is None or value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise AssertionError("PHASE35_INTERNAL_CLOCK_NOT_UTC")
    return value.astimezone(_timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_utc_text(value: object) -> _datetime | None:
    if type(value) is not str or not value.endswith("Z") or value != value.strip():
        return None
    try:
        parsed = _datetime.fromisoformat(value[:-1] + "+00:00")
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    if parsed.utcoffset().total_seconds() != 0:
        return None
    return parsed.astimezone(_timezone.utc)


def _is_lower_hex_64(value: object) -> bool:
    return type(value) is str and _LOWER_HEX_64.fullmatch(value) is not None


def _is_evidence_id(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and value == value.strip()
        and all(0x20 <= ord(ch) <= 0x7E for ch in value)
    )


def _is_local_opaque_reference(value: object) -> bool:
    return (
        type(value) is str
        and value != ""
        and value == value.strip()
        and all(ord(ch) >= 0x20 and ord(ch) != 0x7F for ch in value)
    )


def _phase34_structure_valid(source_snapshot: _Phase34Snapshot) -> bool:
    if tuple(field.name for field in _dataclass_fields(_Phase34Snapshot)) != _PHASE34_FIELDS:
        return False
    if type(source_snapshot.decision) is not _Phase34Decision:
        return False
    if (
        source_snapshot.indeterminate_reason is not None
        and type(source_snapshot.indeterminate_reason) is not _Phase34IndeterminateReason
    ):
        return False
    try:
        phase33_snapshot = source_snapshot.source_snapshot
        phase32_snapshot = phase33_snapshot.source_snapshot
        phase31_snapshot = phase32_snapshot.source_snapshot
        request_snapshot = phase31_snapshot.source_snapshot
        nested_string_fields = (
            phase33_snapshot.verification_fingerprint,
            phase32_snapshot.evidence_fingerprint,
            phase31_snapshot.claim_fingerprint,
            request_snapshot.materialization_fingerprint,
            request_snapshot.source_attempt_ref,
            request_snapshot.authorization_evidence_ref,
            request_snapshot.environment,
            request_snapshot.side,
            request_snapshot.exchange,
            request_snapshot.api_id,
            request_snapshot.http_method,
            request_snapshot.api_path,
        )
    except AttributeError:
        return False
    if source_snapshot.request_snapshot is not request_snapshot:
        return False
    return all(type(value) is str for value in nested_string_fields)


def _phase34_eligibility_envelope(source_snapshot: _Phase34Snapshot) -> dict[str, object]:
    return {
        "domain": "phase34-provider-send-eligibility-candidate-v1",
        "phase33_verification_fingerprint": source_snapshot.source_snapshot.verification_fingerprint,
        "phase32_evidence_fingerprint": source_snapshot.source_snapshot.source_snapshot.evidence_fingerprint,
        "phase31_claim_fingerprint": source_snapshot.source_snapshot.source_snapshot.source_snapshot.claim_fingerprint,
        "phase30_materialization_fingerprint": source_snapshot.request_snapshot.materialization_fingerprint,
        "source_attempt_ref": source_snapshot.request_snapshot.source_attempt_ref,
        "authorization_evidence_ref": source_snapshot.request_snapshot.authorization_evidence_ref,
        "decision": source_snapshot.decision.value,
        "indeterminate_reason": (
            None
            if source_snapshot.indeterminate_reason is None
            else source_snapshot.indeterminate_reason.value
        ),
        "request_materialization_verified": source_snapshot.request_materialization_verified,
        "authorization_claim_binding_verified": source_snapshot.authorization_claim_binding_verified,
        "durable_consumption_verified": source_snapshot.durable_consumption_verified,
        "provider_request_contract_verified": source_snapshot.provider_request_contract_verified,
        "authority_approval_provenance_verified": source_snapshot.authority_approval_provenance_verified,
        "authority_conformance_provenance_verified": source_snapshot.authority_conformance_provenance_verified,
        "provider_send_eligibility_candidate_ready": source_snapshot.provider_send_eligibility_candidate_ready,
        "provider_send_eligibility_authorized": source_snapshot.provider_send_eligibility_authorized,
        "production_authority_use_authorized": source_snapshot.production_authority_use_authorized,
        "transport_allowed": source_snapshot.transport_allowed,
        "credential_accessed": source_snapshot.credential_accessed,
        "network_performed": source_snapshot.network_performed,
        "account_accessed": source_snapshot.account_accessed,
        "order_submitted": source_snapshot.order_submitted,
        "automatic_retry_permitted": source_snapshot.automatic_retry_permitted,
        "reconciliation_required": source_snapshot.reconciliation_required,
    }


def _phase34_eligibility_fingerprint(source_snapshot: _Phase34Snapshot) -> str:
    return _canonical_sha256(_phase34_eligibility_envelope(source_snapshot))


def _phase34_safety_matrix_valid(source_snapshot: _Phase34Snapshot) -> bool:
    bool_values = (
        source_snapshot.request_materialization_verified,
        source_snapshot.authorization_claim_binding_verified,
        source_snapshot.durable_consumption_verified,
        source_snapshot.provider_request_contract_verified,
        source_snapshot.authority_approval_provenance_verified,
        source_snapshot.authority_conformance_provenance_verified,
        source_snapshot.provider_send_eligibility_candidate_ready,
        source_snapshot.provider_send_eligibility_authorized,
        source_snapshot.production_authority_use_authorized,
        source_snapshot.transport_allowed,
        source_snapshot.credential_accessed,
        source_snapshot.network_performed,
        source_snapshot.account_accessed,
        source_snapshot.order_submitted,
        source_snapshot.automatic_retry_permitted,
        source_snapshot.reconciliation_required,
    )
    if not all(type(value) is bool for value in bool_values):
        return False
    if source_snapshot.request_materialization_verified is not True:
        return False
    if source_snapshot.authorization_claim_binding_verified is not True:
        return False
    if source_snapshot.provider_request_contract_verified is not True:
        return False
    if source_snapshot.authority_approval_provenance_verified is not False:
        return False
    if source_snapshot.authority_conformance_provenance_verified is not False:
        return False
    if source_snapshot.provider_send_eligibility_authorized is not False:
        return False
    if source_snapshot.production_authority_use_authorized is not False:
        return False
    if source_snapshot.transport_allowed is not False:
        return False
    if source_snapshot.credential_accessed is not False:
        return False
    if source_snapshot.network_performed is not False:
        return False
    if source_snapshot.account_accessed is not False:
        return False
    if source_snapshot.order_submitted is not False:
        return False
    if source_snapshot.automatic_retry_permitted is not False:
        return False

    if source_snapshot.decision is _Phase34Decision.PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY:
        return (
            source_snapshot.indeterminate_reason is None
            and source_snapshot.durable_consumption_verified is True
            and source_snapshot.provider_send_eligibility_candidate_ready is True
            and source_snapshot.reconciliation_required is False
        )

    if source_snapshot.decision is _Phase34Decision.INDETERMINATE:
        return (
            source_snapshot.indeterminate_reason
            is _Phase34IndeterminateReason.SOURCE_DURABLE_VERIFICATION_INDETERMINATE
            and source_snapshot.durable_consumption_verified is False
            and source_snapshot.provider_send_eligibility_candidate_ready is False
            and source_snapshot.reconciliation_required is True
        )

    return False


def _prior_submission_invariant_valid(bundle: Phase35ProviderSendExecutionEvidenceBundle) -> bool:
    state = bundle.prior_submission_state
    prior_ref = bundle.prior_attempt_reference
    reconciliation_ref = bundle.reconciliation_reference
    if type(state) is not _PriorSubmissionState:
        return False
    if state is _PriorSubmissionState.NEVER_ATTEMPTED:
        return prior_ref is None and reconciliation_ref is None
    if state is _PriorSubmissionState.AMBIGUOUS_UNRESOLVED:
        return (
            _is_local_opaque_reference(prior_ref)
            and (
                reconciliation_ref is None
                or _is_local_opaque_reference(reconciliation_ref)
            )
        )
    if state in (
        _PriorSubmissionState.CONFIRMED_NOT_ACCEPTED,
        _PriorSubmissionState.CONFIRMED_ACCEPTED,
    ):
        return (
            _is_local_opaque_reference(prior_ref)
            and _is_local_opaque_reference(reconciliation_ref)
        )
    return False


def _evidence_envelope(evidence: object) -> dict[str, object]:
    domain = _EVIDENCE_DOMAIN_BY_TYPE[type(evidence)]
    result: dict[str, object] = {"domain": domain}
    for field in _dataclass_fields(type(evidence)):
        if field.name == "evidence_fingerprint":
            break
        result[field.name] = getattr(evidence, field.name)
    return result


def _evidence_fingerprint(evidence: object) -> str:
    return _canonical_sha256(_evidence_envelope(evidence))


def _evidence_structure_valid(evidence: object) -> bool:
    evidence_type = type(evidence)
    if evidence_type not in _EVIDENCE_DOMAIN_BY_TYPE:
        return False
    if not _is_evidence_id(evidence.evidence_id):
        return False
    for name in ("verifier_id", "verifier_identity_sha256", "scope_fingerprint", "evidence_fingerprint"):
        if type(getattr(evidence, name)) is not str:
            return False
    if not _is_lower_hex_64(evidence.verifier_identity_sha256):
        return False
    if not _is_lower_hex_64(evidence.scope_fingerprint):
        return False
    if not _is_lower_hex_64(evidence.evidence_fingerprint):
        return False
    if _parse_utc_text(evidence.issued_at_utc) is None:
        return False

    if isinstance(
        evidence,
        (
            Phase35ProviderSendApprovalEvidence,
            Phase35ProviderSendConformanceEvidence,
            Phase35CredentialOwnershipEvidence,
            Phase35AccountOwnershipEvidence,
        ),
    ):
        issued = _parse_utc_text(evidence.issued_at_utc)
        expires = _parse_utc_text(evidence.expires_at_utc)
        if issued is None or expires is None or expires <= issued:
            return False

    if isinstance(
        evidence,
        (
            Phase35ExecutionRiskFreshnessEvidence,
            Phase35ExecutionBuyingPowerFreshnessEvidence,
        ),
    ):
        if _parse_utc_text(evidence.observed_at_utc) is None:
            return False

    if isinstance(
        evidence,
        (
            Phase35ProviderSendApprovalEvidence,
            Phase35ProviderSendConformanceEvidence,
        ),
    ):
        return (
            _is_lower_hex_64(evidence.phase34_eligibility_fingerprint)
            and _is_lower_hex_64(evidence.phase30_materialization_fingerprint)
            and _is_local_opaque_reference(evidence.source_attempt_ref)
            and _is_local_opaque_reference(evidence.authorization_evidence_ref)
        )

    if isinstance(evidence, Phase35ExecutionRiskFreshnessEvidence):
        return (
            _is_lower_hex_64(evidence.phase34_eligibility_fingerprint)
            and _is_lower_hex_64(evidence.phase30_materialization_fingerprint)
            and _is_local_opaque_reference(evidence.source_attempt_ref)
            and type(evidence.risk_decision) is str
            and evidence.risk_decision in ("RISK_CLEAR", "RISK_BLOCKED")
        )

    if isinstance(evidence, Phase35ExecutionBuyingPowerFreshnessEvidence):
        return (
            _is_lower_hex_64(evidence.phase34_eligibility_fingerprint)
            and _is_lower_hex_64(evidence.phase30_materialization_fingerprint)
            and _is_local_opaque_reference(evidence.source_attempt_ref)
            and type(evidence.account_ref_id) is str
            and _ACCOUNT_REF.fullmatch(evidence.account_ref_id) is not None
            and type(evidence.buying_power_decision) is str
            and evidence.buying_power_decision
            in ("BUYING_POWER_SUFFICIENT", "BUYING_POWER_INSUFFICIENT")
        )

    if isinstance(evidence, Phase35CredentialOwnershipEvidence):
        return (
            type(evidence.credential_ref_id) is str
            and _CREDENTIAL_REF.fullmatch(evidence.credential_ref_id) is not None
            and type(evidence.owner_ref) is str
            and _OWNER_REF.fullmatch(evidence.owner_ref) is not None
            and type(evidence.environment) is str
        )

    if isinstance(evidence, Phase35AccountOwnershipEvidence):
        return (
            type(evidence.account_ref_id) is str
            and _ACCOUNT_REF.fullmatch(evidence.account_ref_id) is not None
            and type(evidence.account_owner_ref) is str
            and _OWNER_REF.fullmatch(evidence.account_owner_ref) is not None
            and type(evidence.bound_credential_ref_id) is str
            and _CREDENTIAL_REF.fullmatch(evidence.bound_credential_ref_id) is not None
            and type(evidence.environment) is str
        )

    return False


def _trust_anchor_valid(evidence: object) -> bool:
    evidence_type = type(evidence)
    expected_id = _EXPECTED_VERIFIER_BY_TYPE[evidence_type]
    return (
        evidence.verifier_id == expected_id
        and evidence.verifier_identity_sha256 == _VERIFIER_REGISTRY[expected_id]
    )


def _scope_envelope(
    source_snapshot: _Phase34Snapshot,
    credential_ref_id: str,
    account_ref_id: str,
) -> dict[str, object]:
    request = source_snapshot.request_snapshot
    return {
        "domain": "phase35-provider-send-execution-scope-v1",
        "phase34_eligibility_fingerprint": source_snapshot.eligibility_fingerprint,
        "phase33_verification_fingerprint": source_snapshot.source_snapshot.verification_fingerprint,
        "phase30_materialization_fingerprint": request.materialization_fingerprint,
        "source_attempt_ref": request.source_attempt_ref,
        "authorization_evidence_ref": request.authorization_evidence_ref,
        "environment": "demo",
        "host": "mockapi.kiwoom.com",
        "api_id": "kt10000",
        "http_method": "POST",
        "api_path": "/api/dostk/ordr",
        "exchange": "KRX",
        "side": "BUY",
        "financing": "CASH",
        "credential_ref_id": credential_ref_id,
        "account_ref_id": account_ref_id,
    }


def _scope_fingerprint(
    source_snapshot: _Phase34Snapshot,
    credential_ref_id: str,
    account_ref_id: str,
) -> str:
    return _canonical_sha256(
        _scope_envelope(source_snapshot, credential_ref_id, account_ref_id)
    )


def _request_target_valid(source_snapshot: _Phase34Snapshot) -> bool:
    request = source_snapshot.request_snapshot
    try:
        return (
            request.environment == "demo"
            and request.side == "BUY"
            and request.exchange == "KRX"
            and request.api_id == "kt10000"
            and request.http_method == "POST"
            and request.api_path == "/api/dostk/ordr"
        )
    except AttributeError:
        return False


def _safe_fingerprint(value: object) -> str | None:
    return value if type(value) is str else None


def _format_age_for_fingerprint(value: float | None) -> str | None:
    if value is None:
        return None
    if not _math.isfinite(value):
        raise AssertionError("PHASE35_INTERNAL_NONFINITE_AGE")
    return f"{value:.3f}"


def _readiness_envelope(
    snapshot: WatchlistOrderProviderSendExecutionReadinessSnapshot,
) -> dict[str, object]:
    return {
        "domain": "phase35-provider-send-execution-readiness-v1",
        "decision": snapshot.decision.value,
        "primary_reason_code": (
            None
            if snapshot.primary_reason_code is None
            else snapshot.primary_reason_code.value
        ),
        "all_reason_codes": [reason.value for reason in snapshot.all_reason_codes],
        "evaluated_at_utc": snapshot.evaluated_at_utc,
        "risk_age_seconds": _format_age_for_fingerprint(snapshot.risk_age_seconds),
        "buying_power_age_seconds": _format_age_for_fingerprint(
            snapshot.buying_power_age_seconds
        ),
        "phase34_eligibility_fingerprint": snapshot.phase34_eligibility_fingerprint,
        "phase33_verification_fingerprint": snapshot.phase33_verification_fingerprint,
        "phase30_materialization_fingerprint": snapshot.phase30_materialization_fingerprint,
        "source_attempt_ref": snapshot.source_attempt_ref,
        "authorization_evidence_ref": snapshot.authorization_evidence_ref,
        "scope_fingerprint": snapshot.scope_fingerprint,
        "approval_evidence_fingerprint": snapshot.approval_evidence_fingerprint,
        "conformance_evidence_fingerprint": snapshot.conformance_evidence_fingerprint,
        "risk_evidence_fingerprint": snapshot.risk_evidence_fingerprint,
        "buying_power_evidence_fingerprint": snapshot.buying_power_evidence_fingerprint,
        "credential_ownership_evidence_fingerprint":
            snapshot.credential_ownership_evidence_fingerprint,
        "account_ownership_evidence_fingerprint":
            snapshot.account_ownership_evidence_fingerprint,
        "prior_submission_state": (
            snapshot.prior_submission_state.value
            if type(snapshot.prior_submission_state) is _PriorSubmissionState
            else None
        ),
        "prior_attempt_reference": snapshot.prior_attempt_reference,
        "reconciliation_reference": snapshot.reconciliation_reference,
        "reconciliation_required": snapshot.reconciliation_required,
        "provider_send_execution_ready": snapshot.provider_send_execution_ready,
        "transport_authorized": snapshot.transport_authorized,
        "provider_call_performed": snapshot.provider_call_performed,
        "actual_kt10000_post_performed": snapshot.actual_kt10000_post_performed,
        "credential_lookup_performed": snapshot.credential_lookup_performed,
        "account_lookup_performed": snapshot.account_lookup_performed,
        "token_acquisition_performed": snapshot.token_acquisition_performed,
        "automatic_retry_permitted": snapshot.automatic_retry_permitted,
        "retransmission_permitted": snapshot.retransmission_permitted,
    }


def _readiness_fingerprint(
    snapshot: WatchlistOrderProviderSendExecutionReadinessSnapshot,
) -> str:
    return _canonical_sha256(_readiness_envelope(snapshot))


def _add_reason(
    reasons: set[KiwoomOrderProviderSendExecutionReadinessReason],
    reason: KiwoomOrderProviderSendExecutionReadinessReason,
) -> None:
    reasons.add(reason)


def _ordered_reasons(
    reasons: set[KiwoomOrderProviderSendExecutionReadinessReason],
) -> tuple[KiwoomOrderProviderSendExecutionReadinessReason, ...]:
    return tuple(
        sorted(reasons, key=lambda item: _REASON_PRIORITY[item], reverse=True)
    )


def _assert_internal_output(
    snapshot: WatchlistOrderProviderSendExecutionReadinessSnapshot,
) -> None:
    if type(snapshot) is not WatchlistOrderProviderSendExecutionReadinessSnapshot:
        raise AssertionError("PHASE35_INTERNAL_OUTPUT_TYPE_DEFECT")
    if type(snapshot.decision) is not KiwoomOrderProviderSendExecutionReadinessDecision:
        raise AssertionError("PHASE35_INTERNAL_DECISION_DEFECT")
    if (
        snapshot.primary_reason_code is not None
        and type(snapshot.primary_reason_code)
        is not KiwoomOrderProviderSendExecutionReadinessReason
    ):
        raise AssertionError("PHASE35_INTERNAL_PRIMARY_REASON_DEFECT")
    if type(snapshot.all_reason_codes) is not tuple:
        raise AssertionError("PHASE35_INTERNAL_REASON_TUPLE_DEFECT")
    if any(
        type(item) is not KiwoomOrderProviderSendExecutionReadinessReason
        for item in snapshot.all_reason_codes
    ):
        raise AssertionError("PHASE35_INTERNAL_REASON_ITEM_DEFECT")
    if snapshot.primary_reason_code != (
        None if not snapshot.all_reason_codes else snapshot.all_reason_codes[0]
    ):
        raise AssertionError("PHASE35_INTERNAL_REASON_PRECEDENCE_DEFECT")

    flag_values = (
        snapshot.reconciliation_required,
        snapshot.provider_send_execution_ready,
        snapshot.transport_authorized,
        snapshot.provider_call_performed,
        snapshot.actual_kt10000_post_performed,
        snapshot.credential_lookup_performed,
        snapshot.account_lookup_performed,
        snapshot.token_acquisition_performed,
        snapshot.automatic_retry_permitted,
        snapshot.retransmission_permitted,
    )
    if not all(type(value) is bool for value in flag_values):
        raise AssertionError("PHASE35_INTERNAL_FLAG_TYPE_DEFECT")
    if any(
        (
            snapshot.transport_authorized,
            snapshot.provider_call_performed,
            snapshot.actual_kt10000_post_performed,
            snapshot.credential_lookup_performed,
            snapshot.account_lookup_performed,
            snapshot.token_acquisition_performed,
            snapshot.automatic_retry_permitted,
            snapshot.retransmission_permitted,
        )
    ):
        raise AssertionError("PHASE35_INTERNAL_SIDE_EFFECT_FLAG_DEFECT")

    if (
        snapshot.decision
        is KiwoomOrderProviderSendExecutionReadinessDecision.PROVIDER_SEND_EXECUTION_READY
    ):
        if snapshot.primary_reason_code is not None or snapshot.all_reason_codes != ():
            raise AssertionError("PHASE35_INTERNAL_READY_REASON_DEFECT")
        if snapshot.provider_send_execution_ready is not True:
            raise AssertionError("PHASE35_INTERNAL_READY_FLAG_DEFECT")
        if snapshot.reconciliation_required is not False:
            raise AssertionError("PHASE35_INTERNAL_READY_RECONCILIATION_DEFECT")
    else:
        if snapshot.provider_send_execution_ready is not False:
            raise AssertionError("PHASE35_INTERNAL_NONREADY_FLAG_DEFECT")
        if not snapshot.all_reason_codes:
            raise AssertionError("PHASE35_INTERNAL_NONREADY_REASON_DEFECT")

    if not _is_lower_hex_64(snapshot.readiness_fingerprint):
        raise AssertionError("PHASE35_INTERNAL_FINGERPRINT_FORMAT_DEFECT")
    if snapshot.readiness_fingerprint != _readiness_fingerprint(snapshot):
        raise AssertionError("PHASE35_INTERNAL_FINGERPRINT_DEFECT")


def build_demo_watchlist_order_provider_send_execution_readiness_snapshot(
    source_snapshot,
    evidence_bundle,
):
    # 1. exact public input type/arity validation
    if type(source_snapshot) is not _Phase34Snapshot:
        raise WatchlistOrderProviderSendExecutionGateError(
            "PHASE34_SOURCE_SNAPSHOT_TYPE_INVALID"
        )
    if type(evidence_bundle) is not Phase35ProviderSendExecutionEvidenceBundle:
        raise WatchlistOrderProviderSendExecutionGateError(
            "EVIDENCE_BUNDLE_TYPE_INVALID"
        )

    # 2. Phase34 exact type and 21-field structural invariant
    if not _phase34_structure_valid(source_snapshot):
        raise WatchlistOrderProviderSendExecutionGateError(
            "PHASE34_SOURCE_STRUCTURE_INVALID"
        )

    # 3. exact object identity source chain is part of structural validation.

    # 4. Phase34 eligibility fingerprint recomputation.
    # Contractual first-error ordering requires this before the safety matrix.
    if (
        not _is_lower_hex_64(source_snapshot.eligibility_fingerprint)
        or source_snapshot.eligibility_fingerprint
        != _phase34_eligibility_fingerprint(source_snapshot)
    ):
        raise WatchlistOrderProviderSendExecutionGateError(
            "PHASE34_ELIGIBILITY_FINGERPRINT_INVALID"
        )

    # 5. Phase34 decision/safety matrix
    if not _phase34_safety_matrix_valid(source_snapshot):
        raise WatchlistOrderProviderSendExecutionGateError(
            "PHASE34_SOURCE_SAFETY_MATRIX_INVALID"
        )

    reasons: set[KiwoomOrderProviderSendExecutionReadinessReason] = set()
    if source_snapshot.decision is _Phase34Decision.INDETERMINATE:
        _add_reason(
            reasons,
            KiwoomOrderProviderSendExecutionReadinessReason.PHASE34_SOURCE_INDETERMINATE,
        )

    # 6. exact Phase27 prior-submission state/reference invariant
    prior_invariant_valid = _prior_submission_invariant_valid(evidence_bundle)
    if not prior_invariant_valid:
        _add_reason(
            reasons,
            KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED,
        )
    else:
        state = evidence_bundle.prior_submission_state
        if state is _PriorSubmissionState.AMBIGUOUS_UNRESOLVED:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.RECONCILIATION_REQUIRED,
            )
        elif state is _PriorSubmissionState.CONFIRMED_ACCEPTED:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.PRIOR_SUBMISSION_ALREADY_ACCEPTED,
            )
        elif state is _PriorSubmissionState.CONFIRMED_NOT_ACCEPTED:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.FRESH_REAUTHORIZATION_REQUIRED,
            )

    # 7. capture evaluation_time_utc exactly once
    evaluation_time = _utc_now()
    evaluated_at_utc = _canonical_utc_text(evaluation_time)

    evidence_specs = (
        ("approval", evidence_bundle.approval_evidence, Phase35ProviderSendApprovalEvidence),
        ("conformance", evidence_bundle.conformance_evidence, Phase35ProviderSendConformanceEvidence),
        ("risk", evidence_bundle.risk_evidence, Phase35ExecutionRiskFreshnessEvidence),
        ("buying_power", evidence_bundle.buying_power_evidence, Phase35ExecutionBuyingPowerFreshnessEvidence),
        ("credential", evidence_bundle.credential_ownership_evidence, Phase35CredentialOwnershipEvidence),
        ("account", evidence_bundle.account_ownership_evidence, Phase35AccountOwnershipEvidence),
    )

    structural_valid: dict[str, bool] = {}
    trust_valid: dict[str, bool] = {}
    fingerprint_valid: dict[str, bool] = {}

    # 8-10. trust registry, structural checks, independent fingerprint recomputation
    for label, evidence, expected_type in evidence_specs:
        if evidence is None:
            structural_valid[label] = False
            trust_valid[label] = False
            fingerprint_valid[label] = False
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MISSING,
            )
            continue
        if type(evidence) is not expected_type:
            structural_valid[label] = False
            trust_valid[label] = False
            fingerprint_valid[label] = False
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED,
            )
            continue

        trust_valid[label] = _trust_anchor_valid(evidence)
        if not trust_valid[label]:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.TRUST_ANCHOR_UNVERIFIABLE,
            )

        structural_valid[label] = _evidence_structure_valid(evidence)
        if not structural_valid[label]:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED,
            )

        fingerprint_valid[label] = (
            structural_valid[label]
            and evidence.evidence_fingerprint == _evidence_fingerprint(evidence)
        )
        if structural_valid[label] and not fingerprint_valid[label]:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED,
            )

    all_integrity_valid = all(
        structural_valid.get(label, False)
        and trust_valid.get(label, False)
        and fingerprint_valid.get(label, False)
        for label, _, _ in evidence_specs
    )

    credential = evidence_bundle.credential_ownership_evidence
    account = evidence_bundle.account_ownership_evidence

    # 11. Phase35 scope fingerprint recomputation
    expected_scope: str | None = None
    if (
        structural_valid.get("credential", False)
        and structural_valid.get("account", False)
    ):
        expected_scope = _scope_fingerprint(
            source_snapshot,
            credential.credential_ref_id,
            account.account_ref_id,
        )

    # 12. Phase34/Phase30/source-attempt/authorization-evidence binding
    if all_integrity_valid and expected_scope is not None:
        approval = evidence_bundle.approval_evidence
        conformance = evidence_bundle.conformance_evidence
        risk = evidence_bundle.risk_evidence
        buying_power = evidence_bundle.buying_power_evidence

        if (
            approval.phase34_eligibility_fingerprint
            != conformance.phase34_eligibility_fingerprint
            or approval.phase30_materialization_fingerprint
            != conformance.phase30_materialization_fingerprint
            or approval.source_attempt_ref != conformance.source_attempt_ref
            or approval.authorization_evidence_ref
            != conformance.authorization_evidence_ref
        ):
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_CONFLICT,
            )
        else:
            direct_bindings_match = (
                approval.phase34_eligibility_fingerprint
                == source_snapshot.eligibility_fingerprint
                and conformance.phase34_eligibility_fingerprint
                == source_snapshot.eligibility_fingerprint
                and risk.phase34_eligibility_fingerprint
                == source_snapshot.eligibility_fingerprint
                and buying_power.phase34_eligibility_fingerprint
                == source_snapshot.eligibility_fingerprint
                and approval.phase30_materialization_fingerprint
                == source_snapshot.request_snapshot.materialization_fingerprint
                and conformance.phase30_materialization_fingerprint
                == source_snapshot.request_snapshot.materialization_fingerprint
                and risk.phase30_materialization_fingerprint
                == source_snapshot.request_snapshot.materialization_fingerprint
                and buying_power.phase30_materialization_fingerprint
                == source_snapshot.request_snapshot.materialization_fingerprint
                and approval.source_attempt_ref
                == source_snapshot.request_snapshot.source_attempt_ref
                and conformance.source_attempt_ref
                == source_snapshot.request_snapshot.source_attempt_ref
                and risk.source_attempt_ref
                == source_snapshot.request_snapshot.source_attempt_ref
                and buying_power.source_attempt_ref
                == source_snapshot.request_snapshot.source_attempt_ref
                and approval.authorization_evidence_ref
                == source_snapshot.request_snapshot.authorization_evidence_ref
                and conformance.authorization_evidence_ref
                == source_snapshot.request_snapshot.authorization_evidence_ref
                and buying_power.account_ref_id == account.account_ref_id
            )
            scope_bindings_match = all(
                evidence.scope_fingerprint == expected_scope
                for _, evidence, _ in evidence_specs
            )
            if not direct_bindings_match or not scope_bindings_match:
                _add_reason(
                    reasons,
                    KiwoomOrderProviderSendExecutionReadinessReason.SOURCE_BINDING_MISMATCH,
                )

    # 13. demo/transport/credential/account ownership binding
    # Transport validation is source-owned and remains applicable independently
    # of missing/untrusted Phase35 evidence.
    if not _request_target_valid(source_snapshot):
        _add_reason(
            reasons,
            KiwoomOrderProviderSendExecutionReadinessReason.TRANSPORT_BINDING_MISMATCH,
        )

    if all_integrity_valid:
        if credential.environment != "demo" or account.environment != "demo":
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.DEMO_BINDING_MISMATCH,
            )
        if (
            credential.owner_ref != account.account_owner_ref
            or account.bound_credential_ref_id != credential.credential_ref_id
        ):
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.OWNERSHIP_BINDING_MISMATCH,
            )

    # 14. timestamp format/future-skew coherence
    parsed_times: dict[tuple[str, str], _datetime] = {}
    if all_integrity_valid:
        clock_bad = False
        for label, evidence, _ in evidence_specs:
            names = ["issued_at_utc"]
            if hasattr(evidence, "expires_at_utc"):
                names.append("expires_at_utc")
            if hasattr(evidence, "observed_at_utc"):
                names.append("observed_at_utc")
            for name in names:
                parsed = _parse_utc_text(getattr(evidence, name))
                if parsed is None:
                    clock_bad = True
                else:
                    parsed_times[(label, name)] = parsed
            issued = parsed_times.get((label, "issued_at_utc"))
            if (
                issued is not None
                and (issued - evaluation_time).total_seconds()
                > _MAX_FUTURE_CLOCK_SKEW_SECONDS
            ):
                clock_bad = True
        if clock_bad:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.CLOCK_REFERENCE_UNVERIFIABLE,
            )

    # 15. approval/conformance/ownership expiry
    if all_integrity_valid:
        approval_expired = any(
            evaluation_time >= parsed_times[(label, "expires_at_utc")]
            for label in ("approval", "conformance")
        )
        ownership_expired = any(
            evaluation_time >= parsed_times[(label, "expires_at_utc")]
            for label in ("credential", "account")
        )
        if approval_expired:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.APPROVAL_OR_CONFORMANCE_EXPIRED,
            )
        if ownership_expired:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.OWNERSHIP_EVIDENCE_EXPIRED,
            )

    # 16-17. Risk / Buying-Power freshness and decision
    risk_age_seconds: float | None = None
    buying_power_age_seconds: float | None = None
    if all_integrity_valid:
        risk_observed = parsed_times[("risk", "observed_at_utc")]
        buying_observed = parsed_times[("buying_power", "observed_at_utc")]
        risk_age_seconds = (evaluation_time - risk_observed).total_seconds()
        buying_power_age_seconds = (evaluation_time - buying_observed).total_seconds()

        if risk_age_seconds < -_MAX_FUTURE_CLOCK_SKEW_SECONDS:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.CLOCK_REFERENCE_UNVERIFIABLE,
            )
        elif risk_age_seconds > _MAX_RISK_EVIDENCE_AGE_SECONDS:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.RISK_EVIDENCE_STALE,
            )
        elif evidence_bundle.risk_evidence.risk_decision == "RISK_BLOCKED":
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.EXECUTION_RISK_BLOCKED,
            )

        if buying_power_age_seconds < -_MAX_FUTURE_CLOCK_SKEW_SECONDS:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.CLOCK_REFERENCE_UNVERIFIABLE,
            )
        elif buying_power_age_seconds > _MAX_BUYING_POWER_EVIDENCE_AGE_SECONDS:
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.BUYING_POWER_EVIDENCE_STALE,
            )
        elif (
            evidence_bundle.buying_power_evidence.buying_power_decision
            == "BUYING_POWER_INSUFFICIENT"
        ):
            _add_reason(
                reasons,
                KiwoomOrderProviderSendExecutionReadinessReason.BUYING_POWER_INSUFFICIENT,
            )

    # 18. retry/retransmission request checks
    if (
        type(evidence_bundle.automatic_retry_requested) is not bool
        or type(evidence_bundle.retransmission_requested) is not bool
    ):
        _add_reason(
            reasons,
            KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED,
        )
    elif (
        evidence_bundle.automatic_retry_requested is True
        or evidence_bundle.retransmission_requested is True
    ):
        _add_reason(
            reasons,
            KiwoomOrderProviderSendExecutionReadinessReason.RETRY_OR_RETRANSMISSION_REQUESTED,
        )

    # 19. deterministic decision/reason collection
    ordered_reasons = _ordered_reasons(reasons)
    if any(reason in _INDETERMINATE_REASONS for reason in ordered_reasons):
        decision = KiwoomOrderProviderSendExecutionReadinessDecision.INDETERMINATE
    elif ordered_reasons:
        decision = KiwoomOrderProviderSendExecutionReadinessDecision.DENIED
    else:
        decision = (
            KiwoomOrderProviderSendExecutionReadinessDecision.PROVIDER_SEND_EXECUTION_READY
        )

    # 20. output construction
    common = {
        "source_snapshot": source_snapshot,
        "decision": decision,
        "primary_reason_code": None if not ordered_reasons else ordered_reasons[0],
        "all_reason_codes": ordered_reasons,
        "evaluated_at_utc": evaluated_at_utc,
        "risk_age_seconds": risk_age_seconds,
        "buying_power_age_seconds": buying_power_age_seconds,
        "phase34_eligibility_fingerprint": source_snapshot.eligibility_fingerprint,
        "phase33_verification_fingerprint": source_snapshot.source_snapshot.verification_fingerprint,
        "phase30_materialization_fingerprint": source_snapshot.request_snapshot.materialization_fingerprint,
        "source_attempt_ref": source_snapshot.request_snapshot.source_attempt_ref,
        "authorization_evidence_ref": source_snapshot.request_snapshot.authorization_evidence_ref,
        "scope_fingerprint": expected_scope,
        "approval_evidence_fingerprint": _safe_fingerprint(
            getattr(evidence_bundle.approval_evidence, "evidence_fingerprint", None)
        ),
        "conformance_evidence_fingerprint": _safe_fingerprint(
            getattr(evidence_bundle.conformance_evidence, "evidence_fingerprint", None)
        ),
        "risk_evidence_fingerprint": _safe_fingerprint(
            getattr(evidence_bundle.risk_evidence, "evidence_fingerprint", None)
        ),
        "buying_power_evidence_fingerprint": _safe_fingerprint(
            getattr(evidence_bundle.buying_power_evidence, "evidence_fingerprint", None)
        ),
        "credential_ownership_evidence_fingerprint": _safe_fingerprint(
            getattr(
                evidence_bundle.credential_ownership_evidence,
                "evidence_fingerprint",
                None,
            )
        ),
        "account_ownership_evidence_fingerprint": _safe_fingerprint(
            getattr(
                evidence_bundle.account_ownership_evidence,
                "evidence_fingerprint",
                None,
            )
        ),
        "prior_submission_state": (
            evidence_bundle.prior_submission_state
            if type(evidence_bundle.prior_submission_state) is _PriorSubmissionState
            else None
        ),
        "prior_attempt_reference": (
            evidence_bundle.prior_attempt_reference
            if type(evidence_bundle.prior_attempt_reference) is str
            else None
        ),
        "reconciliation_reference": (
            evidence_bundle.reconciliation_reference
            if type(evidence_bundle.reconciliation_reference) is str
            else None
        ),
        "reconciliation_required": (
            evidence_bundle.prior_submission_state
            is _PriorSubmissionState.AMBIGUOUS_UNRESOLVED
        ),
        "provider_send_execution_ready": (
            decision
            is KiwoomOrderProviderSendExecutionReadinessDecision.PROVIDER_SEND_EXECUTION_READY
        ),
        "transport_authorized": False,
        "provider_call_performed": False,
        "actual_kt10000_post_performed": False,
        "credential_lookup_performed": False,
        "account_lookup_performed": False,
        "token_acquisition_performed": False,
        "automatic_retry_permitted": False,
        "retransmission_permitted": False,
    }

    provisional = WatchlistOrderProviderSendExecutionReadinessSnapshot(
        **common,
        readiness_fingerprint="0" * 64,
    )

    # 21. readiness fingerprint recomputation
    snapshot = WatchlistOrderProviderSendExecutionReadinessSnapshot(
        **common,
        readiness_fingerprint=_readiness_fingerprint(provisional),
    )

    # 22. internal output safety assertion
    _assert_internal_output(snapshot)
    return snapshot


for _verifier_id in _VERIFIER_IDS:
    if _VERIFIER_REGISTRY[_verifier_id] != _hashlib.sha256(
        _verifier_id.encode("utf-8")
    ).hexdigest():
        raise AssertionError("PHASE35_INTERNAL_VERIFIER_REGISTRY_DEFECT")
