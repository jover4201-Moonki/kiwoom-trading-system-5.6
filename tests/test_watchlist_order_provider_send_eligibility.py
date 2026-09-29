import ast
import dataclasses
import hashlib
import importlib
import inspect
import json
import re
import sys
import unittest
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

TARGET_MODULE = "kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_provider_send_eligibility"
TARGET_SOURCE = SRC / "kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_provider_send_eligibility.py"
TARGET_TEST = ROOT / "tests/test_watchlist_order_provider_send_eligibility.py"

from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_send_request import (
    WatchlistOrderSendRequestSnapshot,
)
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_authorization_consumption_claim import (
    KiwoomOrderAuthorizationConsumptionClaimContext,
    WatchlistOrderAuthorizationConsumptionClaimSnapshot,
)
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_authorization_adapter_evidence import (
    KiwoomOrderAuthorizationAuthorityReportedResult,
    WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
)
from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_authorization_durable_authority import (
    KiwoomOrderAuthorizationDurableLedgerRecord,
    WatchlistOrderAuthorizationDurableVerificationSnapshot,
)


PUBLIC_SYMBOLS = (
    "WatchlistOrderProviderSendEligibilityError",
    "KiwoomOrderProviderSendEligibilityDecision",
    "KiwoomOrderProviderSendEligibilityIndeterminateReason",
    "WatchlistOrderProviderSendEligibilityCandidateSnapshot",
    "build_demo_watchlist_order_provider_send_eligibility_candidate_snapshot",
)

PUBLIC_ERROR_CODES = (
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

UPSTREAM_HASHES = {
    "src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_send_request.py": "5a1cd94d50ff850b9453986ceb322f674f864e2369c7edd61439c3a50ff9b4cf",
    "tests/test_watchlist_order_send_request.py": "ea2424186baef0b6da5fc2c8e590001dfce2ccb4868b9aa5f70e5831d8292173",
    "src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_authorization_consumption_claim.py": "6190d9831c93d1567aa0add07a3b64253097eed904d79ef43f9536ff70070dbc",
    "tests/test_watchlist_order_authorization_consumption_claim.py": "cb480f3dbceb172a28cf58e4c9323d6760392b1cd0c8912ca7241203dcf2d8bd",
    "src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_authorization_adapter_evidence.py": "23097e2fb7eec16659be2ef5e5f1c7f0ce2d0431b79553bc9f5aa93a66a090e6",
    "tests/test_watchlist_order_authorization_adapter_evidence.py": "b7534d9842039ce2c56458b45e9b9f53384cc1aa28f61b34bd757d4ddd895bde",
    "src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_authorization_durable_authority.py": "b8b4f4b6cc7b69dd6f3766a4588c7bce1161b744fe5471700bbca068925f60ac",
    "tests/test_watchlist_order_authorization_durable_authority.py": "0481dca2db6b6240789e69bf32cc6a1f20dbab1ec2c34fae6e59b57fb6fb31d4",
}

SNAPSHOT_FIELDS = (
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

ELIGIBILITY_KEYS = {
    "domain",
    "phase33_verification_fingerprint",
    "phase32_evidence_fingerprint",
    "phase31_claim_fingerprint",
    "phase30_materialization_fingerprint",
    "source_attempt_ref",
    "authorization_evidence_ref",
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
}


class StrSubclass(str):
    pass


class ExplodingMapping(Mapping):
    def __init__(self, exc_type):
        self.exc_type = exc_type

    def __len__(self):
        return 6

    def __iter__(self):
        raise self.exc_type("boom")

    def __getitem__(self, key):
        raise self.exc_type("boom")

    def keys(self):
        raise self.exc_type("boom")

    def values(self):
        raise self.exc_type("boom")


class RuntimeExplodingMapping(ExplodingMapping):
    def __init__(self):
        super().__init__(RuntimeError)


def _subject():
    try:
        return importlib.import_module(TARGET_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name == TARGET_MODULE:
            raise AssertionError("PHASE34_SOURCE_MISSING_EXPECTED_RED") from exc
        raise


def _canonical_sha(envelope):
    raw = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _phase30_fp(request):
    return _canonical_sha(
        {
            "environment": request.environment,
            "side": request.side,
            "exchange": request.exchange,
            "api_id": request.api_id,
            "http_method": request.http_method,
            "api_path": request.api_path,
            "body": dict(request.body),
            "source_attempt_ref": request.source_attempt_ref,
            "authorization_evidence_ref": request.authorization_evidence_ref,
        }
    )


def _phase31_fp(request, identity, replay):
    return _canonical_sha(
        {
            "materialization_fingerprint": request.materialization_fingerprint,
            "authorization_claim_identity": identity,
            "authorization_replay_guard": replay,
        }
    )


def _phase32_fp(snapshot):
    phase31 = snapshot.source_snapshot
    return _canonical_sha(
        {
            "claim_fingerprint": phase31.claim_fingerprint,
            "asserted_authority_approval_reference": snapshot.asserted_authority_approval_reference,
            "asserted_authority_conformance_reference": snapshot.asserted_authority_conformance_reference,
            "decision": snapshot.decision,
            "block_reason": snapshot.block_reason,
            "indeterminate_reason": snapshot.indeterminate_reason,
            "authority_result_reference": snapshot.authority_result_reference,
            "consumption_reference": snapshot.consumption_reference,
            "authority_reported_authorization_consumption_committed": snapshot.authority_reported_authorization_consumption_committed,
            "authority_reported_replay_guard_consumption_committed": snapshot.authority_reported_replay_guard_consumption_committed,
            "commit_state_known": snapshot.commit_state_known,
            "consumption_evidence_candidate_ready": snapshot.consumption_evidence_candidate_ready,
            "authority_trust_independently_verified": snapshot.authority_trust_independently_verified,
            "automatic_retry_permitted": snapshot.automatic_retry_permitted,
            "reconciliation_required": snapshot.reconciliation_required,
            "authority_invocation_attempted": snapshot.authority_invocation_attempted,
            "phase32_direct_credential_accessed": snapshot.phase32_direct_credential_accessed,
            "phase32_direct_network_performed": snapshot.phase32_direct_network_performed,
            "phase32_direct_account_accessed": snapshot.phase32_direct_account_accessed,
            "phase32_direct_order_submitted": snapshot.phase32_direct_order_submitted,
        }
    )


def _authority_result_ref(*, backend, identity, replay, claim_fp, approval, conformance):
    return "phase33-result-" + _canonical_sha(
        {
            "domain": "phase33-authority-result-v1",
            "schema_id": "kiwoom-watchlist-order-authorization-durable-ledger-v1",
            "transaction_profile_id": "sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1",
            "durability_profile_id": "sqlite-main-wal-synchronous-full-v1",
            "backend_instance_reference": backend,
            "authorization_claim_identity": identity,
            "authorization_replay_guard": replay,
            "claim_fingerprint": claim_fp,
            "authority_approval_reference": approval,
            "authority_conformance_reference": conformance,
        }
    )


def _consumption_ref(*, backend, identity, replay, claim_fp, approval, conformance, result_ref):
    return "phase33-consume-" + _canonical_sha(
        {
            "domain": "phase33-consumption-v1",
            "schema_id": "kiwoom-watchlist-order-authorization-durable-ledger-v1",
            "transaction_profile_id": "sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1",
            "durability_profile_id": "sqlite-main-wal-synchronous-full-v1",
            "backend_instance_reference": backend,
            "authorization_claim_identity": identity,
            "authorization_replay_guard": replay,
            "claim_fingerprint": claim_fp,
            "authority_approval_reference": approval,
            "authority_conformance_reference": conformance,
            "authority_result_reference": result_ref,
        }
    )


def _record_fp(record):
    return _canonical_sha(
        {
            "domain": "phase33-durable-record-v1",
            "schema_id": "kiwoom-watchlist-order-authorization-durable-ledger-v1",
            "transaction_profile_id": "sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1",
            "durability_profile_id": "sqlite-main-wal-synchronous-full-v1",
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


def _phase33_fp(snapshot):
    durable_fp = None if snapshot.durable_record is None else snapshot.durable_record.record_fingerprint
    return _canonical_sha(
        {
            "domain": "phase33-local-durable-verification-v1",
            "source_evidence_fingerprint": snapshot.source_snapshot.evidence_fingerprint,
            "durable_record_fingerprint": durable_fp,
            "backend_instance_reference": snapshot.backend_instance_reference,
            "ledger_schema_reference": "kiwoom-watchlist-order-authorization-durable-ledger-v1",
            "verification_decision": snapshot.verification_decision,
            "indeterminate_reason": snapshot.indeterminate_reason,
            "concrete_sqlite_authority_identity_verified": snapshot.concrete_sqlite_authority_identity_verified,
            "ledger_schema_verified": snapshot.ledger_schema_verified,
            "sqlite_connection_surface_verified": snapshot.sqlite_connection_surface_verified,
            "sqlite_durability_profile_verified": snapshot.sqlite_durability_profile_verified,
            "durable_record_present": snapshot.durable_record_present,
            "exact_binding_verified": snapshot.exact_binding_verified,
            "durable_consumption_record_verified": snapshot.durable_consumption_record_verified,
            "authority_approval_provenance_verified": snapshot.authority_approval_provenance_verified,
            "authority_conformance_provenance_verified": snapshot.authority_conformance_provenance_verified,
            "provider_send_eligibility_authorized": snapshot.provider_send_eligibility_authorized,
            "production_authority_use_authorized": snapshot.production_authority_use_authorized,
            "reconciliation_required": snapshot.reconciliation_required,
        }
    )


def _make_request(**overrides):
    values = {
        "environment": "demo",
        "side": "BUY",
        "exchange": "KRX",
        "api_id": "kt10000",
        "http_method": "POST",
        "api_path": "/api/dostk/ordr",
        "body": MappingProxyType(
            {
                "dmst_stex_tp": "KRX",
                "stk_cd": "005930",
                "ord_qty": "3",
                "ord_uv": "64500",
                "trde_tp": "0",
                "cond_uv": "",
            }
        ),
        "source_attempt_ref": "attempt-1",
        "authorization_evidence_ref": "snapshot-1",
        "materialization_fingerprint": "0" * 64,
        "transport_allowed": False,
        "credential_accessed": False,
        "network_performed": False,
        "account_accessed": False,
        "order_submitted": False,
    }
    values.update(overrides)
    request = WatchlistOrderSendRequestSnapshot(**values)
    if "materialization_fingerprint" not in overrides:
        request = replace(request, materialization_fingerprint=_phase30_fp(request))
    return request


def _make_context(**overrides):
    values = {
        "authorization_authority_reference": "authority-1",
        "authorization_evidence_snapshot_id": "snapshot-1",
        "submission_attempt_reference": "attempt-1",
        "send_authorization_reference": "send-auth-1",
    }
    values.update(overrides)
    return KiwoomOrderAuthorizationConsumptionClaimContext(**values)


def _make_phase31(request=None, context=None, **overrides):
    request = request or _make_request()
    context = context or _make_context(
        authorization_evidence_snapshot_id=request.authorization_evidence_ref,
        submission_attempt_reference=request.source_attempt_ref,
    )
    identity = (
        context.authorization_authority_reference,
        context.authorization_evidence_snapshot_id,
        context.submission_attempt_reference,
        context.send_authorization_reference,
    )
    replay = (
        context.authorization_authority_reference,
        context.send_authorization_reference,
    )
    values = {
        "source_snapshot": request,
        "context": context,
        "authorization_claim_identity": identity,
        "authorization_replay_guard": replay,
        "claim_fingerprint": _phase31_fp(request, identity, replay),
        "claim_prepared": True,
        "authorization_consumption_committed": False,
        "post_permitted": False,
        "automatic_retry_permitted": False,
        "network_performed": False,
        "order_submitted": False,
    }
    values.update(overrides)
    return WatchlistOrderAuthorizationConsumptionClaimSnapshot(**values)


def _make_phase32(phase31=None, backend="backend-1", approval="approval-1", conformance="conformance-1", **overrides):
    phase31 = phase31 or _make_phase31()
    result_ref = _authority_result_ref(
        backend=backend,
        identity=phase31.authorization_claim_identity,
        replay=phase31.authorization_replay_guard,
        claim_fp=phase31.claim_fingerprint,
        approval=approval,
        conformance=conformance,
    )
    consume_ref = _consumption_ref(
        backend=backend,
        identity=phase31.authorization_claim_identity,
        replay=phase31.authorization_replay_guard,
        claim_fp=phase31.claim_fingerprint,
        approval=approval,
        conformance=conformance,
        result_ref=result_ref,
    )
    authority_result = KiwoomOrderAuthorizationAuthorityReportedResult(
        authorization_claim_identity=phase31.authorization_claim_identity,
        authorization_replay_guard=phase31.authorization_replay_guard,
        claim_fingerprint=phase31.claim_fingerprint,
        asserted_authority_approval_reference=approval,
        asserted_authority_conformance_reference=conformance,
        authority_result_reference=result_ref,
        decision="AUTHORITY_REPORTED_CONSUMED",
        block_reason=None,
        indeterminate_reason=None,
        consumption_reference=consume_ref,
        authority_reported_authorization_consumption_committed=True,
        authority_reported_replay_guard_consumption_committed=True,
        commit_state_known=True,
    )
    values = {
        "source_snapshot": phase31,
        "asserted_authority_approval_reference": approval,
        "asserted_authority_conformance_reference": conformance,
        "authority_result": authority_result,
        "decision": "AUTHORITY_REPORTED_CONSUMED",
        "block_reason": None,
        "indeterminate_reason": None,
        "authority_result_reference": result_ref,
        "consumption_reference": consume_ref,
        "evidence_fingerprint": "0" * 64,
        "authority_reported_authorization_consumption_committed": True,
        "authority_reported_replay_guard_consumption_committed": True,
        "commit_state_known": True,
        "consumption_evidence_candidate_ready": True,
        "authority_trust_independently_verified": False,
        "automatic_retry_permitted": False,
        "reconciliation_required": False,
        "authority_invocation_attempted": True,
        "phase32_direct_credential_accessed": False,
        "phase32_direct_network_performed": False,
        "phase32_direct_account_accessed": False,
        "phase32_direct_order_submitted": False,
    }
    values.update(overrides)
    snapshot = WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot(**values)
    if "evidence_fingerprint" not in overrides:
        snapshot = replace(snapshot, evidence_fingerprint=_phase32_fp(snapshot))
    return snapshot


def _make_record(phase32, backend="backend-1", **overrides):
    phase31 = phase32.source_snapshot
    context = phase31.context
    values = {
        "backend_instance_reference": backend,
        "authorization_authority_reference": context.authorization_authority_reference,
        "authorization_evidence_snapshot_id": context.authorization_evidence_snapshot_id,
        "submission_attempt_reference": context.submission_attempt_reference,
        "send_authorization_reference": context.send_authorization_reference,
        "claim_fingerprint": phase31.claim_fingerprint,
        "authority_approval_reference": phase32.asserted_authority_approval_reference,
        "authority_conformance_reference": phase32.asserted_authority_conformance_reference,
        "authority_result_reference": phase32.authority_result_reference,
        "consumption_reference": phase32.consumption_reference,
        "sqlite_journal_mode": "wal",
        "sqlite_synchronous_level": 2,
        "record_fingerprint": "0" * 64,
    }
    values.update(overrides)
    record = KiwoomOrderAuthorizationDurableLedgerRecord(**values)
    if "record_fingerprint" not in overrides:
        record = replace(record, record_fingerprint=_record_fp(record))
    return record


def _self_consistent_record(phase32, *, backend="backend-1", **field_overrides):
    phase31 = phase32.source_snapshot
    context = phase31.context
    auth = field_overrides.get("authorization_authority_reference", context.authorization_authority_reference)
    evidence = field_overrides.get("authorization_evidence_snapshot_id", context.authorization_evidence_snapshot_id)
    attempt = field_overrides.get("submission_attempt_reference", context.submission_attempt_reference)
    send = field_overrides.get("send_authorization_reference", context.send_authorization_reference)
    claim = field_overrides.get("claim_fingerprint", phase31.claim_fingerprint)
    approval = field_overrides.get("authority_approval_reference", phase32.asserted_authority_approval_reference)
    conformance = field_overrides.get("authority_conformance_reference", phase32.asserted_authority_conformance_reference)
    identity = (auth, evidence, attempt, send)
    replay = (auth, send)
    result_ref = _authority_result_ref(
        backend=field_overrides.get("backend_instance_reference", backend),
        identity=identity,
        replay=replay,
        claim_fp=claim,
        approval=approval,
        conformance=conformance,
    )
    consume_ref = _consumption_ref(
        backend=field_overrides.get("backend_instance_reference", backend),
        identity=identity,
        replay=replay,
        claim_fp=claim,
        approval=approval,
        conformance=conformance,
        result_ref=result_ref,
    )
    values = {
        "backend_instance_reference": backend,
        "authorization_authority_reference": auth,
        "authorization_evidence_snapshot_id": evidence,
        "submission_attempt_reference": attempt,
        "send_authorization_reference": send,
        "claim_fingerprint": claim,
        "authority_approval_reference": approval,
        "authority_conformance_reference": conformance,
        "authority_result_reference": result_ref,
        "consumption_reference": consume_ref,
        "sqlite_journal_mode": "wal",
        "sqlite_synchronous_level": 2,
        "record_fingerprint": "0" * 64,
    }
    values.update(field_overrides)
    record = KiwoomOrderAuthorizationDurableLedgerRecord(**values)
    return replace(record, record_fingerprint=_record_fp(record))


def _make_phase33(*, success=True, request=None, phase31=None, phase32=None, record=None, backend="backend-1", reason="LEDGER_RECORD_NOT_FOUND", **overrides):
    if phase31 is None:
        phase31 = _make_phase31(request=request)
    if phase32 is None:
        phase32 = _make_phase32(phase31=phase31, backend=backend)
    if success:
        if record is None:
            record = _make_record(phase32, backend=backend)
        values = {
            "source_snapshot": phase32,
            "durable_record": record,
            "backend_instance_reference": backend,
            "ledger_schema_reference": "kiwoom-watchlist-order-authorization-durable-ledger-v1",
            "verification_decision": "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED",
            "indeterminate_reason": None,
            "concrete_sqlite_authority_identity_verified": True,
            "ledger_schema_verified": True,
            "sqlite_connection_surface_verified": True,
            "sqlite_durability_profile_verified": True,
            "durable_record_present": True,
            "exact_binding_verified": True,
            "durable_consumption_record_verified": True,
            "authority_approval_provenance_verified": False,
            "authority_conformance_provenance_verified": False,
            "provider_send_eligibility_authorized": False,
            "production_authority_use_authorized": False,
            "reconciliation_required": False,
            "verification_fingerprint": "0" * 64,
        }
    else:
        values = {
            "source_snapshot": phase32,
            "durable_record": None,
            "backend_instance_reference": backend,
            "ledger_schema_reference": "kiwoom-watchlist-order-authorization-durable-ledger-v1",
            "verification_decision": "INDETERMINATE",
            "indeterminate_reason": reason,
            "concrete_sqlite_authority_identity_verified": False,
            "ledger_schema_verified": False,
            "sqlite_connection_surface_verified": False,
            "sqlite_durability_profile_verified": False,
            "durable_record_present": False,
            "exact_binding_verified": False,
            "durable_consumption_record_verified": False,
            "authority_approval_provenance_verified": False,
            "authority_conformance_provenance_verified": False,
            "provider_send_eligibility_authorized": False,
            "production_authority_use_authorized": False,
            "reconciliation_required": True,
            "verification_fingerprint": "0" * 64,
        }
    values.update(overrides)
    snapshot = WatchlistOrderAuthorizationDurableVerificationSnapshot(**values)
    if "verification_fingerprint" not in overrides:
        snapshot = replace(snapshot, verification_fingerprint=_phase33_fp(snapshot))
    return snapshot


def _build(subject, source):
    return subject.build_demo_watchlist_order_provider_send_eligibility_candidate_snapshot(source)


def _assert_error(tc, subject, source, code):
    with tc.assertRaises(subject.WatchlistOrderProviderSendEligibilityError) as caught:
        _build(subject, source)
    tc.assertEqual(str(caught.exception), code)


def _source_text():
    return TARGET_SOURCE.read_text(encoding="utf-8")


def _source_tree():
    return ast.parse(_source_text(), filename=str(TARGET_SOURCE))


def _replace_phase32_in_phase33(source, phase32):
    return replace(source, source_snapshot=phase32)


def _replace_phase31_in_phase33(source, phase31):
    phase32 = replace(source.source_snapshot, source_snapshot=phase31)
    return replace(source, source_snapshot=phase32)


def _replace_request_in_phase33(source, request):
    phase31 = replace(source.source_snapshot.source_snapshot, source_snapshot=request)
    return _replace_phase31_in_phase33(source, phase31)


def _expected_output_fingerprint(output):
    envelope = {
        "domain": "phase34-provider-send-eligibility-candidate-v1",
        "phase33_verification_fingerprint": output.source_snapshot.verification_fingerprint,
        "phase32_evidence_fingerprint": output.source_snapshot.source_snapshot.evidence_fingerprint,
        "phase31_claim_fingerprint": output.source_snapshot.source_snapshot.source_snapshot.claim_fingerprint,
        "phase30_materialization_fingerprint": output.request_snapshot.materialization_fingerprint,
        "source_attempt_ref": output.request_snapshot.source_attempt_ref,
        "authorization_evidence_ref": output.request_snapshot.authorization_evidence_ref,
        "decision": output.decision.value,
        "indeterminate_reason": None if output.indeterminate_reason is None else output.indeterminate_reason.value,
        "request_materialization_verified": output.request_materialization_verified,
        "authorization_claim_binding_verified": output.authorization_claim_binding_verified,
        "durable_consumption_verified": output.durable_consumption_verified,
        "provider_request_contract_verified": output.provider_request_contract_verified,
        "authority_approval_provenance_verified": output.authority_approval_provenance_verified,
        "authority_conformance_provenance_verified": output.authority_conformance_provenance_verified,
        "provider_send_eligibility_candidate_ready": output.provider_send_eligibility_candidate_ready,
        "provider_send_eligibility_authorized": output.provider_send_eligibility_authorized,
        "production_authority_use_authorized": output.production_authority_use_authorized,
        "transport_allowed": output.transport_allowed,
        "credential_accessed": output.credential_accessed,
        "network_performed": output.network_performed,
        "account_accessed": output.account_accessed,
        "order_submitted": output.order_submitted,
        "automatic_retry_permitted": output.automatic_retry_permitted,
        "reconciliation_required": output.reconciliation_required,
    }
    return _canonical_sha(envelope)


def _check_success_matrix(tc, subject):
    source = _make_phase33(success=True)
    output = _build(subject, source)
    tc.assertIs(output.source_snapshot, source)
    tc.assertIs(output.request_snapshot, source.source_snapshot.source_snapshot.source_snapshot)
    tc.assertIs(output.decision, subject.KiwoomOrderProviderSendEligibilityDecision.PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY)
    tc.assertIsNone(output.indeterminate_reason)
    tc.assertIs(output.request_materialization_verified, True)
    tc.assertIs(output.authorization_claim_binding_verified, True)
    tc.assertIs(output.durable_consumption_verified, True)
    tc.assertIs(output.provider_request_contract_verified, True)
    tc.assertIs(output.authority_approval_provenance_verified, False)
    tc.assertIs(output.authority_conformance_provenance_verified, False)
    tc.assertIs(output.provider_send_eligibility_candidate_ready, True)
    for name in (
        "provider_send_eligibility_authorized",
        "production_authority_use_authorized",
        "transport_allowed",
        "credential_accessed",
        "network_performed",
        "account_accessed",
        "order_submitted",
        "automatic_retry_permitted",
        "reconciliation_required",
    ):
        tc.assertIs(getattr(output, name), False, name)
    tc.assertRegex(output.eligibility_fingerprint, r"^[0-9a-f]{64}$")
    tc.assertEqual(output.eligibility_fingerprint, _expected_output_fingerprint(output))


def _check_indeterminate_matrix(tc, subject):
    source = _make_phase33(success=False)
    output = _build(subject, source)
    tc.assertIs(output.source_snapshot, source)
    tc.assertIs(output.request_snapshot, source.source_snapshot.source_snapshot.source_snapshot)
    tc.assertIs(output.decision, subject.KiwoomOrderProviderSendEligibilityDecision.INDETERMINATE)
    tc.assertIs(
        output.indeterminate_reason,
        subject.KiwoomOrderProviderSendEligibilityIndeterminateReason.SOURCE_DURABLE_VERIFICATION_INDETERMINATE,
    )
    tc.assertIs(output.request_materialization_verified, True)
    tc.assertIs(output.authorization_claim_binding_verified, True)
    tc.assertIs(output.durable_consumption_verified, False)
    tc.assertIs(output.provider_request_contract_verified, True)
    tc.assertIs(output.authority_approval_provenance_verified, False)
    tc.assertIs(output.authority_conformance_provenance_verified, False)
    tc.assertIs(output.provider_send_eligibility_candidate_ready, False)
    for name in (
        "provider_send_eligibility_authorized",
        "production_authority_use_authorized",
        "transport_allowed",
        "credential_accessed",
        "network_performed",
        "account_accessed",
        "order_submitted",
        "automatic_retry_permitted",
    ):
        tc.assertIs(getattr(output, name), False, name)
    tc.assertIs(output.reconciliation_required, True)
    tc.assertEqual(output.eligibility_fingerprint, _expected_output_fingerprint(output))


def _check_error_case(tc, subject, ac):
    source = _make_phase33(success=True)
    if ac == 85:
        _assert_error(tc, subject, object(), "SOURCE_SNAPSHOT_TYPE_INVALID")
    elif ac == 86:
        _assert_error(tc, subject, replace(source, verification_decision=StrSubclass(source.verification_decision)), "PHASE33_DECISION_INVALID")
    elif ac == 87:
        _assert_error(tc, subject, replace(source, source_snapshot=object()), "PHASE32_SOURCE_SNAPSHOT_TYPE_INVALID")
    elif ac == 88:
        phase32 = replace(source.source_snapshot, source_snapshot=object())
        _assert_error(tc, subject, replace(source, source_snapshot=phase32), "PHASE31_SOURCE_SNAPSHOT_TYPE_INVALID")
    elif ac == 89:
        phase31 = replace(source.source_snapshot.source_snapshot, context=object())
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_CONTEXT_TYPE_INVALID")
    elif ac == 90:
        phase31 = replace(source.source_snapshot.source_snapshot, source_snapshot=object())
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE30_REQUEST_SNAPSHOT_TYPE_INVALID")
    elif ac == 91:
        _assert_error(tc, subject, replace(source, reconciliation_required=True), "PHASE33_STATE_INVARIANT_INVALID")
    elif ac == 92:
        phase32 = replace(source.source_snapshot, decision="AUTHORITY_REPORTED_BLOCKED")
        _assert_error(tc, subject, replace(source, source_snapshot=phase32), "PHASE32_STATE_OR_RESULT_INVALID")
    elif ac == 93:
        phase31 = replace(source.source_snapshot.source_snapshot, claim_prepared=False)
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_STATE_OR_REFERENCE_INVALID")
    elif ac == 94:
        phase31 = replace(source.source_snapshot.source_snapshot, authorization_claim_identity=("x", "y", "z", "w"))
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_CLAIM_IDENTITY_INVALID")
    elif ac == 95:
        phase31 = replace(source.source_snapshot.source_snapshot, authorization_replay_guard=("x", "y"))
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_REPLAY_GUARD_INVALID")
    elif ac == 96:
        request = replace(source.source_snapshot.source_snapshot.source_snapshot, body={"dmst_stex_tp": "KRX"})
        _assert_error(tc, subject, _replace_request_in_phase33(source, request), "PHASE30_REQUEST_STRUCTURE_INVALID")
    elif ac == 97:
        request = replace(source.source_snapshot.source_snapshot.source_snapshot, transport_allowed=0)
        _assert_error(tc, subject, _replace_request_in_phase33(source, request), "PHASE30_REQUEST_SAFETY_INVALID")
    elif ac == 98:
        phase31 = source.source_snapshot.source_snapshot
        context = replace(phase31.context, submission_attempt_reference="attempt-other")
        identity = (
            context.authorization_authority_reference,
            context.authorization_evidence_snapshot_id,
            context.submission_attempt_reference,
            context.send_authorization_reference,
        )
        phase31 = replace(phase31, context=context, authorization_claim_identity=identity)
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE30_CONTEXT_BINDING_INVALID")
    elif ac == 99:
        request = replace(source.source_snapshot.source_snapshot.source_snapshot, materialization_fingerprint="0" * 64)
        _assert_error(tc, subject, _replace_request_in_phase33(source, request), "PHASE30_MATERIALIZATION_FINGERPRINT_INVALID")
    elif ac == 100:
        phase31 = replace(source.source_snapshot.source_snapshot, claim_fingerprint="0" * 64)
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_CLAIM_FINGERPRINT_INVALID")
    elif ac == 101:
        ar = replace(source.source_snapshot.authority_result, decision=StrSubclass("AUTHORITY_REPORTED_CONSUMED"))
        phase32 = replace(source.source_snapshot, authority_result=ar)
        _assert_error(tc, subject, replace(source, source_snapshot=phase32), "PHASE32_AUTHORITY_RESULT_BINDING_INVALID")
    elif ac == 102:
        phase32 = replace(source.source_snapshot, evidence_fingerprint="0" * 64)
        _assert_error(tc, subject, replace(source, source_snapshot=phase32), "PHASE32_EVIDENCE_FINGERPRINT_INVALID")
    elif ac == 103:
        record = replace(source.durable_record, sqlite_synchronous_level=True)
        _assert_error(tc, subject, replace(source, durable_record=record), "PHASE33_DURABLE_RECORD_STRUCTURE_INVALID")
    elif ac == 104:
        record = replace(source.durable_record, record_fingerprint="0" * 64)
        _assert_error(tc, subject, replace(source, durable_record=record), "PHASE33_DURABLE_RECORD_FINGERPRINT_INVALID")
    elif ac == 105:
        record = replace(source.durable_record, authority_result_reference="phase33-result-" + "1" * 64)
        record = replace(record, record_fingerprint=_record_fp(record))
        _assert_error(tc, subject, replace(source, durable_record=record), "PHASE33_DURABLE_RECORD_REFERENCE_SELF_BINDING_INVALID")
    elif ac == 106:
        record = _self_consistent_record(source.source_snapshot, authorization_evidence_snapshot_id="snapshot-cross-bound")
        _assert_error(tc, subject, replace(source, durable_record=record), "PHASE33_DURABLE_RECORD_SOURCE_BINDING_INVALID")
    elif ac == 107:
        _assert_error(tc, subject, replace(source, verification_fingerprint="0" * 64), "PHASE33_VERIFICATION_FINGERPRINT_INVALID")
    elif ac == 108:
        request = _make_request(environment="prod")
        phase31 = _make_phase31(request=request)
        phase32 = _make_phase32(phase31=phase31)
        record = _make_record(phase32)
        source2 = _make_phase33(phase31=phase31, phase32=phase32, record=record)
        _assert_error(tc, subject, source2, "PROVIDER_REQUEST_CONTRACT_INVALID")
    else:
        raise AssertionError(f"unhandled error ac={ac}")


def _run_ac(tc, ac):
    subject = _subject()

    if ac == 1:
        tc.assertEqual(tuple(subject.__all__), PUBLIC_SYMBOLS)
        public_names = tuple(name for name in vars(subject) if not name.startswith("_") and name != "__builtins__")
        tc.assertEqual(public_names, PUBLIC_SYMBOLS)
        return
    if ac == 2:
        tc.assertEqual(subject.WatchlistOrderProviderSendEligibilityError.__bases__, (RuntimeError,))
        return
    if ac in (3, 4):
        enum_cls = subject.KiwoomOrderProviderSendEligibilityDecision
        tc.assertEqual(enum_cls.__bases__[0], str)
        tc.assertEqual(tuple((m.name, m.value) for m in enum_cls), (
            ("PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY", "PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY"),
            ("INDETERMINATE", "INDETERMINATE"),
        ))
        return
    if ac == 5:
        enum_cls = subject.KiwoomOrderProviderSendEligibilityIndeterminateReason
        tc.assertEqual(tuple((m.name, m.value) for m in enum_cls), (("SOURCE_DURABLE_VERIFICATION_INDETERMINATE", "SOURCE_DURABLE_VERIFICATION_INDETERMINATE"),))
        return
    if ac == 6:
        cls = subject.WatchlistOrderProviderSendEligibilityCandidateSnapshot
        tc.assertEqual(tuple(f.name for f in dataclasses.fields(cls)), SNAPSHOT_FIELDS)
        tc.assertEqual(cls.__dataclass_params__.frozen, True)
        return
    if ac == 7:
        source = _make_phase33(success=False)
        _assert_error(tc, subject, replace(source, reconciliation_required=1), "PHASE33_STATE_INVARIANT_INVALID")
        return
    if ac == 8:
        sig = inspect.signature(subject.build_demo_watchlist_order_provider_send_eligibility_candidate_snapshot)
        tc.assertEqual(tuple(sig.parameters), ("source_snapshot",))
        parameter = sig.parameters["source_snapshot"]
        tc.assertIs(parameter.annotation, WatchlistOrderAuthorizationDurableVerificationSnapshot)
        tc.assertIs(parameter.default, inspect.Parameter.empty)
        tc.assertIs(sig.return_annotation, subject.WatchlistOrderProviderSendEligibilityCandidateSnapshot)
        tc.assertFalse(inspect.iscoroutinefunction(subject.build_demo_watchlist_order_provider_send_eligibility_candidate_snapshot))
        return

    if ac in (9, 18, 49, 51, 54, 55, 56, 57, 58, 59, 60, 61, 62, 64):
        _check_success_matrix(tc, subject)
        return
    if ac in (12, 50, 52, 53, 63, 65):
        _check_indeterminate_matrix(tc, subject)
        return
    if ac == 10:
        _check_success_matrix(tc, subject)
        _assert_error(tc, subject, replace(_make_phase33(), verification_decision=StrSubclass("LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED")), "PHASE33_DECISION_INVALID")
        return
    if ac == 11:
        _assert_error(tc, subject, replace(_make_phase33(), durable_record_present=False), "PHASE33_STATE_INVARIANT_INVALID")
        return
    if ac == 13:
        tc.assertEqual(tuple(f.name for f in dataclasses.fields(KiwoomOrderAuthorizationDurableLedgerRecord)), (
            "backend_instance_reference", "authorization_authority_reference", "authorization_evidence_snapshot_id",
            "submission_attempt_reference", "send_authorization_reference", "claim_fingerprint",
            "authority_approval_reference", "authority_conformance_reference", "authority_result_reference",
            "consumption_reference", "sqlite_journal_mode", "sqlite_synchronous_level", "record_fingerprint",
        ))
        _check_error_case(tc, subject, 103)
        return
    if ac == 14:
        _check_error_case(tc, subject, 104)
        return
    if ac == 15:
        _check_error_case(tc, subject, 105)
        return
    if ac in (16, 17):
        _check_error_case(tc, subject, 106)
        return

    if ac == 19:
        _check_error_case(tc, subject, 87)
        return
    if ac == 20:
        _check_error_case(tc, subject, 92)
        return
    if ac == 21:
        _check_error_case(tc, subject, 101)
        return
    if ac == 22:
        _check_error_case(tc, subject, 102)
        return

    if ac == 23:
        _check_error_case(tc, subject, 88)
        return
    if ac == 24:
        _check_error_case(tc, subject, 89)
        return
    if ac == 25:
        source = _make_phase33()
        phase31 = replace(source.source_snapshot.source_snapshot, authorization_claim_identity=["a", "b", "c", "d"])
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_STATE_OR_REFERENCE_INVALID")
        return
    if ac == 26:
        _check_error_case(tc, subject, 93)
        return
    if ac in (27, 30):
        source = _make_phase33()
        ctx = replace(source.source_snapshot.source_snapshot.context, authorization_authority_reference="   ")
        phase31 = replace(source.source_snapshot.source_snapshot, context=ctx)
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_STATE_OR_REFERENCE_INVALID")
        return
    if ac in (28, 29):
        source = _make_phase33()
        ctx = replace(source.source_snapshot.source_snapshot.context, authorization_evidence_snapshot_id="bad\x00ref")
        phase31 = replace(source.source_snapshot.source_snapshot, context=ctx)
        _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_STATE_OR_REFERENCE_INVALID")
        return
    if ac == 31:
        _check_error_case(tc, subject, 94)
        return
    if ac == 32:
        _check_error_case(tc, subject, 95)
        return
    if ac in (33, 34):
        _check_error_case(tc, subject, 98)
        return
    if ac == 35:
        _check_error_case(tc, subject, 100)
        return
    if ac == 36:
        request = _make_request(source_attempt_ref="Attempt-X", authorization_evidence_ref="Snapshot-X")
        context = _make_context(authorization_evidence_snapshot_id="Snapshot-X", submission_attempt_reference="Attempt-X", authorization_authority_reference="Authority-X", send_authorization_reference="Send-X")
        phase31 = _make_phase31(request=request, context=context)
        source = _make_phase33(phase31=phase31)
        output = _build(subject, source)
        tc.assertEqual(output.request_snapshot.source_attempt_ref, "Attempt-X")
        tc.assertEqual(output.request_snapshot.authorization_evidence_ref, "Snapshot-X")
        return
    if ac == 37:
        _check_error_case(tc, subject, 94)
        tc.assertFalse(hasattr(subject, "authority"))
        return

    if ac == 38:
        _check_success_matrix(tc, subject)
        return
    if ac == 39:
        source = _make_phase33()
        output = _build(subject, source)
        tc.assertIs(output.request_snapshot, source.source_snapshot.source_snapshot.source_snapshot)
        return
    if ac == 40:
        source = _make_phase33()
        request = replace(source.source_snapshot.source_snapshot.source_snapshot, api_id=StrSubclass("kt10000"))
        _assert_error(tc, subject, _replace_request_in_phase33(source, request), "PHASE30_REQUEST_STRUCTURE_INVALID")
        return
    if ac == 41:
        _check_error_case(tc, subject, 96)
        return
    if ac == 42:
        source = _make_phase33()
        body = dict(source.source_snapshot.source_snapshot.source_snapshot.body)
        body["stk_cd"] = StrSubclass("005930")
        request = replace(source.source_snapshot.source_snapshot.source_snapshot, body=body)
        _assert_error(tc, subject, _replace_request_in_phase33(source, request), "PHASE30_REQUEST_STRUCTURE_INVALID")
        return
    if ac == 43:
        source = _make_phase33()
        request = replace(source.source_snapshot.source_snapshot.source_snapshot, body=ExplodingMapping(KeyError))
        _assert_error(tc, subject, _replace_request_in_phase33(source, request), "PHASE30_REQUEST_STRUCTURE_INVALID")
        return
    if ac == 44:
        source = _make_phase33()
        for bad_reference in ("bad\x00ref", "bad\u0080ref", "bad\u009fref"):
            with tc.subTest(bad_reference=repr(bad_reference)):
                request = replace(
                    source.source_snapshot.source_snapshot.source_snapshot,
                    source_attempt_ref=bad_reference,
                )
                _assert_error(
                    tc,
                    subject,
                    _replace_request_in_phase33(source, request),
                    "PHASE30_REQUEST_STRUCTURE_INVALID",
                )
        return
    if ac == 45:
        _check_error_case(tc, subject, 97)
        return
    if ac in (46, 47):
        _check_error_case(tc, subject, 99)
        return
    if ac == 48:
        _check_error_case(tc, subject, 108)
        return

    if ac == 66:
        with tc.assertRaises(subject.WatchlistOrderProviderSendEligibilityError):
            _build(subject, replace(_make_phase33(), reconciliation_required=True))
        return

    if ac in range(67, 83):
        output = _build(subject, _make_phase33())
        envelope = subject._eligibility_envelope(output)
        if ac == 67:
            tc.assertEqual(envelope["domain"], "phase34-provider-send-eligibility-candidate-v1")
        elif ac == 68:
            tc.assertEqual(set(envelope), ELIGIBILITY_KEYS)
            tc.assertEqual(len(envelope), 25)
        elif ac == 69:
            tc.assertEqual(output.eligibility_fingerprint, _expected_output_fingerprint(output))
        elif ac == 70:
            tc.assertEqual(envelope["decision"], output.decision.value)
        elif ac == 71:
            tc.assertIsNone(envelope["indeterminate_reason"])
            ind = _build(subject, _make_phase33(success=False))
            tc.assertEqual(subject._eligibility_envelope(ind)["indeterminate_reason"], ind.indeterminate_reason.value)
        elif ac == 72:
            output2 = _build(subject, output.source_snapshot)
            tc.assertEqual(output.eligibility_fingerprint, output2.eligibility_fingerprint)
        elif ac in (73, 74, 75, 76, 77):
            base = output.eligibility_fingerprint
            if ac == 73:
                changed_source = replace(output.source_snapshot, verification_fingerprint="1" * 64)
                changed = replace(output, source_snapshot=changed_source)
            elif ac == 74:
                p32 = replace(output.source_snapshot.source_snapshot, evidence_fingerprint="1" * 64)
                changed = replace(output, source_snapshot=replace(output.source_snapshot, source_snapshot=p32))
            elif ac == 75:
                p31 = replace(output.source_snapshot.source_snapshot.source_snapshot, claim_fingerprint="1" * 64)
                p32 = replace(output.source_snapshot.source_snapshot, source_snapshot=p31)
                changed = replace(output, source_snapshot=replace(output.source_snapshot, source_snapshot=p32))
            elif ac == 76:
                req = replace(output.request_snapshot, materialization_fingerprint="1" * 64)
                changed = replace(output, request_snapshot=req)
            else:
                req = replace(output.request_snapshot, source_attempt_ref="attempt-other")
                changed = replace(output, request_snapshot=req)
            tc.assertNotEqual(subject._eligibility_fingerprint(changed), base)
        elif ac in (78, 79, 80, 81):
            base = output.eligibility_fingerprint
            mutations = {
                78: {"request_materialization_verified": False},
                79: {"authority_approval_provenance_verified": True},
                80: {"provider_send_eligibility_candidate_ready": False},
                81: {"credential_accessed": True},
            }
            changed = replace(output, **mutations[ac])
            tc.assertNotEqual(subject._eligibility_fingerprint(changed), base)
        elif ac == 82:
            text = inspect.getsource(subject._eligibility_envelope)
            for forbidden in ("id(", "time", "uuid", "pid", "machine", "sqlite", "credential_value", "account_value", "provider_response"):
                tc.assertNotIn(forbidden, text.lower())
        return

    if ac == 83:
        tree = _source_tree()
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        tc.assertFalse(roots & {"socket", "requests", "urllib", "httpx", "aiohttp", "sqlite3", "os", "subprocess"})
        for rel, expected in UPSTREAM_HASHES.items():
            tc.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), expected, rel)
        return
    if ac == 84:
        names = {f"test_ac_{n:03d}" for n in range(1, 129)}
        tc.assertEqual({name for name in dir(Phase34A6ContractTests) if name.startswith("test_ac_")}, names)
        return

    if 85 <= ac <= 108:
        _check_error_case(tc, subject, ac)
        return

    if ac == 109:
        source = _make_phase33()
        phase32 = replace(source.source_snapshot, decision="AUTHORITY_REPORTED_BLOCKED")
        source = replace(source, verification_decision="BAD", source_snapshot=phase32)
        _assert_error(tc, subject, source, "PHASE33_DECISION_INVALID")
        return
    if ac == 110:
        for exc_type in (AttributeError, KeyError, TypeError):
            source = _make_phase33()
            request = replace(source.source_snapshot.source_snapshot.source_snapshot, body=ExplodingMapping(exc_type))
            _assert_error(tc, subject, _replace_request_in_phase33(source, request), "PHASE30_REQUEST_STRUCTURE_INVALID")
        return
    if ac == 111:
        source = _make_phase33()
        request = replace(source.source_snapshot.source_snapshot.source_snapshot, body=RuntimeExplodingMapping())
        with tc.assertRaisesRegex(RuntimeError, "^boom$"):
            _build(subject, _replace_request_in_phase33(source, request))
        for exc_type in (KeyboardInterrupt, SystemExit):
            request = replace(source.source_snapshot.source_snapshot.source_snapshot, body=ExplodingMapping(exc_type))
            with tc.assertRaises(exc_type):
                _build(subject, _replace_request_in_phase33(source, request))
        output = _build(subject, _make_phase33())
        with tc.assertRaisesRegex(AssertionError, "^PHASE34_INTERNAL_SAFETY_STATE_DEFECT$"):
            subject._assert_internal_safety_state(replace(output, transport_allowed=True))
        return
    if ac == 112:
        source = _make_phase33()
        output = _build(subject, source)
        tc.assertIs(output.request_snapshot, source.source_snapshot.source_snapshot.source_snapshot)
        return
    if ac == 113:
        _check_error_case(tc, subject, 106)
        return
    if ac == 114:
        tc.assertNotIn("PHASE34_SAFETY_STATE_CONSTRUCTION_INVALID", _source_text())
        tc.assertIn("PHASE34_INTERNAL_SAFETY_STATE_DEFECT", _source_text())
        return
    if ac == 115:
        tc.assertEqual(TARGET_SOURCE.name, "watchlist_order_provider_send_eligibility.py")
        tc.assertEqual(TARGET_TEST.name, "test_watchlist_order_provider_send_eligibility.py")
        tc.assertNotIn("PHASE34_DRAFT_A6", _source_text())
        return
    if ac == 116:
        tc.assertEqual(subject._PUBLIC_ERROR_CODES, PUBLIC_ERROR_CODES)
        tc.assertEqual(len(subject._PUBLIC_ERROR_CODES), 24)
        return
    if ac in (117, 118, 119):
        source = _make_phase33()
        if ac == 117:
            value = " authority-1 "
        elif ac == 118:
            value = "a" * 129
        else:
            value = "authority\x7f1"
        record = replace(source.durable_record, authorization_authority_reference=value)
        _assert_error(tc, subject, replace(source, durable_record=record), "PHASE33_DURABLE_RECORD_STRUCTURE_INVALID")
        return
    if ac in (120, 121, 122):
        source = _make_phase33()
        ar = source.source_snapshot.authority_result
        if ac == 120:
            ar = replace(ar, asserted_authority_approval_reference=StrSubclass(ar.asserted_authority_approval_reference))
        elif ac == 121:
            ar = replace(ar, decision=StrSubclass(ar.decision))
        else:
            ar = replace(ar, authority_result_reference=StrSubclass(ar.authority_result_reference))
        phase32 = replace(source.source_snapshot, authority_result=ar)
        _assert_error(tc, subject, replace(source, source_snapshot=phase32), "PHASE32_AUTHORITY_RESULT_BINDING_INVALID")
        return
    if ac == 123:
        source = _make_phase33()
        _assert_error(tc, subject, replace(source, backend_instance_reference="bad\ud800"), "PHASE33_STATE_INVARIANT_INVALID")
        source = _make_phase33()
        record = replace(source.durable_record, authority_approval_reference="bad\ud800")
        _assert_error(tc, subject, replace(source, durable_record=record), "PHASE33_DURABLE_RECORD_STRUCTURE_INVALID")
        return
    if ac == 124:
        for success in (True, False):
            source = _make_phase33(success=success)
            phase31 = source.source_snapshot.source_snapshot
            ctx = replace(phase31.context, authorization_authority_reference=" authority-1 ")
            phase31 = replace(phase31, context=ctx)
            _assert_error(tc, subject, _replace_phase31_in_phase33(source, phase31), "PHASE31_STATE_OR_REFERENCE_INVALID")
            source = _make_phase33(success=success)
            phase32 = replace(source.source_snapshot, asserted_authority_approval_reference="bad\ud800")
            _assert_error(tc, subject, replace(source, source_snapshot=phase32), "PHASE32_STATE_OR_RESULT_INVALID")
        return
    if ac in (125, 126, 128):
        for success in (True, False):
            source = _make_phase33(success=success)
            if ac in (125, 128):
                value = StrSubclass("kiwoom-watchlist-order-authorization-durable-ledger-v1")
            else:
                value = "wrong-ledger-schema"
            changed = replace(source, ledger_schema_reference=value)
            _assert_error(tc, subject, changed, "PHASE33_STATE_INVARIANT_INVALID")
        return
    if ac == 127:
        sig = inspect.signature(subject._phase33_verification_fingerprint)
        tc.assertNotIn("ledger_schema_reference", sig.parameters)
        text = inspect.getsource(subject._phase33_verification_fingerprint)
        tc.assertIn('"ledger_schema_reference": _LEDGER_SCHEMA_REFERENCE', text)
        return

    raise AssertionError(f"unhandled AC-{ac:03d}")


class Phase34A6ContractTests(unittest.TestCase):
    pass


def _make_ac_test(ac):
    def test(self):
        _run_ac(self, ac)

    test.__name__ = f"test_ac_{ac:03d}"
    test.__qualname__ = f"Phase34A6ContractTests.test_ac_{ac:03d}"
    test.__doc__ = f"Phase34 A6 AC-{ac:03d}"
    return test


for _ac in range(1, 129):
    setattr(Phase34A6ContractTests, f"test_ac_{_ac:03d}", _make_ac_test(_ac))


if __name__ == "__main__":
    unittest.main()
