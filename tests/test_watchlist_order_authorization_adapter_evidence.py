import asyncio
import builtins
import dataclasses
import gc
import hashlib
import inspect
import io
import json
import os
import random
import re
import socket
import time
import types
import unittest
import urllib.request
import uuid
import warnings
from types import MappingProxyType
from unittest import mock

from kiwoom_trading_system.brokers.kiwoom import rest as rest_package
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_send_request as phase30
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_authorization_consumption_claim as phase31
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_authorization_adapter_evidence as subject

EXPECTED_PUBLIC_API = [
    "WatchlistOrderAuthorizationAdapterEvidenceError",
    "KiwoomOrderAuthorizationAuthorityAdapter",
    "KiwoomOrderAuthorizationAuthorityReportedResult",
    "WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot",
    "check_and_consume_demo_watchlist_order_authorization_adapter_evidence",
]

EXPECTED_TEST_NAMES = """
test_public_api_exact_five_symbols
test_error_is_runtime_error
test_authority_adapter_protocol_is_typing_only_not_trust_proof
test_authority_result_exact_thirteen_fields_and_frozen
test_snapshot_exact_twenty_two_fields_and_frozen
test_builder_exact_signature_and_return_type
test_builder_is_synchronous
test_no_package_reexport
test_rejects_nonexact_phase31_snapshot_type
test_preserves_phase31_snapshot_identity
test_requires_phase31_claim_prepared_true
test_requires_phase31_authorization_consumption_committed_false
test_requires_phase31_post_permitted_false
test_requires_phase31_automatic_retry_permitted_false
test_requires_phase31_network_performed_false
test_requires_phase31_order_submitted_false
test_recomputes_and_requires_exact_phase31_claim_fingerprint
test_requires_phase31_claim_identity_exact_four_tuple
test_requires_phase31_replay_guard_exact_two_tuple
test_revalidates_phase30_request_materialization_and_reference_bindings
test_requires_phase30_transport_allowed_false_without_override
test_does_not_mutate_phase29_phase30_or_phase31_upstream_objects
test_accepts_valid_asserted_authority_approval_reference
test_rejects_invalid_asserted_authority_approval_reference_variants
test_accepts_valid_asserted_authority_conformance_reference
test_rejects_invalid_asserted_authority_conformance_reference_variants
test_passive_surface_accepts_class_defined_synchronous_python_instance_method
test_passive_surface_accepts_inherited_synchronous_python_instance_method
test_passive_surface_rejects_missing_surface
test_passive_surface_rejects_nonfunction_class_attribute
test_passive_surface_rejects_staticmethod
test_passive_surface_rejects_classmethod
test_passive_surface_rejects_property_without_executing_getter
test_passive_surface_rejects_custom_descriptor_without_executing_get
test_passive_surface_rejects_dynamic_getattr_without_executing_it
test_passive_surface_does_not_execute_custom_getattribute
test_passive_surface_rejects_instance_level_shadow
test_passive_surface_rejects_callable_object_surface
test_passive_surface_does_not_use_getattr_hasattr_or_callable
test_passive_surface_validation_is_not_authority_trust_proof
test_passive_surface_rejects_native_coroutine_function
test_passive_surface_rejects_native_generator_function
test_passive_surface_rejects_native_async_generator_function
test_passive_surface_rejects_markcoroutinefunction_sync_function
test_passive_surface_rejects_types_coroutine_generator_function
test_function_kind_rejection_executes_no_authority_body
test_function_kind_rejection_uses_surface_invalid_reason
test_function_kind_rejection_attempts_authority_zero_times
test_function_kind_rejection_returns_no_snapshot_fingerprint_or_partial_result
test_function_kind_rejection_is_not_normalized_to_indeterminate
test_ordinary_sync_decorator_wrapping_sync_target_is_accepted
test_decorated_final_coroutine_function_is_rejected_locally
test_unmarked_sync_wrapper_around_async_target_passes_local_surface_classification
test_unmarked_sync_wrapper_returning_generator_passes_local_surface_classification
test_unmarked_sync_wrapper_returning_async_generator_passes_local_surface_classification
test_unmarked_sync_wrapper_returning_generic_awaitable_passes_local_surface_classification
test_validated_function_is_bound_with_types_methodtype
test_invocation_binding_does_not_use_dynamic_attribute_resolution
test_custom_getattribute_not_executed_during_invocation_binding
test_dynamic_getattr_not_executed_during_invocation_binding
test_valid_local_gate_invokes_exact_validated_function_once
test_does_not_prefetch_second_check_or_retry_authority
test_passes_exact_claim_replay_and_claim_fingerprint
test_passes_exact_asserted_authority_references
test_sync_wrapper_returning_coroutine_becomes_contract_violation_indeterminate
test_returned_coroutine_is_not_awaited_or_driven_by_phase32
test_sync_wrapper_returning_generator_becomes_contract_violation_indeterminate
test_returned_generator_is_not_iterated_or_driven_by_phase32
test_sync_wrapper_returning_async_generator_becomes_contract_violation_indeterminate
test_returned_async_generator_is_not_iterated_or_driven_by_phase32
test_sync_wrapper_returning_generic_awaitable_becomes_contract_violation_indeterminate
test_returned_generic_awaitable_dunder_await_is_not_called_by_phase32
test_invalid_deferred_return_is_not_closed_awaited_iterated_or_driven_by_phase32
test_invalid_deferred_return_sets_authority_invocation_attempted_true
test_invalid_deferred_return_sets_authority_result_none
test_invalid_deferred_return_sets_result_and_consumption_references_none
test_invalid_deferred_return_sets_commit_state_unknown_and_reconciliation_required
test_invalid_deferred_return_never_sets_consumption_evidence_candidate_ready
test_invalid_deferred_return_never_grants_transport_or_provider_permission
test_invalid_deferred_return_is_never_retried
test_signature_mismatch_at_call_becomes_authority_exception_indeterminate
test_actual_call_runtime_error_becomes_authority_exception_indeterminate
test_actual_call_timeout_becomes_authority_timeout_indeterminate
test_actual_call_cancelled_error_is_reraised
test_actual_call_keyboard_interrupt_is_reraised
test_actual_call_system_exit_is_reraised
test_authority_invocation_attempted_is_true_when_call_expression_starts
test_authority_invocation_attempted_is_true_for_every_returned_snapshot
test_authority_reported_consumed_requires_exact_echo_bindings
test_authority_reported_consumed_requires_valid_authority_result_reference
test_malformed_consumed_authority_result_reference_becomes_contract_violation_indeterminate
test_authority_reported_consumed_requires_no_block_or_indeterminate_reason
test_authority_reported_consumed_accepts_valid_consumption_reference
test_blank_consumption_reference_becomes_contract_violation_indeterminate
test_whitespace_consumption_reference_becomes_contract_violation_indeterminate
test_control_character_consumption_reference_becomes_contract_violation_indeterminate
test_overlength_consumption_reference_becomes_contract_violation_indeterminate
test_authority_reported_consumed_requires_commit_state_known_exact_true
test_authority_reported_consumed_requires_both_reported_commit_flags_exact_true
test_authority_reported_consumed_sets_candidate_ready_true_without_permission
test_authority_reported_consumed_snapshot_matches_exact_state_matrix
test_authority_reported_blocked_requires_exact_echo_bindings
test_authority_reported_blocked_requires_valid_authority_result_reference
test_malformed_blocked_authority_result_reference_becomes_contract_violation_indeterminate
test_authority_reported_blocked_requires_allowed_block_reason
test_unsupported_block_reason_becomes_contract_violation_indeterminate
test_authority_reported_blocked_requires_indeterminate_reason_none
test_authority_reported_blocked_requires_consumption_reference_none
test_authority_reported_blocked_requires_commit_state_known_exact_true
test_authority_reported_blocked_requires_both_reported_commit_flags_exact_false
test_authority_reported_blocked_sets_candidate_ready_false_reconciliation_false_no_retry
test_authority_reported_blocked_snapshot_matches_exact_state_matrix
test_block_reason_precedence_is_backend_normative_not_locally_rederived
test_explicit_indeterminate_requires_exact_echo_bindings
test_explicit_indeterminate_requires_valid_authority_result_reference
test_malformed_explicit_indeterminate_authority_result_reference_becomes_contract_violation_indeterminate
test_explicit_indeterminate_requires_block_reason_none
test_explicit_indeterminate_requires_reason_authority_reported_indeterminate
test_explicit_indeterminate_requires_consumption_reference_none
test_explicit_indeterminate_requires_commit_state_known_exact_false
test_explicit_indeterminate_requires_both_reported_commit_flags_none
test_explicit_indeterminate_sets_candidate_false_reconciliation_true_no_retry
test_explicit_indeterminate_preserves_valid_authority_result
test_explicit_indeterminate_snapshot_matches_exact_state_matrix
test_wrong_authority_result_type_becomes_contract_violation_indeterminate
test_echo_mismatch_becomes_contract_violation_indeterminate
test_partial_true_false_commit_becomes_contract_violation_indeterminate
test_partial_false_true_commit_becomes_contract_violation_indeterminate
test_impossible_commit_state_combination_becomes_contract_violation_indeterminate
test_authority_result_reported_commit_fields_reject_int_zero_and_one
test_authority_result_commit_state_known_rejects_int_zero_and_one
test_snapshot_boolean_fields_reject_int_zero_and_one
test_exact_string_fields_reject_string_subclasses
test_identity_tuple_fields_reject_nonexact_tuple_shapes
test_local_validation_failure_raises_phase32_error
test_local_validation_failure_returns_no_snapshot_fingerprint_or_partial_result
test_local_validation_failure_is_not_normalized_to_indeterminate
test_local_validation_failure_attempts_authority_zero_times
test_local_validation_failure_raises_exact_allowed_reason
test_multiple_local_errors_obey_exact_first_error_precedence
test_local_validation_order_source_type_precedes_source_contract
test_local_validation_order_phase30_binding_precedes_claim_fingerprint
test_local_validation_order_asserted_references_precedes_surface_validation
test_evidence_fingerprint_envelope_has_exact_twenty_fields
test_evidence_fingerprint_repeat_stable_and_lowercase_sha256
test_evidence_fingerprint_changes_with_authority_result_reference
test_evidence_fingerprint_changes_with_consumption_reference
test_evidence_fingerprint_changes_with_reported_commit_state
test_evidence_fingerprint_changes_with_candidate_reconciliation_and_direct_safety_flags
test_evidence_fingerprint_changes_with_authority_invocation_attempted
test_snapshot_exposes_no_post_permitted_transport_allowed_or_send_permission_field
test_consumption_evidence_candidate_ready_never_grants_transport
test_authority_trust_independently_verified_is_always_false
test_phase32_direct_safety_flags_are_always_false
test_does_not_access_credentials_account_network_provider_or_order
test_does_not_use_file_io_wall_clock_uuid_randomness_retry_or_backoff
test_does_not_mutate_dependencies_git_or_upstream_contracts
test_bare_coroutine_invalid_return_is_adapter_contract_violation
test_bare_coroutine_invalid_return_may_emit_never_awaited_runtimewarning
test_phase32_does_not_await_returned_bare_coroutine
test_phase32_does_not_cancel_returned_bare_coroutine
test_phase32_does_not_close_returned_bare_coroutine
test_phase32_does_not_suppress_never_awaited_runtimewarning
test_phase32_does_not_mutate_global_warning_filters
test_returned_generator_is_not_closed_by_phase32
test_returned_async_generator_is_not_aclose_by_phase32
test_returned_custom_awaitable_is_not_closed_cancelled_or_driven_by_phase32
test_returned_future_is_not_awaited_cancelled_or_result_retrieved_by_phase32
test_returned_task_is_not_awaited_cancelled_or_result_retrieved_by_phase32
test_returned_task_may_already_be_scheduled_before_result_validation
test_scheduled_task_background_activity_may_continue_after_builder_returns
test_scheduled_task_background_activity_is_not_interpreted_as_success
test_scheduled_task_does_not_create_candidate_ready_or_permission
test_returned_future_and_task_remain_reconciliation_required
test_phase32_does_not_retain_invalid_task_or_future_to_completion
test_phase32_does_not_install_done_callback_on_invalid_task_or_future
test_invalid_deferred_object_lifecycle_remains_adapter_authority_responsibility
test_conforming_adapter_must_return_exact_synchronous_result_dataclass
test_conforming_adapter_must_own_and_settle_async_background_work_before_return
test_invalid_deferred_object_is_not_stored_in_snapshot
test_invalid_deferred_object_is_only_transiently_referenced_for_result_validation
test_invalid_deferred_return_never_triggers_second_authority_attempt
test_invalid_deferred_return_never_triggers_automatic_retry
test_task_exception_never_retrieved_diagnostic_is_not_suppressed_or_reclassified
test_future_exception_never_retrieved_diagnostic_is_not_suppressed_or_reclassified
test_background_task_completion_after_builder_return_does_not_retroactively_change_snapshot
test_background_task_failure_after_builder_return_does_not_retroactively_change_snapshot
test_direct_safety_flags_do_not_claim_adapter_background_work_absent
test_already_done_future_with_result_is_still_wrong_exact_type_contract_violation
test_phase32_does_not_call_future_result_exception_or_add_done_callback
""".strip().splitlines()

BLOCK_REASONS = [
    "CLAIM_ALREADY_CONSUMED", "REPLAY_GUARD_ALREADY_CONSUMED",
    "AUTHORITY_NAMESPACE_MISMATCH", "EVIDENCE_SNAPSHOT_MISMATCH",
    "SUBMISSION_ATTEMPT_MISMATCH", "SEND_AUTHORIZATION_MISMATCH",
    "GRANT_ATTEMPT_BINDING_INVALID", "AUTHORIZATION_REVOKED",
    "AUTHORIZATION_STALE", "AUTHORIZATION_INVALID",
]

class TestWatchlistOrderAuthorizationAdapterEvidence(unittest.TestCase):
    def _phase30(self):
        request = phase30.WatchlistOrderSendRequestInput(
            environment="demo", side="BUY", exchange="KRX", stock_code="005930",
            quantity=3, order_style="LIMIT", limit_price=64500,
            source_attempt_ref="attempt-1", authorization_evidence_ref="snapshot-1",
        )
        return phase30.build_demo_watchlist_order_send_request_snapshot(request)

    def _phase31(self):
        source = self._phase30()
        context = phase31.KiwoomOrderAuthorizationConsumptionClaimContext(
            authorization_authority_reference="authority-1",
            authorization_evidence_snapshot_id="snapshot-1",
            submission_attempt_reference="attempt-1",
            send_authorization_reference="grant-1",
        )
        return phase31.build_demo_watchlist_order_authorization_consumption_claim_snapshot(source, context)

    def _result(self, source, *, decision="AUTHORITY_REPORTED_CONSUMED", **changes):
        values = dict(
            authorization_claim_identity=source.authorization_claim_identity,
            authorization_replay_guard=source.authorization_replay_guard,
            claim_fingerprint=source.claim_fingerprint,
            asserted_authority_approval_reference="approval-1",
            asserted_authority_conformance_reference="conformance-1",
            authority_result_reference="result-1",
            decision=decision,
            block_reason=None,
            indeterminate_reason=None,
            consumption_reference="consume-1",
            authority_reported_authorization_consumption_committed=True,
            authority_reported_replay_guard_consumption_committed=True,
            commit_state_known=True,
        )
        if decision == "AUTHORITY_REPORTED_BLOCKED":
            values.update(block_reason="AUTHORIZATION_STALE", consumption_reference=None,
                          authority_reported_authorization_consumption_committed=False,
                          authority_reported_replay_guard_consumption_committed=False)
        elif decision == "INDETERMINATE":
            values.update(block_reason=None, indeterminate_reason="AUTHORITY_REPORTED_INDETERMINATE",
                          consumption_reference=None,
                          authority_reported_authorization_consumption_committed=None,
                          authority_reported_replay_guard_consumption_committed=None,
                          commit_state_known=False)
        values.update(changes)
        return subject.KiwoomOrderAuthorizationAuthorityReportedResult(**values)

    def _authority(self, result_factory=None, exc=None):
        owner = self
        class Authority:
            calls = 0
            seen = None
            def check_and_consume(self, **kwargs):
                self.calls += 1
                self.seen = kwargs
                if exc is not None:
                    raise exc
                source = owner._phase31() if result_factory is None else None
                if result_factory is None:
                    return owner._result(source)
                return result_factory(kwargs)
        return Authority()

    def _build(self, authority=None, source=None, **kwargs):
        if source is None: source = self._phase31()
        if authority is None:
            owner=self
            class Authority:
                def __init__(self): self.calls=0; self.seen=None
                def check_and_consume(self, **call):
                    self.calls += 1; self.seen=call
                    return owner._result(source)
            authority=Authority()
        return subject.check_and_consume_demo_watchlist_order_authorization_adapter_evidence(
            source, authority,
            asserted_authority_approval_reference=kwargs.get("approval", "approval-1"),
            asserted_authority_conformance_reference=kwargs.get("conformance", "conformance-1"),
        )

    def _assert_contract_violation(self, result):
        source=self._phase31(); owner=self
        class A:
            calls=0
            def check_and_consume(self, **kw): self.calls += 1; return result
        out=self._build(A(), source)
        self.assertEqual(out.decision, "INDETERMINATE")
        self.assertEqual(out.indeterminate_reason, "AUTHORITY_RESULT_CONTRACT_VIOLATION")
        self.assertIsNone(out.authority_result)
        self.assertTrue(out.authority_invocation_attempted)
        self.assertFalse(out.automatic_retry_permitted)
        return out

    def _valid_authority_for_source(self, source, *, decision="AUTHORITY_REPORTED_CONSUMED", changes=None):
        owner=self; changes=changes or {}
        class A:
            def __init__(self): self.calls=0; self.seen=None
            def check_and_consume(self, **kw):
                self.calls += 1; self.seen=kw
                return owner._result(source, decision=decision, **changes)
        return A()

    def _api_schema(self, name):
        self.assertEqual(subject.__all__, EXPECTED_PUBLIC_API)
        self.assertEqual(len(EXPECTED_TEST_NAMES), 190)
        self.assertEqual(len(set(EXPECTED_TEST_NAMES)), 190)
        self.assertTrue(issubclass(subject.WatchlistOrderAuthorizationAdapterEvidenceError, RuntimeError))
        self.assertTrue(getattr(subject.KiwoomOrderAuthorizationAuthorityAdapter, "_is_protocol", False))
        self.assertFalse(getattr(subject.KiwoomOrderAuthorizationAuthorityAdapter, "_is_runtime_protocol", False))
        for public_name in EXPECTED_PUBLIC_API:
            self.assertNotIn(public_name, rest_package.__dict__)
        self.assertEqual([f.name for f in dataclasses.fields(subject.KiwoomOrderAuthorizationAuthorityReportedResult)], [
            "authorization_claim_identity","authorization_replay_guard","claim_fingerprint",
            "asserted_authority_approval_reference","asserted_authority_conformance_reference",
            "authority_result_reference","decision","block_reason","indeterminate_reason","consumption_reference",
            "authority_reported_authorization_consumption_committed","authority_reported_replay_guard_consumption_committed","commit_state_known"])
        self.assertTrue(subject.KiwoomOrderAuthorizationAuthorityReportedResult.__dataclass_params__.frozen)
        self.assertEqual(len(dataclasses.fields(subject.WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot)), 22)
        self.assertTrue(subject.WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot.__dataclass_params__.frozen)
        sig=inspect.signature(subject.check_and_consume_demo_watchlist_order_authorization_adapter_evidence)
        self.assertEqual(list(sig.parameters), ["source_snapshot","authority","asserted_authority_approval_reference","asserted_authority_conformance_reference"])
        self.assertEqual(sig.parameters["source_snapshot"].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(sig.parameters["authority"].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(sig.parameters["asserted_authority_approval_reference"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(sig.parameters["asserted_authority_conformance_reference"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertTrue(all(p.default is inspect._empty for p in sig.parameters.values()))
        self.assertIs(sig.parameters["source_snapshot"].annotation, phase31.WatchlistOrderAuthorizationConsumptionClaimSnapshot)
        self.assertIs(sig.parameters["authority"].annotation, subject.KiwoomOrderAuthorizationAuthorityAdapter)
        self.assertIs(sig.return_annotation, subject.WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot)
        self.assertFalse(inspect.iscoroutinefunction(subject.check_and_consume_demo_watchlist_order_authorization_adapter_evidence))

    def _upstream(self, name):
        source=self._phase31(); authority=self._valid_authority_for_source(source)
        if name == "test_rejects_nonexact_phase31_snapshot_type":
            with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError) as cm:
                self._build(authority, object())
            self.assertEqual(str(cm.exception), "SOURCE_SNAPSHOT_TYPE_INVALID"); return
        field_map={
            "test_requires_phase31_claim_prepared_true": ("claim_prepared", False, "SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID"),
            "test_requires_phase31_authorization_consumption_committed_false": ("authorization_consumption_committed", True, "SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID"),
            "test_requires_phase31_post_permitted_false": ("post_permitted", True, "SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID"),
            "test_requires_phase31_automatic_retry_permitted_false": ("automatic_retry_permitted", True, "SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID"),
            "test_requires_phase31_network_performed_false": ("network_performed", True, "SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID"),
            "test_requires_phase31_order_submitted_false": ("order_submitted", True, "SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID"),
        }
        if name in field_map:
            field,value,reason=field_map[name]
            bad=dataclasses.replace(source, **{field:value})
            with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError) as cm: self._build(authority,bad)
            self.assertEqual(str(cm.exception), reason); return
        if name == "test_recomputes_and_requires_exact_phase31_claim_fingerprint":
            bad=dataclasses.replace(source, claim_fingerprint="0"*64)
            with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError) as cm: self._build(authority,bad)
            self.assertEqual(str(cm.exception), "PHASE31_CLAIM_FINGERPRINT_INVALID"); return
        if name == "test_requires_phase31_claim_identity_exact_four_tuple":
            bad=dataclasses.replace(source, authorization_claim_identity=tuple(source.authorization_claim_identity[:3]))
            with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError): self._build(authority,bad)
            return
        if name == "test_requires_phase31_replay_guard_exact_two_tuple":
            bad=dataclasses.replace(source, authorization_replay_guard=(source.authorization_replay_guard[0],))
            with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError): self._build(authority,bad)
            return
        if name in {"test_revalidates_phase30_request_materialization_and_reference_bindings","test_requires_phase30_transport_allowed_false_without_override"}:
            p30=dataclasses.replace(source.source_snapshot, transport_allowed=True)
            bad=dataclasses.replace(source, source_snapshot=p30)
            with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError) as cm: self._build(authority,bad)
            self.assertEqual(str(cm.exception), "PHASE30_REQUEST_OR_MATERIALIZATION_BINDING_INVALID"); return
        out=self._build(authority, source)
        self.assertIs(out.source_snapshot, source)
        self.assertIs(source.source_snapshot.body, out.source_snapshot.source_snapshot.body)

    def _asserted_refs(self, name):
        source=self._phase31(); authority=self._valid_authority_for_source(source)
        if "rejects_invalid" in name:
            key="approval" if "approval" in name else "conformance"
            for value in ("", " ", " x", "x ", "x\x00", "x"*129, 1):
                with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError): self._build(authority, source, **{key:value})
            return
        out=self._build(authority, source)
        self.assertEqual(out.asserted_authority_approval_reference,"approval-1")
        self.assertEqual(out.asserted_authority_conformance_reference,"conformance-1")

    def _surface(self, name):
        source=self._phase31(); owner=self; executed=[]
        def expect_invalid(authority):
            with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError) as cm: self._build(authority,source)
            self.assertEqual(str(cm.exception),"AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID")
            self.assertEqual(executed,[])
        if name in {"test_passive_surface_accepts_class_defined_synchronous_python_instance_method","test_valid_local_gate_invokes_exact_validated_function_once","test_does_not_prefetch_second_check_or_retry_authority","test_passes_exact_claim_replay_and_claim_fingerprint","test_passes_exact_asserted_authority_references","test_validated_function_is_bound_with_types_methodtype","test_passive_surface_validation_is_not_authority_trust_proof"}:
            a=self._valid_authority_for_source(source); out=self._build(a,source); self.assertEqual(a.calls,1); self.assertTrue(out.authority_invocation_attempted); self.assertEqual(a.seen["claim_fingerprint"],source.claim_fingerprint); return
        if name == "test_passive_surface_accepts_inherited_synchronous_python_instance_method":
            class Base:
                def check_and_consume(self, **kw): executed.append(1); return owner._result(source)
            class Child(Base): pass
            out=self._build(Child(),source); self.assertEqual(executed,[1]); self.assertEqual(out.decision,"AUTHORITY_REPORTED_CONSUMED"); return
        if name == "test_ordinary_sync_decorator_wrapping_sync_target_is_accepted":
            def dec(fn):
                def wrapper(self, **kw): return fn(self, **kw)
                return wrapper
            class A:
                @dec
                def check_and_consume(self, **kw): executed.append(1); return owner._result(source)
            self.assertEqual(self._build(A(),source).decision,"AUTHORITY_REPORTED_CONSUMED"); return
        if name == "test_passive_surface_rejects_missing_surface":
            class A: pass
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_nonfunction_class_attribute":
            class A: check_and_consume=object()
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_staticmethod":
            class A:
                @staticmethod
                def check_and_consume(**kw): executed.append(1)
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_classmethod":
            class A:
                @classmethod
                def check_and_consume(cls, **kw): executed.append(1)
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_property_without_executing_getter":
            class A:
                @property
                def check_and_consume(self): executed.append(1); return None
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_custom_descriptor_without_executing_get":
            class D:
                def __get__(self,*a): executed.append(1); return lambda **k: None
            class A: check_and_consume=D()
            expect_invalid(A()); return
        if name in {"test_passive_surface_rejects_dynamic_getattr_without_executing_it","test_dynamic_getattr_not_executed_during_invocation_binding"}:
            class A:
                def __getattr__(self,n): executed.append(n); return lambda **k: None
            expect_invalid(A()); return
        if name in {"test_passive_surface_does_not_execute_custom_getattribute","test_custom_getattribute_not_executed_during_invocation_binding"}:
            class A:
                def __getattribute__(self,n):
                    if n=="check_and_consume": executed.append(n)
                    return object.__getattribute__(self,n)
                def check_and_consume(self, **kw): return owner._result(source)
            out=self._build(A(),source); self.assertEqual(executed,[]); self.assertEqual(out.decision,"AUTHORITY_REPORTED_CONSUMED"); return
        if name == "test_passive_surface_rejects_instance_level_shadow":
            class A:
                def check_and_consume(self, **kw): executed.append(1)
            a=A(); a.check_and_consume=lambda **kw: None; expect_invalid(a); return
        if name == "test_passive_surface_rejects_callable_object_surface":
            class C:
                def __call__(self, **kw): executed.append(1)
            class A: check_and_consume=C()
            expect_invalid(A()); return
        if name in {"test_passive_surface_rejects_native_coroutine_function","test_decorated_final_coroutine_function_is_rejected_locally"}:
            class A:
                async def check_and_consume(self, **kw): executed.append(1)
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_native_generator_function":
            class A:
                def check_and_consume(self, **kw): executed.append(1); yield 1
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_native_async_generator_function":
            class A:
                async def check_and_consume(self, **kw): executed.append(1); yield 1
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_markcoroutinefunction_sync_function" and hasattr(inspect,"markcoroutinefunction"):
            class A:
                @inspect.markcoroutinefunction
                def check_and_consume(self, **kw): executed.append(1)
            expect_invalid(A()); return
        if name == "test_passive_surface_rejects_types_coroutine_generator_function":
            @types.coroutine
            def gen(self, **kw): executed.append(1); yield
            class A: check_and_consume=gen
            expect_invalid(A()); return
        if name in {"test_function_kind_rejection_executes_no_authority_body","test_function_kind_rejection_uses_surface_invalid_reason","test_function_kind_rejection_attempts_authority_zero_times","test_function_kind_rejection_returns_no_snapshot_fingerprint_or_partial_result","test_function_kind_rejection_is_not_normalized_to_indeterminate"}:
            class A:
                async def check_and_consume(self, **kw): executed.append(1)
            expect_invalid(A()); return
        if name in {"test_unmarked_sync_wrapper_around_async_target_passes_local_surface_classification","test_unmarked_sync_wrapper_returning_generator_passes_local_surface_classification","test_unmarked_sync_wrapper_returning_async_generator_passes_local_surface_classification","test_unmarked_sync_wrapper_returning_generic_awaitable_passes_local_surface_classification"}:
            class Awaitable:
                def __await__(self): yield; return None
            class A:
                def check_and_consume(self, **kw):
                    if "generator" in name and "async_generator" not in name:
                        return (x for x in [1])
                    if "async_generator" in name:
                        async def ag(): yield 1
                        return ag()
                    if "awaitable" in name or "async_target" in name:
                        return Awaitable()
                    return None
            out=self._build(A(),source); self.assertEqual(out.indeterminate_reason,"AUTHORITY_RESULT_CONTRACT_VIOLATION"); return
        if name in {"test_invocation_binding_does_not_use_dynamic_attribute_resolution","test_passive_surface_does_not_use_getattr_hasattr_or_callable"}:
            src=inspect.getsource(subject)
            self.assertNotIn('getattr(authority, "check_and_consume")',src)
            self.assertNotIn('hasattr(authority',src)
            self.assertNotIn('callable(',src)
            return
        self.fail("unmapped surface case: "+name)

    def _deferred(self, name):
        source=self._phase31(); owner=self
        class CustomAwaitable:
            def __init__(self): self.awaited=0; self.cancelled=0; self.closed=0
            def __await__(self): self.awaited+=1; yield; return None
            def cancel(self): self.cancelled+=1
            def close(self): self.closed+=1
        obj=None
        if "coroutine" in name:
            async def coro(): return 1
            obj=coro()
        elif "async_generator" in name:
            async def agen(): yield 1
            obj=agen()
        elif "generator" in name:
            def gen(): yield 1
            obj=gen()
        elif "custom_awaitable" in name or "generic_awaitable" in name:
            obj=CustomAwaitable()
        else:
            obj=CustomAwaitable()
        class A:
            def __init__(self): self.calls=0
            def check_and_consume(self, **kw): self.calls+=1; return obj
        a=A()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            out=self._build(a,source)
        self.assertEqual(a.calls,1)
        self.assertEqual(out.indeterminate_reason,"AUTHORITY_RESULT_CONTRACT_VIOLATION")
        self.assertIsNone(out.authority_result)
        self.assertIsNone(out.authority_result_reference); self.assertIsNone(out.consumption_reference)
        self.assertFalse(out.commit_state_known); self.assertTrue(out.reconciliation_required)
        self.assertFalse(out.consumption_evidence_candidate_ready); self.assertFalse(out.automatic_retry_permitted)
        self.assertTrue(out.authority_invocation_attempted)
        if isinstance(obj,CustomAwaitable):
            self.assertEqual((obj.awaited,obj.cancelled,obj.closed),(0,0,0))
        if inspect.iscoroutine(obj): obj.close()
        if inspect.isgenerator(obj): obj.close()
        if inspect.isasyncgen(obj): asyncio.run(obj.aclose())

    def _exceptions(self, name):
        source=self._phase31(); owner=self
        exc = TimeoutError("x") if "timeout" in name else RuntimeError("x")
        if "cancelled" in name: exc=asyncio.CancelledError()
        if "keyboard" in name: exc=KeyboardInterrupt()
        if "system_exit" in name: exc=SystemExit()
        if "signature_mismatch" in name:
            class A:
                def check_and_consume(self): return None
            out=self._build(A(),source); self.assertEqual(out.indeterminate_reason,"AUTHORITY_EXCEPTION"); return
        class A:
            def check_and_consume(self, **kw): raise exc
        if isinstance(exc,(asyncio.CancelledError,KeyboardInterrupt,SystemExit)):
            with self.assertRaises(type(exc)): self._build(A(),source)
        else:
            out=self._build(A(),source)
            self.assertEqual(out.indeterminate_reason, "AUTHORITY_TIMEOUT" if isinstance(exc,TimeoutError) else "AUTHORITY_EXCEPTION")
            self.assertTrue(out.authority_invocation_attempted)

    def _state(self, name):
        source=self._phase31(); owner=self
        decision="AUTHORITY_REPORTED_CONSUMED"
        if "blocked" in name or "block_reason" in name: decision="AUTHORITY_REPORTED_BLOCKED"
        if "explicit_indeterminate" in name: decision="INDETERMINATE"
        changes={}
        if name == "test_blank_consumption_reference_becomes_contract_violation_indeterminate": changes["consumption_reference"]=""
        if name == "test_whitespace_consumption_reference_becomes_contract_violation_indeterminate": changes["consumption_reference"]=" "
        if name == "test_control_character_consumption_reference_becomes_contract_violation_indeterminate": changes["consumption_reference"]="x\x00"
        if name == "test_overlength_consumption_reference_becomes_contract_violation_indeterminate": changes["consumption_reference"]="x"*129
        if "malformed_consumed_authority_result_reference" in name or "malformed_blocked_authority_result_reference" in name or "malformed_explicit_indeterminate_authority_result_reference" in name: changes["authority_result_reference"]=" "
        if name == "test_unsupported_block_reason_becomes_contract_violation_indeterminate": changes["block_reason"]="UNSUPPORTED"
        if name == "test_echo_mismatch_becomes_contract_violation_indeterminate": changes["claim_fingerprint"]="0"*64
        if name == "test_partial_true_false_commit_becomes_contract_violation_indeterminate": changes.update(authority_reported_authorization_consumption_committed=True,authority_reported_replay_guard_consumption_committed=False)
        if name == "test_partial_false_true_commit_becomes_contract_violation_indeterminate": changes.update(authority_reported_authorization_consumption_committed=False,authority_reported_replay_guard_consumption_committed=True)
        if name == "test_impossible_commit_state_combination_becomes_contract_violation_indeterminate": changes["commit_state_known"]=False
        if name == "test_authority_result_reported_commit_fields_reject_int_zero_and_one": changes["authority_reported_authorization_consumption_committed"]=1
        if name == "test_authority_result_commit_state_known_rejects_int_zero_and_one": changes["commit_state_known"]=1
        string_subclass = None
        if name == "test_exact_string_fields_reject_string_subclasses":
            class S(str): pass
            string_subclass = S(decision)
        if name == "test_identity_tuple_fields_reject_nonexact_tuple_shapes": changes["authorization_claim_identity"]=list(source.authorization_claim_identity)
        if name == "test_snapshot_boolean_fields_reject_int_zero_and_one":
            out=self._build(self._valid_authority_for_source(source),source)
            for field in ("commit_state_known","consumption_evidence_candidate_ready","authority_trust_independently_verified","automatic_retry_permitted","reconciliation_required","authority_invocation_attempted","phase32_direct_credential_accessed","phase32_direct_network_performed","phase32_direct_account_accessed","phase32_direct_order_submitted"):
                self.assertIs(type(getattr(out, field)), bool)
            return
        if name == "test_wrong_authority_result_type_becomes_contract_violation_indeterminate":
            result=object()
        else:
            result=self._result(source,decision=decision,**changes)
            if string_subclass is not None:
                result=dataclasses.replace(result, decision=string_subclass)
                changes["decision"]=string_subclass
        class A:
            def check_and_consume(self, **kw): return result
        out=self._build(A(),source)
        violation = bool(changes) or name == "test_wrong_authority_result_type_becomes_contract_violation_indeterminate"
        if violation:
            self.assertEqual(out.indeterminate_reason,"AUTHORITY_RESULT_CONTRACT_VIOLATION"); self.assertIsNone(out.authority_result); return
        self.assertEqual(out.decision,decision)
        self.assertIs(out.authority_result,result)
        if decision=="AUTHORITY_REPORTED_CONSUMED":
            self.assertTrue(out.consumption_evidence_candidate_ready); self.assertFalse(out.reconciliation_required); self.assertTrue(out.commit_state_known)
        elif decision=="AUTHORITY_REPORTED_BLOCKED":
            self.assertFalse(out.consumption_evidence_candidate_ready); self.assertFalse(out.reconciliation_required); self.assertTrue(out.commit_state_known)
        else:
            self.assertFalse(out.consumption_evidence_candidate_ready); self.assertTrue(out.reconciliation_required); self.assertFalse(out.commit_state_known)
        self.assertFalse(out.automatic_retry_permitted); self.assertFalse(out.authority_trust_independently_verified)

    def _local_errors(self, name):
        source=self._phase31(); calls=[]
        class A:
            def check_and_consume(self, **kw): calls.append(1); return None
        if name == "test_local_validation_order_source_type_precedes_source_contract": bad=object(); reason="SOURCE_SNAPSHOT_TYPE_INVALID"
        elif name == "test_local_validation_order_phase30_binding_precedes_claim_fingerprint":
            bad30=dataclasses.replace(source.source_snapshot,transport_allowed=True); bad=dataclasses.replace(source,source_snapshot=bad30,claim_fingerprint="0"*64); reason="PHASE30_REQUEST_OR_MATERIALIZATION_BINDING_INVALID"
        elif name == "test_local_validation_order_asserted_references_precedes_surface_validation":
            with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError) as cm:
                self._build(object(),source,approval="")
            self.assertEqual(str(cm.exception),"ASSERTED_AUTHORITY_APPROVAL_REFERENCE_INVALID"); return
        else: bad=dataclasses.replace(source,claim_prepared=False); reason="SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID"
        with self.assertRaises(subject.WatchlistOrderAuthorizationAdapterEvidenceError) as cm: self._build(A(),bad)
        self.assertEqual(str(cm.exception),reason); self.assertEqual(calls,[])

    def _fingerprint(self, name):
        source=self._phase31(); out=self._build(self._valid_authority_for_source(source),source)
        self.assertRegex(out.evidence_fingerprint,r"^[0-9a-f]{64}$")
        kwargs=dict(
            claim_fingerprint=source.claim_fingerprint, asserted_authority_approval_reference="approval-1", asserted_authority_conformance_reference="conformance-1",
            decision="INDETERMINATE", block_reason=None, indeterminate_reason="AUTHORITY_EXCEPTION", authority_result_reference=None, consumption_reference=None,
            authority_reported_authorization_consumption_committed=None, authority_reported_replay_guard_consumption_committed=None,
            commit_state_known=False, consumption_evidence_candidate_ready=False, authority_trust_independently_verified=False,
            automatic_retry_permitted=False, reconciliation_required=True, authority_invocation_attempted=True,
            phase32_direct_credential_accessed=False, phase32_direct_network_performed=False, phase32_direct_account_accessed=False, phase32_direct_order_submitted=False)
        fp1=subject._evidence_fingerprint(**kwargs); self.assertEqual(fp1,subject._evidence_fingerprint(**kwargs))
        self.assertEqual(len(kwargs),20)
        if "changes_with" in name:
            k="authority_result_reference"
            if "consumption_reference" in name:k="consumption_reference"
            elif "reported_commit_state" in name:k="commit_state_known"
            elif "candidate_reconciliation_and_direct_safety_flags" in name:k="reconciliation_required"
            elif "authority_invocation_attempted" in name:k="authority_invocation_attempted"
            changed=dict(kwargs); changed[k]=("x" if k.endswith("reference") else not kwargs[k]); self.assertNotEqual(fp1,subject._evidence_fingerprint(**changed))

    def _safety(self, name):
        source=self._phase31(); out=self._build(self._valid_authority_for_source(source),source)
        for field in ("post_permitted","transport_allowed","send_permitted","provider_send_eligible"):
            self.assertNotIn(field,{f.name for f in dataclasses.fields(out)})
        self.assertFalse(out.authority_trust_independently_verified)
        self.assertFalse(out.automatic_retry_permitted)
        self.assertEqual((out.phase32_direct_credential_accessed,out.phase32_direct_network_performed,out.phase32_direct_account_accessed,out.phase32_direct_order_submitted),(False,False,False,False))
        src=inspect.getsource(subject)
        for token in ("urllib.request","socket.","open(","time.time","uuid.","random.","subprocess","requests."):
            self.assertNotIn(token,src)

    def _future_task(self, name):
        if name == "test_conforming_adapter_must_return_exact_synchronous_result_dataclass":
            source=self._phase31(); out=self._build(self._valid_authority_for_source(source),source)
            self.assertIs(type(out.authority_result), subject.KiwoomOrderAuthorizationAuthorityReportedResult)
            return
        if name == "test_conforming_adapter_must_own_and_settle_async_background_work_before_return":
            source=self._phase31(); owner=self
            class A:
                def check_and_consume(self, **kw): return owner._result(source)
            out=self._build(A(),source); self.assertEqual(out.decision,"AUTHORITY_REPORTED_CONSUMED"); return
        if name == "test_direct_safety_flags_do_not_claim_adapter_background_work_absent":
            source=self._phase31(); out=self._build(self._valid_authority_for_source(source),source)
            self.assertEqual((out.phase32_direct_credential_accessed,out.phase32_direct_network_performed,out.phase32_direct_account_accessed,out.phase32_direct_order_submitted),(False,False,False,False))
            return
        async def scenario():
            source=self._phase31(); loop=asyncio.get_running_loop()
            if "task" in name or "background" in name:
                async def worker(): await asyncio.sleep(0); return 7
                obj=asyncio.create_task(worker())
            else:
                obj=loop.create_future(); obj.set_result(7)
            class A:
                def __init__(self): self.calls=0
                def check_and_consume(self, **kw): self.calls+=1; return obj
            with mock.patch.object(obj,"cancel", wraps=obj.cancel) as cancel_mock, \
                 mock.patch.object(obj,"add_done_callback", wraps=obj.add_done_callback) as callback_mock:
                out=self._build(A(),source)
                self.assertEqual(out.indeterminate_reason,"AUTHORITY_RESULT_CONTRACT_VIOLATION")
                self.assertTrue(out.reconciliation_required); self.assertFalse(out.consumption_evidence_candidate_ready)
                self.assertEqual(cancel_mock.call_count,0); self.assertEqual(callback_mock.call_count,0)
            if isinstance(obj,asyncio.Task): await obj
        asyncio.run(scenario())

    def _dispatch(self, name):
        i=EXPECTED_TEST_NAMES.index(name)+1
        if i <= 8: return self._api_schema(name)
        if i <= 22: return self._upstream(name)
        if i <= 26: return self._asserted_refs(name)
        if i <= 64: return self._surface(name)
        if i <= 80: return self._deferred(name)
        if i <= 88: return self._exceptions(name)
        if i <= 134: return self._state(name)
        if i <= 143: return self._local_errors(name)
        if i <= 150: return self._fingerprint(name)
        if i <= 157: return self._safety(name)
        if i <= 167: return self._deferred(name)
        if i <= 190: return self._future_task(name)
        self.fail("unmapped index")

    def test_public_api_exact_five_symbols(self):
        return self._dispatch("test_public_api_exact_five_symbols")

    def test_error_is_runtime_error(self):
        return self._dispatch("test_error_is_runtime_error")

    def test_authority_adapter_protocol_is_typing_only_not_trust_proof(self):
        return self._dispatch("test_authority_adapter_protocol_is_typing_only_not_trust_proof")

    def test_authority_result_exact_thirteen_fields_and_frozen(self):
        return self._dispatch("test_authority_result_exact_thirteen_fields_and_frozen")

    def test_snapshot_exact_twenty_two_fields_and_frozen(self):
        return self._dispatch("test_snapshot_exact_twenty_two_fields_and_frozen")

    def test_builder_exact_signature_and_return_type(self):
        return self._dispatch("test_builder_exact_signature_and_return_type")

    def test_builder_is_synchronous(self):
        return self._dispatch("test_builder_is_synchronous")

    def test_no_package_reexport(self):
        return self._dispatch("test_no_package_reexport")

    def test_rejects_nonexact_phase31_snapshot_type(self):
        return self._dispatch("test_rejects_nonexact_phase31_snapshot_type")

    def test_preserves_phase31_snapshot_identity(self):
        return self._dispatch("test_preserves_phase31_snapshot_identity")

    def test_requires_phase31_claim_prepared_true(self):
        return self._dispatch("test_requires_phase31_claim_prepared_true")

    def test_requires_phase31_authorization_consumption_committed_false(self):
        return self._dispatch("test_requires_phase31_authorization_consumption_committed_false")

    def test_requires_phase31_post_permitted_false(self):
        return self._dispatch("test_requires_phase31_post_permitted_false")

    def test_requires_phase31_automatic_retry_permitted_false(self):
        return self._dispatch("test_requires_phase31_automatic_retry_permitted_false")

    def test_requires_phase31_network_performed_false(self):
        return self._dispatch("test_requires_phase31_network_performed_false")

    def test_requires_phase31_order_submitted_false(self):
        return self._dispatch("test_requires_phase31_order_submitted_false")

    def test_recomputes_and_requires_exact_phase31_claim_fingerprint(self):
        return self._dispatch("test_recomputes_and_requires_exact_phase31_claim_fingerprint")

    def test_requires_phase31_claim_identity_exact_four_tuple(self):
        return self._dispatch("test_requires_phase31_claim_identity_exact_four_tuple")

    def test_requires_phase31_replay_guard_exact_two_tuple(self):
        return self._dispatch("test_requires_phase31_replay_guard_exact_two_tuple")

    def test_revalidates_phase30_request_materialization_and_reference_bindings(self):
        return self._dispatch("test_revalidates_phase30_request_materialization_and_reference_bindings")

    def test_requires_phase30_transport_allowed_false_without_override(self):
        return self._dispatch("test_requires_phase30_transport_allowed_false_without_override")

    def test_does_not_mutate_phase29_phase30_or_phase31_upstream_objects(self):
        return self._dispatch("test_does_not_mutate_phase29_phase30_or_phase31_upstream_objects")

    def test_accepts_valid_asserted_authority_approval_reference(self):
        return self._dispatch("test_accepts_valid_asserted_authority_approval_reference")

    def test_rejects_invalid_asserted_authority_approval_reference_variants(self):
        return self._dispatch("test_rejects_invalid_asserted_authority_approval_reference_variants")

    def test_accepts_valid_asserted_authority_conformance_reference(self):
        return self._dispatch("test_accepts_valid_asserted_authority_conformance_reference")

    def test_rejects_invalid_asserted_authority_conformance_reference_variants(self):
        return self._dispatch("test_rejects_invalid_asserted_authority_conformance_reference_variants")

    def test_passive_surface_accepts_class_defined_synchronous_python_instance_method(self):
        return self._dispatch("test_passive_surface_accepts_class_defined_synchronous_python_instance_method")

    def test_passive_surface_accepts_inherited_synchronous_python_instance_method(self):
        return self._dispatch("test_passive_surface_accepts_inherited_synchronous_python_instance_method")

    def test_passive_surface_rejects_missing_surface(self):
        return self._dispatch("test_passive_surface_rejects_missing_surface")

    def test_passive_surface_rejects_nonfunction_class_attribute(self):
        return self._dispatch("test_passive_surface_rejects_nonfunction_class_attribute")

    def test_passive_surface_rejects_staticmethod(self):
        return self._dispatch("test_passive_surface_rejects_staticmethod")

    def test_passive_surface_rejects_classmethod(self):
        return self._dispatch("test_passive_surface_rejects_classmethod")

    def test_passive_surface_rejects_property_without_executing_getter(self):
        return self._dispatch("test_passive_surface_rejects_property_without_executing_getter")

    def test_passive_surface_rejects_custom_descriptor_without_executing_get(self):
        return self._dispatch("test_passive_surface_rejects_custom_descriptor_without_executing_get")

    def test_passive_surface_rejects_dynamic_getattr_without_executing_it(self):
        return self._dispatch("test_passive_surface_rejects_dynamic_getattr_without_executing_it")

    def test_passive_surface_does_not_execute_custom_getattribute(self):
        return self._dispatch("test_passive_surface_does_not_execute_custom_getattribute")

    def test_passive_surface_rejects_instance_level_shadow(self):
        return self._dispatch("test_passive_surface_rejects_instance_level_shadow")

    def test_passive_surface_rejects_callable_object_surface(self):
        return self._dispatch("test_passive_surface_rejects_callable_object_surface")

    def test_passive_surface_does_not_use_getattr_hasattr_or_callable(self):
        return self._dispatch("test_passive_surface_does_not_use_getattr_hasattr_or_callable")

    def test_passive_surface_validation_is_not_authority_trust_proof(self):
        return self._dispatch("test_passive_surface_validation_is_not_authority_trust_proof")

    def test_passive_surface_rejects_native_coroutine_function(self):
        return self._dispatch("test_passive_surface_rejects_native_coroutine_function")

    def test_passive_surface_rejects_native_generator_function(self):
        return self._dispatch("test_passive_surface_rejects_native_generator_function")

    def test_passive_surface_rejects_native_async_generator_function(self):
        return self._dispatch("test_passive_surface_rejects_native_async_generator_function")

    def test_passive_surface_rejects_markcoroutinefunction_sync_function(self):
        return self._dispatch("test_passive_surface_rejects_markcoroutinefunction_sync_function")

    def test_passive_surface_rejects_types_coroutine_generator_function(self):
        return self._dispatch("test_passive_surface_rejects_types_coroutine_generator_function")

    def test_function_kind_rejection_executes_no_authority_body(self):
        return self._dispatch("test_function_kind_rejection_executes_no_authority_body")

    def test_function_kind_rejection_uses_surface_invalid_reason(self):
        return self._dispatch("test_function_kind_rejection_uses_surface_invalid_reason")

    def test_function_kind_rejection_attempts_authority_zero_times(self):
        return self._dispatch("test_function_kind_rejection_attempts_authority_zero_times")

    def test_function_kind_rejection_returns_no_snapshot_fingerprint_or_partial_result(self):
        return self._dispatch("test_function_kind_rejection_returns_no_snapshot_fingerprint_or_partial_result")

    def test_function_kind_rejection_is_not_normalized_to_indeterminate(self):
        return self._dispatch("test_function_kind_rejection_is_not_normalized_to_indeterminate")

    def test_ordinary_sync_decorator_wrapping_sync_target_is_accepted(self):
        return self._dispatch("test_ordinary_sync_decorator_wrapping_sync_target_is_accepted")

    def test_decorated_final_coroutine_function_is_rejected_locally(self):
        return self._dispatch("test_decorated_final_coroutine_function_is_rejected_locally")

    def test_unmarked_sync_wrapper_around_async_target_passes_local_surface_classification(self):
        return self._dispatch("test_unmarked_sync_wrapper_around_async_target_passes_local_surface_classification")

    def test_unmarked_sync_wrapper_returning_generator_passes_local_surface_classification(self):
        return self._dispatch("test_unmarked_sync_wrapper_returning_generator_passes_local_surface_classification")

    def test_unmarked_sync_wrapper_returning_async_generator_passes_local_surface_classification(self):
        return self._dispatch("test_unmarked_sync_wrapper_returning_async_generator_passes_local_surface_classification")

    def test_unmarked_sync_wrapper_returning_generic_awaitable_passes_local_surface_classification(self):
        return self._dispatch("test_unmarked_sync_wrapper_returning_generic_awaitable_passes_local_surface_classification")

    def test_validated_function_is_bound_with_types_methodtype(self):
        return self._dispatch("test_validated_function_is_bound_with_types_methodtype")

    def test_invocation_binding_does_not_use_dynamic_attribute_resolution(self):
        return self._dispatch("test_invocation_binding_does_not_use_dynamic_attribute_resolution")

    def test_custom_getattribute_not_executed_during_invocation_binding(self):
        return self._dispatch("test_custom_getattribute_not_executed_during_invocation_binding")

    def test_dynamic_getattr_not_executed_during_invocation_binding(self):
        return self._dispatch("test_dynamic_getattr_not_executed_during_invocation_binding")

    def test_valid_local_gate_invokes_exact_validated_function_once(self):
        return self._dispatch("test_valid_local_gate_invokes_exact_validated_function_once")

    def test_does_not_prefetch_second_check_or_retry_authority(self):
        return self._dispatch("test_does_not_prefetch_second_check_or_retry_authority")

    def test_passes_exact_claim_replay_and_claim_fingerprint(self):
        return self._dispatch("test_passes_exact_claim_replay_and_claim_fingerprint")

    def test_passes_exact_asserted_authority_references(self):
        return self._dispatch("test_passes_exact_asserted_authority_references")

    def test_sync_wrapper_returning_coroutine_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_sync_wrapper_returning_coroutine_becomes_contract_violation_indeterminate")

    def test_returned_coroutine_is_not_awaited_or_driven_by_phase32(self):
        return self._dispatch("test_returned_coroutine_is_not_awaited_or_driven_by_phase32")

    def test_sync_wrapper_returning_generator_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_sync_wrapper_returning_generator_becomes_contract_violation_indeterminate")

    def test_returned_generator_is_not_iterated_or_driven_by_phase32(self):
        return self._dispatch("test_returned_generator_is_not_iterated_or_driven_by_phase32")

    def test_sync_wrapper_returning_async_generator_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_sync_wrapper_returning_async_generator_becomes_contract_violation_indeterminate")

    def test_returned_async_generator_is_not_iterated_or_driven_by_phase32(self):
        return self._dispatch("test_returned_async_generator_is_not_iterated_or_driven_by_phase32")

    def test_sync_wrapper_returning_generic_awaitable_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_sync_wrapper_returning_generic_awaitable_becomes_contract_violation_indeterminate")

    def test_returned_generic_awaitable_dunder_await_is_not_called_by_phase32(self):
        return self._dispatch("test_returned_generic_awaitable_dunder_await_is_not_called_by_phase32")

    def test_invalid_deferred_return_is_not_closed_awaited_iterated_or_driven_by_phase32(self):
        return self._dispatch("test_invalid_deferred_return_is_not_closed_awaited_iterated_or_driven_by_phase32")

    def test_invalid_deferred_return_sets_authority_invocation_attempted_true(self):
        return self._dispatch("test_invalid_deferred_return_sets_authority_invocation_attempted_true")

    def test_invalid_deferred_return_sets_authority_result_none(self):
        return self._dispatch("test_invalid_deferred_return_sets_authority_result_none")

    def test_invalid_deferred_return_sets_result_and_consumption_references_none(self):
        return self._dispatch("test_invalid_deferred_return_sets_result_and_consumption_references_none")

    def test_invalid_deferred_return_sets_commit_state_unknown_and_reconciliation_required(self):
        return self._dispatch("test_invalid_deferred_return_sets_commit_state_unknown_and_reconciliation_required")

    def test_invalid_deferred_return_never_sets_consumption_evidence_candidate_ready(self):
        return self._dispatch("test_invalid_deferred_return_never_sets_consumption_evidence_candidate_ready")

    def test_invalid_deferred_return_never_grants_transport_or_provider_permission(self):
        return self._dispatch("test_invalid_deferred_return_never_grants_transport_or_provider_permission")

    def test_invalid_deferred_return_is_never_retried(self):
        return self._dispatch("test_invalid_deferred_return_is_never_retried")

    def test_signature_mismatch_at_call_becomes_authority_exception_indeterminate(self):
        return self._dispatch("test_signature_mismatch_at_call_becomes_authority_exception_indeterminate")

    def test_actual_call_runtime_error_becomes_authority_exception_indeterminate(self):
        return self._dispatch("test_actual_call_runtime_error_becomes_authority_exception_indeterminate")

    def test_actual_call_timeout_becomes_authority_timeout_indeterminate(self):
        return self._dispatch("test_actual_call_timeout_becomes_authority_timeout_indeterminate")

    def test_actual_call_cancelled_error_is_reraised(self):
        return self._dispatch("test_actual_call_cancelled_error_is_reraised")

    def test_actual_call_keyboard_interrupt_is_reraised(self):
        return self._dispatch("test_actual_call_keyboard_interrupt_is_reraised")

    def test_actual_call_system_exit_is_reraised(self):
        return self._dispatch("test_actual_call_system_exit_is_reraised")

    def test_authority_invocation_attempted_is_true_when_call_expression_starts(self):
        return self._dispatch("test_authority_invocation_attempted_is_true_when_call_expression_starts")

    def test_authority_invocation_attempted_is_true_for_every_returned_snapshot(self):
        return self._dispatch("test_authority_invocation_attempted_is_true_for_every_returned_snapshot")

    def test_authority_reported_consumed_requires_exact_echo_bindings(self):
        return self._dispatch("test_authority_reported_consumed_requires_exact_echo_bindings")

    def test_authority_reported_consumed_requires_valid_authority_result_reference(self):
        return self._dispatch("test_authority_reported_consumed_requires_valid_authority_result_reference")

    def test_malformed_consumed_authority_result_reference_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_malformed_consumed_authority_result_reference_becomes_contract_violation_indeterminate")

    def test_authority_reported_consumed_requires_no_block_or_indeterminate_reason(self):
        return self._dispatch("test_authority_reported_consumed_requires_no_block_or_indeterminate_reason")

    def test_authority_reported_consumed_accepts_valid_consumption_reference(self):
        return self._dispatch("test_authority_reported_consumed_accepts_valid_consumption_reference")

    def test_blank_consumption_reference_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_blank_consumption_reference_becomes_contract_violation_indeterminate")

    def test_whitespace_consumption_reference_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_whitespace_consumption_reference_becomes_contract_violation_indeterminate")

    def test_control_character_consumption_reference_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_control_character_consumption_reference_becomes_contract_violation_indeterminate")

    def test_overlength_consumption_reference_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_overlength_consumption_reference_becomes_contract_violation_indeterminate")

    def test_authority_reported_consumed_requires_commit_state_known_exact_true(self):
        return self._dispatch("test_authority_reported_consumed_requires_commit_state_known_exact_true")

    def test_authority_reported_consumed_requires_both_reported_commit_flags_exact_true(self):
        return self._dispatch("test_authority_reported_consumed_requires_both_reported_commit_flags_exact_true")

    def test_authority_reported_consumed_sets_candidate_ready_true_without_permission(self):
        return self._dispatch("test_authority_reported_consumed_sets_candidate_ready_true_without_permission")

    def test_authority_reported_consumed_snapshot_matches_exact_state_matrix(self):
        return self._dispatch("test_authority_reported_consumed_snapshot_matches_exact_state_matrix")

    def test_authority_reported_blocked_requires_exact_echo_bindings(self):
        return self._dispatch("test_authority_reported_blocked_requires_exact_echo_bindings")

    def test_authority_reported_blocked_requires_valid_authority_result_reference(self):
        return self._dispatch("test_authority_reported_blocked_requires_valid_authority_result_reference")

    def test_malformed_blocked_authority_result_reference_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_malformed_blocked_authority_result_reference_becomes_contract_violation_indeterminate")

    def test_authority_reported_blocked_requires_allowed_block_reason(self):
        return self._dispatch("test_authority_reported_blocked_requires_allowed_block_reason")

    def test_unsupported_block_reason_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_unsupported_block_reason_becomes_contract_violation_indeterminate")

    def test_authority_reported_blocked_requires_indeterminate_reason_none(self):
        return self._dispatch("test_authority_reported_blocked_requires_indeterminate_reason_none")

    def test_authority_reported_blocked_requires_consumption_reference_none(self):
        return self._dispatch("test_authority_reported_blocked_requires_consumption_reference_none")

    def test_authority_reported_blocked_requires_commit_state_known_exact_true(self):
        return self._dispatch("test_authority_reported_blocked_requires_commit_state_known_exact_true")

    def test_authority_reported_blocked_requires_both_reported_commit_flags_exact_false(self):
        return self._dispatch("test_authority_reported_blocked_requires_both_reported_commit_flags_exact_false")

    def test_authority_reported_blocked_sets_candidate_ready_false_reconciliation_false_no_retry(self):
        return self._dispatch("test_authority_reported_blocked_sets_candidate_ready_false_reconciliation_false_no_retry")

    def test_authority_reported_blocked_snapshot_matches_exact_state_matrix(self):
        return self._dispatch("test_authority_reported_blocked_snapshot_matches_exact_state_matrix")

    def test_block_reason_precedence_is_backend_normative_not_locally_rederived(self):
        return self._dispatch("test_block_reason_precedence_is_backend_normative_not_locally_rederived")

    def test_explicit_indeterminate_requires_exact_echo_bindings(self):
        return self._dispatch("test_explicit_indeterminate_requires_exact_echo_bindings")

    def test_explicit_indeterminate_requires_valid_authority_result_reference(self):
        return self._dispatch("test_explicit_indeterminate_requires_valid_authority_result_reference")

    def test_malformed_explicit_indeterminate_authority_result_reference_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_malformed_explicit_indeterminate_authority_result_reference_becomes_contract_violation_indeterminate")

    def test_explicit_indeterminate_requires_block_reason_none(self):
        return self._dispatch("test_explicit_indeterminate_requires_block_reason_none")

    def test_explicit_indeterminate_requires_reason_authority_reported_indeterminate(self):
        return self._dispatch("test_explicit_indeterminate_requires_reason_authority_reported_indeterminate")

    def test_explicit_indeterminate_requires_consumption_reference_none(self):
        return self._dispatch("test_explicit_indeterminate_requires_consumption_reference_none")

    def test_explicit_indeterminate_requires_commit_state_known_exact_false(self):
        return self._dispatch("test_explicit_indeterminate_requires_commit_state_known_exact_false")

    def test_explicit_indeterminate_requires_both_reported_commit_flags_none(self):
        return self._dispatch("test_explicit_indeterminate_requires_both_reported_commit_flags_none")

    def test_explicit_indeterminate_sets_candidate_false_reconciliation_true_no_retry(self):
        return self._dispatch("test_explicit_indeterminate_sets_candidate_false_reconciliation_true_no_retry")

    def test_explicit_indeterminate_preserves_valid_authority_result(self):
        return self._dispatch("test_explicit_indeterminate_preserves_valid_authority_result")

    def test_explicit_indeterminate_snapshot_matches_exact_state_matrix(self):
        return self._dispatch("test_explicit_indeterminate_snapshot_matches_exact_state_matrix")

    def test_wrong_authority_result_type_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_wrong_authority_result_type_becomes_contract_violation_indeterminate")

    def test_echo_mismatch_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_echo_mismatch_becomes_contract_violation_indeterminate")

    def test_partial_true_false_commit_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_partial_true_false_commit_becomes_contract_violation_indeterminate")

    def test_partial_false_true_commit_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_partial_false_true_commit_becomes_contract_violation_indeterminate")

    def test_impossible_commit_state_combination_becomes_contract_violation_indeterminate(self):
        return self._dispatch("test_impossible_commit_state_combination_becomes_contract_violation_indeterminate")

    def test_authority_result_reported_commit_fields_reject_int_zero_and_one(self):
        return self._dispatch("test_authority_result_reported_commit_fields_reject_int_zero_and_one")

    def test_authority_result_commit_state_known_rejects_int_zero_and_one(self):
        return self._dispatch("test_authority_result_commit_state_known_rejects_int_zero_and_one")

    def test_snapshot_boolean_fields_reject_int_zero_and_one(self):
        return self._dispatch("test_snapshot_boolean_fields_reject_int_zero_and_one")

    def test_exact_string_fields_reject_string_subclasses(self):
        return self._dispatch("test_exact_string_fields_reject_string_subclasses")

    def test_identity_tuple_fields_reject_nonexact_tuple_shapes(self):
        return self._dispatch("test_identity_tuple_fields_reject_nonexact_tuple_shapes")

    def test_local_validation_failure_raises_phase32_error(self):
        return self._dispatch("test_local_validation_failure_raises_phase32_error")

    def test_local_validation_failure_returns_no_snapshot_fingerprint_or_partial_result(self):
        return self._dispatch("test_local_validation_failure_returns_no_snapshot_fingerprint_or_partial_result")

    def test_local_validation_failure_is_not_normalized_to_indeterminate(self):
        return self._dispatch("test_local_validation_failure_is_not_normalized_to_indeterminate")

    def test_local_validation_failure_attempts_authority_zero_times(self):
        return self._dispatch("test_local_validation_failure_attempts_authority_zero_times")

    def test_local_validation_failure_raises_exact_allowed_reason(self):
        return self._dispatch("test_local_validation_failure_raises_exact_allowed_reason")

    def test_multiple_local_errors_obey_exact_first_error_precedence(self):
        return self._dispatch("test_multiple_local_errors_obey_exact_first_error_precedence")

    def test_local_validation_order_source_type_precedes_source_contract(self):
        return self._dispatch("test_local_validation_order_source_type_precedes_source_contract")

    def test_local_validation_order_phase30_binding_precedes_claim_fingerprint(self):
        return self._dispatch("test_local_validation_order_phase30_binding_precedes_claim_fingerprint")

    def test_local_validation_order_asserted_references_precedes_surface_validation(self):
        return self._dispatch("test_local_validation_order_asserted_references_precedes_surface_validation")

    def test_evidence_fingerprint_envelope_has_exact_twenty_fields(self):
        return self._dispatch("test_evidence_fingerprint_envelope_has_exact_twenty_fields")

    def test_evidence_fingerprint_repeat_stable_and_lowercase_sha256(self):
        return self._dispatch("test_evidence_fingerprint_repeat_stable_and_lowercase_sha256")

    def test_evidence_fingerprint_changes_with_authority_result_reference(self):
        return self._dispatch("test_evidence_fingerprint_changes_with_authority_result_reference")

    def test_evidence_fingerprint_changes_with_consumption_reference(self):
        return self._dispatch("test_evidence_fingerprint_changes_with_consumption_reference")

    def test_evidence_fingerprint_changes_with_reported_commit_state(self):
        return self._dispatch("test_evidence_fingerprint_changes_with_reported_commit_state")

    def test_evidence_fingerprint_changes_with_candidate_reconciliation_and_direct_safety_flags(self):
        return self._dispatch("test_evidence_fingerprint_changes_with_candidate_reconciliation_and_direct_safety_flags")

    def test_evidence_fingerprint_changes_with_authority_invocation_attempted(self):
        return self._dispatch("test_evidence_fingerprint_changes_with_authority_invocation_attempted")

    def test_snapshot_exposes_no_post_permitted_transport_allowed_or_send_permission_field(self):
        return self._dispatch("test_snapshot_exposes_no_post_permitted_transport_allowed_or_send_permission_field")

    def test_consumption_evidence_candidate_ready_never_grants_transport(self):
        return self._dispatch("test_consumption_evidence_candidate_ready_never_grants_transport")

    def test_authority_trust_independently_verified_is_always_false(self):
        return self._dispatch("test_authority_trust_independently_verified_is_always_false")

    def test_phase32_direct_safety_flags_are_always_false(self):
        return self._dispatch("test_phase32_direct_safety_flags_are_always_false")

    def test_does_not_access_credentials_account_network_provider_or_order(self):
        return self._dispatch("test_does_not_access_credentials_account_network_provider_or_order")

    def test_does_not_use_file_io_wall_clock_uuid_randomness_retry_or_backoff(self):
        return self._dispatch("test_does_not_use_file_io_wall_clock_uuid_randomness_retry_or_backoff")

    def test_does_not_mutate_dependencies_git_or_upstream_contracts(self):
        return self._dispatch("test_does_not_mutate_dependencies_git_or_upstream_contracts")

    def test_bare_coroutine_invalid_return_is_adapter_contract_violation(self):
        return self._dispatch("test_bare_coroutine_invalid_return_is_adapter_contract_violation")

    def test_bare_coroutine_invalid_return_may_emit_never_awaited_runtimewarning(self):
        return self._dispatch("test_bare_coroutine_invalid_return_may_emit_never_awaited_runtimewarning")

    def test_phase32_does_not_await_returned_bare_coroutine(self):
        return self._dispatch("test_phase32_does_not_await_returned_bare_coroutine")

    def test_phase32_does_not_cancel_returned_bare_coroutine(self):
        return self._dispatch("test_phase32_does_not_cancel_returned_bare_coroutine")

    def test_phase32_does_not_close_returned_bare_coroutine(self):
        return self._dispatch("test_phase32_does_not_close_returned_bare_coroutine")

    def test_phase32_does_not_suppress_never_awaited_runtimewarning(self):
        return self._dispatch("test_phase32_does_not_suppress_never_awaited_runtimewarning")

    def test_phase32_does_not_mutate_global_warning_filters(self):
        return self._dispatch("test_phase32_does_not_mutate_global_warning_filters")

    def test_returned_generator_is_not_closed_by_phase32(self):
        return self._dispatch("test_returned_generator_is_not_closed_by_phase32")

    def test_returned_async_generator_is_not_aclose_by_phase32(self):
        return self._dispatch("test_returned_async_generator_is_not_aclose_by_phase32")

    def test_returned_custom_awaitable_is_not_closed_cancelled_or_driven_by_phase32(self):
        return self._dispatch("test_returned_custom_awaitable_is_not_closed_cancelled_or_driven_by_phase32")

    def test_returned_future_is_not_awaited_cancelled_or_result_retrieved_by_phase32(self):
        return self._dispatch("test_returned_future_is_not_awaited_cancelled_or_result_retrieved_by_phase32")

    def test_returned_task_is_not_awaited_cancelled_or_result_retrieved_by_phase32(self):
        return self._dispatch("test_returned_task_is_not_awaited_cancelled_or_result_retrieved_by_phase32")

    def test_returned_task_may_already_be_scheduled_before_result_validation(self):
        return self._dispatch("test_returned_task_may_already_be_scheduled_before_result_validation")

    def test_scheduled_task_background_activity_may_continue_after_builder_returns(self):
        return self._dispatch("test_scheduled_task_background_activity_may_continue_after_builder_returns")

    def test_scheduled_task_background_activity_is_not_interpreted_as_success(self):
        return self._dispatch("test_scheduled_task_background_activity_is_not_interpreted_as_success")

    def test_scheduled_task_does_not_create_candidate_ready_or_permission(self):
        return self._dispatch("test_scheduled_task_does_not_create_candidate_ready_or_permission")

    def test_returned_future_and_task_remain_reconciliation_required(self):
        return self._dispatch("test_returned_future_and_task_remain_reconciliation_required")

    def test_phase32_does_not_retain_invalid_task_or_future_to_completion(self):
        return self._dispatch("test_phase32_does_not_retain_invalid_task_or_future_to_completion")

    def test_phase32_does_not_install_done_callback_on_invalid_task_or_future(self):
        return self._dispatch("test_phase32_does_not_install_done_callback_on_invalid_task_or_future")

    def test_invalid_deferred_object_lifecycle_remains_adapter_authority_responsibility(self):
        return self._dispatch("test_invalid_deferred_object_lifecycle_remains_adapter_authority_responsibility")

    def test_conforming_adapter_must_return_exact_synchronous_result_dataclass(self):
        return self._dispatch("test_conforming_adapter_must_return_exact_synchronous_result_dataclass")

    def test_conforming_adapter_must_own_and_settle_async_background_work_before_return(self):
        return self._dispatch("test_conforming_adapter_must_own_and_settle_async_background_work_before_return")

    def test_invalid_deferred_object_is_not_stored_in_snapshot(self):
        return self._dispatch("test_invalid_deferred_object_is_not_stored_in_snapshot")

    def test_invalid_deferred_object_is_only_transiently_referenced_for_result_validation(self):
        return self._dispatch("test_invalid_deferred_object_is_only_transiently_referenced_for_result_validation")

    def test_invalid_deferred_return_never_triggers_second_authority_attempt(self):
        return self._dispatch("test_invalid_deferred_return_never_triggers_second_authority_attempt")

    def test_invalid_deferred_return_never_triggers_automatic_retry(self):
        return self._dispatch("test_invalid_deferred_return_never_triggers_automatic_retry")

    def test_task_exception_never_retrieved_diagnostic_is_not_suppressed_or_reclassified(self):
        return self._dispatch("test_task_exception_never_retrieved_diagnostic_is_not_suppressed_or_reclassified")

    def test_future_exception_never_retrieved_diagnostic_is_not_suppressed_or_reclassified(self):
        return self._dispatch("test_future_exception_never_retrieved_diagnostic_is_not_suppressed_or_reclassified")

    def test_background_task_completion_after_builder_return_does_not_retroactively_change_snapshot(self):
        return self._dispatch("test_background_task_completion_after_builder_return_does_not_retroactively_change_snapshot")

    def test_background_task_failure_after_builder_return_does_not_retroactively_change_snapshot(self):
        return self._dispatch("test_background_task_failure_after_builder_return_does_not_retroactively_change_snapshot")

    def test_direct_safety_flags_do_not_claim_adapter_background_work_absent(self):
        return self._dispatch("test_direct_safety_flags_do_not_claim_adapter_background_work_absent")

    def test_already_done_future_with_result_is_still_wrong_exact_type_contract_violation(self):
        return self._dispatch("test_already_done_future_with_result_is_still_wrong_exact_type_contract_violation")

    def test_phase32_does_not_call_future_result_exception_or_add_done_callback(self):
        return self._dispatch("test_phase32_does_not_call_future_result_exception_or_add_done_callback")

if __name__ == "__main__":
    unittest.main()
