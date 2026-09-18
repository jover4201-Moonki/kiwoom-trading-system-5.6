import builtins
import dataclasses
import hashlib
import inspect
import json
import os
import random
import re
import socket
import time
import unittest
import urllib.request
import uuid
from types import MappingProxyType
from unittest import mock

from kiwoom_trading_system.brokers.kiwoom import rest as rest_package
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_send_request as phase30
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_authorization_consumption_claim as subject


EXPECTED_PUBLIC_API = [
    "WatchlistOrderAuthorizationConsumptionClaimError",
    "KiwoomOrderAuthorizationConsumptionClaimContext",
    "WatchlistOrderAuthorizationConsumptionClaimSnapshot",
    "build_demo_watchlist_order_authorization_consumption_claim_snapshot",
]

EXPECTED_TEST_NAMES = [
    "test_public_api_exact_four_symbols",
    "test_error_is_runtime_error",
    "test_context_exact_fields_and_frozen",
    "test_snapshot_exact_fields_and_frozen",
    "test_builder_exact_signature_and_return_type",
    "test_builder_is_synchronous",
    "test_rejects_nonexact_phase30_snapshot_type",
    "test_preserves_phase30_snapshot_identity",
    "test_requires_phase30_demo_environment",
    "test_requires_phase30_buy_side",
    "test_requires_phase30_krx_exchange",
    "test_requires_phase30_kt10000_api_id",
    "test_requires_phase30_post_method",
    "test_requires_phase30_order_path",
    "test_requires_phase30_exact_provider_body_key_set_and_string_values",
    "test_requires_phase30_all_safety_flags_false",
    "test_recomputes_and_requires_exact_phase30_materialization_fingerprint",
    "test_does_not_remap_recalculate_replace_mutate_or_reorder_phase30_request",
    "test_rejects_nonexact_context_type",
    "test_authorization_authority_reference_preserves_phase29_exact_str_nonblank_contract",
    "test_authorization_evidence_snapshot_id_binding_input_invalid_rejected",
    "test_submission_attempt_reference_binding_input_invalid_rejected",
    "test_send_authorization_reference_preserves_phase29_exact_str_nonblank_contract",
    "test_submission_attempt_reference_binding_exact",
    "test_authorization_evidence_reference_binding_exact",
    "test_claim_identity_exact_four_tuple",
    "test_replay_guard_exact_two_tuple",
    "test_context_references_preserved_exactly_without_external_origin_claim",
    "test_claim_fingerprint_repeat_stable",
    "test_claim_fingerprint_known_vector",
    "test_claim_fingerprint_changes_with_materialization_fingerprint",
    "test_claim_fingerprint_changes_with_authority_reference",
    "test_claim_fingerprint_changes_with_send_authorization_reference",
    "test_claim_fingerprint_is_lowercase_sha256_hex",
    "test_claim_prepared_true",
    "test_authorization_consumption_committed_false",
    "test_post_permitted_false",
    "test_automatic_retry_permitted_false",
    "test_builder_does_not_call_authorization_authority_or_mutate_ledger",
    "test_builder_does_not_read_credentials_access_account_or_perform_network",
    "test_builder_does_not_call_provider_parse_response_or_handle_order_number",
    "test_builder_does_not_use_file_io_retry_time_uuid_or_randomness",
]


class TestWatchlistOrderAuthorizationConsumptionClaim(unittest.TestCase):
    def _valid_source(self, *, quantity=3, stock_code="005930"):
        request = phase30.WatchlistOrderSendRequestInput(
            environment="demo",
            side="BUY",
            exchange="KRX",
            stock_code=stock_code,
            quantity=quantity,
            order_style="LIMIT",
            limit_price=64500,
            source_attempt_ref="attempt-1",
            authorization_evidence_ref="snapshot-1",
        )
        return phase30.build_demo_watchlist_order_send_request_snapshot(request)

    def _valid_market_source(self):
        request = phase30.WatchlistOrderSendRequestInput(
            environment="demo",
            side="BUY",
            exchange="KRX",
            stock_code="005930",
            quantity=3,
            order_style="MARKET",
            limit_price=None,
            source_attempt_ref="attempt-1",
            authorization_evidence_ref="snapshot-1",
        )
        return phase30.build_demo_watchlist_order_send_request_snapshot(request)

    def _valid_context(self, **changes):
        values = {
            "authorization_authority_reference": "authority-1",
            "authorization_evidence_snapshot_id": "snapshot-1",
            "submission_attempt_reference": "attempt-1",
            "send_authorization_reference": "grant-1",
        }
        values.update(changes)
        return subject.KiwoomOrderAuthorizationConsumptionClaimContext(**values)

    def _build(self, source=None, context=None):
        return subject.build_demo_watchlist_order_authorization_consumption_claim_snapshot(
            self._valid_source() if source is None else source,
            self._valid_context() if context is None else context,
        )

    def _assert_error(self, code, *, source=None, context=None):
        with self.assertRaises(subject.WatchlistOrderAuthorizationConsumptionClaimError) as cm:
            self._build(source=source, context=context)
        self.assertEqual(str(cm.exception), code)

    def _with_body(self, source, mutate):
        body = dict(source.body)
        mutate(body)
        return dataclasses.replace(source, body=MappingProxyType(body))

    def test_public_api_exact_four_symbols(self):
        self.assertEqual(subject.__all__, EXPECTED_PUBLIC_API)
        self.assertEqual(
            sorted(name for name in dir(self.__class__) if name.startswith("test_")),
            sorted(EXPECTED_TEST_NAMES),
        )
        for name in EXPECTED_PUBLIC_API:
            self.assertNotIn(name, rest_package.__dict__)

    def test_error_is_runtime_error(self):
        self.assertTrue(issubclass(subject.WatchlistOrderAuthorizationConsumptionClaimError, RuntimeError))

    def test_context_exact_fields_and_frozen(self):
        self.assertEqual(
            [field.name for field in dataclasses.fields(subject.KiwoomOrderAuthorizationConsumptionClaimContext)],
            [
                "authorization_authority_reference",
                "authorization_evidence_snapshot_id",
                "submission_attempt_reference",
                "send_authorization_reference",
            ],
        )
        self.assertTrue(subject.KiwoomOrderAuthorizationConsumptionClaimContext.__dataclass_params__.frozen)
        context = self._valid_context()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            context.authorization_authority_reference = "changed"

    def test_snapshot_exact_fields_and_frozen(self):
        self.assertEqual(
            [field.name for field in dataclasses.fields(subject.WatchlistOrderAuthorizationConsumptionClaimSnapshot)],
            [
                "source_snapshot",
                "context",
                "authorization_claim_identity",
                "authorization_replay_guard",
                "claim_fingerprint",
                "claim_prepared",
                "authorization_consumption_committed",
                "post_permitted",
                "automatic_retry_permitted",
                "network_performed",
                "order_submitted",
            ],
        )
        self.assertTrue(subject.WatchlistOrderAuthorizationConsumptionClaimSnapshot.__dataclass_params__.frozen)
        snapshot = self._build()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.claim_prepared = False

    def test_builder_exact_signature_and_return_type(self):
        signature = inspect.signature(subject.build_demo_watchlist_order_authorization_consumption_claim_snapshot)
        self.assertEqual(list(signature.parameters), ["source_snapshot", "context"])
        self.assertIs(signature.parameters["source_snapshot"].annotation, phase30.WatchlistOrderSendRequestSnapshot)
        self.assertIs(
            signature.parameters["context"].annotation,
            subject.KiwoomOrderAuthorizationConsumptionClaimContext,
        )
        self.assertIs(
            signature.return_annotation,
            subject.WatchlistOrderAuthorizationConsumptionClaimSnapshot,
        )
        self.assertTrue(all(p.default is inspect._empty for p in signature.parameters.values()))
        self.assertIs(type(self._build()), subject.WatchlistOrderAuthorizationConsumptionClaimSnapshot)

    def test_builder_is_synchronous(self):
        self.assertFalse(inspect.iscoroutinefunction(subject.build_demo_watchlist_order_authorization_consumption_claim_snapshot))

    def test_rejects_nonexact_phase30_snapshot_type(self):
        class SnapshotImpostor:
            pass
        self._assert_error(
            "SOURCE_SNAPSHOT_TYPE_INVALID",
            source=SnapshotImpostor(),
            context=object(),
        )

    def test_preserves_phase30_snapshot_identity(self):
        source = self._valid_source()
        result = self._build(source=source)
        self.assertIs(result.source_snapshot, source)

    def test_requires_phase30_demo_environment(self):
        self._assert_error("SOURCE_SNAPSHOT_STRUCTURE_INVALID", source=dataclasses.replace(self._valid_source(), environment="prod"))

    def test_requires_phase30_buy_side(self):
        self._assert_error("SOURCE_SNAPSHOT_STRUCTURE_INVALID", source=dataclasses.replace(self._valid_source(), side="SELL"))

    def test_requires_phase30_krx_exchange(self):
        self._assert_error("SOURCE_SNAPSHOT_STRUCTURE_INVALID", source=dataclasses.replace(self._valid_source(), exchange="NXT"))

    def test_requires_phase30_kt10000_api_id(self):
        self._assert_error("SOURCE_SNAPSHOT_STRUCTURE_INVALID", source=dataclasses.replace(self._valid_source(), api_id="kt10001"))

    def test_requires_phase30_post_method(self):
        self._assert_error("SOURCE_SNAPSHOT_STRUCTURE_INVALID", source=dataclasses.replace(self._valid_source(), http_method="GET"))

    def test_requires_phase30_order_path(self):
        self._assert_error("SOURCE_SNAPSHOT_STRUCTURE_INVALID", source=dataclasses.replace(self._valid_source(), api_path="/wrong"))

    def test_requires_phase30_exact_provider_body_key_set_and_string_values(self):
        source = self._valid_source()
        invalid_sources = [
            self._with_body(source, lambda b: b.__setitem__("extra", "x")),
            self._with_body(source, lambda b: b.__setitem__("ord_qty", 3)),
            self._with_body(source, lambda b: b.__setitem__("dmst_stex_tp", "NXT")),
            self._with_body(source, lambda b: b.__setitem__("trde_tp", "9")),
            self._with_body(source, lambda b: b.__setitem__("ord_uv", "")),
            self._with_body(source, lambda b: b.__setitem__("cond_uv", "1")),
        ]
        market = self._valid_market_source()
        invalid_sources.append(self._with_body(market, lambda b: b.__setitem__("ord_uv", "1")))
        for bad in invalid_sources:
            with self.subTest(body=bad.body):
                self._assert_error("SOURCE_SNAPSHOT_STRUCTURE_INVALID", source=bad)

    def test_requires_phase30_all_safety_flags_false(self):
        source = self._valid_source()
        for field in ["transport_allowed", "credential_accessed", "network_performed", "account_accessed", "order_submitted"]:
            with self.subTest(field=field):
                self._assert_error("SOURCE_SNAPSHOT_SAFETY_INVALID", source=dataclasses.replace(source, **{field: True}))

    def test_recomputes_and_requires_exact_phase30_materialization_fingerprint(self):
        source = dataclasses.replace(self._valid_source(), materialization_fingerprint="0" * 64)
        self._assert_error("SOURCE_MATERIALIZATION_FINGERPRINT_INVALID", source=source)

    def test_does_not_remap_recalculate_replace_mutate_or_reorder_phase30_request(self):
        source = self._valid_source()
        before = (source, source.body, tuple(source.body.items()), source.materialization_fingerprint)
        result = self._build(source=source)
        after = (source, source.body, tuple(source.body.items()), source.materialization_fingerprint)
        self.assertEqual(before, after)
        self.assertIs(result.source_snapshot, source)
        self.assertIs(result.source_snapshot.body, source.body)

    def test_rejects_nonexact_context_type(self):
        class ContextImpostor:
            authorization_authority_reference = ""
        self._assert_error("CONTEXT_TYPE_INVALID", context=ContextImpostor())

    def test_authorization_authority_reference_preserves_phase29_exact_str_nonblank_contract(self):
        for invalid in [None, 1, "", " ", "\t\r\n"]:
            with self.subTest(invalid=invalid):
                self._assert_error(
                    "AUTHORIZATION_AUTHORITY_REFERENCE_INVALID",
                    context=self._valid_context(authorization_authority_reference=invalid),
                )
        for valid in ["A" * 500, "authority\ncontrol", " authority "]:
            with self.subTest(valid=valid):
                result = self._build(context=self._valid_context(authorization_authority_reference=valid))
                self.assertEqual(result.context.authorization_authority_reference, valid)

    def test_authorization_evidence_snapshot_id_binding_input_invalid_rejected(self):
        invalids = [None, 1, "", " ", "x\n", "x\x7f", "x" * 129]
        for invalid in invalids:
            with self.subTest(invalid=invalid):
                self._assert_error(
                    "AUTHORIZATION_EVIDENCE_SNAPSHOT_ID_INVALID",
                    context=self._valid_context(authorization_evidence_snapshot_id=invalid),
                )

    def test_submission_attempt_reference_binding_input_invalid_rejected(self):
        invalids = [None, 1, "", " ", "x\n", "x\x7f", "x" * 129]
        for invalid in invalids:
            with self.subTest(invalid=invalid):
                self._assert_error(
                    "SUBMISSION_ATTEMPT_REFERENCE_INVALID",
                    context=self._valid_context(submission_attempt_reference=invalid),
                )

    def test_send_authorization_reference_preserves_phase29_exact_str_nonblank_contract(self):
        for invalid in [None, 1, "", " ", "\t\r\n"]:
            with self.subTest(invalid=invalid):
                self._assert_error(
                    "SEND_AUTHORIZATION_REFERENCE_INVALID",
                    context=self._valid_context(send_authorization_reference=invalid),
                )
        for valid in ["G" * 500, "grant\ncontrol", " grant "]:
            with self.subTest(valid=valid):
                result = self._build(context=self._valid_context(send_authorization_reference=valid))
                self.assertEqual(result.context.send_authorization_reference, valid)

    def test_submission_attempt_reference_binding_exact(self):
        self._assert_error(
            "SUBMISSION_ATTEMPT_REFERENCE_MISMATCH",
            context=self._valid_context(submission_attempt_reference="attempt-2"),
        )

    def test_authorization_evidence_reference_binding_exact(self):
        self._assert_error(
            "AUTHORIZATION_EVIDENCE_REFERENCE_MISMATCH",
            context=self._valid_context(authorization_evidence_snapshot_id="snapshot-2"),
        )

    def test_claim_identity_exact_four_tuple(self):
        result = self._build()
        self.assertEqual(
            result.authorization_claim_identity,
            ("authority-1", "snapshot-1", "attempt-1", "grant-1"),
        )
        self.assertIs(type(result.authorization_claim_identity), tuple)

    def test_replay_guard_exact_two_tuple(self):
        result = self._build()
        self.assertEqual(result.authorization_replay_guard, ("authority-1", "grant-1"))
        self.assertIs(type(result.authorization_replay_guard), tuple)

    def test_context_references_preserved_exactly_without_external_origin_claim(self):
        context = self._valid_context(
            authorization_authority_reference=" authority\nopaque ",
            send_authorization_reference=" grant\topaque ",
        )
        result = self._build(context=context)
        self.assertIs(result.context, context)
        self.assertEqual(result.authorization_claim_identity[0], context.authorization_authority_reference)
        self.assertEqual(result.authorization_claim_identity[3], context.send_authorization_reference)
        for forbidden in ["authority_verified", "grant_verified", "currently_valid", "consumed", "revoked"]:
            self.assertNotIn(forbidden, {field.name for field in dataclasses.fields(result)})

    def test_claim_fingerprint_repeat_stable(self):
        first = self._build().claim_fingerprint
        second = self._build().claim_fingerprint
        self.assertEqual(first, second)

    def test_claim_fingerprint_known_vector(self):
        self.assertEqual(
            self._build().claim_fingerprint,
            "6ecb23bec89d683c156299afc011b8eac1345e0d664de070b7a3dba427f3e7c4",
        )

    def test_claim_fingerprint_changes_with_materialization_fingerprint(self):
        first = self._build()
        second_source = self._valid_source(quantity=4)
        second = self._build(source=second_source)
        self.assertNotEqual(first.source_snapshot.materialization_fingerprint, second.source_snapshot.materialization_fingerprint)
        self.assertNotEqual(first.claim_fingerprint, second.claim_fingerprint)

    def test_claim_fingerprint_changes_with_authority_reference(self):
        first = self._build()
        second = self._build(context=self._valid_context(authorization_authority_reference="authority-2"))
        self.assertNotEqual(first.claim_fingerprint, second.claim_fingerprint)

    def test_claim_fingerprint_changes_with_send_authorization_reference(self):
        first = self._build()
        second = self._build(context=self._valid_context(send_authorization_reference="grant-2"))
        self.assertNotEqual(first.claim_fingerprint, second.claim_fingerprint)

    def test_claim_fingerprint_is_lowercase_sha256_hex(self):
        fingerprint = self._build().claim_fingerprint
        self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")
        self.assertEqual(fingerprint, fingerprint.lower())

    def test_claim_prepared_true(self):
        self.assertIs(self._build().claim_prepared, True)

    def test_authorization_consumption_committed_false(self):
        self.assertIs(self._build().authorization_consumption_committed, False)

    def test_post_permitted_false(self):
        self.assertIs(self._build().post_permitted, False)

    def test_automatic_retry_permitted_false(self):
        self.assertIs(self._build().automatic_retry_permitted, False)

    def test_builder_does_not_call_authorization_authority_or_mutate_ledger(self):
        with mock.patch.object(subject, "_authorization_authority_call", create=True) as authority_call, \
             mock.patch.object(subject, "_authorization_ledger_mutation", create=True) as ledger_mutation:
            result = self._build()
        authority_call.assert_not_called()
        ledger_mutation.assert_not_called()
        self.assertIs(result.authorization_consumption_committed, False)

    def test_builder_does_not_read_credentials_access_account_or_perform_network(self):
        with mock.patch.object(os, "getenv", side_effect=AssertionError("os.getenv forbidden")), \
             mock.patch.object(socket, "socket", side_effect=AssertionError("socket forbidden")), \
             mock.patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("urlopen forbidden")):
            result = self._build()
        self.assertIs(result.network_performed, False)
        self.assertFalse(hasattr(result, "account"))

    def test_builder_does_not_call_provider_parse_response_or_handle_order_number(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("provider forbidden")), \
             mock.patch.object(json, "loads", side_effect=AssertionError("response parsing forbidden")):
            result = self._build()
        self.assertFalse(hasattr(result, "response"))
        self.assertFalse(hasattr(result, "ord_no"))

    def test_builder_does_not_use_file_io_retry_time_uuid_or_randomness(self):
        with mock.patch.object(builtins, "open", side_effect=AssertionError("file I/O forbidden")), \
             mock.patch.object(time, "time", side_effect=AssertionError("time forbidden")), \
             mock.patch.object(time, "sleep", side_effect=AssertionError("retry/backoff forbidden")), \
             mock.patch.object(uuid, "uuid4", side_effect=AssertionError("uuid forbidden")), \
             mock.patch.object(random, "random", side_effect=AssertionError("random forbidden")):
            result = self._build()
        self.assertTrue(result.claim_prepared)


if __name__ == "__main__":
    unittest.main()
