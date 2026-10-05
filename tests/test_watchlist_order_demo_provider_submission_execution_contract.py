from __future__ import annotations

import asyncio
import ast
import importlib
import inspect
import pathlib
import sys
import types
import unittest
from unittest import mock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_provider_submission_boundary import (
    KiwoomOrderProviderSubmissionOutcome,
    KiwoomOrderProviderSubmissionReceipt,
    Phase36SubmissionRegistryState,
    WatchlistOrderProviderSubmissionBoundaryError,
)

TARGET_MODULE = (
    "kiwoom_trading_system.brokers.kiwoom.rest."
    "watchlist_order_demo_provider_submission_execution"
)
TARGET_FUNCTION = "execute_demo_watchlist_order_once"
TARGET_SOURCE = (
    PROJECT_ROOT
    / "src"
    / "kiwoom_trading_system"
    / "brokers"
    / "kiwoom"
    / "rest"
    / "watchlist_order_demo_provider_submission_execution.py"
)
PHASE36_MODULE = (
    "kiwoom_trading_system.brokers.kiwoom.rest."
    "watchlist_order_provider_submission_boundary"
)
ALLOWED_PHASE36_PUBLIC = {
    "WatchlistOrderProviderSubmissionBoundaryError",
    "KiwoomOrderProviderSubmissionOutcome",
    "Phase36SubmissionRegistryState",
    "Phase36SubmissionApprovalEvidence",
    "Phase36ProviderExecutionContext",
    "Phase36AtomicSubmissionRegistry",
    "KiwoomOrderProviderSubmissionReceipt",
    "submit_demo_watchlist_order_once",
}
FORBIDDEN_PHASE36_PRIVATE = {
    "_Phase36RuntimeValidationApproval",
    "_Phase36RuntimeValidationEvidence",
    "_KiwoomSdkCachedTokenInspector",
    "_KiwoomSdkDemoAuthRefresher",
    "_Phase36DemoAccountBindingProbe",
    "_validate_phase36_runtime_materials_once",
}
FORBIDDEN_NETWORK_IMPORT_ROOTS = {
    "aiohttp",
    "httpx",
    "requests",
    "socket",
    "urllib",
    "websockets",
}


def _target():
    try:
        return importlib.import_module(TARGET_MODULE)
    except ModuleNotFoundError as exc:
        raise AssertionError("PHASE37_IMPLEMENTATION_MODULE_MISSING") from exc


def _source_tree():
    if not TARGET_SOURCE.is_file():
        raise AssertionError("PHASE37_IMPLEMENTATION_SOURCE_MISSING")
    text = TARGET_SOURCE.read_text(encoding="utf-8")
    return text, ast.parse(text, filename=str(TARGET_SOURCE))


def _receipt(
    *,
    outcome=KiwoomOrderProviderSubmissionOutcome.CONFIRMED_ACCEPTED,
    terminal_state=Phase36SubmissionRegistryState.CONFIRMED_ACCEPTED,
    transport_attempt_count=1,
    normalized_return_code=0,
    provider_return_msg="accepted",
    provider_order_no="0000001",
    provider_exchange="KRX",
):
    return KiwoomOrderProviderSubmissionReceipt(
        attempt_fingerprint="a" * 64,
        request_fingerprint="b" * 64,
        readiness_fingerprint="c" * 64,
        submission_approval_fingerprint="d" * 64,
        claim_fingerprint="e" * 64,
        mode="demo",
        endpoint_identity="https://mockapi.kiwoom.com/api/dostk/ordr",
        api_id="kt10000",
        normalized_return_code=normalized_return_code,
        provider_return_msg=provider_return_msg,
        provider_order_no=provider_order_no,
        provider_exchange=provider_exchange,
        outcome=outcome,
        registry_terminal_state=terminal_state,
        transport_attempt_count=transport_attempt_count,
        started_at_utc="2026-10-05T00:00:00Z",
        completed_at_utc="2026-10-05T00:00:01Z",
        credential_provenance_fingerprint="f" * 64,
        account_provenance_fingerprint="1" * 64,
    )


def _inputs():
    transport = types.SimpleNamespace(post_order=mock.AsyncMock())
    execution_context = types.SimpleNamespace(transport=transport)
    return object(), object(), execution_context, object(), transport


async def _invoke_returning(receipt):
    target = _target()
    delegate = mock.AsyncMock(return_value=receipt)
    readiness, approval, context, registry, transport = _inputs()
    with mock.patch.object(target, "submit_demo_watchlist_order_once", delegate):
        result = await getattr(target, TARGET_FUNCTION)(
            readiness,
            approval,
            context,
            registry,
        )
    return result, delegate, readiness, approval, context, registry, transport


def _delegated_value(delegate, position, keyword):
    call = delegate.await_args
    if len(call.args) > position:
        return call.args[position]
    return call.kwargs[keyword]


class Phase37SurfaceContractTests(unittest.TestCase):
    def test_01_target_module_importable(self):
        self.assertEqual(_target().__name__, TARGET_MODULE)

    def test_02_public_all_exact(self):
        self.assertEqual(tuple(getattr(_target(), "__all__", ())), (TARGET_FUNCTION,))

    def test_03_public_function_exists(self):
        self.assertTrue(callable(getattr(_target(), TARGET_FUNCTION, None)))

    def test_04_public_function_is_async(self):
        self.assertTrue(inspect.iscoroutinefunction(getattr(_target(), TARGET_FUNCTION)))

    def test_05_public_function_signature_exact(self):
        signature = inspect.signature(getattr(_target(), TARGET_FUNCTION))
        self.assertEqual(
            list(signature.parameters),
            [
                "readiness_snapshot",
                "submission_approval",
                "execution_context",
                "submission_registry",
            ],
        )

    def test_06_phase36_imports_public_only(self):
        _, tree = _source_tree()
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == PHASE36_MODULE:
                imported.extend(alias.name for alias in node.names)
        self.assertTrue(imported)
        self.assertTrue(set(imported).issubset(ALLOWED_PHASE36_PUBLIC))

    def test_07_private_runtime_symbols_absent(self):
        text, tree = _source_tree()
        referenced = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        }
        referenced.update(
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        )
        self.assertFalse(FORBIDDEN_PHASE36_PRIVATE.intersection(referenced))
        for name in FORBIDDEN_PHASE36_PRIVATE:
            self.assertNotIn(name, text)

    def test_08_no_direct_post_order_reference(self):
        _, tree = _source_tree()
        self.assertFalse(
            any(
                isinstance(node, ast.Attribute) and node.attr == "post_order"
                for node in ast.walk(tree)
            )
        )

    def test_09_no_network_client_imports(self):
        _, tree = _source_tree()
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        self.assertFalse(FORBIDDEN_NETWORK_IMPORT_ROOTS.intersection(roots))

    def test_10_no_print_or_logging_calls(self):
        _, tree = _source_tree()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                self.assertNotEqual(node.func.id, "print")
            if isinstance(node.func, ast.Attribute):
                self.assertNotIn(
                    node.func.attr,
                    {"debug", "info", "warning", "error", "exception", "critical"},
                )


class Phase37DelegationContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_11_delegate_once_for_zero_transport_attempt_receipt(self):
        _, delegate, *_ = await _invoke_returning(_receipt(transport_attempt_count=0))
        delegate.assert_awaited_once()

    async def test_12_delegate_once_for_one_transport_attempt_receipt(self):
        _, delegate, *_ = await _invoke_returning(_receipt(transport_attempt_count=1))
        delegate.assert_awaited_once()

    async def test_13_zero_attempt_receipt_identity_preserved(self):
        receipt = _receipt(transport_attempt_count=0)
        result, *_ = await _invoke_returning(receipt)
        self.assertIs(result, receipt)

    async def test_14_one_attempt_receipt_identity_preserved(self):
        receipt = _receipt(transport_attempt_count=1)
        result, *_ = await _invoke_returning(receipt)
        self.assertIs(result, receipt)

    async def test_15_readiness_identity_passed_through(self):
        _, delegate, readiness, _, _, _, _ = await _invoke_returning(_receipt())
        self.assertIs(
            _delegated_value(delegate, 0, "readiness_snapshot"),
            readiness,
        )

    async def test_16_approval_identity_passed_through(self):
        _, delegate, _, approval, _, _, _ = await _invoke_returning(_receipt())
        self.assertIs(
            _delegated_value(delegate, 1, "submission_approval"),
            approval,
        )

    async def test_17_execution_context_identity_passed_through(self):
        _, delegate, _, _, context, _, _ = await _invoke_returning(_receipt())
        self.assertIs(
            _delegated_value(delegate, 2, "execution_context"),
            context,
        )

    async def test_18_registry_identity_passed_through(self):
        _, delegate, _, _, _, registry, _ = await _invoke_returning(_receipt())
        self.assertIs(
            _delegated_value(delegate, 3, "submission_registry"),
            registry,
        )

    async def test_19_zero_attempt_does_not_call_transport_directly(self):
        _, _, _, _, _, _, transport = await _invoke_returning(
            _receipt(transport_attempt_count=0)
        )
        transport.post_order.assert_not_awaited()

    async def test_20_one_attempt_does_not_call_transport_directly(self):
        _, _, _, _, _, _, transport = await _invoke_returning(
            _receipt(transport_attempt_count=1)
        )
        transport.post_order.assert_not_awaited()


class Phase37ReceiptPreservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_21_confirmed_accepted_outcome_preserved(self):
        receipt = _receipt(
            outcome=KiwoomOrderProviderSubmissionOutcome.CONFIRMED_ACCEPTED,
            terminal_state=Phase36SubmissionRegistryState.CONFIRMED_ACCEPTED,
        )
        result, *_ = await _invoke_returning(receipt)
        self.assertIs(result.outcome, receipt.outcome)

    async def test_22_confirmed_not_accepted_outcome_preserved(self):
        receipt = _receipt(
            outcome=KiwoomOrderProviderSubmissionOutcome.CONFIRMED_NOT_ACCEPTED,
            terminal_state=Phase36SubmissionRegistryState.CONFIRMED_NOT_ACCEPTED,
        )
        result, *_ = await _invoke_returning(receipt)
        self.assertIs(result.outcome, receipt.outcome)

    async def test_23_blocked_before_send_outcome_preserved(self):
        receipt = _receipt(
            outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
            terminal_state=Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,
            transport_attempt_count=0,
        )
        result, *_ = await _invoke_returning(receipt)
        self.assertIs(result.outcome, receipt.outcome)

    async def test_24_ambiguous_unresolved_outcome_preserved(self):
        receipt = _receipt(
            outcome=KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
            terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
        )
        result, *_ = await _invoke_returning(receipt)
        self.assertIs(result.outcome, receipt.outcome)

    async def test_25_terminal_registry_state_preserved(self):
        receipt = _receipt(
            terminal_state=Phase36SubmissionRegistryState.CONFIRMED_NOT_ACCEPTED
        )
        result, *_ = await _invoke_returning(receipt)
        self.assertIs(result.registry_terminal_state, receipt.registry_terminal_state)

    async def test_26_normalized_return_code_preserved(self):
        receipt = _receipt(normalized_return_code=17)
        result, *_ = await _invoke_returning(receipt)
        self.assertEqual(result.normalized_return_code, 17)

    async def test_27_provider_fields_preserved(self):
        receipt = _receipt(
            provider_return_msg="provider-safe-message",
            provider_order_no="7654321",
            provider_exchange="KRX",
        )
        result, *_ = await _invoke_returning(receipt)
        self.assertEqual(
            (
                result.provider_return_msg,
                result.provider_order_no,
                result.provider_exchange,
            ),
            (
                receipt.provider_return_msg,
                receipt.provider_order_no,
                receipt.provider_exchange,
            ),
        )

    async def test_28_timestamps_preserved(self):
        receipt = _receipt()
        result, *_ = await _invoke_returning(receipt)
        self.assertEqual(
            (result.started_at_utc, result.completed_at_utc),
            (receipt.started_at_utc, receipt.completed_at_utc),
        )

    async def test_29_fingerprints_preserved(self):
        receipt = _receipt()
        result, *_ = await _invoke_returning(receipt)
        self.assertEqual(
            (
                result.attempt_fingerprint,
                result.request_fingerprint,
                result.readiness_fingerprint,
                result.submission_approval_fingerprint,
                result.claim_fingerprint,
                result.credential_provenance_fingerprint,
                result.account_provenance_fingerprint,
            ),
            (
                receipt.attempt_fingerprint,
                receipt.request_fingerprint,
                receipt.readiness_fingerprint,
                receipt.submission_approval_fingerprint,
                receipt.claim_fingerprint,
                receipt.credential_provenance_fingerprint,
                receipt.account_provenance_fingerprint,
            ),
        )

    async def test_30_demo_endpoint_and_api_identity_preserved(self):
        receipt = _receipt()
        result, *_ = await _invoke_returning(receipt)
        self.assertEqual(
            (result.mode, result.endpoint_identity, result.api_id),
            ("demo", "https://mockapi.kiwoom.com/api/dostk/ordr", "kt10000"),
        )


class Phase37FailureAndNoRetryTests(unittest.IsolatedAsyncioTestCase):
    async def _assert_invalid_count(self, value):
        target = _target()
        receipt = _receipt(transport_attempt_count=value)
        delegate = mock.AsyncMock(return_value=receipt)
        readiness, approval, context, registry, _ = _inputs()
        with mock.patch.object(target, "submit_demo_watchlist_order_once", delegate):
            with self.assertRaises(WatchlistOrderProviderSubmissionBoundaryError):
                await getattr(target, TARGET_FUNCTION)(
                    readiness,
                    approval,
                    context,
                    registry,
                )
        delegate.assert_awaited_once()

    async def _assert_propagated_once(self, exc_type):
        target = _target()
        delegate = mock.AsyncMock(side_effect=exc_type("phase36-failure"))
        readiness, approval, context, registry, _ = _inputs()
        with mock.patch.object(target, "submit_demo_watchlist_order_once", delegate):
            with self.assertRaises(exc_type):
                await getattr(target, TARGET_FUNCTION)(
                    readiness,
                    approval,
                    context,
                    registry,
                )
        delegate.assert_awaited_once()

    async def test_31_negative_transport_attempt_count_fails_closed(self):
        await self._assert_invalid_count(-1)

    async def test_32_two_transport_attempt_count_fails_closed(self):
        await self._assert_invalid_count(2)

    async def test_33_true_transport_attempt_count_fails_closed(self):
        await self._assert_invalid_count(True)

    async def test_34_false_transport_attempt_count_fails_closed(self):
        await self._assert_invalid_count(False)

    async def test_35_non_receipt_result_fails_closed(self):
        target = _target()
        delegate = mock.AsyncMock(return_value=object())
        readiness, approval, context, registry, _ = _inputs()
        with mock.patch.object(target, "submit_demo_watchlist_order_once", delegate):
            with self.assertRaises(WatchlistOrderProviderSubmissionBoundaryError):
                await getattr(target, TARGET_FUNCTION)(
                    readiness,
                    approval,
                    context,
                    registry,
                )
        delegate.assert_awaited_once()

    async def test_36_phase36_boundary_error_propagates_without_retry(self):
        await self._assert_propagated_once(
            WatchlistOrderProviderSubmissionBoundaryError
        )

    async def test_37_timeout_error_propagates_without_retry(self):
        await self._assert_propagated_once(TimeoutError)

    async def test_38_cancelled_error_propagates_without_retry(self):
        target = _target()
        delegate = mock.AsyncMock(side_effect=asyncio.CancelledError())
        readiness, approval, context, registry, _ = _inputs()
        with mock.patch.object(target, "submit_demo_watchlist_order_once", delegate):
            with self.assertRaises(asyncio.CancelledError):
                await getattr(target, TARGET_FUNCTION)(
                    readiness,
                    approval,
                    context,
                    registry,
                )
        delegate.assert_awaited_once()

    async def test_39_runtime_error_propagates_without_retry(self):
        await self._assert_propagated_once(RuntimeError)

    async def test_40_invalid_count_error_is_secret_safe(self):
        target = _target()
        sentinel = "RAW-SECRET-SENTINEL-DO-NOT-LEAK"
        receipt = _receipt(
            transport_attempt_count=2,
            provider_return_msg=sentinel,
        )
        delegate = mock.AsyncMock(return_value=receipt)
        readiness, approval, context, registry, _ = _inputs()
        with mock.patch.object(target, "submit_demo_watchlist_order_once", delegate):
            with self.assertRaises(
                WatchlistOrderProviderSubmissionBoundaryError
            ) as caught:
                await getattr(target, TARGET_FUNCTION)(
                    readiness,
                    approval,
                    context,
                    registry,
                )
        self.assertNotIn(sentinel, str(caught.exception))
        delegate.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
