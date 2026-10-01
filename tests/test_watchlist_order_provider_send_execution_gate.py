import ast
import dataclasses
import hashlib
import importlib
import inspect
import json
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

SUBJECT_MODULE = "kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_provider_send_execution_gate"
PHASE34_MODULE = "kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_provider_send_eligibility"
PHASE27_MODULE = "kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_submission_safety"

PUBLIC_SYMBOLS = (
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

REASONS = (
    "RECONCILIATION_REQUIRED",
    "PHASE34_SOURCE_INDETERMINATE",
    "TRUST_ANCHOR_UNVERIFIABLE",
    "EVIDENCE_CONFLICT",
    "EVIDENCE_MALFORMED",
    "EVIDENCE_MISSING",
    "CLOCK_REFERENCE_UNVERIFIABLE",
    "PRIOR_SUBMISSION_ALREADY_ACCEPTED",
    "FRESH_REAUTHORIZATION_REQUIRED",
    "RETRY_OR_RETRANSMISSION_REQUESTED",
    "EXECUTION_RISK_BLOCKED",
    "BUYING_POWER_INSUFFICIENT",
    "RISK_EVIDENCE_STALE",
    "BUYING_POWER_EVIDENCE_STALE",
    "APPROVAL_OR_CONFORMANCE_EXPIRED",
    "OWNERSHIP_EVIDENCE_EXPIRED",
    "DEMO_BINDING_MISMATCH",
    "OWNERSHIP_BINDING_MISMATCH",
    "TRANSPORT_BINDING_MISMATCH",
    "SOURCE_BINDING_MISMATCH",
)

OUTPUT_FIELDS = (
    "source_snapshot", "decision", "primary_reason_code", "all_reason_codes",
    "evaluated_at_utc", "risk_age_seconds", "buying_power_age_seconds",
    "phase34_eligibility_fingerprint", "phase33_verification_fingerprint",
    "phase30_materialization_fingerprint", "source_attempt_ref",
    "authorization_evidence_ref", "scope_fingerprint",
    "approval_evidence_fingerprint", "conformance_evidence_fingerprint",
    "risk_evidence_fingerprint", "buying_power_evidence_fingerprint",
    "credential_ownership_evidence_fingerprint",
    "account_ownership_evidence_fingerprint", "prior_submission_state",
    "prior_attempt_reference", "reconciliation_reference",
    "reconciliation_required", "provider_send_execution_ready",
    "transport_authorized", "provider_call_performed",
    "actual_kt10000_post_performed", "credential_lookup_performed",
    "account_lookup_performed", "token_acquisition_performed",
    "automatic_retry_permitted", "retransmission_permitted",
    "readiness_fingerprint",
)

VERIFIERS = {
    "phase35-explicit-provider-send-approval-verifier-v1": "4caaa7efb7ef985b98ed3ed8e4aa228df3a9747dae025c2700566978c9401af7",
    "phase35-provider-send-conformance-verifier-v1": "d27104d5e61e6592a29135daa240f7d5c546ffd1ffc140281da707528d814947",
    "phase35-execution-risk-freshness-verifier-v1": "49333769e15478e16280bd539f3751e00b5cc2597e7b5bfca05fd10c766418a6",
    "phase35-execution-buying-power-freshness-verifier-v1": "7e0121363914e113979250bb495fbcabfbef25ef155a18816966257e124b1f57",
    "phase35-demo-credential-ownership-verifier-v1": "8cd94990ad8914a834c3c5406641076a10ff59bcb7f9f2725c3212bf34c302d0",
    "phase35-demo-account-ownership-verifier-v1": "79feeef34933b768ece50d68e7d1dcf1d526e21783c229c65ade954901bdea18",
}

DOMAINS = {
    "Phase35ProviderSendApprovalEvidence": "phase35-explicit-provider-send-approval-evidence-v1",
    "Phase35ProviderSendConformanceEvidence": "phase35-provider-send-conformance-evidence-v1",
    "Phase35ExecutionRiskFreshnessEvidence": "phase35-execution-risk-freshness-evidence-v1",
    "Phase35ExecutionBuyingPowerFreshnessEvidence": "phase35-execution-buying-power-freshness-evidence-v1",
    "Phase35CredentialOwnershipEvidence": "phase35-demo-credential-ownership-evidence-v1",
    "Phase35AccountOwnershipEvidence": "phase35-demo-account-ownership-evidence-v1",
}

FIXED_NOW = datetime(2026, 10, 1, 5, 0, 0, tzinfo=timezone.utc)


def subject():
    return importlib.import_module(SUBJECT_MODULE)


def phase34():
    return importlib.import_module(PHASE34_MODULE)


def phase27():
    return importlib.import_module(PHASE27_MODULE)


def canonical_sha(envelope):
    raw = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def utc_text(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def phase34_envelope(s):
    return {
        "domain": "phase34-provider-send-eligibility-candidate-v1",
        "phase33_verification_fingerprint": s.source_snapshot.verification_fingerprint,
        "phase32_evidence_fingerprint": s.source_snapshot.source_snapshot.evidence_fingerprint,
        "phase31_claim_fingerprint": s.source_snapshot.source_snapshot.source_snapshot.claim_fingerprint,
        "phase30_materialization_fingerprint": s.request_snapshot.materialization_fingerprint,
        "source_attempt_ref": s.request_snapshot.source_attempt_ref,
        "authorization_evidence_ref": s.request_snapshot.authorization_evidence_ref,
        "decision": s.decision.value,
        "indeterminate_reason": None if s.indeterminate_reason is None else s.indeterminate_reason.value,
        "request_materialization_verified": s.request_materialization_verified,
        "authorization_claim_binding_verified": s.authorization_claim_binding_verified,
        "durable_consumption_verified": s.durable_consumption_verified,
        "provider_request_contract_verified": s.provider_request_contract_verified,
        "authority_approval_provenance_verified": s.authority_approval_provenance_verified,
        "authority_conformance_provenance_verified": s.authority_conformance_provenance_verified,
        "provider_send_eligibility_candidate_ready": s.provider_send_eligibility_candidate_ready,
        "provider_send_eligibility_authorized": s.provider_send_eligibility_authorized,
        "production_authority_use_authorized": s.production_authority_use_authorized,
        "transport_allowed": s.transport_allowed,
        "credential_accessed": s.credential_accessed,
        "network_performed": s.network_performed,
        "account_accessed": s.account_accessed,
        "order_submitted": s.order_submitted,
        "automatic_retry_permitted": s.automatic_retry_permitted,
        "reconciliation_required": s.reconciliation_required,
    }


def make_phase34(*, indeterminate=False):
    p34 = phase34()
    request = SimpleNamespace(
        environment="demo", side="BUY", exchange="KRX", api_id="kt10000",
        http_method="POST", api_path="/api/dostk/ordr",
        materialization_fingerprint="1" * 64,
        source_attempt_ref="attempt:phase35-1",
        authorization_evidence_ref="auth-evidence:phase35-1",
    )
    p31 = SimpleNamespace(source_snapshot=request, claim_fingerprint="2" * 64)
    p32 = SimpleNamespace(source_snapshot=p31, evidence_fingerprint="3" * 64)
    p33 = SimpleNamespace(source_snapshot=p32, verification_fingerprint="4" * 64)
    if indeterminate:
        decision = p34.KiwoomOrderProviderSendEligibilityDecision.INDETERMINATE
        reason = p34.KiwoomOrderProviderSendEligibilityIndeterminateReason.SOURCE_DURABLE_VERIFICATION_INDETERMINATE
        durable = False
        candidate = False
        reconciliation = True
    else:
        decision = p34.KiwoomOrderProviderSendEligibilityDecision.PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY
        reason = None
        durable = True
        candidate = True
        reconciliation = False
    s = p34.WatchlistOrderProviderSendEligibilityCandidateSnapshot(
        p33, request, decision, reason, True, True, durable, True, False, False,
        candidate, False, False, False, False, False, False, False, False,
        reconciliation, "0" * 64,
    )
    return replace(s, eligibility_fingerprint=canonical_sha(phase34_envelope(s)))


def scope_envelope(s, cred="credref:demo-1", acct="acctref:demo-1"):
    r = s.request_snapshot
    return {
        "domain": "phase35-provider-send-execution-scope-v1",
        "phase34_eligibility_fingerprint": s.eligibility_fingerprint,
        "phase33_verification_fingerprint": s.source_snapshot.verification_fingerprint,
        "phase30_materialization_fingerprint": r.materialization_fingerprint,
        "source_attempt_ref": r.source_attempt_ref,
        "authorization_evidence_ref": r.authorization_evidence_ref,
        "environment": "demo", "host": "mockapi.kiwoom.com",
        "api_id": "kt10000", "http_method": "POST", "api_path": "/api/dostk/ordr",
        "exchange": "KRX", "side": "BUY", "financing": "CASH",
        "credential_ref_id": cred, "account_ref_id": acct,
    }


def evidence_fp(e):
    envelope = {"domain": DOMAINS[type(e).__name__]}
    for f in dataclasses.fields(e):
        if f.name == "evidence_fingerprint":
            break
        envelope[f.name] = getattr(e, f.name)
    return canonical_sha(envelope)


def with_fp(e):
    return replace(e, evidence_fingerprint=evidence_fp(e))


def make_bundle(s, *, now=FIXED_NOW, state=None, prior=None, reconciliation=None,
                risk_age=2.0, buying_age=2.0, risk_decision="RISK_CLEAR",
                buying_decision="BUYING_POWER_SUFFICIENT", retry=False, retrans=False):
    m = subject()
    p27 = phase27()
    state = p27.KiwoomPriorSubmissionState.NEVER_ATTEMPTED if state is None else state
    cred_ref = "credref:demo-1"
    acct_ref = "acctref:demo-1"
    owner_ref = "ownerref:user-1"
    scope = canonical_sha(scope_envelope(s, cred_ref, acct_ref))
    issued = utc_text(now - timedelta(seconds=1))
    expires = utc_text(now + timedelta(seconds=60))
    observed_risk = utc_text(now - timedelta(seconds=risk_age))
    observed_buying = utc_text(now - timedelta(seconds=buying_age))
    approval = with_fp(m.Phase35ProviderSendApprovalEvidence(
        "phase35-explicit-provider-send-approval-verifier-v1", VERIFIERS["phase35-explicit-provider-send-approval-verifier-v1"],
        "approval-1", issued, expires, s.eligibility_fingerprint, s.request_snapshot.materialization_fingerprint,
        s.request_snapshot.source_attempt_ref, s.request_snapshot.authorization_evidence_ref, scope, "0" * 64))
    conformance = with_fp(m.Phase35ProviderSendConformanceEvidence(
        "phase35-provider-send-conformance-verifier-v1", VERIFIERS["phase35-provider-send-conformance-verifier-v1"],
        "conformance-1", issued, expires, s.eligibility_fingerprint, s.request_snapshot.materialization_fingerprint,
        s.request_snapshot.source_attempt_ref, s.request_snapshot.authorization_evidence_ref, scope, "0" * 64))
    risk = with_fp(m.Phase35ExecutionRiskFreshnessEvidence(
        "phase35-execution-risk-freshness-verifier-v1", VERIFIERS["phase35-execution-risk-freshness-verifier-v1"],
        "risk-1", issued, observed_risk, s.eligibility_fingerprint, s.request_snapshot.materialization_fingerprint,
        s.request_snapshot.source_attempt_ref, risk_decision, scope, "0" * 64))
    buying = with_fp(m.Phase35ExecutionBuyingPowerFreshnessEvidence(
        "phase35-execution-buying-power-freshness-verifier-v1", VERIFIERS["phase35-execution-buying-power-freshness-verifier-v1"],
        "buying-1", issued, observed_buying, s.eligibility_fingerprint, s.request_snapshot.materialization_fingerprint,
        s.request_snapshot.source_attempt_ref, acct_ref, buying_decision, scope, "0" * 64))
    credential = with_fp(m.Phase35CredentialOwnershipEvidence(
        "phase35-demo-credential-ownership-verifier-v1", VERIFIERS["phase35-demo-credential-ownership-verifier-v1"],
        "credential-1", issued, expires, cred_ref, owner_ref, "demo", scope, "0" * 64))
    account = with_fp(m.Phase35AccountOwnershipEvidence(
        "phase35-demo-account-ownership-verifier-v1", VERIFIERS["phase35-demo-account-ownership-verifier-v1"],
        "account-1", issued, expires, acct_ref, owner_ref, cred_ref, "demo", scope, "0" * 64))
    return m.Phase35ProviderSendExecutionEvidenceBundle(
        approval, conformance, risk, buying, credential, account, state, prior, reconciliation, retry, retrans)


def build(s=None, b=None, now=FIXED_NOW):
    m = subject()
    s = make_phase34() if s is None else s
    b = make_bundle(s, now=now) if b is None else b
    old = m._utc_now
    calls = []
    def clock():
        calls.append(1)
        return now
    m._utc_now = clock
    try:
        return m.build_demo_watchlist_order_provider_send_execution_readiness_snapshot(s, b), len(calls)
    finally:
        m._utc_now = old


class Phase35ContractTests(unittest.TestCase):
    def test_001_public_api_exact_twelve_symbols(self):
        m = subject()
        self.assertEqual(tuple(m.__all__), PUBLIC_SYMBOLS)
        names = tuple(n for n in vars(m) if not n.startswith("_") and n != "__builtins__")
        self.assertEqual(names, PUBLIC_SYMBOLS)

    def test_002_error_is_runtime_error(self):
        self.assertEqual(subject().WatchlistOrderProviderSendExecutionGateError.__bases__, (RuntimeError,))

    def test_003_decision_enum_exact(self):
        e = subject().KiwoomOrderProviderSendExecutionReadinessDecision
        self.assertEqual(tuple((x.name, x.value) for x in e), (("PROVIDER_SEND_EXECUTION_READY", "PROVIDER_SEND_EXECUTION_READY"), ("DENIED", "DENIED"), ("INDETERMINATE", "INDETERMINATE")))

    def test_004_reason_enum_exact(self):
        e = subject().KiwoomOrderProviderSendExecutionReadinessReason
        self.assertEqual(tuple(x.value for x in e), REASONS)

    def test_005_builder_exact_signature_and_sync(self):
        fn = subject().build_demo_watchlist_order_provider_send_execution_readiness_snapshot
        sig = inspect.signature(fn)
        self.assertEqual(tuple(sig.parameters), ("source_snapshot", "evidence_bundle"))
        self.assertTrue(all(p.default is inspect.Parameter.empty for p in sig.parameters.values()))
        self.assertFalse(inspect.iscoroutinefunction(fn))

    def test_006_evidence_dataclass_fields_and_frozen(self):
        m = subject()
        expected = {
            m.Phase35ProviderSendApprovalEvidence: ("verifier_id","verifier_identity_sha256","evidence_id","issued_at_utc","expires_at_utc","phase34_eligibility_fingerprint","phase30_materialization_fingerprint","source_attempt_ref","authorization_evidence_ref","scope_fingerprint","evidence_fingerprint"),
            m.Phase35ProviderSendConformanceEvidence: ("verifier_id","verifier_identity_sha256","evidence_id","issued_at_utc","expires_at_utc","phase34_eligibility_fingerprint","phase30_materialization_fingerprint","source_attempt_ref","authorization_evidence_ref","scope_fingerprint","evidence_fingerprint"),
            m.Phase35ExecutionRiskFreshnessEvidence: ("verifier_id","verifier_identity_sha256","evidence_id","issued_at_utc","observed_at_utc","phase34_eligibility_fingerprint","phase30_materialization_fingerprint","source_attempt_ref","risk_decision","scope_fingerprint","evidence_fingerprint"),
            m.Phase35ExecutionBuyingPowerFreshnessEvidence: ("verifier_id","verifier_identity_sha256","evidence_id","issued_at_utc","observed_at_utc","phase34_eligibility_fingerprint","phase30_materialization_fingerprint","source_attempt_ref","account_ref_id","buying_power_decision","scope_fingerprint","evidence_fingerprint"),
            m.Phase35CredentialOwnershipEvidence: ("verifier_id","verifier_identity_sha256","evidence_id","issued_at_utc","expires_at_utc","credential_ref_id","owner_ref","environment","scope_fingerprint","evidence_fingerprint"),
            m.Phase35AccountOwnershipEvidence: ("verifier_id","verifier_identity_sha256","evidence_id","issued_at_utc","expires_at_utc","account_ref_id","account_owner_ref","bound_credential_ref_id","environment","scope_fingerprint","evidence_fingerprint"),
        }
        for cls, fields in expected.items():
            self.assertEqual(tuple(f.name for f in dataclasses.fields(cls)), fields)
            self.assertTrue(cls.__dataclass_params__.frozen)

    def test_007_bundle_fields_and_frozen(self):
        m = subject(); cls = m.Phase35ProviderSendExecutionEvidenceBundle
        self.assertEqual(tuple(f.name for f in dataclasses.fields(cls)), ("approval_evidence","conformance_evidence","risk_evidence","buying_power_evidence","credential_ownership_evidence","account_ownership_evidence","prior_submission_state","prior_attempt_reference","reconciliation_reference","automatic_retry_requested","retransmission_requested"))
        self.assertTrue(cls.__dataclass_params__.frozen)

    def test_008_output_exact_33_fields_and_frozen(self):
        cls = subject().WatchlistOrderProviderSendExecutionReadinessSnapshot
        self.assertEqual(tuple(f.name for f in dataclasses.fields(cls)), OUTPUT_FIELDS)
        self.assertTrue(cls.__dataclass_params__.frozen)

    def test_009_registry_exact_and_hash_bound(self):
        m = subject()
        self.assertEqual(dict(m._VERIFIER_REGISTRY), VERIFIERS)
        for verifier_id, digest in VERIFIERS.items():
            self.assertEqual(hashlib.sha256(verifier_id.encode()).hexdigest(), digest)

    def test_010_wrong_source_type_fails_closed(self):
        m = subject(); s=make_phase34(); b=make_bundle(s)
        with self.assertRaisesRegex(m.WatchlistOrderProviderSendExecutionGateError, "PHASE34_SOURCE_SNAPSHOT_TYPE_INVALID"):
            m.build_demo_watchlist_order_provider_send_execution_readiness_snapshot(object(), b)

    def test_011_wrong_bundle_type_fails_closed(self):
        m = subject(); s=make_phase34()
        with self.assertRaisesRegex(m.WatchlistOrderProviderSendExecutionGateError, "EVIDENCE_BUNDLE_TYPE_INVALID"):
            m.build_demo_watchlist_order_provider_send_execution_readiness_snapshot(s, object())

    def test_012_ready_happy_path(self):
        m=subject(); out,calls=build()
        self.assertIs(out.decision, m.KiwoomOrderProviderSendExecutionReadinessDecision.PROVIDER_SEND_EXECUTION_READY)
        self.assertIsNone(out.primary_reason_code); self.assertEqual(out.all_reason_codes, ())
        self.assertTrue(out.provider_send_execution_ready); self.assertFalse(out.reconciliation_required)
        self.assertEqual(calls,1)

    def test_013_ready_side_effect_flags_all_false(self):
        out,_=build()
        for name in ("transport_authorized","provider_call_performed","actual_kt10000_post_performed","credential_lookup_performed","account_lookup_performed","token_acquisition_performed","automatic_retry_permitted","retransmission_permitted"):
            self.assertIs(getattr(out,name), False)

    def test_014_output_preserves_source_object_identity(self):
        s=make_phase34(); out,_=build(s=s,b=make_bundle(s)); self.assertIs(out.source_snapshot,s)

    def test_015_clock_captured_exactly_once(self):
        _,calls=build(); self.assertEqual(calls,1)

    def test_016_keyboard_interrupt_not_swallowed(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); old=m._utc_now
        def boom(): raise KeyboardInterrupt()
        m._utc_now=boom
        try:
            with self.assertRaises(KeyboardInterrupt): m.build_demo_watchlist_order_provider_send_execution_readiness_snapshot(s,b)
        finally: m._utc_now=old

    def test_017_system_exit_not_swallowed(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); old=m._utc_now
        def boom(): raise SystemExit(9)
        m._utc_now=boom
        try:
            with self.assertRaises(SystemExit): m.build_demo_watchlist_order_provider_send_execution_readiness_snapshot(s,b)
        finally: m._utc_now=old

    def test_018_phase34_fingerprint_precedes_safety_matrix(self):
        m=subject(); s=make_phase34(); s=replace(s, eligibility_fingerprint="f"*64, transport_allowed=True); b=make_bundle(s)
        with self.assertRaisesRegex(m.WatchlistOrderProviderSendExecutionGateError, "PHASE34_ELIGIBILITY_FINGERPRINT_INVALID"):
            build(s=s,b=b)

    def test_019_phase34_identity_chain_invalid_fails_structure(self):
        m=subject(); s=make_phase34(); s=replace(s, request_snapshot=SimpleNamespace(**vars(s.request_snapshot)))
        with self.assertRaisesRegex(m.WatchlistOrderProviderSendExecutionGateError, "PHASE34_SOURCE_STRUCTURE_INVALID"):
            build(s=s,b=make_bundle(s))

    def test_020_phase34_nested_structure_invalid_is_phase35_error(self):
        m=subject(); s=make_phase34(); bad33=SimpleNamespace(source_snapshot=s.source_snapshot.source_snapshot)
        s=replace(s, source_snapshot=bad33)
        with self.assertRaisesRegex(m.WatchlistOrderProviderSendExecutionGateError, "PHASE34_SOURCE_STRUCTURE_INVALID"):
            build(s=s,b=make_bundle(make_phase34()))

    def test_021_phase34_indeterminate_maps_indeterminate(self):
        m=subject(); s=make_phase34(indeterminate=True); out,_=build(s=s,b=make_bundle(s))
        self.assertIs(out.decision,m.KiwoomOrderProviderSendExecutionReadinessDecision.INDETERMINATE)
        self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.PHASE34_SOURCE_INDETERMINATE)

    def test_022_malformed_prior_state_returns_indeterminate_not_exception(self):
        m=subject(); s=make_phase34(); b=replace(make_bundle(s),prior_submission_state="BAD")
        out,_=build(s=s,b=b)
        self.assertIs(out.decision,m.KiwoomOrderProviderSendExecutionReadinessDecision.INDETERMINATE)
        self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED)
        self.assertIsNone(out.prior_submission_state)

    def test_023_malformed_prior_reference_object_returns_indeterminate(self):
        m=subject(); s=make_phase34(); p27=phase27(); b=replace(make_bundle(s),prior_submission_state=p27.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,prior_attempt_reference=object(),reconciliation_reference="recon:1")
        out,_=build(s=s,b=b)
        self.assertIs(out.decision,m.KiwoomOrderProviderSendExecutionReadinessDecision.INDETERMINATE)
        self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED)
        self.assertIsNone(out.prior_attempt_reference)

    def test_024_confirmed_accepted_denied(self):
        m=subject(); s=make_phase34(); p27=phase27(); b=replace(make_bundle(s),prior_submission_state=p27.KiwoomPriorSubmissionState.CONFIRMED_ACCEPTED,prior_attempt_reference="attempt:old",reconciliation_reference="recon:old")
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.PRIOR_SUBMISSION_ALREADY_ACCEPTED)

    def test_025_confirmed_not_accepted_requires_fresh_reauth(self):
        m=subject(); s=make_phase34(); p27=phase27(); b=replace(make_bundle(s),prior_submission_state=p27.KiwoomPriorSubmissionState.CONFIRMED_NOT_ACCEPTED,prior_attempt_reference="attempt:old",reconciliation_reference="recon:old")
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.FRESH_REAUTHORIZATION_REQUIRED)

    def test_026_ambiguous_requires_reconciliation(self):
        m=subject(); s=make_phase34(); p27=phase27(); b=replace(make_bundle(s),prior_submission_state=p27.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED,prior_attempt_reference="attempt:old",reconciliation_reference=None)
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.RECONCILIATION_REQUIRED); self.assertTrue(out.reconciliation_required)

    def test_027_missing_evidence_indeterminate(self):
        m=subject(); s=make_phase34(); b=replace(make_bundle(s), approval_evidence=None)
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MISSING)

    def test_028_wrong_evidence_type_malformed(self):
        m=subject(); s=make_phase34(); b=replace(make_bundle(s), approval_evidence="bad")
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED)

    def test_029_untrusted_verifier_hash_indeterminate(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=replace(b.approval_evidence,verifier_identity_sha256="f"*64); e=with_fp(e); b=replace(b,approval_evidence=e)
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.TRUST_ANCHOR_UNVERIFIABLE)

    def test_030_tampered_evidence_fingerprint_malformed(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); b=replace(b,risk_evidence=replace(b.risk_evidence,evidence_fingerprint="f"*64))
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED)

    def test_031_approval_conformance_conflict_indeterminate(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=replace(b.approval_evidence,source_attempt_ref="attempt:other"); e=with_fp(e); b=replace(b,approval_evidence=e)
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_CONFLICT)

    def test_032_scope_binding_mismatch_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=replace(b.risk_evidence,scope_fingerprint="a"*64); e=with_fp(e); b=replace(b,risk_evidence=e)
        out,_=build(s=s,b=b); self.assertIs(out.decision,m.KiwoomOrderProviderSendExecutionReadinessDecision.DENIED); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.SOURCE_BINDING_MISMATCH,out.all_reason_codes)

    def test_033_demo_binding_mismatch_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=with_fp(replace(b.credential_ownership_evidence,environment="prod")); b=replace(b,credential_ownership_evidence=e)
        out,_=build(s=s,b=b); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.DEMO_BINDING_MISMATCH,out.all_reason_codes)

    def test_034_ownership_binding_mismatch_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=with_fp(replace(b.account_ownership_evidence,account_owner_ref="ownerref:other")); b=replace(b,account_ownership_evidence=e)
        out,_=build(s=s,b=b); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.OWNERSHIP_BINDING_MISMATCH,out.all_reason_codes)

    def test_035_transport_binding_mismatch_denied(self):
        m=subject(); s=make_phase34(); s.request_snapshot.api_id="kt99999"; b=make_bundle(s)
        out,_=build(s=s,b=b); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.TRANSPORT_BINDING_MISMATCH,out.all_reason_codes)

    def test_036_risk_blocked_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s,risk_decision="RISK_BLOCKED"); out,_=build(s=s,b=b)
        self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.EXECUTION_RISK_BLOCKED,out.all_reason_codes)

    def test_037_buying_power_insufficient_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s,buying_decision="BUYING_POWER_INSUFFICIENT"); out,_=build(s=s,b=b)
        self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.BUYING_POWER_INSUFFICIENT,out.all_reason_codes)

    def test_038_risk_stale_over_five_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s,risk_age=5.001); out,_=build(s=s,b=b)
        self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.RISK_EVIDENCE_STALE,out.all_reason_codes)

    def test_039_buying_power_stale_over_five_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s,buying_age=5.001); out,_=build(s=s,b=b)
        self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.BUYING_POWER_EVIDENCE_STALE,out.all_reason_codes)

    def test_040_freshness_exact_five_seconds_passes(self):
        m=subject(); s=make_phase34(); out,_=build(s=s,b=make_bundle(s,risk_age=5.0,buying_age=5.0))
        self.assertIs(out.decision,m.KiwoomOrderProviderSendExecutionReadinessDecision.PROVIDER_SEND_EXECUTION_READY)

    def test_041_future_skew_exact_one_second_passes(self):
        m=subject(); s=make_phase34(); out,_=build(s=s,b=make_bundle(s,risk_age=-1.0,buying_age=-1.0))
        self.assertIs(out.decision,m.KiwoomOrderProviderSendExecutionReadinessDecision.PROVIDER_SEND_EXECUTION_READY)

    def test_042_future_skew_beyond_one_second_indeterminate(self):
        m=subject(); s=make_phase34(); out,_=build(s=s,b=make_bundle(s,risk_age=-1.001))
        self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.CLOCK_REFERENCE_UNVERIFIABLE)

    def test_043_malformed_timestamp_indeterminate(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=replace(b.risk_evidence,observed_at_utc="2026-10-01T05:00:00"); e=with_fp(e); b=replace(b,risk_evidence=e)
        out,_=build(s=s,b=b); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED,out.all_reason_codes)

    def test_044_approval_expired_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=replace(b.approval_evidence,expires_at_utc=utc_text(FIXED_NOW)); e=with_fp(e); b=replace(b,approval_evidence=e)
        out,_=build(s=s,b=b); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.APPROVAL_OR_CONFORMANCE_EXPIRED,out.all_reason_codes)

    def test_045_ownership_expired_denied(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=replace(b.account_ownership_evidence,expires_at_utc=utc_text(FIXED_NOW)); e=with_fp(e); b=replace(b,account_ownership_evidence=e)
        out,_=build(s=s,b=b); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.OWNERSHIP_EVIDENCE_EXPIRED,out.all_reason_codes)

    def test_046_retry_requested_denied(self):
        m=subject(); s=make_phase34(); out,_=build(s=s,b=replace(make_bundle(s),automatic_retry_requested=True))
        self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.RETRY_OR_RETRANSMISSION_REQUESTED,out.all_reason_codes); self.assertFalse(out.automatic_retry_permitted)

    def test_047_retransmission_requested_denied(self):
        m=subject(); s=make_phase34(); out,_=build(s=s,b=replace(make_bundle(s),retransmission_requested=True))
        self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.RETRY_OR_RETRANSMISSION_REQUESTED,out.all_reason_codes); self.assertFalse(out.retransmission_permitted)

    def test_048_nonbool_retry_is_malformed(self):
        m=subject(); s=make_phase34(); out,_=build(s=s,b=replace(make_bundle(s),automatic_retry_requested=1))
        self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED)

    def test_049_reason_priority_reconciliation_over_missing(self):
        m=subject(); s=make_phase34(); p27=phase27(); b=make_bundle(s); b=replace(b,approval_evidence=None,prior_submission_state=p27.KiwoomPriorSubmissionState.AMBIGUOUS_UNRESOLVED,prior_attempt_reference="attempt:x")
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.RECONCILIATION_REQUIRED); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MISSING,out.all_reason_codes)

    def test_050_trust_priority_over_malformed(self):
        m=subject(); s=make_phase34(); b=make_bundle(s); e=replace(b.approval_evidence,verifier_identity_sha256="X"*64); b=replace(b,approval_evidence=e)
        out,_=build(s=s,b=b); self.assertIs(out.primary_reason_code,m.KiwoomOrderProviderSendExecutionReadinessReason.TRUST_ANCHOR_UNVERIFIABLE); self.assertIn(m.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MALFORMED,out.all_reason_codes)

    def test_051_readiness_fingerprint_matches_independent_canonical_envelope(self):
        out,_=build()
        envelope={
            "domain":"phase35-provider-send-execution-readiness-v1",
            "decision":out.decision.value,
            "primary_reason_code":None if out.primary_reason_code is None else out.primary_reason_code.value,
            "all_reason_codes":[x.value for x in out.all_reason_codes],
            "evaluated_at_utc":out.evaluated_at_utc,
            "risk_age_seconds":None if out.risk_age_seconds is None else f"{out.risk_age_seconds:.3f}",
            "buying_power_age_seconds":None if out.buying_power_age_seconds is None else f"{out.buying_power_age_seconds:.3f}",
        }
        for name in OUTPUT_FIELDS[7:-1]:
            if name in ("prior_submission_state",):
                value=getattr(out,name); value=None if value is None else value.value
            elif name in ("primary_reason_code","all_reason_codes"):
                continue
            else: value=getattr(out,name)
            envelope[name]=value
        self.assertEqual(out.readiness_fingerprint,canonical_sha(envelope))
        self.assertEqual(envelope["risk_age_seconds"],"2.000")

    def test_052_output_fingerprint_lowercase_sha256(self):
        out,_=build(); self.assertRegex(out.readiness_fingerprint,r"^[0-9a-f]{64}$")

    def test_053_caller_verified_boolean_not_a_public_field(self):
        m=subject()
        for cls in (m.Phase35ProviderSendApprovalEvidence,m.Phase35ProviderSendConformanceEvidence,m.Phase35ExecutionRiskFreshnessEvidence,m.Phase35ExecutionBuyingPowerFreshnessEvidence,m.Phase35CredentialOwnershipEvidence,m.Phase35AccountOwnershipEvidence):
            self.assertNotIn("verified",tuple(f.name for f in dataclasses.fields(cls)))

    def test_054_no_network_or_credential_io_import_surface(self):
        module_file=Path(subject().__file__); tree=ast.parse(module_file.read_text(encoding="utf-8"))
        forbidden_imports={"requests","httpx","urllib","socket","websockets","aiohttp","os","pathlib","subprocess"}
        imported=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import): imported.update(a.name.split('.')[0] for a in n.names)
            elif isinstance(n,ast.ImportFrom) and n.module: imported.add(n.module.split('.')[0])
        self.assertTrue(imported.isdisjoint(forbidden_imports), imported & forbidden_imports)
        text=module_file.read_text(encoding="utf-8")
        for token in ("get_client(","get_ws_client(","Invoke-WebRequest","Invoke-RestMethod","requests.","httpx.","socket.","open("):
            self.assertNotIn(token,text)
        string_literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertNotIn(".env", string_literals)

    def test_055_input_evidence_objects_not_mutated(self):
        s=make_phase34(); b=make_bundle(s); before=repr(b); build(s=s,b=b); self.assertEqual(repr(b),before)

    def test_056_output_is_immutable(self):
        out,_=build()
        with self.assertRaises(dataclasses.FrozenInstanceError): out.provider_send_execution_ready=False


if __name__ == "__main__":
    unittest.main(verbosity=2)
