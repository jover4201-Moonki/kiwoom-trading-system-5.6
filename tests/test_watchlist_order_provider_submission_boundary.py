import asyncio
import ast
import dataclasses
import hashlib
import importlib
import inspect
import json
import sys
import unittest
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SUBJECT_MODULE = (
    "kiwoom_trading_system.brokers.kiwoom.rest."
    "watchlist_order_provider_submission_boundary"
)
P35_MODULE = (
    "kiwoom_trading_system.brokers.kiwoom.rest."
    "watchlist_order_provider_send_execution_gate"
)
TARGET_SOURCE = (
    SRC
    / "kiwoom_trading_system/brokers/kiwoom/rest/"
    "watchlist_order_provider_submission_boundary.py"
)
REST_INIT = (
    SRC / "kiwoom_trading_system/brokers/kiwoom/rest/__init__.py"
)

PUBLIC_SYMBOLS = (
    "WatchlistOrderProviderSubmissionBoundaryError",
    "KiwoomOrderProviderSubmissionOutcome",
    "Phase36SubmissionRegistryState",
    "Phase36SubmissionApprovalEvidence",
    "Phase36ProviderExecutionContext",
    "Phase36AtomicSubmissionRegistry",
    "KiwoomOrderProviderSubmissionReceipt",
    "submit_demo_watchlist_order_once",
)

APPROVAL_FIELDS = (
    "approval_id",
    "issued_at_utc",
    "not_before_utc",
    "expires_at_utc",
    "readiness_fingerprint",
    "request_fingerprint",
    "source_attempt_ref",
    "authorization_evidence_ref",
    "scope_fingerprint",
    "credential_ownership_evidence_fingerprint",
    "account_ownership_evidence_fingerprint",
    "one_shot_authorized",
    "approval_fingerprint",
)

CONTEXT_FIELDS = (
    "mode",
    "base_url",
    "credential_ref_id",
    "account_ref_id",
    "credential_ownership_evidence_fingerprint",
    "account_ownership_evidence_fingerprint",
    "runtime_credential_account_access_authorized",
    "auth_network_authorized",
    "provider_network_authorized",
    "actual_kt10000_post_authorized",
    "test_execution",
    "timeout_seconds",
    "resolver",
    "token_provider",
    "readiness_revalidator",
    "transport",
    "cleanup",
    "clock",
)

RECEIPT_FIELDS = (
    "attempt_fingerprint",
    "request_fingerprint",
    "readiness_fingerprint",
    "submission_approval_fingerprint",
    "claim_fingerprint",
    "mode",
    "endpoint_identity",
    "api_id",
    "normalized_return_code",
    "provider_return_msg",
    "provider_order_no",
    "provider_exchange",
    "outcome",
    "registry_terminal_state",
    "transport_attempt_count",
    "started_at_utc",
    "completed_at_utc",
    "credential_provenance_fingerprint",
    "account_provenance_fingerprint",
)

FIXED_NOW = datetime(2026, 10, 3, 0, 0, 0, tzinfo=timezone.utc)
CRED_FP = "c" * 64
ACCT_FP = "d" * 64
SCOPE_FP = "e" * 64


def subject():
    try:
        return importlib.import_module(SUBJECT_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name == SUBJECT_MODULE:
            raise AssertionError("PHASE36_SOURCE_MISSING_EXPECTED_RED") from exc
        raise


def p35():
    return importlib.import_module(P35_MODULE)


def canonical_sha(envelope):
    raw = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def utc_text(value):
    return value.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def request_fp(request):
    return canonical_sha(
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


def make_request(**overrides):
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
        "source_attempt_ref": "attempt-phase36-1",
        "authorization_evidence_ref": "auth-evidence-phase36-1",
        "materialization_fingerprint": "0" * 64,
    }
    values.update(overrides)
    request = SimpleNamespace(**values)
    if "materialization_fingerprint" not in overrides:
        request.materialization_fingerprint = request_fp(request)
    return request


def make_readiness(*, request=None, **overrides):
    m = p35()
    request = request or make_request()
    values = {
        "source_snapshot": SimpleNamespace(request_snapshot=request),
        "decision": m.KiwoomOrderProviderSendExecutionReadinessDecision.PROVIDER_SEND_EXECUTION_READY,
        "primary_reason_code": None,
        "all_reason_codes": (),
        "evaluated_at_utc": utc_text(FIXED_NOW - timedelta(seconds=1)),
        "risk_age_seconds": 1.0,
        "buying_power_age_seconds": 1.0,
        "phase34_eligibility_fingerprint": "1" * 64,
        "phase33_verification_fingerprint": "2" * 64,
        "phase30_materialization_fingerprint": request.materialization_fingerprint,
        "source_attempt_ref": request.source_attempt_ref,
        "authorization_evidence_ref": request.authorization_evidence_ref,
        "scope_fingerprint": SCOPE_FP,
        "approval_evidence_fingerprint": "3" * 64,
        "conformance_evidence_fingerprint": "4" * 64,
        "risk_evidence_fingerprint": "5" * 64,
        "buying_power_evidence_fingerprint": "6" * 64,
        "credential_ownership_evidence_fingerprint": CRED_FP,
        "account_ownership_evidence_fingerprint": ACCT_FP,
        "prior_submission_state": None,
        "prior_attempt_reference": None,
        "reconciliation_reference": None,
        "reconciliation_required": False,
        "provider_send_execution_ready": True,
        "transport_authorized": False,
        "provider_call_performed": False,
        "actual_kt10000_post_performed": False,
        "credential_lookup_performed": False,
        "account_lookup_performed": False,
        "token_acquisition_performed": False,
        "automatic_retry_permitted": False,
        "retransmission_permitted": False,
        "readiness_fingerprint": "0" * 64,
    }
    values.update(overrides)
    snapshot = m.WatchlistOrderProviderSendExecutionReadinessSnapshot(**values)
    if "readiness_fingerprint" not in overrides:
        snapshot = replace(
            snapshot,
            readiness_fingerprint=m._readiness_fingerprint(snapshot),
        )
    return snapshot


def mutate_request(readiness, **changes):
    request = readiness.source_snapshot.request_snapshot
    body = changes.pop("body", request.body)
    values = vars(request).copy()
    values.update(changes)
    values["body"] = MappingProxyType(dict(body))
    new_request = SimpleNamespace(**values)
    if "materialization_fingerprint" not in changes:
        new_request.materialization_fingerprint = request_fp(new_request)
    new_source = SimpleNamespace(request_snapshot=new_request)
    m = p35()
    updated = replace(
        readiness,
        source_snapshot=new_source,
        phase30_materialization_fingerprint=new_request.materialization_fingerprint,
        source_attempt_ref=new_request.source_attempt_ref,
        authorization_evidence_ref=new_request.authorization_evidence_ref,
        readiness_fingerprint="0" * 64,
    )
    return replace(
        updated,
        readiness_fingerprint=m._readiness_fingerprint(updated),
    )


def make_approval(m, readiness, *, now=FIXED_NOW, **overrides):
    values = {
        "approval_id": "phase36-approval-1",
        "issued_at_utc": utc_text(now - timedelta(seconds=2)),
        "not_before_utc": utc_text(now - timedelta(seconds=1)),
        "expires_at_utc": utc_text(now + timedelta(seconds=60)),
        "readiness_fingerprint": readiness.readiness_fingerprint,
        "request_fingerprint": readiness.phase30_materialization_fingerprint,
        "source_attempt_ref": readiness.source_attempt_ref,
        "authorization_evidence_ref": readiness.authorization_evidence_ref,
        "scope_fingerprint": readiness.scope_fingerprint,
        "credential_ownership_evidence_fingerprint":
            readiness.credential_ownership_evidence_fingerprint,
        "account_ownership_evidence_fingerprint":
            readiness.account_ownership_evidence_fingerprint,
        "one_shot_authorized": True,
        "approval_fingerprint": "0" * 64,
    }
    values.update(overrides)
    evidence = m.Phase36SubmissionApprovalEvidence(**values)
    if "approval_fingerprint" not in overrides:
        evidence = replace(
            evidence,
            approval_fingerprint=m._approval_fingerprint(evidence),
        )
    return evidence


class Clock:
    def __init__(self, *values):
        self.values = list(values) or [FIXED_NOW]
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if len(self.values) > 1:
            return self.values.pop(0)
        return self.values[0]


class FakeResolver:
    def __init__(self, *, result=None, exc=None, event_log=None):
        self.result = result
        self.exc = exc
        self.calls = 0
        self.event_log = event_log

    async def resolve(self, **kwargs):
        self.calls += 1
        if self.event_log is not None:
            self.event_log.append("resolve")
        if self.exc is not None:
            raise self.exc
        if self.result is None:
            return {
                "mode": "demo",
                "credential_ref_id": kwargs["credential_ref_id"],
                "account_ref_id": kwargs["account_ref_id"],
                "credential_ownership_evidence_fingerprint": CRED_FP,
                "account_ownership_evidence_fingerprint": ACCT_FP,
            }
        return self.result


class FakeTokenProvider:
    def __init__(self, *, result=None, exc=None, event_log=None):
        self.result = result
        self.exc = exc
        self.calls = 0
        self.event_log = event_log

    async def acquire(self, *, resolved):
        self.calls += 1
        if self.event_log is not None:
            self.event_log.append("token")
        if self.exc is not None:
            raise self.exc
        if self.result is None:
            return {
                "token": "token-supersecret-123",
                "mode": resolved["mode"],
                "credential_ref_id": resolved["credential_ref_id"],
                "account_ref_id": resolved["account_ref_id"],
                "credential_ownership_evidence_fingerprint":
                    resolved["credential_ownership_evidence_fingerprint"],
                "account_ownership_evidence_fingerprint":
                    resolved["account_ownership_evidence_fingerprint"],
            }
        return self.result


class FakeRevalidator:
    def __init__(self, *, result=True, exc=None, event_log=None):
        self.result = result
        self.exc = exc
        self.calls = 0
        self.event_log = event_log

    async def validate(self, **kwargs):
        self.calls += 1
        if self.event_log is not None:
            self.event_log.append("revalidate")
        if self.exc is not None:
            raise self.exc
        return self.result


class FakeTransport:
    def __init__(
        self,
        *,
        response=None,
        exc=None,
        delay=0.0,
        event_log=None,
        entered_event=None,
    ):
        self.response = response or {
            "status_code": 200,
            "body": {
                "return_code": 0,
                "return_msg": "OK",
                "ord_no": "123456",
                "dmst_stex_tp": "KRX",
            },
        }
        self.exc = exc
        self.delay = delay
        self.calls = 0
        self.kwargs = []
        self.event_log = event_log
        self.entered_event = entered_event

    async def post_order(self, **kwargs):
        self.calls += 1
        self.kwargs.append(kwargs)
        if self.event_log is not None:
            self.event_log.append("transport")
        if self.entered_event is not None:
            self.entered_event.set()
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc is not None:
            raise self.exc
        return self.response


class FakeCleanup:
    def __init__(self, *, exc=None):
        self.exc = exc
        self.calls = 0

    async def cleanup(self):
        self.calls += 1
        if self.exc is not None:
            raise self.exc


def make_registry(
    m,
    *,
    durable=False,
    test_only=True,
    cas_result=True,
    claim_exc=None,
    cas_exc=None,
    finalize_fail_states=(),
    finalize_exc_states=(),
    event_log=None,
):
    class Registry(m.Phase36AtomicSubmissionRegistry):
        def __init__(self):
            self.states = {}
            self.receipts = {}
            self.claims = {}
            self.lock = asyncio.Lock()
            self.claim_calls = 0
            self.cas_calls = 0
            self.finalize_calls = 0

        @property
        def is_durable(self):
            return durable

        @property
        def test_only(self):
            return test_only

        async def claim(self, *, attempt_fingerprint, claim_fingerprint):
            self.claim_calls += 1
            if event_log is not None:
                event_log.append("claim")
            if claim_exc is not None:
                raise claim_exc
            async with self.lock:
                if attempt_fingerprint in self.states:
                    return False
                self.states[attempt_fingerprint] = (
                    m.Phase36SubmissionRegistryState.CLAIMED_PRE_SEND
                )
                self.claims[attempt_fingerprint] = claim_fingerprint
                return True

        async def compare_and_set(
            self,
            *,
            attempt_fingerprint,
            expected_state,
            new_state,
        ):
            self.cas_calls += 1
            if event_log is not None:
                event_log.append("cas")
            if cas_exc is not None:
                raise cas_exc
            async with self.lock:
                if not cas_result:
                    return False
                if self.states.get(attempt_fingerprint) is not expected_state:
                    return False
                self.states[attempt_fingerprint] = new_state
                return True

        async def finalize(
            self,
            *,
            attempt_fingerprint,
            expected_state,
            terminal_state,
            receipt,
        ):
            self.finalize_calls += 1
            if terminal_state in finalize_exc_states:
                raise RuntimeError("registry-finalize-secret-token")
            if terminal_state in finalize_fail_states:
                return False
            async with self.lock:
                if self.states.get(attempt_fingerprint) is not expected_state:
                    return False
                self.states[attempt_fingerprint] = terminal_state
                self.receipts[attempt_fingerprint] = receipt
                return True

    return Registry()


def make_context(
    m,
    readiness,
    *,
    resolver=None,
    token_provider=None,
    revalidator=None,
    transport=None,
    cleanup=None,
    clock=None,
    **overrides,
):
    values = {
        "mode": "demo",
        "base_url": "https://mockapi.kiwoom.com",
        "credential_ref_id": "credref:demo-1",
        "account_ref_id": "acctref:demo-1",
        "credential_ownership_evidence_fingerprint":
            readiness.credential_ownership_evidence_fingerprint,
        "account_ownership_evidence_fingerprint":
            readiness.account_ownership_evidence_fingerprint,
        "runtime_credential_account_access_authorized": True,
        "auth_network_authorized": True,
        "provider_network_authorized": True,
        "actual_kt10000_post_authorized": True,
        "test_execution": True,
        "timeout_seconds": 1.0,
        "resolver": resolver or FakeResolver(),
        "token_provider": token_provider or FakeTokenProvider(),
        "readiness_revalidator": revalidator or FakeRevalidator(),
        "transport": transport or FakeTransport(),
        "cleanup": cleanup or FakeCleanup(),
        "clock": clock or Clock(FIXED_NOW),
    }
    values.update(overrides)
    return m.Phase36ProviderExecutionContext(**values)


async def submit_with(
    *,
    readiness=None,
    approval=None,
    context=None,
    registry=None,
):
    m = subject()
    readiness = readiness or make_readiness()
    approval = approval or make_approval(m, readiness)
    context = context or make_context(m, readiness)
    registry = registry or make_registry(m)
    receipt = await m.submit_demo_watchlist_order_once(
        readiness,
        approval,
        context,
        registry,
    )
    return m, readiness, approval, context, registry, receipt


class Phase36PublicApiTests(unittest.TestCase):
    def test_001_public_api_exact_eight_symbols(self):
        m = subject()
        self.assertEqual(tuple(m.__all__), PUBLIC_SYMBOLS)
        names = tuple(
            name
            for name in vars(m)
            if not name.startswith("_") and name != "__builtins__"
        )
        self.assertEqual(names, PUBLIC_SYMBOLS)

    def test_002_error_is_runtime_error(self):
        m = subject()
        self.assertEqual(
            m.WatchlistOrderProviderSubmissionBoundaryError.__bases__,
            (RuntimeError,),
        )

    def test_003_outcome_enum_exact(self):
        m = subject()
        self.assertEqual(
            tuple((x.name, x.value) for x in m.KiwoomOrderProviderSubmissionOutcome),
            (
                ("BLOCKED_BEFORE_SEND", "BLOCKED_BEFORE_SEND"),
                ("CONFIRMED_ACCEPTED", "CONFIRMED_ACCEPTED"),
                ("CONFIRMED_NOT_ACCEPTED", "CONFIRMED_NOT_ACCEPTED"),
                ("AMBIGUOUS_UNRESOLVED", "AMBIGUOUS_UNRESOLVED"),
            ),
        )

    def test_004_registry_state_enum_exact(self):
        m = subject()
        self.assertEqual(
            tuple(x.value for x in m.Phase36SubmissionRegistryState),
            (
                "AVAILABLE",
                "CLAIMED_PRE_SEND",
                "IN_FLIGHT",
                "ABORTED_BEFORE_SEND",
                "CONFIRMED_ACCEPTED",
                "CONFIRMED_NOT_ACCEPTED",
                "AMBIGUOUS_UNRESOLVED",
            ),
        )

    def test_005_approval_dataclass_exact_fields_frozen_slots(self):
        m = subject()
        cls = m.Phase36SubmissionApprovalEvidence
        self.assertEqual(tuple(f.name for f in dataclasses.fields(cls)), APPROVAL_FIELDS)
        self.assertTrue(cls.__dataclass_params__.frozen)
        self.assertIn("__slots__", vars(cls))

    def test_006_context_dataclass_exact_fields_frozen_secret_safe_repr(self):
        m = subject()
        cls = m.Phase36ProviderExecutionContext
        self.assertEqual(tuple(f.name for f in dataclasses.fields(cls)), CONTEXT_FIELDS)
        self.assertTrue(cls.__dataclass_params__.frozen)
        r = make_readiness()
        c = make_context(m, r)
        text = repr(c)
        self.assertNotIn("FakeTransport", text)
        self.assertNotIn("token-supersecret", text)

    def test_007_registry_is_abstract_with_atomic_surface(self):
        m = subject()
        cls = m.Phase36AtomicSubmissionRegistry
        self.assertTrue(inspect.isabstract(cls))
        self.assertEqual(
            set(cls.__abstractmethods__),
            {"is_durable", "test_only", "claim", "compare_and_set", "finalize"},
        )

    def test_008_receipt_fields_frozen_and_submit_signature_async(self):
        m = subject()
        cls = m.KiwoomOrderProviderSubmissionReceipt
        self.assertEqual(tuple(f.name for f in dataclasses.fields(cls)), RECEIPT_FIELDS)
        self.assertTrue(cls.__dataclass_params__.frozen)
        fn = m.submit_demo_watchlist_order_once
        self.assertTrue(inspect.iscoroutinefunction(fn))
        self.assertEqual(
            tuple(inspect.signature(fn).parameters),
            (
                "readiness_snapshot",
                "submission_approval",
                "execution_context",
                "submission_registry",
            ),
        )
        self.assertTrue(
            all(
                p.default is inspect.Parameter.empty
                for p in inspect.signature(fn).parameters.values()
            )
        )


class Phase36OfficialMappingTests(unittest.IsolatedAsyncioTestCase):
    async def test_009_limit_order_exact_endpoint_headers_body(self):
        m, r, a, c, reg, out = await submit_with()
        t = c.transport
        self.assertEqual(out.outcome, m.KiwoomOrderProviderSubmissionOutcome.CONFIRMED_ACCEPTED)
        self.assertEqual(t.calls, 1)
        kw = t.kwargs[0]
        self.assertEqual(kw["base_url"], "https://mockapi.kiwoom.com")
        self.assertEqual(kw["path"], "/api/dostk/ordr")
        self.assertEqual(
            kw["headers"],
            {
                "authorization": "Bearer token-supersecret-123",
                "api-id": "kt10000",
                "Content-Type": "application/json;charset=UTF-8",
            },
        )
        self.assertEqual(
            kw["body"],
            {
                "dmst_stex_tp": "KRX",
                "stk_cd": "005930",
                "ord_qty": "3",
                "ord_uv": "64500",
                "trde_tp": "0",
                "cond_uv": "",
            },
        )

    async def test_010_market_order_preserves_empty_ord_uv(self):
        request = make_request(
            body=MappingProxyType(
                {
                    "dmst_stex_tp": "KRX",
                    "stk_cd": "005930",
                    "ord_qty": "3",
                    "ord_uv": "",
                    "trde_tp": "3",
                    "cond_uv": "",
                }
            )
        )
        request.materialization_fingerprint = request_fp(request)
        r = make_readiness(request=request)
        m = subject()
        c = make_context(m, r)
        out = await m.submit_demo_watchlist_order_once(
            r, make_approval(m, r), c, make_registry(m)
        )
        self.assertEqual(out.outcome, m.KiwoomOrderProviderSubmissionOutcome.CONFIRMED_ACCEPTED)
        self.assertEqual(c.transport.kwargs[0]["body"]["ord_uv"], "")

    async def test_011_no_continuation_or_header_override_surface(self):
        _, _, _, c, _, _ = await submit_with()
        kw = c.transport.kwargs[0]
        self.assertNotIn("cont-yn", kw["headers"])
        self.assertNotIn("next-key", kw["headers"])
        self.assertEqual(set(kw), {"base_url", "path", "headers", "body", "retry_on_auth_failure"})

    async def test_012_wrong_execution_mode_blocks_zero_send(self):
        m = subject(); r = make_readiness()
        c = make_context(m, r, mode="prod")
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.outcome.value, "BLOCKED_BEFORE_SEND")
        self.assertEqual(c.transport.calls, 0)

    async def test_013_wrong_base_url_blocks_zero_send(self):
        m = subject(); r = make_readiness()
        c = make_context(m, r, base_url="https://api.kiwoom.com")
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)
        self.assertEqual(c.transport.calls, 0)

    async def test_014_wrong_request_environment_blocks(self):
        r = mutate_request(make_readiness(), environment="prod")
        m = subject(); c = make_context(m, r)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.outcome.value, "BLOCKED_BEFORE_SEND")

    async def test_015_wrong_request_side_blocks(self):
        r = mutate_request(make_readiness(), side="SELL")
        m = subject(); c = make_context(m, r)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_016_wrong_request_exchange_blocks(self):
        r = mutate_request(make_readiness(), exchange="NXT")
        m = subject(); c = make_context(m, r)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_017_wrong_api_or_path_blocks(self):
        r = mutate_request(make_readiness(), api_id="ka10001")
        m = subject(); c = make_context(m, r)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_018_wrong_body_contract_blocks(self):
        body = dict(make_readiness().source_snapshot.request_snapshot.body)
        body["dmst_stex_tp"] = "NXT"
        r = mutate_request(make_readiness(), body=body)
        m = subject(); c = make_context(m, r)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.outcome.value, "BLOCKED_BEFORE_SEND")


class Phase36ReadinessApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def _blocked(self, r, a=None, c=None, reg=None):
        m = subject()
        a = a if a is not None else (make_approval(m, r) if type(r) is p35().WatchlistOrderProviderSendExecutionReadinessSnapshot else object())
        c = c or (make_context(m, r) if type(r) is p35().WatchlistOrderProviderSendExecutionReadinessSnapshot else None)
        reg = reg or make_registry(m)
        out = await m.submit_demo_watchlist_order_once(r, a, c, reg)
        self.assertEqual(out.outcome.value, "BLOCKED_BEFORE_SEND")
        self.assertEqual(out.transport_attempt_count, 0)
        if c is not None:
            self.assertEqual(c.transport.calls, 0)

    async def test_019_wrong_readiness_type_blocks(self):
        await self._blocked(object())

    async def test_020_nonready_decision_blocks(self):
        m35 = p35()
        r = make_readiness(
            decision=m35.KiwoomOrderProviderSendExecutionReadinessDecision.DENIED,
            primary_reason_code=m35.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MISSING,
            all_reason_codes=(m35.KiwoomOrderProviderSendExecutionReadinessReason.EVIDENCE_MISSING,),
            provider_send_execution_ready=False,
        )
        r = replace(r, readiness_fingerprint=m35._readiness_fingerprint(r))
        await self._blocked(r)

    async def test_021_readiness_fingerprint_mismatch_blocks(self):
        await self._blocked(replace(make_readiness(), readiness_fingerprint="f" * 64))

    async def test_022_request_fingerprint_mismatch_blocks(self):
        r = replace(make_readiness(), phase30_materialization_fingerprint="f" * 64)
        r = replace(r, readiness_fingerprint=p35()._readiness_fingerprint(r))
        await self._blocked(r)

    async def test_023_wrong_approval_type_blocks(self):
        m = subject(); r = make_readiness(); c = make_context(m, r)
        out = await m.submit_demo_watchlist_order_once(r, object(), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_024_expired_approval_blocks(self):
        m = subject(); r = make_readiness()
        a = make_approval(m, r, expires_at_utc=utc_text(FIXED_NOW))
        a = replace(a, approval_fingerprint=m._approval_fingerprint(a))
        await self._blocked(r, a=a, c=make_context(m, r))

    async def test_025_not_yet_valid_approval_blocks(self):
        m = subject(); r = make_readiness()
        a = make_approval(
            m,
            r,
            not_before_utc=utc_text(FIXED_NOW + timedelta(seconds=10)),
            expires_at_utc=utc_text(FIXED_NOW + timedelta(seconds=20)),
        )
        a = replace(a, approval_fingerprint=m._approval_fingerprint(a))
        await self._blocked(r, a=a, c=make_context(m, r))

    async def test_026_one_shot_false_blocks(self):
        m = subject(); r = make_readiness()
        a = make_approval(m, r, one_shot_authorized=False)
        a = replace(a, approval_fingerprint=m._approval_fingerprint(a))
        await self._blocked(r, a=a, c=make_context(m, r))

    async def test_027_approval_fingerprint_mismatch_blocks(self):
        m = subject(); r = make_readiness()
        a = replace(make_approval(m, r), approval_fingerprint="f" * 64)
        await self._blocked(r, a=a, c=make_context(m, r))

    async def test_028_approval_readiness_binding_mismatch_blocks(self):
        m = subject(); r = make_readiness()
        a = make_approval(m, r, readiness_fingerprint="f" * 64)
        a = replace(a, approval_fingerprint=m._approval_fingerprint(a))
        await self._blocked(r, a=a, c=make_context(m, r))

    async def test_029_scope_binding_mismatch_blocks(self):
        m = subject(); r = make_readiness()
        a = make_approval(m, r, scope_fingerprint="f" * 64)
        a = replace(a, approval_fingerprint=m._approval_fingerprint(a))
        await self._blocked(r, a=a, c=make_context(m, r))

    async def test_030_ownership_fingerprint_binding_mismatch_blocks(self):
        m = subject(); r = make_readiness()
        a = make_approval(m, r, credential_ownership_evidence_fingerprint="f" * 64)
        a = replace(a, approval_fingerprint=m._approval_fingerprint(a))
        await self._blocked(r, a=a, c=make_context(m, r))


class Phase36PreflightTests(unittest.IsolatedAsyncioTestCase):
    async def test_031_ordered_preflight_resolve_token_revalidate_claim_cas_transport(self):
        _stage7_module = __import__(
            "kiwoom_trading_system.brokers.kiwoom.rest."
            "watchlist_order_provider_submission_boundary",
            fromlist=["*"],
        )
        Resolver = getattr(
            _stage7_module,
            "_KiwoomSdkLocalCredentialAccountResolver",
        )
        TokenProvider = getattr(
            _stage7_module,
            "_KiwoomSdkCachedTokenProvider",
        )

        class LocalProfile:
            def __init__(self, alias="demo-1", mode="demo"):
                self.alias = alias
                self.mode = mode

        class LocalSecretProvider:
            def __init__(self):
                self.calls = 0

            def get_credentials(self, mode):
                self.calls += 1
                self.mode = mode
                return object()

        profile_calls = []

        def profile_loader(alias):
            profile_calls.append(alias)
            return LocalProfile(alias=alias, mode="demo")

        secret_provider = LocalSecretProvider()

        resolver = Resolver(
            profile_alias="demo-1",
            credential_ref_id="credref:demo-1",
            account_ref_id="acctref:demo-1",
            credential_ownership_evidence_fingerprint=CRED_FP,
            account_ownership_evidence_fingerprint=ACCT_FP,
            profile_loader=profile_loader,
            secret_provider=secret_provider,
            credential_fingerprint=lambda credentials: CRED_FP,
        )

        resolved = await resolver.resolve(
            credential_ref_id="credref:demo-1",
            account_ref_id="acctref:demo-1",
        )

        self.assertEqual(
            resolved,
            {
                "mode": "demo",
                "credential_ref_id": "credref:demo-1",
                "account_ref_id": "acctref:demo-1",
                "credential_ownership_evidence_fingerprint": CRED_FP,
                "account_ownership_evidence_fingerprint": ACCT_FP,
            },
        )
        self.assertEqual(profile_calls, ["demo-1"])
        self.assertEqual(secret_provider.calls, 1)
        self.assertEqual(secret_provider.mode, "demo")
        self.assertNotIn("credref:demo-1", repr(resolver))
        self.assertNotIn("acctref:demo-1", repr(resolver))

        bad_profile_resolver = Resolver(
            profile_alias="demo-1",
            credential_ref_id="credref:demo-1",
            account_ref_id="acctref:demo-1",
            credential_ownership_evidence_fingerprint=CRED_FP,
            account_ownership_evidence_fingerprint=ACCT_FP,
            profile_loader=lambda alias: LocalProfile(
                alias="other",
                mode="demo",
            ),
            secret_provider=LocalSecretProvider(),
            credential_fingerprint=lambda credentials: CRED_FP,
        )

        with self.assertRaisesRegex(
            _stage7_module.WatchlistOrderProviderSubmissionBoundaryError,
            "STAGE7_DEMO_PROFILE_BINDING_MISMATCH",
        ):
            await bad_profile_resolver.resolve(
                credential_ref_id="credref:demo-1",
                account_ref_id="acctref:demo-1",
            )

        bad_credential_resolver = Resolver(
            profile_alias="demo-1",
            credential_ref_id="credref:demo-1",
            account_ref_id="acctref:demo-1",
            credential_ownership_evidence_fingerprint=CRED_FP,
            account_ownership_evidence_fingerprint=ACCT_FP,
            profile_loader=profile_loader,
            secret_provider=LocalSecretProvider(),
            credential_fingerprint=lambda credentials: "f" * 64,
        )

        with self.assertRaisesRegex(
            _stage7_module.WatchlistOrderProviderSubmissionBoundaryError,
            "STAGE7_CREDENTIAL_OWNERSHIP_MISMATCH",
        ):
            await bad_credential_resolver.resolve(
                credential_ref_id="credref:demo-1",
                account_ref_id="acctref:demo-1",
            )

        class LocalTokenRecord:
            def __init__(
                self,
                *,
                credential_fingerprint=CRED_FP,
                expires_at=None,
            ):
                self.access_token = "token-supersecret-123"
                self.token_type = "bearer"
                self.expires_at = (
                    expires_at
                    if expires_at is not None
                    else FIXED_NOW + timedelta(hours=1)
                )
                self.mode = "demo"
                self.profile = "demo-1"
                self.credential_fingerprint = credential_fingerprint

        class LocalTokenStore:
            def __init__(self, record):
                self.record = record
                self.peek_calls = []

            def peek(self, mode, *, profile=None):
                self.peek_calls.append((mode, profile))
                return self.record

            def load(self, *args, **kwargs):
                raise AssertionError("STAGE7_LOAD_MUST_NOT_BE_USED")

            def clear(self, *args, **kwargs):
                raise AssertionError("STAGE7_CLEAR_MUST_NOT_BE_USED")

            def save(self, *args, **kwargs):
                raise AssertionError("STAGE7_SAVE_MUST_NOT_BE_USED")

        token_store = LocalTokenStore(LocalTokenRecord())

        token_provider = TokenProvider(
            profile_alias="demo-1",
            token_store=token_store,
            now_utc=lambda: FIXED_NOW,
            minimum_validity_seconds=600,
        )

        token_material = await token_provider.acquire(
            resolved=resolved,
        )

        self.assertEqual(
            token_material,
            {
                "token": "token-supersecret-123",
                "mode": "demo",
                "credential_ref_id": "credref:demo-1",
                "account_ref_id": "acctref:demo-1",
                "credential_ownership_evidence_fingerprint": CRED_FP,
                "account_ownership_evidence_fingerprint": ACCT_FP,
            },
        )
        self.assertEqual(
            token_store.peek_calls,
            [("demo", "demo-1")],
        )
        self.assertNotIn(
            "token-supersecret-123",
            repr(token_provider),
        )

        with self.assertRaisesRegex(
            _stage7_module.WatchlistOrderProviderSubmissionBoundaryError,
            "STAGE7_CACHED_TOKEN_MISSING",
        ):
            await TokenProvider(
                profile_alias="demo-1",
                token_store=LocalTokenStore(None),
                now_utc=lambda: FIXED_NOW,
            ).acquire(resolved=resolved)

        with self.assertRaisesRegex(
            _stage7_module.WatchlistOrderProviderSubmissionBoundaryError,
            "STAGE7_CACHED_TOKEN_BINDING_MISMATCH",
        ):
            await TokenProvider(
                profile_alias="demo-1",
                token_store=LocalTokenStore(
                    LocalTokenRecord(
                        credential_fingerprint="f" * 64,
                    )
                ),
                now_utc=lambda: FIXED_NOW,
            ).acquire(resolved=resolved)

        with self.assertRaisesRegex(
            _stage7_module.WatchlistOrderProviderSubmissionBoundaryError,
            "STAGE7_CACHED_TOKEN_NOT_REUSABLE",
        ):
            await TokenProvider(
                profile_alias="demo-1",
                token_store=LocalTokenStore(
                    LocalTokenRecord(
                        expires_at=FIXED_NOW + timedelta(seconds=600),
                    )
                ),
                now_utc=lambda: FIXED_NOW,
                minimum_validity_seconds=600,
            ).acquire(resolved=resolved)
        m = subject(); r = make_readiness(); events = []
        c = make_context(
            m, r,
            resolver=FakeResolver(event_log=events),
            token_provider=FakeTokenProvider(event_log=events),
            revalidator=FakeRevalidator(event_log=events),
            transport=FakeTransport(event_log=events),
        )
        reg = make_registry(m, event_log=events)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, reg)
        self.assertEqual(out.outcome.value, "CONFIRMED_ACCEPTED")
        self.assertEqual(events[:6], ["resolve", "token", "revalidate", "claim", "cas", "transport"])

    async def test_032_resolver_failure_blocks_zero_send(self):
        m = subject(); r = make_readiness()
        c = make_context(m, r, resolver=FakeResolver(exc=RuntimeError("secret")))
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_033_resolver_provenance_mismatch_blocks(self):
        m = subject(); r = make_readiness()
        bad = {
            "mode": "demo",
            "credential_ref_id": "other",
            "account_ref_id": "acctref:demo-1",
            "credential_ownership_evidence_fingerprint": CRED_FP,
            "account_ownership_evidence_fingerprint": ACCT_FP,
        }
        c = make_context(m, r, resolver=FakeResolver(result=bad))
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_034_token_acquired_before_claim(self):
        m = subject(); r = make_readiness(); events = []
        c = make_context(m, r, token_provider=FakeTokenProvider(event_log=events))
        reg = make_registry(m, event_log=events)
        await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, reg)
        self.assertLess(events.index("token"), events.index("claim"))

    async def test_035_token_failure_blocks_zero_send(self):
        m = subject(); r = make_readiness()
        c = make_context(m, r, token_provider=FakeTokenProvider(exc=RuntimeError("auth")))
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_036_token_provenance_mismatch_blocks(self):
        m = subject(); r = make_readiness()
        bad = {
            "token": "secret",
            "mode": "demo",
            "credential_ref_id": "other",
            "account_ref_id": "acctref:demo-1",
            "credential_ownership_evidence_fingerprint": CRED_FP,
            "account_ownership_evidence_fingerprint": ACCT_FP,
        }
        c = make_context(m, r, token_provider=FakeTokenProvider(result=bad))
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, make_registry(m))
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_037_revalidation_false_blocks_before_claim(self):
        m = subject(); r = make_readiness()
        c = make_context(m, r, revalidator=FakeRevalidator(result=False))
        reg = make_registry(m)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, reg)
        self.assertEqual(out.transport_attempt_count, 0)
        self.assertEqual(reg.claim_calls, 0)

    async def test_038_approval_expiry_after_token_blocks_before_claim(self):
        m = subject(); r = make_readiness()
        a = make_approval(m, r, expires_at_utc=utc_text(FIXED_NOW + timedelta(seconds=5)))
        a = replace(a, approval_fingerprint=m._approval_fingerprint(a))
        clock = Clock(FIXED_NOW, FIXED_NOW, FIXED_NOW + timedelta(seconds=6))
        c = make_context(m, r, clock=clock)
        reg = make_registry(m)
        out = await m.submit_demo_watchlist_order_once(r, a, c, reg)
        self.assertEqual(out.transport_attempt_count, 0)
        self.assertEqual(reg.claim_calls, 0)

    async def test_039_test_only_registry_blocked_for_actual_execution_context(self):
        m = subject(); r = make_readiness()
        c = make_context(m, r, test_execution=False)
        reg = make_registry(m, durable=False, test_only=True)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, reg)
        self.assertEqual(out.transport_attempt_count, 0)

    async def test_040_durable_registry_allows_production_capability_with_fake_transport(self):
        m = subject(); r = make_readiness()
        c = make_context(m, r, test_execution=False)
        reg = make_registry(m, durable=True, test_only=False)
        out = await m.submit_demo_watchlist_order_once(r, make_approval(m, r), c, reg)
        self.assertEqual(out.outcome.value, "CONFIRMED_ACCEPTED")
        self.assertEqual(c.transport.calls, 1)


class Phase36RegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_041_transition_table_exact(self):
        m = subject()
        pairs = {(a.value, b.value) for a, b in m._ALLOWED_TRANSITIONS}
        self.assertEqual(
            pairs,
            {
                ("AVAILABLE", "CLAIMED_PRE_SEND"),
                ("CLAIMED_PRE_SEND", "IN_FLIGHT"),
                ("CLAIMED_PRE_SEND", "ABORTED_BEFORE_SEND"),
                ("IN_FLIGHT", "CONFIRMED_ACCEPTED"),
                ("IN_FLIGHT", "CONFIRMED_NOT_ACCEPTED"),
                ("IN_FLIGHT", "AMBIGUOUS_UNRESOLVED"),
            },
        )

    async def test_042_claim_moves_to_claimed_pre_send(self):
        m = subject(); reg = make_registry(m)
        ok = await reg.claim(attempt_fingerprint="a"*64, claim_fingerprint="b"*64)
        self.assertTrue(ok)
        self.assertIs(reg.states["a"*64], m.Phase36SubmissionRegistryState.CLAIMED_PRE_SEND)

    async def test_043_duplicate_claim_rejected(self):
        m = subject(); reg = make_registry(m)
        self.assertTrue(await reg.claim(attempt_fingerprint="a"*64, claim_fingerprint="b"*64))
        self.assertFalse(await reg.claim(attempt_fingerprint="a"*64, claim_fingerprint="b"*64))

    async def test_044_claimed_to_inflight_cas(self):
        m = subject(); reg = make_registry(m)
        await reg.claim(attempt_fingerprint="a"*64, claim_fingerprint="b"*64)
        self.assertTrue(await reg.compare_and_set(
            attempt_fingerprint="a"*64,
            expected_state=m.Phase36SubmissionRegistryState.CLAIMED_PRE_SEND,
            new_state=m.Phase36SubmissionRegistryState.IN_FLIGHT,
        ))

    async def test_045_wrong_expected_state_cas_fails(self):
        m = subject(); reg = make_registry(m)
        await reg.claim(attempt_fingerprint="a"*64, claim_fingerprint="b"*64)
        self.assertFalse(await reg.compare_and_set(
            attempt_fingerprint="a"*64,
            expected_state=m.Phase36SubmissionRegistryState.IN_FLIGHT,
            new_state=m.Phase36SubmissionRegistryState.CONFIRMED_ACCEPTED,
        ))

    async def test_046_accepted_finalizes_terminal(self):
        m, _, _, _, reg, out = await submit_with()
        self.assertIs(reg.states[out.attempt_fingerprint], m.Phase36SubmissionRegistryState.CONFIRMED_ACCEPTED)

    async def test_047_rejected_finalizes_terminal(self):
        m = subject(); r = make_readiness()
        t = FakeTransport(response={"status_code": 400, "body": {"return_code": -10, "return_msg": "reject"}})
        c = make_context(m, r, transport=t); reg=make_registry(m)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertIs(reg.states[out.attempt_fingerprint], m.Phase36SubmissionRegistryState.CONFIRMED_NOT_ACCEPTED)

    async def test_048_ambiguous_finalizes_terminal(self):
        m = subject(); r = make_readiness()
        t = FakeTransport(response={"status_code": 500, "body": None})
        c=make_context(m,r,transport=t); reg=make_registry(m)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertIs(reg.states[out.attempt_fingerprint], m.Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED)

    async def test_049_inflight_cas_failure_aborts_zero_send(self):
        m=subject(); r=make_readiness(); c=make_context(m,r); reg=make_registry(m,cas_result=False)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(out.transport_attempt_count,0)
        self.assertEqual(c.transport.calls,0)
        self.assertIs(reg.states[out.attempt_fingerprint], m.Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND)

    async def test_050_concurrent_same_attempt_exactly_one_transport(self):
        m=subject(); r=make_readiness(); t=FakeTransport(delay=0.02)
        c=make_context(m,r,transport=t); reg=make_registry(m); a=make_approval(m,r)
        first, second = await asyncio.gather(
            m.submit_demo_watchlist_order_once(r,a,c,reg),
            m.submit_demo_watchlist_order_once(r,a,c,reg),
        )
        self.assertEqual(t.calls,1)
        self.assertEqual(sorted(x.transport_attempt_count for x in (first,second)),[0,1])

    async def test_051_replayed_completed_claim_cannot_send_again(self):
        m=subject(); r=make_readiness(); t=FakeTransport(); c=make_context(m,r,transport=t)
        reg=make_registry(m); a=make_approval(m,r)
        one=await m.submit_demo_watchlist_order_once(r,a,c,reg)
        two=await m.submit_demo_watchlist_order_once(r,a,c,reg)
        self.assertEqual(one.transport_attempt_count,1)
        self.assertEqual(two.transport_attempt_count,0)
        self.assertEqual(t.calls,1)

    async def test_052_claim_storage_exception_blocks_zero_send(self):
        m=subject(); r=make_readiness(); c=make_context(m,r)
        reg=make_registry(m,claim_exc=RuntimeError("ledger unavailable"))
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(out.outcome.value,"BLOCKED_BEFORE_SEND")
        self.assertEqual(c.transport.calls,0)

    async def test_053_test_fake_registry_allowed_only_in_test_execution(self):
        m=subject(); r=make_readiness()
        reg=make_registry(m,durable=False,test_only=True)
        c=make_context(m,r,test_execution=True)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(out.transport_attempt_count,1)

    async def test_054_nondurable_registry_blocked_when_not_test_execution(self):
        m=subject(); r=make_readiness()
        reg=make_registry(m,durable=False,test_only=False)
        c=make_context(m,r,test_execution=False)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(out.transport_attempt_count,0)


class Phase36OneShotTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_055_happy_path_exactly_one_call(self):
        _,_,_,c,_,out=await submit_with()
        self.assertEqual(c.transport.calls,1); self.assertEqual(out.transport_attempt_count,1)

    async def test_056_rejection_exactly_one_call(self):
        m=subject(); r=make_readiness(); t=FakeTransport(response={"status_code":400,"body":{"return_code":-1,"return_msg":"no"}})
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(t.calls,1); self.assertEqual(out.transport_attempt_count,1)

    async def test_057_timeout_never_retries(self):
        m=subject(); r=make_readiness(); t=FakeTransport(delay=0.05)
        c=make_context(m,r,transport=t,timeout_seconds=0.005)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(t.calls,1); self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")

    async def test_058_connection_reset_never_retries(self):
        m=subject(); r=make_readiness(); t=FakeTransport(exc=ConnectionResetError("reset"))
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(t.calls,1); self.assertEqual(out.transport_attempt_count,1)

    async def test_059_http_error_with_definitive_provider_rejection_no_retry(self):
        m=subject(); r=make_readiness(); t=FakeTransport(response={"status_code":500,"body":{"return_code":-300,"return_msg":"rejected"}})
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(out.outcome.value,"CONFIRMED_NOT_ACCEPTED"); self.assertEqual(t.calls,1)

    async def test_060_auth_rejection_with_provider_body_no_retry(self):
        m=subject(); r=make_readiness(); t=FakeTransport(response={"status_code":401,"body":{"return_code":"-101","return_msg":"auth"}})
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(out.outcome.value,"CONFIRMED_NOT_ACCEPTED"); self.assertEqual(t.calls,1)

    async def test_061_retry_on_auth_failure_explicit_false(self):
        _,_,_,c,_,_=await submit_with()
        self.assertIs(c.transport.kwargs[0]["retry_on_auth_failure"],False)

    async def test_062_completed_claim_second_call_zero_send(self):
        m=subject(); r=make_readiness(); t=FakeTransport(); c=make_context(m,r,transport=t)
        reg=make_registry(m); a=make_approval(m,r)
        await m.submit_demo_watchlist_order_once(r,a,c,reg)
        second=await m.submit_demo_watchlist_order_once(r,a,c,reg)
        self.assertEqual(second.transport_attempt_count,0); self.assertEqual(t.calls,1)

    async def test_063_token_expiry_provider_rejection_never_retries(self):
        m=subject(); r=make_readiness(); t=FakeTransport(response={"status_code":200,"body":{"return_code":-100,"return_msg":"token expired"}})
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(out.outcome.value,"CONFIRMED_NOT_ACCEPTED"); self.assertEqual(t.calls,1)

    async def test_064_unknown_transport_exception_never_retries(self):
        m=subject(); r=make_readiness(); t=FakeTransport(exc=RuntimeError("unknown token-supersecret-123"))
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED"); self.assertEqual(t.calls,1)


class Phase36OutcomeTests(unittest.IsolatedAsyncioTestCase):
    async def _response(self, body):
        m=subject(); r=make_readiness(); t=FakeTransport(response={"status_code":200,"body":body})
        c=make_context(m,r,transport=t)
        return m, await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))

    async def test_065_bool_return_code_invalid(self):
        m,out=await self._response({"return_code":True,"ord_no":"1"})
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED"); self.assertIsNone(out.normalized_return_code)

    async def test_066_none_return_code_absent(self):
        _,out=await self._response({"return_code":None})
        self.assertIsNone(out.normalized_return_code); self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")

    async def test_067_blank_return_code_absent(self):
        _,out=await self._response({"return_code":"  "})
        self.assertIsNone(out.normalized_return_code)

    async def test_068_nonnumeric_return_code_absent(self):
        _,out=await self._response({"return_code":"abc"})
        self.assertIsNone(out.normalized_return_code)

    async def test_069_int_zero_with_order_number_accepted(self):
        _,out=await self._response({"return_code":0,"ord_no":"123","dmst_stex_tp":"KRX"})
        self.assertEqual(out.outcome.value,"CONFIRMED_ACCEPTED"); self.assertEqual(out.normalized_return_code,0)

    async def test_070_numeric_string_zero_accepted(self):
        _,out=await self._response({"return_code":"0","ord_no":"123"})
        self.assertEqual(out.outcome.value,"CONFIRMED_ACCEPTED")

    async def test_071_whitespace_numeric_zero_accepted(self):
        _,out=await self._response({"return_code":" 0 ","ord_no":" 123 "})
        self.assertEqual(out.provider_order_no,"123"); self.assertEqual(out.outcome.value,"CONFIRMED_ACCEPTED")

    async def test_072_nonzero_int_without_order_number_rejected(self):
        _,out=await self._response({"return_code":-1,"return_msg":"reject"})
        self.assertEqual(out.outcome.value,"CONFIRMED_NOT_ACCEPTED")

    async def test_073_nonzero_numeric_string_without_order_number_rejected(self):
        _,out=await self._response({"return_code":"42"})
        self.assertEqual(out.normalized_return_code,42); self.assertEqual(out.outcome.value,"CONFIRMED_NOT_ACCEPTED")

    async def test_074_zero_missing_order_number_ambiguous(self):
        _,out=await self._response({"return_code":0})
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")

    async def test_075_nonzero_with_order_number_conflict_ambiguous(self):
        _,out=await self._response({"return_code":-1,"ord_no":"123"})
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")

    async def test_076_exchange_conflict_ambiguous(self):
        _,out=await self._response({"return_code":0,"ord_no":"123","dmst_stex_tp":"NXT"})
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")


class SentinelBaseException(BaseException):
    pass


class Phase36FailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_077_timeout_finalizes_ambiguous(self):
        m=subject(); r=make_readiness(); t=FakeTransport(delay=0.05)
        c=make_context(m,r,transport=t,timeout_seconds=0.005); reg=make_registry(m)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertIs(reg.states[out.attempt_fingerprint],m.Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED)

    async def test_078_network_error_finalizes_ambiguous(self):
        m=subject(); r=make_readiness(); c=make_context(m,r,transport=FakeTransport(exc=OSError("net"))); reg=make_registry(m)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")

    async def test_079_malformed_response_ambiguous(self):
        m=subject(); r=make_readiness(); c=make_context(m,r,transport=FakeTransport(response={"status_code":200,"body":"not-json"}))
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")

    async def test_080_bare_http_failure_without_provider_body_ambiguous(self):
        m=subject(); r=make_readiness(); c=make_context(m,r,transport=FakeTransport(response={"status_code":503,"body":None}))
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")

    async def test_081_terminal_finalize_failure_downgrades_to_ambiguous(self):
        m=subject(); r=make_readiness(); c=make_context(m,r)
        reg=make_registry(m,finalize_fail_states=(m.Phase36SubmissionRegistryState.CONFIRMED_ACCEPTED,))
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(out.outcome.value,"AMBIGUOUS_UNRESOLVED")
        self.assertIs(reg.states[out.attempt_fingerprint],m.Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED)

    async def test_082_all_terminal_persistence_failure_raises_secret_safe_error(self):
        m=subject(); r=make_readiness(); c=make_context(m,r)
        reg=make_registry(m,finalize_fail_states=(
            m.Phase36SubmissionRegistryState.CONFIRMED_ACCEPTED,
            m.Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
        ))
        with self.assertRaisesRegex(m.WatchlistOrderProviderSubmissionBoundaryError,"TERMINAL_PERSISTENCE_FAILED_AFTER_SEND"):
            await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(c.transport.calls,1)

    async def test_083_cancellation_during_inflight_cas_aborts_before_send(self):
        m=subject(); r=make_readiness(); c=make_context(m,r)
        reg=make_registry(m,cas_exc=asyncio.CancelledError())
        with self.assertRaises(asyncio.CancelledError):
            await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(c.transport.calls,0)
        self.assertIn(m.Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,reg.states.values())

    async def test_084_cancellation_after_inflight_marks_ambiguous_and_rethrows(self):
        m=subject(); r=make_readiness(); entered=asyncio.Event()
        t=FakeTransport(delay=10,entered_event=entered); c=make_context(m,r,transport=t); reg=make_registry(m)
        task=asyncio.create_task(m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg))
        await entered.wait(); task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertIn(m.Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,reg.states.values())

    async def test_085_baseexception_before_inflight_aborts_and_rethrows(self):
        m=subject(); r=make_readiness(); c=make_context(m,r)
        reg=make_registry(m,cas_exc=SentinelBaseException("boom"))
        with self.assertRaises(SentinelBaseException):
            await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(c.transport.calls,0)
        self.assertIn(m.Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,reg.states.values())

    async def test_086_baseexception_after_inflight_ambiguous_and_rethrows(self):
        m=subject(); r=make_readiness(); t=FakeTransport(exc=SentinelBaseException("boom"))
        c=make_context(m,r,transport=t); reg=make_registry(m)
        with self.assertRaises(SentinelBaseException):
            await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertIn(m.Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,reg.states.values())


class Phase36SafetyCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_087_raw_token_removed_from_provider_message(self):
        m=subject(); r=make_readiness()
        t=FakeTransport(response={"status_code":400,"body":{"return_code":-1,"return_msg":"bad token-supersecret-123"}})
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertNotIn("token-supersecret-123",out.provider_return_msg)

    async def test_088_bearer_value_redacted_from_provider_message(self):
        m=subject(); r=make_readiness()
        t=FakeTransport(response={"status_code":400,"body":{"return_code":-1,"return_msg":"Authorization Bearer abcdef"}})
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertIn("[REDACTED]",out.provider_return_msg); self.assertNotIn("abcdef",out.provider_return_msg)

    async def test_089_receipt_repr_contains_no_raw_token_or_account_number(self):
        _,_,_,_,_,out=await submit_with()
        text=repr(out)
        self.assertNotIn("token-supersecret",text)
        self.assertNotIn("123-456-789",text)

    async def test_090_transport_exception_text_not_copied_to_receipt(self):
        m=subject(); r=make_readiness(); t=FakeTransport(exc=RuntimeError("Bearer secret-token"))
        c=make_context(m,r,transport=t)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertIsNone(out.provider_return_msg)

    async def test_091_cleanup_called_once_on_success(self):
        m=subject(); r=make_readiness(); cleanup=FakeCleanup(); c=make_context(m,r,cleanup=cleanup)
        await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(cleanup.calls,1)

    async def test_092_cleanup_called_once_on_blocked(self):
        m=subject(); r=make_readiness(); cleanup=FakeCleanup(); c=make_context(m,r,cleanup=cleanup,mode="prod")
        await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(cleanup.calls,1)

    async def test_093_cleanup_called_once_on_timeout(self):
        m=subject(); r=make_readiness(); cleanup=FakeCleanup(); c=make_context(m,r,cleanup=cleanup,transport=FakeTransport(delay=.05),timeout_seconds=.005)
        await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,make_registry(m))
        self.assertEqual(cleanup.calls,1)

    async def test_094_cleanup_called_on_cancellation(self):
        m=subject(); r=make_readiness(); cleanup=FakeCleanup(); entered=asyncio.Event()
        c=make_context(m,r,cleanup=cleanup,transport=FakeTransport(delay=10,entered_event=entered)); reg=make_registry(m)
        task=asyncio.create_task(m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg))
        await entered.wait(); task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(cleanup.calls,1)

    async def test_095_cleanup_exception_never_causes_resend_or_secret_leak(self):
        m=subject(); r=make_readiness(); cleanup=FakeCleanup(exc=RuntimeError("secret-token"))
        c=make_context(m,r,cleanup=cleanup); reg=make_registry(m)
        out=await m.submit_demo_watchlist_order_once(r,make_approval(m,r),c,reg)
        self.assertEqual(c.transport.calls,1)
        self.assertNotIn("secret-token",repr(out))

    async def test_096_source_has_no_direct_provider_network_env_keyring_or_package_reexport(self):
        text=TARGET_SOURCE.read_text(encoding="utf-8")
        tree=ast.parse(text)
        roots=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertTrue(roots.isdisjoint({"requests","httpx","socket","websockets","urllib","keyring"}))
        self.assertNotIn("os.environ",text)
        self.assertEqual(REST_INIT.read_bytes(),b"")


if __name__ == "__main__":
    unittest.main()
