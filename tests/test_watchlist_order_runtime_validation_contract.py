import asyncio
import dataclasses
import importlib
import inspect
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SUBJECT_MODULE = (
    "kiwoom_trading_system.brokers.kiwoom.rest."
    "watchlist_order_provider_submission_boundary"
)
TARGET_SOURCE = (
    SRC
    / "kiwoom_trading_system/brokers/kiwoom/rest/"
    "watchlist_order_provider_submission_boundary.py"
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
PRIVATE_CANDIDATES = (
    "_Phase36RuntimeValidationApproval",
    "_Phase36RuntimeValidationEvidence",
    "_KiwoomSdkCachedTokenInspector",
    "_KiwoomSdkDemoAuthRefresher",
    "_Phase36DemoAccountBindingProbe",
    "_validate_phase36_runtime_materials_once",
)
NOW = datetime(2026, 10, 4, 14, 0, 0, tzinfo=timezone.utc)
CRED_REF = "credref:demo-1"
ACCT_REF = "acctref:demo-1"
CRED_FP = "c" * 64
ACCT_FP = "d" * 64
RAW_TOKEN = "token-supersecret-runtime-123"
RAW_ACCOUNT = "1234567890"


def subject():
    return importlib.import_module(SUBJECT_MODULE)


def resolved_binding(**overrides):
    values = {
        "mode": "demo",
        "credential_ref_id": CRED_REF,
        "account_ref_id": ACCT_REF,
        "credential_ownership_evidence_fingerprint": CRED_FP,
        "account_ownership_evidence_fingerprint": ACCT_FP,
    }
    values.update(overrides)
    return values


def token_record(
    *,
    remaining_seconds=601,
    mode="demo",
    profile="demo-profile",
    credential_fingerprint=CRED_FP,
    token_type="bearer",
    access_token=RAW_TOKEN,
):
    return SimpleNamespace(
        access_token=access_token,
        token_type=token_type,
        expires_at=NOW + timedelta(seconds=remaining_seconds),
        mode=mode,
        profile=profile,
        credential_fingerprint=credential_fingerprint,
    )


class FakeResolver:
    def __init__(self, *, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = 0

    async def resolve(self, *, credential_ref_id, account_ref_id):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        if self.result is not None:
            return self.result
        return resolved_binding(
            credential_ref_id=credential_ref_id,
            account_ref_id=account_ref_id,
        )


class FakeTokenStore:
    def __init__(self, record=None, *, peek_exc=None):
        self.record = record
        self.peek_exc = peek_exc
        self.peek_calls = 0
        self.load_calls = 0
        self.save_calls = 0
        self.clear_calls = 0

    def peek(self, mode, *, profile=None):
        self.peek_calls += 1
        self.last_peek = (mode, profile)
        if self.peek_exc is not None:
            raise self.peek_exc
        return self.record

    def load(self, *args, **kwargs):
        self.load_calls += 1
        raise AssertionError("load must not be called")

    def save(self, *args, **kwargs):
        self.save_calls += 1
        raise AssertionError("save must not be called by inspector")

    def clear(self, *args, **kwargs):
        self.clear_calls += 1
        raise AssertionError("clear must not be called by inspector")


class FakeAuth:
    def __init__(self, *, token_store=None, record=None, exc=None, mode="demo"):
        self.token_store = token_store
        self.record = record
        self.exc = exc
        self.mode = mode
        self.refresh_calls = 0

    def refresh_access_token(self):
        self.refresh_calls += 1
        if self.exc is not None:
            raise self.exc
        if self.token_store is not None:
            self.token_store.record = self.record
        return RAW_TOKEN


class FakeAsyncAuth:
    def __init__(
        self,
        *,
        delay=0.0,
        token_store=None,
        record=None,
        started=None,
        mode="demo",
    ):
        self.delay = delay
        self.token_store = token_store
        self.record = record
        self.started = started
        self.mode = mode
        self.refresh_calls = 0

    async def refresh_access_token(self):
        self.refresh_calls += 1
        if self.started is not None:
            self.started.set()
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.token_store is not None:
            self.token_store.record = self.record
        return RAW_TOKEN


class FakeCleanup:
    def __init__(self):
        self.calls = 0

    async def cleanup(self):
        self.calls += 1


class ExpectedAccountResolver:
    def __init__(self, value=RAW_ACCOUNT, *, exc=None):
        self.value = value
        self.exc = exc
        self.calls = 0
        self.refs = []

    def __call__(self, *, account_ref_id):
        self.calls += 1
        self.refs.append(account_ref_id)
        if self.exc is not None:
            raise self.exc
        return self.value


class FakeAccountTransport:
    def __init__(self, *, account=RAW_ACCOUNT, response=None, delay=0.0, exc=None):
        self.account = account
        self.response = response
        self.delay = delay
        self.exc = exc
        self.calls = 0
        self.kwargs = []

    async def post_account_binding(self, **kwargs):
        self.calls += 1
        self.kwargs.append(kwargs)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc is not None:
            raise self.exc
        if self.response is not None:
            return self.response
        return {"status_code": 200, "body": {"acctNo": self.account}}


def approval(m, **overrides):
    values = {
        "runtime_credential_account_access_authorized": True,
        "cached_token_access_authorized": True,
        "auth_network_authorized": True,
        "token_cache_write_authorized": True,
        "provider_network_authorized": True,
        "expected_account_resolution_authorized": True,
        "actual_kt10000_post_authorized": False,
        "test_execution": True,
    }
    values.update(overrides)
    return m._Phase36RuntimeValidationApproval(**values)


def components(m, *, record=None, auth_record=None, account=RAW_ACCOUNT):
    store = FakeTokenStore(
        record=record if record is not None else token_record()
    )
    inspector = m._KiwoomSdkCachedTokenInspector(
        profile_alias="demo-profile",
        token_store=store,
        now_utc=lambda: NOW,
    )
    auth = FakeAuth(
        token_store=store,
        record=auth_record if auth_record is not None else token_record(),
    )
    refresher = m._KiwoomSdkDemoAuthRefresher(
        auth_client=auth,
        base_url="https://mockapi.kiwoom.com",
        timeout_seconds=1.0,
    )
    transport = FakeAccountTransport(account=account)
    probe = m._Phase36DemoAccountBindingProbe(
        transport=transport,
        base_url="https://mockapi.kiwoom.com",
        timeout_seconds=1.0,
    )
    expected = ExpectedAccountResolver(value=account)
    return store, inspector, auth, refresher, transport, probe, expected


async def validate(
    m,
    *,
    runtime_approval=None,
    resolver=None,
    inspector=None,
    refresher=None,
    probe=None,
    expected=None,
):
    if runtime_approval is None:
        runtime_approval = approval(m)
    if resolver is None:
        resolver = FakeResolver()
    if inspector is None or refresher is None or probe is None or expected is None:
        _store, default_inspector, _auth, default_refresher, _transport, default_probe, default_expected = (
            components(m)
        )
        inspector = inspector or default_inspector
        refresher = refresher or default_refresher
        probe = probe or default_probe
        expected = expected or default_expected
    return await m._validate_phase36_runtime_materials_once(
        approval=runtime_approval,
        resolver=resolver,
        credential_ref_id=CRED_REF,
        account_ref_id=ACCT_REF,
        credential_ownership_evidence_fingerprint=CRED_FP,
        account_ownership_evidence_fingerprint=ACCT_FP,
        cached_token_inspector=inspector,
        auth_refresher=refresher,
        account_probe=probe,
        expected_account_resolver=expected,
    )


class Phase36RuntimeCompatibilityTests(unittest.TestCase):
    def test_001_public_api_exact_eight_unchanged(self):
        m = subject()
        self.assertEqual(tuple(m.__all__), PUBLIC_SYMBOLS)

    def test_002_private_candidates_exist_and_are_private(self):
        m = subject()
        for name in PRIVATE_CANDIDATES:
            self.assertTrue(hasattr(m, name), name)
            self.assertNotIn(name, m.__all__)

    def test_003_private_approval_and_evidence_are_frozen_slots(self):
        m = subject()
        for cls in (
            m._Phase36RuntimeValidationApproval,
            m._Phase36RuntimeValidationEvidence,
        ):
            self.assertTrue(dataclasses.is_dataclass(cls))
            self.assertTrue(cls.__dataclass_params__.frozen)
            self.assertIn("__slots__", vars(cls))

    def test_004_validator_is_private_async_keyword_only_surface(self):
        m = subject()
        fn = m._validate_phase36_runtime_materials_once
        self.assertTrue(inspect.iscoroutinefunction(fn))
        sig = inspect.signature(fn)
        self.assertEqual(
            tuple(sig.parameters),
            (
                "approval",
                "resolver",
                "credential_ref_id",
                "account_ref_id",
                "credential_ownership_evidence_fingerprint",
                "account_ownership_evidence_fingerprint",
                "cached_token_inspector",
                "auth_refresher",
                "account_probe",
                "expected_account_resolver",
            ),
        )
        self.assertTrue(
            all(
                p.kind is inspect.Parameter.KEYWORD_ONLY
                for p in sig.parameters.values()
            )
        )


class Phase36RuntimeLocalDemoBindingTests(unittest.IsolatedAsyncioTestCase):
    async def test_005_runtime_access_gate_blocks_before_resolver(self):
        m = subject()
        resolver = FakeResolver()
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^RUNTIME_CREDENTIAL_ACCOUNT_ACCESS_NOT_AUTHORIZED$",
        ):
            await validate(
                m,
                runtime_approval=approval(
                    m,
                    runtime_credential_account_access_authorized=False,
                ),
                resolver=resolver,
            )
        self.assertEqual(resolver.calls, 0)

    async def test_006_wrong_demo_mode_binding_blocks(self):
        m = subject()
        resolver = FakeResolver(result=resolved_binding(mode="real"))
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^RUNTIME_LOCAL_DEMO_BINDING_MISMATCH$",
        ):
            await validate(m, resolver=resolver)

    async def test_007_wrong_credential_ref_binding_blocks(self):
        m = subject()
        resolver = FakeResolver(
            result=resolved_binding(credential_ref_id="credref:other")
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^RUNTIME_LOCAL_DEMO_BINDING_MISMATCH$",
        ):
            await validate(m, resolver=resolver)

    async def test_008_wrong_account_ref_binding_blocks(self):
        m = subject()
        resolver = FakeResolver(
            result=resolved_binding(account_ref_id="acctref:other")
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^RUNTIME_LOCAL_DEMO_BINDING_MISMATCH$",
        ):
            await validate(m, resolver=resolver)

    async def test_009_wrong_credential_fingerprint_binding_blocks(self):
        m = subject()
        resolver = FakeResolver(
            result=resolved_binding(
                credential_ownership_evidence_fingerprint="a" * 64
            )
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^RUNTIME_LOCAL_DEMO_BINDING_MISMATCH$",
        ):
            await validate(m, resolver=resolver)

    async def test_010_wrong_account_fingerprint_binding_blocks(self):
        m = subject()
        resolver = FakeResolver(
            result=resolved_binding(
                account_ownership_evidence_fingerprint="b" * 64
            )
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^RUNTIME_LOCAL_DEMO_BINDING_MISMATCH$",
        ):
            await validate(m, resolver=resolver)


class Phase36RuntimeCachedTokenTests(unittest.IsolatedAsyncioTestCase):
    async def test_011_cached_token_gate_blocks_before_peek(self):
        m = subject()
        store, inspector, _auth, refresher, _transport, probe, expected = components(m)
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^CACHED_TOKEN_ACCESS_NOT_AUTHORIZED$",
        ):
            await validate(
                m,
                runtime_approval=approval(m, cached_token_access_authorized=False),
                inspector=inspector,
                refresher=refresher,
                probe=probe,
                expected=expected,
            )
        self.assertEqual(store.peek_calls, 0)

    async def test_012_inspector_uses_peek_only_and_returns_safe_metadata(self):
        m = subject()
        store = FakeTokenStore(record=token_record())
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=store,
            now_utc=lambda: NOW,
        )
        out = await inspector.inspect(
            resolved=resolved_binding(),
            access_authorized=True,
        )
        self.assertEqual(store.peek_calls, 1)
        self.assertEqual(store.load_calls, 0)
        self.assertEqual(store.save_calls, 0)
        self.assertEqual(store.clear_calls, 0)
        self.assertTrue(out["cached_token_reusable"])
        self.assertNotIn("token", out)
        self.assertNotIn(RAW_TOKEN, repr(out))

    async def test_013_missing_cached_token_requires_auth_network(self):
        m = subject()
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=FakeTokenStore(record=None),
            now_utc=lambda: NOW,
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^AUTH_NETWORK_REQUIRED$",
        ):
            await inspector.inspect(
                resolved=resolved_binding(),
                access_authorized=True,
            )

        unsafe_store = FakeTokenStore(
            peek_exc=RuntimeError(f"secret={RAW_TOKEN}")
        )
        unsafe_inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=unsafe_store,
            now_utc=lambda: NOW,
        )
        with self.assertRaises(
            m.WatchlistOrderProviderSubmissionBoundaryError
        ) as cm:
            await unsafe_inspector.inspect(
                resolved=resolved_binding(),
                access_authorized=True,
            )
        self.assertEqual(str(cm.exception), "RUNTIME_CACHED_TOKEN_READ_FAILED")
        self.assertIsNone(cm.exception.__cause__)
        self.assertNotIn(RAW_TOKEN, str(cm.exception))

    async def test_014_expired_cached_token_requires_auth_network(self):
        m = subject()
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=FakeTokenStore(record=token_record(remaining_seconds=-1)),
            now_utc=lambda: NOW,
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^AUTH_NETWORK_REQUIRED$",
        ):
            await inspector.inspect(
                resolved=resolved_binding(),
                access_authorized=True,
            )

    async def test_015_exact_600_seconds_is_not_reusable(self):
        m = subject()
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=FakeTokenStore(record=token_record(remaining_seconds=600)),
            now_utc=lambda: NOW,
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^AUTH_NETWORK_REQUIRED$",
        ):
            await inspector.inspect(
                resolved=resolved_binding(),
                access_authorized=True,
            )

    async def test_016_greater_than_600_seconds_is_reusable(self):
        m = subject()
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=FakeTokenStore(record=token_record(remaining_seconds=600.001)),
            now_utc=lambda: NOW,
        )
        out = await inspector.inspect(
            resolved=resolved_binding(),
            access_authorized=True,
        )
        self.assertTrue(out["cached_token_reusable"])

    async def test_017_wrong_token_type_requires_auth_network(self):
        m = subject()
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=FakeTokenStore(
                record=token_record(token_type="mac")
            ),
            now_utc=lambda: NOW,
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^AUTH_NETWORK_REQUIRED$",
        ):
            await inspector.inspect(
                resolved=resolved_binding(),
                access_authorized=True,
            )

    async def test_018_cached_token_mode_profile_or_credential_mismatch_requires_network(self):
        m = subject()
        variants = (
            token_record(mode="real"),
            token_record(profile="other-profile"),
            token_record(credential_fingerprint="a" * 64),
        )
        for record in variants:
            with self.subTest(record=record):
                inspector = m._KiwoomSdkCachedTokenInspector(
                    profile_alias="demo-profile",
                    token_store=FakeTokenStore(record=record),
                    now_utc=lambda: NOW,
                )
                with self.assertRaisesRegex(
                    m.WatchlistOrderProviderSubmissionBoundaryError,
                    "^AUTH_NETWORK_REQUIRED$",
                ):
                    await inspector.inspect(
                        resolved=resolved_binding(),
                        access_authorized=True,
                    )


class Phase36RuntimeAuthRefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_019_reusable_cached_token_skips_auth_refresh(self):
        m = subject()
        store, inspector, auth, refresher, _transport, probe, expected = components(m)
        evidence = await validate(
            m,
            inspector=inspector,
            refresher=refresher,
            probe=probe,
            expected=expected,
        )
        self.assertFalse(evidence.auth_refresh_performed)
        self.assertEqual(auth.refresh_calls, 0)

    async def test_020_missing_token_without_auth_gate_fails_auth_network_required(self):
        m = subject()
        store = FakeTokenStore(record=None)
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=store,
            now_utc=lambda: NOW,
        )
        auth = FakeAuth(token_store=store, record=token_record())
        refresher = m._KiwoomSdkDemoAuthRefresher(
            auth_client=auth,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        _s, _i, _a, _r, _t, probe, expected = components(m)
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^AUTH_NETWORK_REQUIRED$",
        ):
            await validate(
                m,
                runtime_approval=approval(m, auth_network_authorized=False),
                inspector=inspector,
                refresher=refresher,
                probe=probe,
                expected=expected,
            )
        self.assertEqual(auth.refresh_calls, 0)

        real_auth = FakeAuth(mode="real")
        real_refresher = m._KiwoomSdkDemoAuthRefresher(
            auth_client=real_auth,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^DEMO_AUTH_MODE_INVALID$",
        ):
            await real_refresher.refresh_once(
                auth_network_authorized=True,
                token_cache_write_authorized=True,
            )
        self.assertEqual(real_auth.refresh_calls, 0)

        endpoint_auth = FakeAuth()
        endpoint_refresher = m._KiwoomSdkDemoAuthRefresher(
            auth_client=endpoint_auth,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
            endpoint_resolver=lambda mode: "https://api.kiwoom.com",
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^DEMO_AUTH_BASE_URL_INVALID$",
        ):
            await endpoint_refresher.refresh_once(
                auth_network_authorized=True,
                token_cache_write_authorized=True,
            )
        self.assertEqual(endpoint_auth.refresh_calls, 0)

    async def test_021_missing_token_without_cache_write_gate_blocks_refresh(self):
        m = subject()
        store = FakeTokenStore(record=None)
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=store,
            now_utc=lambda: NOW,
        )
        auth = FakeAuth(token_store=store, record=token_record())
        refresher = m._KiwoomSdkDemoAuthRefresher(
            auth_client=auth,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        _s, _i, _a, _r, _t, probe, expected = components(m)
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^TOKEN_CACHE_WRITE_NOT_AUTHORIZED$",
        ):
            await validate(
                m,
                runtime_approval=approval(
                    m,
                    token_cache_write_authorized=False,
                ),
                inspector=inspector,
                refresher=refresher,
                probe=probe,
                expected=expected,
            )
        self.assertEqual(auth.refresh_calls, 0)

    async def test_022_refresh_exactly_once_then_fresh_b_inspection(self):
        m = subject()
        store = FakeTokenStore(record=None)
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=store,
            now_utc=lambda: NOW,
        )
        auth = FakeAuth(token_store=store, record=token_record())
        refresher = m._KiwoomSdkDemoAuthRefresher(
            auth_client=auth,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        transport = FakeAccountTransport()
        probe = m._Phase36DemoAccountBindingProbe(
            transport=transport,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        expected = ExpectedAccountResolver()
        evidence = await validate(
            m,
            inspector=inspector,
            refresher=refresher,
            probe=probe,
            expected=expected,
        )
        self.assertTrue(evidence.auth_refresh_performed)
        self.assertEqual(auth.refresh_calls, 1)
        self.assertEqual(store.peek_calls, 3)

    async def test_023_refresh_timeout_no_retry_and_external_cancellation_reraises(self):
        m = subject()
        cleanup = FakeCleanup()
        slow = FakeAsyncAuth(delay=0.05)
        refresher = m._KiwoomSdkDemoAuthRefresher(
            auth_client=slow,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=0.001,
            cleanup=cleanup,
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^AUTH_REFRESH_TIMEOUT$",
        ):
            await refresher.refresh_once(
                auth_network_authorized=True,
                token_cache_write_authorized=True,
            )
        self.assertEqual(slow.refresh_calls, 1)
        self.assertEqual(cleanup.calls, 1)

        started = asyncio.Event()
        cleanup2 = FakeCleanup()
        cancellable = FakeAsyncAuth(delay=1.0, started=started)
        refresher2 = m._KiwoomSdkDemoAuthRefresher(
            auth_client=cancellable,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=5.0,
            cleanup=cleanup2,
        )
        task = asyncio.create_task(
            refresher2.refresh_once(
                auth_network_authorized=True,
                token_cache_write_authorized=True,
            )
        )
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(cancellable.refresh_calls, 1)
        self.assertEqual(cleanup2.calls, 1)

        unsafe = FakeAuth(exc=RuntimeError(f"secret={RAW_TOKEN}"))
        refresher3 = m._KiwoomSdkDemoAuthRefresher(
            auth_client=unsafe,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        with self.assertRaises(
            m.WatchlistOrderProviderSubmissionBoundaryError
        ) as cm:
            await refresher3.refresh_once(
                auth_network_authorized=True,
                token_cache_write_authorized=True,
            )
        self.assertEqual(str(cm.exception), "AUTH_REFRESH_FAILED")
        self.assertIsNone(cm.exception.__cause__)
        self.assertNotIn(RAW_TOKEN, str(cm.exception))
        self.assertEqual(unsafe.refresh_calls, 1)


class Phase36RuntimeDemoAccountBindingTests(unittest.IsolatedAsyncioTestCase):
    async def test_024_provider_network_gate_blocks_zero_account_post(self):
        m = subject()
        store, inspector, _auth, refresher, transport, probe, expected = components(m)
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^PROVIDER_NETWORK_REQUIRED$",
        ):
            await validate(
                m,
                runtime_approval=approval(m, provider_network_authorized=False),
                inspector=inspector,
                refresher=refresher,
                probe=probe,
                expected=expected,
            )
        self.assertEqual(transport.calls, 0)

    async def test_025_expected_account_gate_blocks_before_resolver_and_post(self):
        m = subject()
        store, inspector, _auth, refresher, transport, probe, expected = components(m)
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^EXPECTED_ACCOUNT_RESOLUTION_NOT_AUTHORIZED$",
        ):
            await validate(
                m,
                runtime_approval=approval(
                    m,
                    expected_account_resolution_authorized=False,
                ),
                inspector=inspector,
                refresher=refresher,
                probe=probe,
                expected=expected,
            )
        self.assertEqual(expected.calls, 0)
        self.assertEqual(transport.calls, 0)

    async def test_026_ka00001_exact_single_post_and_memory_only_compare(self):
        m = subject()
        store, inspector, _auth, refresher, transport, probe, expected = components(m)
        evidence = await validate(
            m,
            inspector=inspector,
            refresher=refresher,
            probe=probe,
            expected=expected,
        )
        self.assertTrue(evidence.provider_account_binding_validated)
        self.assertEqual(expected.refs, [ACCT_REF])
        self.assertEqual(transport.calls, 1)
        kw = transport.kwargs[0]
        self.assertEqual(kw["base_url"], "https://mockapi.kiwoom.com")
        self.assertEqual(kw["path"], "/api/dostk/acnt")
        self.assertEqual(kw["body"], {})
        self.assertEqual(kw["headers"]["api-id"], "ka00001")
        self.assertEqual(kw["headers"]["authorization"], f"Bearer {RAW_TOKEN}")
        self.assertEqual(kw["timeout_seconds"], 1.0)
        self.assertFalse(kw["retry_on_auth_failure"])

    async def test_027_account_mismatch_fails_without_raw_account_in_error(self):
        m = subject()
        store = FakeTokenStore(record=token_record())
        inspector = m._KiwoomSdkCachedTokenInspector(
            profile_alias="demo-profile",
            token_store=store,
            now_utc=lambda: NOW,
        )
        auth = FakeAuth(token_store=store, record=token_record())
        refresher = m._KiwoomSdkDemoAuthRefresher(
            auth_client=auth,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        transport = FakeAccountTransport(account="9999999999")
        probe = m._Phase36DemoAccountBindingProbe(
            transport=transport,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        expected = ExpectedAccountResolver(RAW_ACCOUNT)
        with self.assertRaises(
            m.WatchlistOrderProviderSubmissionBoundaryError
        ) as cm:
            await validate(
                m,
                inspector=inspector,
                refresher=refresher,
                probe=probe,
                expected=expected,
            )
        self.assertEqual(str(cm.exception), "ACCOUNT_BINDING_MISMATCH")
        self.assertNotIn(RAW_ACCOUNT, str(cm.exception))
        self.assertNotIn("9999999999", str(cm.exception))

        unsafe_expected = ExpectedAccountResolver(
            exc=RuntimeError(f"account={RAW_ACCOUNT}")
        )
        with self.assertRaises(
            m.WatchlistOrderProviderSubmissionBoundaryError
        ) as cm2:
            await probe.probe(
                access_token=RAW_TOKEN,
                account_ref_id=ACCT_REF,
                provider_network_authorized=True,
                expected_account_resolution_authorized=True,
                expected_account_resolver=unsafe_expected,
            )
        self.assertEqual(
            str(cm2.exception),
            "EXPECTED_ACCOUNT_RESOLUTION_FAILED",
        )
        self.assertIsNone(cm2.exception.__cause__)
        self.assertNotIn(RAW_ACCOUNT, str(cm2.exception))

    async def test_028_invalid_provider_response_no_retry_and_no_order_surface(self):
        m = subject()
        transport = FakeAccountTransport(response={"body": {}})
        probe = m._Phase36DemoAccountBindingProbe(
            transport=transport,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^ACCOUNT_BINDING_RESPONSE_INVALID$",
        ):
            await probe.probe(
                access_token=RAW_TOKEN,
                account_ref_id=ACCT_REF,
                provider_network_authorized=True,
                expected_account_resolution_authorized=True,
                expected_account_resolver=ExpectedAccountResolver(),
            )
        self.assertEqual(transport.calls, 1)
        kw = transport.kwargs[0]
        self.assertNotIn("kt00018", repr(kw))
        self.assertNotIn("/api/dostk/ordr", repr(kw))
        self.assertFalse(kw["retry_on_auth_failure"])

        unsafe_transport = FakeAccountTransport(
            exc=RuntimeError(f"token={RAW_TOKEN} account={RAW_ACCOUNT}")
        )
        unsafe_probe = m._Phase36DemoAccountBindingProbe(
            transport=unsafe_transport,
            base_url="https://mockapi.kiwoom.com",
            timeout_seconds=1.0,
        )
        with self.assertRaises(
            m.WatchlistOrderProviderSubmissionBoundaryError
        ) as cm:
            await unsafe_probe.probe(
                access_token=RAW_TOKEN,
                account_ref_id=ACCT_REF,
                provider_network_authorized=True,
                expected_account_resolution_authorized=True,
                expected_account_resolver=ExpectedAccountResolver(),
            )
        self.assertEqual(str(cm.exception), "ACCOUNT_BINDING_REQUEST_FAILED")
        self.assertIsNone(cm.exception.__cause__)
        self.assertNotIn(RAW_TOKEN, str(cm.exception))
        self.assertNotIn(RAW_ACCOUNT, str(cm.exception))
        self.assertEqual(unsafe_transport.calls, 1)


class Phase36RuntimeSecurityBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_029_actual_kt10000_true_blocks_before_any_validation_action(self):
        m = subject()
        resolver = FakeResolver()
        store, inspector, auth, refresher, transport, probe, expected = components(m)
        with self.assertRaisesRegex(
            m.WatchlistOrderProviderSubmissionBoundaryError,
            "^ACTUAL_KT10000_POST_PROHIBITED$",
        ):
            await validate(
                m,
                runtime_approval=approval(
                    m,
                    actual_kt10000_post_authorized=True,
                ),
                resolver=resolver,
                inspector=inspector,
                refresher=refresher,
                probe=probe,
                expected=expected,
            )
        self.assertEqual(resolver.calls, 0)
        self.assertEqual(store.peek_calls, 0)
        self.assertEqual(auth.refresh_calls, 0)
        self.assertEqual(transport.calls, 0)

    async def test_030_final_evidence_contains_no_raw_token_or_account(self):
        m = subject()
        store, inspector, _auth, refresher, _transport, probe, expected = components(m)
        evidence = await validate(
            m,
            inspector=inspector,
            refresher=refresher,
            probe=probe,
            expected=expected,
        )
        payload = dataclasses.asdict(evidence)
        text = repr(payload)
        self.assertNotIn(RAW_TOKEN, text)
        self.assertNotIn(RAW_ACCOUNT, text)
        self.assertNotIn("token", payload)
        self.assertNotIn("acctNo", payload)

    async def test_031_external_secret_bearing_resolver_error_is_sanitized(self):
        m = subject()
        resolver = FakeResolver(
            exc=RuntimeError(
                f"secret={RAW_TOKEN} account={RAW_ACCOUNT}"
            )
        )
        with self.assertRaises(
            m.WatchlistOrderProviderSubmissionBoundaryError
        ) as cm:
            await validate(m, resolver=resolver)
        self.assertEqual(
            str(cm.exception),
            "RUNTIME_LOCAL_DEMO_BINDING_FAILED",
        )
        self.assertNotIn(RAW_TOKEN, str(cm.exception))
        self.assertNotIn(RAW_ACCOUNT, str(cm.exception))
        self.assertIsNone(cm.exception.__cause__)

    async def test_032_private_runtime_source_has_no_get_access_token_or_order_endpoint(self):
        text = TARGET_SOURCE.read_text(encoding="utf-8")
        start = text.index("class _Phase36RuntimeValidationApproval")
        end = text.index(
            "@_dataclass(frozen=True, slots=True)\n"
            "class Phase36ProviderExecutionContext"
        )
        block = text[start:end]
        self.assertNotIn("get_access_token(", block)
        self.assertNotIn("kt00018", block)
        self.assertNotIn("/api/dostk/ordr", block)
        self.assertNotIn("actual_kt10000_post_authorized=True", block)


if __name__ == "__main__":
    unittest.main()