import ast
import dataclasses
import importlib
import inspect
import os
import re
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TARGET_MODULE = "kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_send_request"
TARGET_SOURCE = SRC / "kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_send_request.py"
PHASE29_MODULE = "kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_send_authorization"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _subject():
    try:
        return importlib.import_module(TARGET_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name == TARGET_MODULE:
            raise AssertionError("PHASE30_SOURCE_MISSING_EXPECTED_RED") from exc
        raise


def _valid_input(subject, **overrides):
    values = {
        "environment": "demo",
        "side": "BUY",
        "exchange": "KRX",
        "stock_code": "005930",
        "quantity": 3,
        "order_style": "LIMIT",
        "limit_price": 64500,
        "source_attempt_ref": "attempt-1",
        "authorization_evidence_ref": "snapshot-1",
    }
    values.update(overrides)
    return subject.WatchlistOrderSendRequestInput(**values)


def _build(subject, **overrides):
    return subject.build_demo_watchlist_order_send_request_snapshot(
        _valid_input(subject, **overrides)
    )


def _assert_error(testcase, subject, code, **overrides):
    with testcase.assertRaisesRegex(subject.WatchlistOrderSendRequestError, rf"^{re.escape(code)}$"):
        _build(subject, **overrides)


def _source_tree():
    return ast.parse(TARGET_SOURCE.read_text(encoding="utf-8"), filename=str(TARGET_SOURCE))


def _import_roots():
    roots = set()
    for node in ast.walk(_source_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


class Phase30WatchlistOrderSendRequestTests(unittest.TestCase):
    def test_public_api_exact_four_symbols(self):
        subject = _subject()
        self.assertEqual(
            tuple(subject.__all__),
            (
                "WatchlistOrderSendRequestError",
                "WatchlistOrderSendRequestInput",
                "WatchlistOrderSendRequestSnapshot",
                "build_demo_watchlist_order_send_request_snapshot",
            ),
        )

    def test_builder_exact_signature_and_return_type(self):
        subject = _subject()
        sig = inspect.signature(subject.build_demo_watchlist_order_send_request_snapshot)
        self.assertEqual(tuple(sig.parameters), ("request",))
        parameter = sig.parameters["request"]
        self.assertIs(parameter.annotation, subject.WatchlistOrderSendRequestInput)
        self.assertIs(parameter.default, inspect.Parameter.empty)
        self.assertIs(sig.return_annotation, subject.WatchlistOrderSendRequestSnapshot)
        self.assertFalse(inspect.iscoroutinefunction(subject.build_demo_watchlist_order_send_request_snapshot))

    def test_error_is_runtime_error(self):
        subject = _subject()
        self.assertTrue(issubclass(subject.WatchlistOrderSendRequestError, RuntimeError))

    def test_input_exact_fields_and_frozen(self):
        subject = _subject()
        self.assertTrue(dataclasses.is_dataclass(subject.WatchlistOrderSendRequestInput))
        self.assertTrue(subject.WatchlistOrderSendRequestInput.__dataclass_params__.frozen)
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(subject.WatchlistOrderSendRequestInput)),
            (
                "environment",
                "side",
                "exchange",
                "stock_code",
                "quantity",
                "order_style",
                "limit_price",
                "source_attempt_ref",
                "authorization_evidence_ref",
            ),
        )
        item = _valid_input(subject)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            item.quantity = 4

    def test_snapshot_exact_fields_and_frozen(self):
        subject = _subject()
        self.assertTrue(dataclasses.is_dataclass(subject.WatchlistOrderSendRequestSnapshot))
        self.assertTrue(subject.WatchlistOrderSendRequestSnapshot.__dataclass_params__.frozen)
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(subject.WatchlistOrderSendRequestSnapshot)),
            (
                "environment",
                "side",
                "exchange",
                "api_id",
                "http_method",
                "api_path",
                "body",
                "source_attempt_ref",
                "authorization_evidence_ref",
                "materialization_fingerprint",
                "transport_allowed",
                "credential_accessed",
                "network_performed",
                "account_accessed",
                "order_submitted",
            ),
        )
        snap = _build(subject)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snap.side = "SELL"

    def test_snapshot_body_is_immutable(self):
        subject = _subject()
        snap = _build(subject)
        with self.assertRaises(TypeError):
            snap.body["stk_cd"] = "000660"

    def test_buy_limit_snapshot_exact(self):
        subject = _subject()
        snap = _build(subject)
        self.assertEqual(snap.environment, "demo")
        self.assertEqual(snap.side, "BUY")
        self.assertEqual(snap.exchange, "KRX")
        self.assertEqual(
            dict(snap.body),
            {
                "dmst_stex_tp": "KRX",
                "stk_cd": "005930",
                "ord_qty": "3",
                "ord_uv": "64500",
                "trde_tp": "0",
                "cond_uv": "",
            },
        )

    def test_buy_market_snapshot_exact(self):
        subject = _subject()
        snap = _build(subject, order_style="MARKET", limit_price=None)
        self.assertEqual(
            dict(snap.body),
            {
                "dmst_stex_tp": "KRX",
                "stk_cd": "005930",
                "ord_qty": "3",
                "ord_uv": "",
                "trde_tp": "3",
                "cond_uv": "",
            },
        )

    def test_api_id_method_and_path_exact(self):
        subject = _subject()
        snap = _build(subject)
        self.assertEqual((snap.api_id, snap.http_method, snap.api_path), ("kt10000", "POST", "/api/dostk/ordr"))

    def test_provider_body_key_set_exact(self):
        subject = _subject()
        self.assertEqual(
            tuple(_build(subject).body.keys()),
            ("dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"),
        )

    def test_provider_body_values_are_strings(self):
        subject = _subject()
        self.assertTrue(all(type(value) is str for value in _build(subject).body.values()))

    def test_limit_provider_mapping_exact(self):
        subject = _subject()
        body = _build(subject, quantity=7, limit_price=12345).body
        self.assertEqual(body["ord_qty"], "7")
        self.assertEqual(body["ord_uv"], "12345")
        self.assertEqual(body["trde_tp"], "0")

    def test_market_provider_mapping_exact(self):
        subject = _subject()
        body = _build(subject, quantity=7, order_style="MARKET", limit_price=None).body
        self.assertEqual(body["ord_qty"], "7")
        self.assertEqual(body["ord_uv"], "")
        self.assertEqual(body["trde_tp"], "3")

    def test_provider_exchange_and_condition_price_exact(self):
        subject = _subject()
        body = _build(subject).body
        self.assertEqual(body["dmst_stex_tp"], "KRX")
        self.assertEqual(body["cond_uv"], "")

    def test_non_demo_environment_rejected(self):
        subject = _subject()
        request = subject.WatchlistOrderSendRequestInput(
            environment="real",
            side="SELL",
            exchange="NXT",
            stock_code="",
            quantity=0,
            order_style="BAD",
            limit_price=None,
            source_attempt_ref="",
            authorization_evidence_ref="",
        )
        with self.assertRaisesRegex(subject.WatchlistOrderSendRequestError, "^ENVIRONMENT_PROHIBITED$"):
            subject.build_demo_watchlist_order_send_request_snapshot(request)
        for bad in (None, 1, True, "DEMO"):
            _assert_error(self, subject, "ENVIRONMENT_PROHIBITED", environment=bad)

    def test_non_buy_side_rejected(self):
        subject = _subject()
        request = subject.WatchlistOrderSendRequestInput(
            environment="demo",
            side="SELL",
            exchange="NXT",
            stock_code="",
            quantity=0,
            order_style="BAD",
            limit_price=None,
            source_attempt_ref="",
            authorization_evidence_ref="",
        )
        with self.assertRaisesRegex(subject.WatchlistOrderSendRequestError, "^SIDE_UNSUPPORTED$"):
            subject.build_demo_watchlist_order_send_request_snapshot(request)
        for bad in (None, 1, True, "buy"):
            _assert_error(self, subject, "SIDE_UNSUPPORTED", side=bad)

    def test_non_krx_exchange_rejected(self):
        subject = _subject()
        request = subject.WatchlistOrderSendRequestInput(
            environment="demo",
            side="BUY",
            exchange="NXT",
            stock_code="",
            quantity=0,
            order_style="BAD",
            limit_price=None,
            source_attempt_ref="",
            authorization_evidence_ref="",
        )
        with self.assertRaisesRegex(subject.WatchlistOrderSendRequestError, "^DEMO_EXCHANGE_UNSUPPORTED$"):
            subject.build_demo_watchlist_order_send_request_snapshot(request)
        for bad in (None, 1, True, "SOR"):
            _assert_error(self, subject, "DEMO_EXCHANGE_UNSUPPORTED", exchange=bad)

    def test_stock_code_blank_whitespace_control_rejected(self):
        subject = _subject()
        for bad in ("", "   ", " 005930", "005930 ", "005\n930", "005\t930", "005\x00930"):
            with self.subTest(bad=repr(bad)):
                _assert_error(self, subject, "STOCK_CODE_INVALID", stock_code=bad)

    def test_stock_code_type_and_length_rejected(self):
        subject = _subject()
        for bad in (None, 5930, True, "1234567890123"):
            with self.subTest(bad=repr(bad)):
                _assert_error(self, subject, "STOCK_CODE_INVALID", stock_code=bad)
        self.assertEqual(_build(subject, stock_code="123456789012").body["stk_cd"], "123456789012")

    def test_quantity_requires_exact_int_not_bool(self):
        subject = _subject()
        for bad in (True, False, "1", 1.0, None):
            with self.subTest(bad=repr(bad)):
                _assert_error(self, subject, "QUANTITY_INVALID", quantity=bad)

    def test_quantity_positive_and_12_digit_limit(self):
        subject = _subject()
        for bad in (0, -1, 1000000000000):
            with self.subTest(bad=bad):
                _assert_error(self, subject, "QUANTITY_INVALID", quantity=bad)
        self.assertEqual(_build(subject, quantity=999999999999).body["ord_qty"], "999999999999")

    def test_order_style_invalid_rejected(self):
        subject = _subject()
        request = subject.WatchlistOrderSendRequestInput(
            environment="demo",
            side="BUY",
            exchange="KRX",
            stock_code="005930",
            quantity=1,
            order_style="STOP",
            limit_price=1,
            source_attempt_ref="",
            authorization_evidence_ref="",
        )
        with self.assertRaisesRegex(subject.WatchlistOrderSendRequestError, "^ORDER_STYLE_UNSUPPORTED$"):
            subject.build_demo_watchlist_order_send_request_snapshot(request)
        for bad in (None, 1, True, "limit"):
            _assert_error(self, subject, "ORDER_STYLE_UNSUPPORTED", order_style=bad)

    def test_limit_price_required_exact_positive_int_and_12_digit_limit(self):
        subject = _subject()
        for bad in (None, True, False, "1", 1.0, 0, -1, 1000000000000):
            with self.subTest(bad=repr(bad)):
                _assert_error(self, subject, "LIMIT_PRICE_INVALID", order_style="LIMIT", limit_price=bad)
        self.assertEqual(_build(subject, limit_price=999999999999).body["ord_uv"], "999999999999")

    def test_market_price_must_be_none(self):
        subject = _subject()
        request = subject.WatchlistOrderSendRequestInput(
            environment="demo",
            side="BUY",
            exchange="KRX",
            stock_code="005930",
            quantity=1,
            order_style="MARKET",
            limit_price=1,
            source_attempt_ref="",
            authorization_evidence_ref="",
        )
        with self.assertRaisesRegex(subject.WatchlistOrderSendRequestError, "^MARKET_PRICE_MUST_BE_EMPTY$"):
            subject.build_demo_watchlist_order_send_request_snapshot(request)
        self.assertEqual(_build(subject, order_style="MARKET", limit_price=None).body["trde_tp"], "3")

    def test_source_attempt_ref_invalid_rejected(self):
        subject = _subject()
        for bad in ("", "   ", "x\n", "x\t", "x\x00", "x" * 129, None, 1, True):
            with self.subTest(bad=repr(bad)):
                _assert_error(self, subject, "SOURCE_ATTEMPT_REF_INVALID", source_attempt_ref=bad)

    def test_authorization_evidence_ref_invalid_rejected(self):
        subject = _subject()
        request = subject.WatchlistOrderSendRequestInput(
            environment="demo",
            side="BUY",
            exchange="KRX",
            stock_code="005930",
            quantity=1,
            order_style="MARKET",
            limit_price=None,
            source_attempt_ref="attempt-1",
            authorization_evidence_ref="",
        )
        with self.assertRaisesRegex(subject.WatchlistOrderSendRequestError, "^AUTHORIZATION_EVIDENCE_REF_INVALID$"):
            subject.build_demo_watchlist_order_send_request_snapshot(request)
        for bad in ("", "   ", "x\n", "x\t", "x\x00", "x" * 129, None, 1, True):
            with self.subTest(bad=repr(bad)):
                _assert_error(self, subject, "AUTHORIZATION_EVIDENCE_REF_INVALID", authorization_evidence_ref=bad)

    def test_provenance_references_preserved_exactly(self):
        subject = _subject()
        snap = _build(subject, source_attempt_ref=" Attempt / 001 ", authorization_evidence_ref=" Evidence / A ")
        self.assertEqual(snap.source_attempt_ref, " Attempt / 001 ")
        self.assertEqual(snap.authorization_evidence_ref, " Evidence / A ")

    def test_phase29_submission_attempt_reference_contract_available(self):
        _subject()
        phase29 = importlib.import_module(PHASE29_MODULE)
        fields = tuple(field.name for field in dataclasses.fields(phase29.KiwoomOrderSendAuthorizationContext))
        self.assertIn("submission_attempt_reference", fields)

    def test_phase29_authorization_evidence_snapshot_id_contract_available(self):
        _subject()
        phase29 = importlib.import_module(PHASE29_MODULE)
        fields = tuple(field.name for field in dataclasses.fields(phase29.KiwoomOrderSendAuthorizationContext))
        self.assertIn("authorization_evidence_snapshot_id", fields)

    def test_materializer_does_not_traverse_phase29_source_chain(self):
        subject = _subject()
        tree = _source_tree()
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        self.assertFalse(any("watchlist_order_send_authorization" in name for name in imported))
        self.assertFalse(any("watchlist_order_attempt_preparation" in name for name in imported))
        snap = _build(subject, source_attempt_ref="opaque-a", authorization_evidence_ref="opaque-b")
        self.assertEqual((snap.source_attempt_ref, snap.authorization_evidence_ref), ("opaque-a", "opaque-b"))

    def test_fingerprint_repeat_stable(self):
        subject = _subject()
        self.assertEqual(_build(subject).materialization_fingerprint, _build(subject).materialization_fingerprint)

    def test_fingerprint_known_vector(self):
        subject = _subject()
        self.assertEqual(
            _build(subject).materialization_fingerprint,
            "95a9556fe973f96e40d664b3369d96366f6bc00fbc3ccd34cc14058925bebc69",
        )

    def test_fingerprint_changes_with_provider_request(self):
        subject = _subject()
        self.assertNotEqual(_build(subject).materialization_fingerprint, _build(subject, quantity=4).materialization_fingerprint)

    def test_fingerprint_changes_with_source_attempt_ref(self):
        subject = _subject()
        self.assertNotEqual(
            _build(subject).materialization_fingerprint,
            _build(subject, source_attempt_ref="attempt-2").materialization_fingerprint,
        )

    def test_fingerprint_changes_with_authorization_evidence_ref(self):
        subject = _subject()
        self.assertNotEqual(
            _build(subject).materialization_fingerprint,
            _build(subject, authorization_evidence_ref="snapshot-2").materialization_fingerprint,
        )

    def test_fingerprint_is_lowercase_sha256_hex(self):
        subject = _subject()
        fingerprint = _build(subject).materialization_fingerprint
        self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")

    def test_builder_does_not_read_environment_credentials(self):
        subject = _subject()
        self.assertNotIn("os", _import_roots())
        with mock.patch("os.getenv", side_effect=AssertionError("credential getenv accessed")):
            snap = _build(subject)
        self.assertFalse(snap.credential_accessed)

    def test_builder_does_not_perform_network_io(self):
        subject = _subject()
        self.assertFalse({"socket", "urllib", "http", "requests", "httpx"} & _import_roots())
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network accessed")):
            snap = _build(subject)
        self.assertFalse(snap.network_performed)

    def test_builder_does_not_access_account(self):
        subject = _subject()
        self.assertFalse({"kiwoom", "requests", "httpx"} & _import_roots())
        self.assertFalse(_build(subject).account_accessed)

    def test_builder_does_not_submit_order_or_call_provider(self):
        subject = _subject()
        self.assertFalse({"socket", "urllib", "http", "requests", "httpx", "kiwoom"} & _import_roots())
        snap = _build(subject)
        self.assertFalse(snap.transport_allowed)
        self.assertFalse(snap.order_submitted)

    def test_transport_and_side_effect_flags_are_false(self):
        subject = _subject()
        snap = _build(subject)
        self.assertEqual(
            (
                snap.transport_allowed,
                snap.credential_accessed,
                snap.network_performed,
                snap.account_accessed,
                snap.order_submitted,
            ),
            (False, False, False, False, False),
        )

    def test_builder_does_not_use_file_io_retry_time_uuid_or_randomness(self):
        subject = _subject()
        roots = _import_roots()
        self.assertFalse({"os", "pathlib", "io", "time", "uuid", "random"} & roots)
        tree = _source_tree()
        called_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("open", called_names)
        self.assertNotIn("sleep", called_names)
        self.assertNotIn("uuid4", called_names)
        self.assertEqual(_build(subject).materialization_fingerprint, _build(subject).materialization_fingerprint)


if __name__ == "__main__":
    unittest.main()
