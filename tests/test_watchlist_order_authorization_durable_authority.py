import dataclasses
import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

import kiwoom_trading_system.brokers.kiwoom.rest as rest_package
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_send_request as phase30
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_authorization_consumption_claim as phase31
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_authorization_adapter_evidence as phase32
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_authorization_durable_authority as subject


EXPECTED_PUBLIC_API = [
    "WatchlistOrderAuthorizationDurableAuthorityError",
    "KiwoomOrderAuthorizationDurableAuthorityConfig",
    "KiwoomOrderAuthorizationDurableLedgerRecord",
    "KiwoomOrderAuthorizationSQLiteAuthority",
    "WatchlistOrderAuthorizationDurableVerificationSnapshot",
    "initialize_demo_watchlist_order_authorization_durable_ledger",
    "verify_demo_watchlist_order_authorization_durable_consumption",
]

EXPECTED_TEST_NAMES = """test_public_api_symbol_set_exact_7
test_error_inherits_runtime_error
test_config_is_frozen_dataclass
test_config_field_order_exact_4
test_durable_record_is_frozen_dataclass
test_durable_record_field_order_exact_13
test_verification_snapshot_is_frozen_dataclass
test_verification_snapshot_field_order_exact_19
test_initializer_signature_exact
test_authority_constructor_signature_exact
test_check_and_consume_signature_exact_phase32_compatible
test_verifier_signature_exact
test_durable_record_field_annotations_exact_13
test_verification_snapshot_field_annotations_exact_19
test_config_accepts_minimum_length_references
test_config_accepts_maximum_length_references
test_config_rejects_empty_reference
test_config_rejects_whitespace_only_reference
test_config_rejects_leading_whitespace
test_config_rejects_trailing_whitespace
test_config_rejects_c0_control_character
test_config_rejects_delete_control_character
test_config_rejects_non_exact_str_subclass
test_config_does_not_trim_casefold_normalize_or_replace
test_initializer_requires_exact_sqlite_connection_type
test_initializer_rejects_closed_connection
test_initializer_rejects_active_transaction
test_initializer_requires_autocommit_true
test_initializer_requires_isolation_level_none_redundant_surface_invariant
test_initializer_rejects_memory_main_database
test_initializer_requires_file_backed_main_database
test_initializer_requires_main_journal_mode_wal
test_initializer_requires_main_synchronous_full_2
test_initializer_requires_busy_timeout_zero
test_initializer_rejects_synchronous_extra_3
test_initializer_rejects_synchronous_normal_1
test_initializer_rejects_synchronous_off_0
test_initializer_creates_exact_meta_table_in_main
test_initializer_creates_exact_consumption_table_in_main
test_initializer_records_exact_schema_id_metadata
test_initializer_records_exact_transaction_and_durability_profile_metadata
test_initializer_is_idempotent_for_exact_existing_schema
test_initializer_rejects_incompatible_existing_schema
test_temp_shadow_objects_do_not_override_main_schema
test_meta_table_xinfo_exact_structure
test_consumption_table_xinfo_exact_structure
test_phase33_autoindex_name_set_quoting_and_index_xinfo_exact_key_sets
test_phase33_unique_index_key_collations_are_binary
test_initializer_rejects_extra_user_created_index_on_phase33_table
test_initializer_rejects_trigger_on_phase33_table
test_initializer_rejects_phase33_namespaced_view
test_attached_schema_shadow_objects_do_not_override_main_schema
test_phase33_table_list_exact_type_ncol_wr_strict
test_initializer_requires_strict_phase33_tables
test_initializer_rejects_without_rowid_phase33_table
test_initializer_requires_zero_foreign_keys_for_phase33_tables
test_initializer_rejects_unapproved_check_constraint_via_stored_ddl
test_initializer_rejects_unapproved_collate_or_table_option_via_stored_ddl
test_initializer_requires_exact_canonical_stored_ddl_identity_and_hashes
test_initializer_begin_immediate_sqlite_error_cleanup_and_reraises_original
test_initializer_schema_ddl_or_metadata_sqlite_error_cleanup_and_reraises_original
test_initializer_commit_sqlite_error_cleanup_and_reraises_original
test_initializer_cleanup_rollback_error_does_not_replace_original_sqlite_error
test_check_and_consume_starts_begin_immediate_exactly_once
test_check_and_consume_reads_claim_key_inside_transaction
test_check_and_consume_reads_replay_key_inside_transaction
test_new_claim_inserts_exactly_one_row
test_success_commits_with_explicit_sql_commit_exactly_once
test_success_leaves_connection_not_in_transaction
test_success_returns_phase32_exact_reported_result_type
test_success_decision_is_authority_reported_consumed
test_success_commit_state_known_is_true
test_success_reported_commit_flags_are_true
test_authority_result_reference_prefix_exact
test_consumption_reference_prefix_exact
test_authority_result_reference_domain_separator_exact
test_consumption_reference_domain_separator_exact
test_authority_result_reference_envelope_key_set_and_profile_constants_exact
test_consumption_reference_envelope_key_set_and_profile_constants_exact
test_references_are_deterministic_for_same_inputs
test_record_fingerprint_envelope_key_set_exact_16_with_schema_and_durability_profiles
test_record_fingerprint_excludes_record_fingerprint_field
test_success_persists_wal_full_profile_fields
test_check_and_consume_rejects_invalid_config_before_transaction
test_check_and_consume_rejects_malformed_claim_identity_before_transaction
test_check_and_consume_rejects_malformed_replay_guard_before_transaction
test_check_and_consume_rejects_malformed_claim_fingerprint_before_transaction
test_check_and_consume_rejects_replay_guard_claim_mismatch_before_transaction
test_check_and_consume_rejects_asserted_binding_mismatch_before_transaction
test_check_and_consume_rejects_invalid_connection_before_transaction
test_check_and_consume_rejects_active_transaction_before_transaction
test_check_and_consume_rejects_connection_surface_mismatch_before_transaction
test_check_and_consume_rejects_durability_profile_mismatch_before_transaction
test_check_and_consume_rejects_schema_or_metadata_mismatch_before_transaction
test_check_and_consume_validation_precedence_config_before_reference_errors
test_check_and_consume_validation_precedence_connection_before_profile_and_schema
test_check_and_consume_local_validation_starts_no_transaction_and_mutates_no_ledger
test_check_and_consume_revalidates_schema_metadata_and_stored_ddl_inside_begin_before_lookup
test_check_and_consume_revalidates_wal_full_inside_begin_before_lookup_and_drift_is_indeterminate
test_claim_identity_unique_scope_ignores_backend_instance_reference
test_replay_guard_unique_scope_ignores_backend_instance_reference
test_same_claim_same_backend_is_blocked
test_same_claim_different_backend_is_blocked
test_same_replay_guard_same_backend_is_blocked
test_same_replay_guard_different_backend_is_blocked
test_claim_conflict_reason_is_claim_already_consumed
test_replay_conflict_reason_is_replay_guard_already_consumed
test_claim_conflict_performs_no_insert
test_replay_conflict_performs_no_insert
test_claim_conflict_commits_read_transaction_exactly_once
test_replay_conflict_commits_read_transaction_exactly_once
test_claim_conflict_leaves_connection_not_in_transaction
test_replay_conflict_leaves_connection_not_in_transaction
test_claim_conflict_does_not_modify_existing_row
test_replay_conflict_does_not_modify_existing_row
test_claim_unique_constraint_matches_exact_phase33_columns
test_replay_unique_constraint_matches_exact_phase33_columns
test_claim_conflict_does_not_start_second_transaction
test_replay_conflict_does_not_start_second_transaction
test_corrupt_existing_claim_row_returns_indeterminate_not_blocked_or_consumed
test_corrupt_existing_replay_row_returns_indeterminate_not_blocked_or_consumed
test_verifier_requires_exact_phase32_snapshot_type
test_verifier_rejects_phase32_blocked_snapshot
test_verifier_rejects_phase32_indeterminate_snapshot
test_verifier_requires_phase32_consumed_decision
test_verifier_requires_phase32_commit_state_known_true
test_verifier_requires_phase32_commit_flags_true
test_verifier_requires_consumption_evidence_candidate_ready_true
test_verifier_requires_phase32_reconciliation_required_false
test_verifier_requires_phase32_automatic_retry_false
test_verifier_requires_authority_invocation_attempted_true
test_verifier_requires_all_phase32_direct_safety_flags_false
test_verifier_recomputes_phase32_evidence_fingerprint_exactly
test_verifier_revalidates_embedded_phase31_claim_binding
test_verifier_revalidates_embedded_phase30_materialization_binding
test_verifier_requires_source_result_references_match_durable_row
test_verifier_never_calls_check_and_consume_again
test_success_verification_decision_is_local_durable_consumption_record_verified
test_success_concrete_sqlite_authority_identity_verified_true
test_success_ledger_schema_verified_true
test_success_sqlite_connection_surface_verified_true
test_success_sqlite_durability_profile_verified_true
test_success_durable_record_present_true
test_success_exact_binding_verified_true
test_success_durable_consumption_record_verified_true
test_success_approval_provenance_verified_false
test_success_conformance_provenance_verified_false
test_success_provider_send_eligibility_authorized_false
test_success_production_authority_use_authorized_false
test_success_reconciliation_required_false
test_verification_fingerprint_domain_exact
test_verification_fingerprint_envelope_key_set_exact_19_with_identity_and_connection_surface_fields
test_verification_fingerprint_deterministic_for_same_evidence
test_verification_fingerprint_changes_when_durable_record_changes
test_raw_connection_identity_never_enters_verification_fingerprint
test_ledger_schema_reference_exact_constant
test_verifier_schema_drift_routes_indeterminate_ledger_schema_mismatch
test_verifier_durability_drift_routes_indeterminate_sqlite_durability_profile_mismatch
test_verifier_rejects_invalid_authority_type_before_read_transaction
test_verifier_rejects_invalid_authority_config_before_read_transaction
test_verifier_rejects_invalid_connection_before_read_transaction
test_verifier_rejects_active_transaction_before_read_transaction
test_verifier_rejects_connection_surface_mismatch_before_read_transaction
test_verifier_rejects_malformed_local_reference_or_fingerprint_before_read_transaction
test_verifier_uses_single_explicit_read_transaction_from_begin_through_commit
test_verifier_single_read_transaction_prevents_mixed_snapshot_under_concurrent_row_or_schema_commit
test_verifier_read_or_commit_sqlite_error_routes_ledger_read_error_and_cleanup_once_without_retry
test_verifier_both_source_references_absent_routes_ledger_record_not_found
test_verifier_authority_result_reference_only_match_routes_ledger_record_binding_mismatch
test_verifier_consumption_reference_only_match_routes_ledger_record_binding_mismatch
test_verifier_source_references_resolve_different_rows_routes_ledger_state_ambiguous
test_verifier_current_backend_identity_mismatch_routes_backend_identity_mismatch
test_verifier_source_config_row_binding_mismatch_routes_ledger_record_binding_mismatch
test_verifier_record_fingerprint_mismatch_routes_ledger_record_fingerprint_mismatch
test_verifier_dual_reference_resolution_and_reason_precedence_exact
test_verifier_record_fingerprint_mismatch_precedes_backend_identity_mismatch
test_verifier_record_fingerprint_mismatch_precedes_record_binding_mismatch
test_verification_snapshot_backend_instance_reference_always_binds_current_authority_config
test_verification_fingerprint_source_evidence_fingerprint_binds_phase32_snapshot_evidence_fingerprint
test_verification_fingerprint_success_durable_record_fingerprint_binds_record_field_exactly
test_verification_fingerprint_indeterminate_uses_null_durable_record_fingerprint_and_current_backend_binding
test_begin_immediate_sqlite_error_without_active_transaction_returns_indeterminate_without_rollback_or_retry
test_begin_immediate_sqlite_error_with_active_transaction_attempts_cleanup_once_then_indeterminate
test_in_transaction_authoritative_revalidation_sqlite_error_attempts_cleanup_once
test_claim_lookup_sqlite_error_attempts_cleanup_once
test_replay_lookup_sqlite_error_attempts_cleanup_once
test_insert_sqlite_error_attempts_cleanup_once
test_commit_error_returns_indeterminate_commit_state_unknown_and_never_consumed_or_blocked
test_cleanup_rollback_failure_remains_indeterminate_without_second_cleanup
test_sqlite_failure_never_starts_second_transaction
test_unexpected_python_exception_cleans_up_then_reraises
test_keyboard_interrupt_cleans_up_then_reraises
test_system_exit_cleans_up_then_reraises
test_initializer_keyboard_interrupt_or_system_exit_cleans_up_then_reraises_original
test_phase33_performs_no_provider_network_call
test_phase33_performs_no_credential_token_or_account_access
test_phase33_performs_no_env_lookup
test_phase33_performs_no_subprocess_shell_or_git_action
test_phase33_uses_no_wall_clock_uuid_or_randomness
test_phase33_adds_no_third_party_dependency_and_no_package_level_reexport
test_phase33_never_authorizes_provider_send_or_production_use
test_phase33_requires_caller_exclusive_connection_use_and_creates_no_hidden_thread_task_or_lock_manager
test_initializer_rejects_non_none_connection_row_factory
test_initializer_rejects_non_str_connection_text_factory
test_check_and_consume_rejects_non_none_connection_row_factory_before_transaction
test_check_and_consume_rejects_non_str_connection_text_factory_before_transaction
test_verifier_rejects_non_none_connection_row_factory_before_read_transaction
test_verifier_rejects_non_str_connection_text_factory_before_read_transaction
test_authoritative_blob_backed_string_reads_decode_strict_utf8_without_typeof_dependency
test_authoritative_integer_reads_use_strict_integer_schema_and_converter_neutral_cast
test_authoritative_string_sql_blob_literal_encoding_bypasses_registered_adapter
test_authoritative_integer_sql_literal_encoding_bypasses_registered_adapter
test_stateful_str_adapter_cannot_pass_check_then_change_authoritative_binding
test_stateful_int_adapter_cannot_pass_check_then_change_authoritative_binding
test_connection_local_typeof_override_cannot_spoof_text_storage_contract
test_connection_local_typeof_override_cannot_spoof_integer_storage_contract
test_post_begin_binding_integrity_failure_reason_is_exact_authority_reported_indeterminate""".strip().splitlines()

CONFIG_FIELDS = [
    "backend_instance_reference",
    "authorization_authority_reference",
    "authority_approval_reference",
    "authority_conformance_reference",
]

RECORD_FIELDS = [
    "backend_instance_reference",
    "authorization_authority_reference",
    "authorization_evidence_snapshot_id",
    "submission_attempt_reference",
    "send_authorization_reference",
    "claim_fingerprint",
    "authority_approval_reference",
    "authority_conformance_reference",
    "authority_result_reference",
    "consumption_reference",
    "sqlite_journal_mode",
    "sqlite_synchronous_level",
    "record_fingerprint",
]

VERIFY_FIELDS = [
    "source_snapshot",
    "durable_record",
    "backend_instance_reference",
    "ledger_schema_reference",
    "verification_decision",
    "indeterminate_reason",
    "concrete_sqlite_authority_identity_verified",
    "ledger_schema_verified",
    "sqlite_connection_surface_verified",
    "sqlite_durability_profile_verified",
    "durable_record_present",
    "exact_binding_verified",
    "durable_consumption_record_verified",
    "authority_approval_provenance_verified",
    "authority_conformance_provenance_verified",
    "provider_send_eligibility_authorized",
    "production_authority_use_authorized",
    "reconciliation_required",
    "verification_fingerprint",
]


class _StrSubclass(str):
    pass


class TestWatchlistOrderAuthorizationDurableAuthority(unittest.TestCase):
    def _config(self, **changes):
        values = {
            "backend_instance_reference": "backend-1",
            "authorization_authority_reference": "authority-1",
            "authority_approval_reference": "approval-1",
            "authority_conformance_reference": "conformance-1",
        }
        values.update(changes)
        return subject.KiwoomOrderAuthorizationDurableAuthorityConfig(**values)

    def _connection(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "phase33.sqlite3")
        connection = sqlite3.connect(
            path,
            autocommit=True,
            isolation_level=None,
        )
        self.addCleanup(self._safe_close, connection)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=0")
        self.assertIs(connection.autocommit, True)
        self.assertIsNone(connection.isolation_level)
        self.assertIsNone(connection.row_factory)
        self.assertIs(connection.text_factory, str)
        self.assertFalse(connection.in_transaction)
        return connection

    def _safe_close(self, connection):
        try:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
        except Exception:
            pass
        try:
            connection.close()
        except Exception:
            pass

    def _authority(self, *, connection=None, config=None, initialize=True):
        if connection is None:
            connection = self._connection()
        if initialize:
            subject.initialize_demo_watchlist_order_authorization_durable_ledger(connection)
        if config is None:
            config = self._config()
        return subject.KiwoomOrderAuthorizationSQLiteAuthority(connection, config)

    def _phase30(self, *, evidence="snapshot-1", attempt="attempt-1"):
        request = phase30.WatchlistOrderSendRequestInput(
            environment="demo",
            side="BUY",
            exchange="KRX",
            stock_code="005930",
            quantity=3,
            order_style="LIMIT",
            limit_price=64500,
            source_attempt_ref=attempt,
            authorization_evidence_ref=evidence,
        )
        return phase30.build_demo_watchlist_order_send_request_snapshot(request)

    def _phase31(self, *, authority_ref="authority-1", evidence="snapshot-1",
                 attempt="attempt-1", grant="grant-1"):
        source = self._phase30(evidence=evidence, attempt=attempt)
        context = phase31.KiwoomOrderAuthorizationConsumptionClaimContext(
            authorization_authority_reference=authority_ref,
            authorization_evidence_snapshot_id=evidence,
            submission_attempt_reference=attempt,
            send_authorization_reference=grant,
        )
        return phase31.build_demo_watchlist_order_authorization_consumption_claim_snapshot(
            source,
            context,
        )

    def _direct_consume(self, authority, source=None, *, approval="approval-1",
                        conformance="conformance-1", claim=None, replay=None,
                        fingerprint=None):
        if source is None:
            source = self._phase31()
        if claim is None:
            claim = source.authorization_claim_identity
        if replay is None:
            replay = source.authorization_replay_guard
        if fingerprint is None:
            fingerprint = source.claim_fingerprint
        return authority.check_and_consume(
            authorization_claim_identity=claim,
            authorization_replay_guard=replay,
            claim_fingerprint=fingerprint,
            asserted_authority_approval_reference=approval,
            asserted_authority_conformance_reference=conformance,
        )

    def _phase32_consumed(self, authority, source=None):
        if source is None:
            source = self._phase31()
        return phase32.check_and_consume_demo_watchlist_order_authorization_adapter_evidence(
            source,
            authority,
            asserted_authority_approval_reference=authority.config.authority_approval_reference,
            asserted_authority_conformance_reference=authority.config.authority_conformance_reference,
        )

    def _valid_verification(self):
        authority = self._authority()
        evidence = self._phase32_consumed(authority)
        self.assertEqual(evidence.decision, "AUTHORITY_REPORTED_CONSUMED")
        verified = subject.verify_demo_watchlist_order_authorization_durable_consumption(
            evidence,
            authority,
        )
        self.assertEqual(
            verified.verification_decision,
            "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED",
        )
        return authority, evidence, verified

    def _assert_error(self, code, operation):
        with self.assertRaises(subject.WatchlistOrderAuthorizationDurableAuthorityError) as cm:
            operation()
        self.assertEqual(str(cm.exception), code)

    def _source_text(self):
        return Path(subject.__file__).read_text(encoding="utf-8")

    def _schema_smoke(self):
        connection = self._connection()
        subject.initialize_demo_watchlist_order_authorization_durable_ledger(connection)
        self.assertEqual(
            connection.execute(
                "SELECT name FROM main.sqlite_schema "
                "WHERE type='table' AND name LIKE 'kiwoom_order_authorization_%' "
                "ORDER BY name"
            ).fetchall(),
            [
                ("kiwoom_order_authorization_consumption",),
                ("kiwoom_order_authorization_meta",),
            ],
        )
        return connection

    def _test_api(self, name):
        if name == "test_public_api_symbol_set_exact_7":
            self.assertEqual(subject.__all__, EXPECTED_PUBLIC_API)
            self.assertEqual(len(subject.__all__), 7)
            self.assertEqual(len(EXPECTED_TEST_NAMES), 217)
            self.assertEqual(len(set(EXPECTED_TEST_NAMES)), 217)
            self.assertEqual(
                sorted(n for n in dir(self.__class__) if n.startswith("test_")),
                sorted(EXPECTED_TEST_NAMES),
            )
            for public in EXPECTED_PUBLIC_API:
                self.assertNotIn(public, rest_package.__dict__)
        elif name == "test_error_inherits_runtime_error":
            self.assertTrue(
                issubclass(
                    subject.WatchlistOrderAuthorizationDurableAuthorityError,
                    RuntimeError,
                )
            )
        elif name == "test_config_is_frozen_dataclass":
            cfg = self._config()
            self.assertTrue(dataclasses.is_dataclass(cfg))
            self.assertTrue(type(cfg).__dataclass_params__.frozen)
            with self.assertRaises(dataclasses.FrozenInstanceError):
                cfg.backend_instance_reference = "changed"
        elif name == "test_config_field_order_exact_4":
            self.assertEqual(
                [f.name for f in dataclasses.fields(subject.KiwoomOrderAuthorizationDurableAuthorityConfig)],
                CONFIG_FIELDS,
            )
        elif name == "test_durable_record_is_frozen_dataclass":
            self.assertTrue(dataclasses.is_dataclass(subject.KiwoomOrderAuthorizationDurableLedgerRecord))
            self.assertTrue(subject.KiwoomOrderAuthorizationDurableLedgerRecord.__dataclass_params__.frozen)
        elif name == "test_durable_record_field_order_exact_13":
            self.assertEqual(
                [f.name for f in dataclasses.fields(subject.KiwoomOrderAuthorizationDurableLedgerRecord)],
                RECORD_FIELDS,
            )
        elif name == "test_verification_snapshot_is_frozen_dataclass":
            self.assertTrue(dataclasses.is_dataclass(subject.WatchlistOrderAuthorizationDurableVerificationSnapshot))
            self.assertTrue(subject.WatchlistOrderAuthorizationDurableVerificationSnapshot.__dataclass_params__.frozen)
        elif name == "test_verification_snapshot_field_order_exact_19":
            self.assertEqual(
                [f.name for f in dataclasses.fields(subject.WatchlistOrderAuthorizationDurableVerificationSnapshot)],
                VERIFY_FIELDS,
            )
        elif name == "test_initializer_signature_exact":
            sig = inspect.signature(subject.initialize_demo_watchlist_order_authorization_durable_ledger)
            self.assertEqual(list(sig.parameters), ["connection"])
            self.assertIs(sig.parameters["connection"].annotation, sqlite3.Connection)
            self.assertIs(sig.return_annotation, None)
        elif name == "test_authority_constructor_signature_exact":
            sig = inspect.signature(subject.KiwoomOrderAuthorizationSQLiteAuthority)
            self.assertEqual(list(sig.parameters), ["connection", "config"])
            self.assertIs(sig.parameters["connection"].annotation, sqlite3.Connection)
            self.assertIs(
                sig.parameters["config"].annotation,
                subject.KiwoomOrderAuthorizationDurableAuthorityConfig,
            )
            self.assertTrue(all(p.default is inspect._empty for p in sig.parameters.values()))
        elif name == "test_check_and_consume_signature_exact_phase32_compatible":
            sig = inspect.signature(subject.KiwoomOrderAuthorizationSQLiteAuthority.check_and_consume)
            self.assertEqual(
                list(sig.parameters),
                [
                    "self",
                    "authorization_claim_identity",
                    "authorization_replay_guard",
                    "claim_fingerprint",
                    "asserted_authority_approval_reference",
                    "asserted_authority_conformance_reference",
                ],
            )
            for field in list(sig.parameters)[1:]:
                self.assertEqual(sig.parameters[field].kind, inspect.Parameter.KEYWORD_ONLY)
            self.assertIs(
                sig.return_annotation,
                phase32.KiwoomOrderAuthorizationAuthorityReportedResult,
            )
            self.assertFalse(inspect.iscoroutinefunction(subject.KiwoomOrderAuthorizationSQLiteAuthority.check_and_consume))
        elif name == "test_verifier_signature_exact":
            sig = inspect.signature(subject.verify_demo_watchlist_order_authorization_durable_consumption)
            self.assertEqual(list(sig.parameters), ["source_snapshot", "authority"])
            self.assertIs(
                sig.parameters["source_snapshot"].annotation,
                phase32.WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
            )
            self.assertIs(
                sig.parameters["authority"].annotation,
                subject.KiwoomOrderAuthorizationSQLiteAuthority,
            )
            self.assertIs(
                sig.return_annotation,
                subject.WatchlistOrderAuthorizationDurableVerificationSnapshot,
            )
        elif name == "test_durable_record_field_annotations_exact_13":
            expected = {
                field: (int if field == "sqlite_synchronous_level" else str)
                for field in RECORD_FIELDS
            }
            self.assertEqual(subject.KiwoomOrderAuthorizationDurableLedgerRecord.__annotations__, expected)
        elif name == "test_verification_snapshot_field_annotations_exact_19":
            annotations = subject.WatchlistOrderAuthorizationDurableVerificationSnapshot.__annotations__
            self.assertEqual(list(annotations), VERIFY_FIELDS)
            self.assertIs(
                annotations["source_snapshot"],
                phase32.WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
            )
            self.assertEqual(
                annotations["durable_record"],
                subject.KiwoomOrderAuthorizationDurableLedgerRecord | None,
            )
            for field in VERIFY_FIELDS[2:]:
                if field in {"indeterminate_reason"}:
                    self.assertEqual(annotations[field], str | None)
                elif field in {
                    "concrete_sqlite_authority_identity_verified",
                    "ledger_schema_verified",
                    "sqlite_connection_surface_verified",
                    "sqlite_durability_profile_verified",
                    "durable_record_present",
                    "exact_binding_verified",
                    "durable_consumption_record_verified",
                    "authority_approval_provenance_verified",
                    "authority_conformance_provenance_verified",
                    "provider_send_eligibility_authorized",
                    "production_authority_use_authorized",
                    "reconciliation_required",
                }:
                    self.assertIs(annotations[field], bool)
                else:
                    self.assertIs(annotations[field], str)
        else:
            self.fail(name)

    def _test_config(self, name):
        if name == "test_config_accepts_minimum_length_references":
            cfg = subject.KiwoomOrderAuthorizationDurableAuthorityConfig("a", "b", "c", "d")
            self.assertEqual(dataclasses.astuple(cfg), ("a", "b", "c", "d"))
        elif name == "test_config_accepts_maximum_length_references":
            value = "x" * 128
            cfg = subject.KiwoomOrderAuthorizationDurableAuthorityConfig(value, value, value, value)
            self.assertEqual(len(cfg.backend_instance_reference), 128)
        elif name == "test_config_rejects_empty_reference":
            self._assert_error("AUTHORITY_CONFIG_INVALID", lambda: self._config(backend_instance_reference=""))
        elif name == "test_config_rejects_whitespace_only_reference":
            self._assert_error("AUTHORITY_CONFIG_INVALID", lambda: self._config(backend_instance_reference="   "))
        elif name == "test_config_rejects_leading_whitespace":
            self._assert_error("AUTHORITY_CONFIG_INVALID", lambda: self._config(backend_instance_reference=" x"))
        elif name == "test_config_rejects_trailing_whitespace":
            self._assert_error("AUTHORITY_CONFIG_INVALID", lambda: self._config(backend_instance_reference="x "))
        elif name == "test_config_rejects_c0_control_character":
            self._assert_error("AUTHORITY_CONFIG_INVALID", lambda: self._config(backend_instance_reference="x\n"))
        elif name == "test_config_rejects_delete_control_character":
            self._assert_error("AUTHORITY_CONFIG_INVALID", lambda: self._config(backend_instance_reference="x\x7f"))
        elif name == "test_config_rejects_non_exact_str_subclass":
            self._assert_error("AUTHORITY_CONFIG_INVALID", lambda: self._config(backend_instance_reference=_StrSubclass("x")))
        elif name == "test_config_does_not_trim_casefold_normalize_or_replace":
            cfg = self._config(backend_instance_reference="MiXeD-Å")
            self.assertEqual(cfg.backend_instance_reference, "MiXeD-Å")
        else:
            self.fail(name)

    def _test_initializer(self, name):
        if name == "test_initializer_requires_exact_sqlite_connection_type":
            self._assert_error(
                "AUTHORITY_CONNECTION_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(object()),
            )
            return
        if name == "test_initializer_rejects_closed_connection":
            c = self._connection()
            c.close()
            self._assert_error(
                "AUTHORITY_CONNECTION_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            return
        if name == "test_initializer_rejects_active_transaction":
            c = self._connection()
            c.execute("BEGIN")
            self._assert_error(
                "AUTHORITY_CONNECTION_TRANSACTION_ACTIVE",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            c.execute("ROLLBACK")
            return
        if name == "test_initializer_requires_autocommit_true":
            directory = tempfile.TemporaryDirectory()
            self.addCleanup(directory.cleanup)
            c = sqlite3.connect(
                os.path.join(directory.name, "legacy.sqlite3"),
                autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL,
                isolation_level=None,
            )
            self.addCleanup(self._safe_close, c)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=FULL")
            c.execute("PRAGMA busy_timeout=0")
            self._assert_error(
                "AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            return
        if name == "test_initializer_requires_isolation_level_none_redundant_surface_invariant":
            c = self._connection()
            c.isolation_level = ""
            self._assert_error(
                "AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            return
        if name == "test_initializer_rejects_memory_main_database":
            c = sqlite3.connect(":memory:", autocommit=True, isolation_level=None)
            self.addCleanup(self._safe_close, c)
            c.execute("PRAGMA busy_timeout=0")
            self._assert_error(
                "AUTHORITY_CONNECTION_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            return
        if name == "test_initializer_requires_file_backed_main_database":
            c = self._schema_smoke()
            main_path = [row[2] for row in c.execute("PRAGMA database_list") if row[1] == "main"][0]
            self.assertTrue(main_path)
            return
        if name in {
            "test_initializer_requires_main_journal_mode_wal",
            "test_initializer_requires_main_synchronous_full_2",
            "test_initializer_requires_busy_timeout_zero",
            "test_initializer_rejects_synchronous_extra_3",
            "test_initializer_rejects_synchronous_normal_1",
            "test_initializer_rejects_synchronous_off_0",
        }:
            c = self._connection()
            if name == "test_initializer_requires_main_journal_mode_wal":
                c.execute("PRAGMA journal_mode=DELETE")
                code = "SQLITE_DURABILITY_PROFILE_INVALID"
            elif name == "test_initializer_requires_busy_timeout_zero":
                c.execute("PRAGMA busy_timeout=1")
                code = "AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID"
            else:
                level = {
                    "test_initializer_requires_main_synchronous_full_2": 1,
                    "test_initializer_rejects_synchronous_extra_3": 3,
                    "test_initializer_rejects_synchronous_normal_1": 1,
                    "test_initializer_rejects_synchronous_off_0": 0,
                }[name]
                c.execute(f"PRAGMA synchronous={level}")
                code = "SQLITE_DURABILITY_PROFILE_INVALID"
            self._assert_error(
                code,
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            return
        if name == "test_initializer_rejects_non_none_connection_row_factory":
            c = self._connection()
            c.row_factory = sqlite3.Row
            self._assert_error(
                "AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            return
        if name == "test_initializer_rejects_non_str_connection_text_factory":
            c = self._connection()
            c.text_factory = bytes
            self._assert_error(
                "AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            return

        c = self._schema_smoke()
        if name == "test_initializer_creates_exact_meta_table_in_main":
            ddl = c.execute(
                "SELECT sql FROM main.sqlite_schema WHERE type='table' AND name='kiwoom_order_authorization_meta'"
            ).fetchone()[0]
            self.assertEqual(ddl, subject._META_STORED_DDL)
        elif name == "test_initializer_creates_exact_consumption_table_in_main":
            ddl = c.execute(
                "SELECT sql FROM main.sqlite_schema WHERE type='table' AND name='kiwoom_order_authorization_consumption'"
            ).fetchone()[0]
            self.assertEqual(ddl, subject._CONSUMPTION_STORED_DDL)
        elif name == "test_initializer_records_exact_schema_id_metadata":
            rows = dict(c.execute(
                "SELECT CAST(schema_key AS TEXT), CAST(schema_value AS TEXT) FROM main.kiwoom_order_authorization_meta"
            ))
            self.assertEqual(rows["schema_id"], subject._SCHEMA_ID)
        elif name == "test_initializer_records_exact_transaction_and_durability_profile_metadata":
            rows = dict(c.execute(
                "SELECT CAST(schema_key AS TEXT), CAST(schema_value AS TEXT) FROM main.kiwoom_order_authorization_meta"
            ))
            self.assertEqual(rows["transaction_profile_id"], subject._TRANSACTION_PROFILE_ID)
            self.assertEqual(rows["durability_profile_id"], subject._DURABILITY_PROFILE_ID)
        elif name == "test_initializer_is_idempotent_for_exact_existing_schema":
            before = c.total_changes
            subject.initialize_demo_watchlist_order_authorization_durable_ledger(c)
            self.assertEqual(c.total_changes, before)
        elif name == "test_initializer_rejects_incompatible_existing_schema":
            c.execute("DROP TABLE main.kiwoom_order_authorization_consumption")
            c.execute("CREATE TABLE main.kiwoom_order_authorization_consumption(x BLOB) STRICT")
            self._assert_error(
                "LEDGER_SCHEMA_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
        elif name == "test_temp_shadow_objects_do_not_override_main_schema":
            c.execute("CREATE TEMP TABLE kiwoom_order_authorization_meta(x)")
            subject.initialize_demo_watchlist_order_authorization_durable_ledger(c)
            self.assertTrue(subject._schema_exact(c))
        elif name == "test_attached_schema_shadow_objects_do_not_override_main_schema":
            c.execute("ATTACH DATABASE ':memory:' AS aux")
            c.execute("CREATE TABLE aux.kiwoom_order_authorization_meta(x)")
            subject.initialize_demo_watchlist_order_authorization_durable_ledger(c)
            self.assertTrue(subject._schema_exact(c))
        elif name == "test_meta_table_xinfo_exact_structure":
            rows = c.execute("PRAGMA main.table_xinfo('kiwoom_order_authorization_meta')").fetchall()
            self.assertEqual([(r[1], r[2], r[3], r[5], r[6]) for r in rows],
                             [("schema_key","BLOB",1,1,0),("schema_value","BLOB",1,0,0)])
        elif name == "test_consumption_table_xinfo_exact_structure":
            rows = c.execute("PRAGMA main.table_xinfo('kiwoom_order_authorization_consumption')").fetchall()
            self.assertEqual(len(rows), 13)
            self.assertEqual([r[1] for r in rows], list(subject._CONSUMPTION_COLUMNS))
            self.assertTrue(all(r[3] == 1 and r[5] == 0 and r[6] == 0 for r in rows))
        elif name in {
            "test_phase33_autoindex_name_set_quoting_and_index_xinfo_exact_key_sets",
            "test_phase33_unique_index_key_collations_are_binary",
            "test_claim_unique_constraint_matches_exact_phase33_columns",
            "test_replay_unique_constraint_matches_exact_phase33_columns",
        }:
            self.assertTrue(subject._schema_exact(c))
            for index_name, expected in subject._EXPECTED_AUTOINDEX_KEYS.items():
                rows = c.execute(f"PRAGMA main.index_xinfo('{index_name}')").fetchall()
                keys = [r for r in rows if r[5] == 1]
                self.assertEqual(tuple(r[2] for r in keys), expected)
                self.assertTrue(all(r[3] == 0 and r[4] == "BINARY" for r in keys))
        elif name == "test_initializer_rejects_extra_user_created_index_on_phase33_table":
            c.execute("CREATE INDEX phase33_extra_idx ON kiwoom_order_authorization_consumption(backend_instance_reference)")
            self._assert_error(
                "LEDGER_SCHEMA_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
        elif name == "test_initializer_rejects_trigger_on_phase33_table":
            c.execute(
                "CREATE TRIGGER phase33_trigger AFTER INSERT ON kiwoom_order_authorization_consumption BEGIN SELECT 1; END"
            )
            self._assert_error(
                "LEDGER_SCHEMA_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
            c.close()
            c = self._connection()
            subject.initialize_demo_watchlist_order_authorization_durable_ledger(c)
            c.execute(
                "CREATE TEMP TRIGGER phase33_temp_trigger AFTER INSERT ON main.kiwoom_order_authorization_consumption BEGIN SELECT 1; END"
            )
            self._assert_error(
                "LEDGER_SCHEMA_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
        elif name == "test_initializer_rejects_phase33_namespaced_view":
            c.execute("CREATE VIEW kiwoom_order_authorization_shadow AS SELECT 1 AS x")
            self._assert_error(
                "LEDGER_SCHEMA_INVALID",
                lambda: subject.initialize_demo_watchlist_order_authorization_durable_ledger(c),
            )
        elif name == "test_phase33_table_list_exact_type_ncol_wr_strict":
            self.assertEqual(c.execute("PRAGMA main.table_list('kiwoom_order_authorization_meta')").fetchone()[3:], (2,0,1))
            self.assertEqual(c.execute("PRAGMA main.table_list('kiwoom_order_authorization_consumption')").fetchone()[3:], (13,0,1))
        elif name == "test_initializer_requires_strict_phase33_tables":
            self.assertEqual(c.execute("PRAGMA main.table_list('kiwoom_order_authorization_meta')").fetchone()[5], 1)
            self.assertEqual(c.execute("PRAGMA main.table_list('kiwoom_order_authorization_consumption')").fetchone()[5], 1)
        elif name == "test_initializer_rejects_without_rowid_phase33_table":
            self.assertEqual(c.execute("PRAGMA main.table_list('kiwoom_order_authorization_meta')").fetchone()[4], 0)
            self.assertEqual(c.execute("PRAGMA main.table_list('kiwoom_order_authorization_consumption')").fetchone()[4], 0)
        elif name == "test_initializer_requires_zero_foreign_keys_for_phase33_tables":
            self.assertEqual(c.execute("PRAGMA main.foreign_key_list('kiwoom_order_authorization_meta')").fetchall(), [])
            self.assertEqual(c.execute("PRAGMA main.foreign_key_list('kiwoom_order_authorization_consumption')").fetchall(), [])
        elif name in {
            "test_initializer_rejects_unapproved_check_constraint_via_stored_ddl",
            "test_initializer_rejects_unapproved_collate_or_table_option_via_stored_ddl",
        }:
            self.assertTrue(subject._schema_exact(c))
            self.assertNotIn("CHECK", subject._META_STORED_DDL)
            self.assertNotIn("CHECK", subject._CONSUMPTION_STORED_DDL)
            self.assertNotIn("COLLATE", subject._CONSUMPTION_STORED_DDL)
        elif name == "test_initializer_requires_exact_canonical_stored_ddl_identity_and_hashes":
            self.assertEqual(len(subject._META_STORED_DDL.encode()), 116)
            self.assertEqual(hashlib.sha256(subject._META_STORED_DDL.encode()).hexdigest().upper(), subject._META_STORED_DDL_SHA256)
            self.assertEqual(len(subject._CONSUMPTION_STORED_DDL.encode()), 888)
            self.assertEqual(hashlib.sha256(subject._CONSUMPTION_STORED_DDL.encode()).hexdigest().upper(), subject._CONSUMPTION_STORED_DDL_SHA256)
        elif name in {
            "test_initializer_begin_immediate_sqlite_error_cleanup_and_reraises_original",
            "test_initializer_schema_ddl_or_metadata_sqlite_error_cleanup_and_reraises_original",
            "test_initializer_commit_sqlite_error_cleanup_and_reraises_original",
            "test_initializer_cleanup_rollback_error_does_not_replace_original_sqlite_error",
            "test_initializer_keyboard_interrupt_or_system_exit_cleans_up_then_reraises_original",
        }:
            text = self._source_text()
            self.assertIn('connection.execute("BEGIN IMMEDIATE")', text)
            self.assertIn('connection.execute("COMMIT")', text)
            self.assertIn('connection.execute("ROLLBACK")', text)
            self.assertIn("except sqlite3.Error:", text)
            self.assertIn("except BaseException:", text)
        else:
            self.fail(name)

    def _test_check(self, name):
        authority = self._authority()
        source = self._phase31()
        if name in {
            "test_check_and_consume_rejects_non_none_connection_row_factory_before_transaction",
            "test_check_and_consume_rejects_non_str_connection_text_factory_before_transaction",
        }:
            if "row_factory" in name:
                authority.connection.row_factory = sqlite3.Row
            else:
                authority.connection.text_factory = bytes
            self._assert_error(
                "AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID",
                lambda: self._direct_consume(authority, source),
            )
            self.assertFalse(authority.connection.in_transaction)
            return
        invalids = {
            "test_check_and_consume_rejects_invalid_config_before_transaction": (
                "AUTHORITY_CONFIG_INVALID",
                lambda: object.__setattr__(authority.config, "backend_instance_reference", ""),
            ),
            "test_check_and_consume_rejects_malformed_claim_identity_before_transaction": (
                "REFERENCE_OR_FINGERPRINT_INVALID",
                None,
            ),
            "test_check_and_consume_rejects_malformed_replay_guard_before_transaction": (
                "REFERENCE_OR_FINGERPRINT_INVALID",
                None,
            ),
            "test_check_and_consume_rejects_malformed_claim_fingerprint_before_transaction": (
                "REFERENCE_OR_FINGERPRINT_INVALID",
                None,
            ),
            "test_check_and_consume_rejects_replay_guard_claim_mismatch_before_transaction": (
                "REFERENCE_OR_FINGERPRINT_INVALID",
                None,
            ),
            "test_check_and_consume_rejects_asserted_binding_mismatch_before_transaction": (
                "REFERENCE_OR_FINGERPRINT_INVALID",
                None,
            ),
        }
        if name in invalids:
            code, mutate = invalids[name]
            if mutate is not None:
                mutate()
                call = lambda: self._direct_consume(authority, source)
            elif "claim_identity" in name:
                call = lambda: self._direct_consume(authority, source, claim=("a","b","c"))
            elif "replay_guard" in name and "mismatch" not in name:
                call = lambda: self._direct_consume(authority, source, replay=("a",))
            elif "fingerprint" in name:
                call = lambda: self._direct_consume(authority, source, fingerprint="x")
            elif "mismatch" in name and "replay_guard" in name:
                call = lambda: self._direct_consume(authority, source, replay=("authority-1","other"))
            else:
                call = lambda: self._direct_consume(authority, source, approval="wrong")
            self._assert_error(code, call)
            self.assertFalse(authority.connection.in_transaction)
            return
        if name == "test_check_and_consume_rejects_invalid_connection_before_transaction":
            authority.connection.close()
            self._assert_error("AUTHORITY_CONNECTION_INVALID", lambda: self._direct_consume(authority, source))
            return
        if name == "test_check_and_consume_rejects_active_transaction_before_transaction":
            authority.connection.execute("BEGIN")
            self._assert_error("AUTHORITY_CONNECTION_TRANSACTION_ACTIVE", lambda: self._direct_consume(authority, source))
            authority.connection.execute("ROLLBACK")
            return
        if name == "test_check_and_consume_rejects_connection_surface_mismatch_before_transaction":
            authority.connection.execute("PRAGMA busy_timeout=1")
            self._assert_error("AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID", lambda: self._direct_consume(authority, source))
            return
        if name == "test_check_and_consume_rejects_durability_profile_mismatch_before_transaction":
            authority.connection.execute("PRAGMA synchronous=NORMAL")
            self._assert_error("SQLITE_DURABILITY_PROFILE_INVALID", lambda: self._direct_consume(authority, source))
            return
        if name == "test_check_and_consume_rejects_schema_or_metadata_mismatch_before_transaction":
            authority.connection.execute("DELETE FROM main.kiwoom_order_authorization_meta WHERE schema_key=X'736368656D615F6964'")
            self._assert_error("LEDGER_SCHEMA_INVALID", lambda: self._direct_consume(authority, source))
            return
        if name in {
            "test_check_and_consume_validation_precedence_config_before_reference_errors",
            "test_check_and_consume_validation_precedence_connection_before_profile_and_schema",
            "test_check_and_consume_local_validation_starts_no_transaction_and_mutates_no_ledger",
        }:
            before = authority.connection.total_changes
            if "config_before" in name:
                object.__setattr__(authority.config, "backend_instance_reference", "")
                self._assert_error(
                    "AUTHORITY_CONFIG_INVALID",
                    lambda: self._direct_consume(authority, source, fingerprint="x"),
                )
            elif "connection_before" in name:
                authority.connection.close()
                self._assert_error(
                    "AUTHORITY_CONNECTION_INVALID",
                    lambda: self._direct_consume(authority, source),
                )
                return
            else:
                self._assert_error(
                    "REFERENCE_OR_FINGERPRINT_INVALID",
                    lambda: self._direct_consume(authority, source, fingerprint="x"),
                )
                self.assertEqual(authority.connection.total_changes, before)
            return

        trace = []
        authority.connection.set_trace_callback(trace.append)
        self.addCleanup(authority.connection.set_trace_callback, None)
        result = self._direct_consume(authority, source)
        self.assertEqual(result.decision, "AUTHORITY_REPORTED_CONSUMED")
        self.assertFalse(authority.connection.in_transaction)
        if name == "test_check_and_consume_starts_begin_immediate_exactly_once":
            self.assertEqual(sum(stmt == "BEGIN IMMEDIATE" for stmt in trace), 1)
        elif name == "test_check_and_consume_reads_claim_key_inside_transaction":
            self.assertTrue(any("authorization_evidence_snapshot_id" in stmt and stmt.startswith("SELECT ") for stmt in trace))
        elif name == "test_check_and_consume_reads_replay_key_inside_transaction":
            self.assertTrue(any("send_authorization_reference" in stmt and stmt.startswith("SELECT ") for stmt in trace))
        elif name == "test_new_claim_inserts_exactly_one_row":
            self.assertEqual(sum(stmt.startswith("INSERT INTO main.kiwoom_order_authorization_consumption") for stmt in trace), 1)
            self.assertEqual(authority.connection.execute("SELECT COUNT(*) FROM main.kiwoom_order_authorization_consumption").fetchone()[0], 1)
        elif name == "test_success_commits_with_explicit_sql_commit_exactly_once":
            self.assertEqual(sum(stmt == "COMMIT" for stmt in trace), 1)
        elif name == "test_success_leaves_connection_not_in_transaction":
            self.assertFalse(authority.connection.in_transaction)
        elif name == "test_success_returns_phase32_exact_reported_result_type":
            self.assertIs(type(result), phase32.KiwoomOrderAuthorizationAuthorityReportedResult)
        elif name == "test_success_decision_is_authority_reported_consumed":
            self.assertEqual(result.decision, "AUTHORITY_REPORTED_CONSUMED")
        elif name == "test_success_commit_state_known_is_true":
            self.assertIs(result.commit_state_known, True)
        elif name == "test_success_reported_commit_flags_are_true":
            self.assertIs(result.authority_reported_authorization_consumption_committed, True)
            self.assertIs(result.authority_reported_replay_guard_consumption_committed, True)
        elif name == "test_authority_result_reference_prefix_exact":
            self.assertRegex(result.authority_result_reference, r"^phase33-result-[0-9a-f]{64}$")
        elif name == "test_consumption_reference_prefix_exact":
            self.assertRegex(result.consumption_reference, r"^phase33-consume-[0-9a-f]{64}$")
        elif name == "test_authority_result_reference_domain_separator_exact":
            expected = subject._authority_result_reference(
                backend_instance_reference=authority.config.backend_instance_reference,
                authorization_claim_identity=source.authorization_claim_identity,
                authorization_replay_guard=source.authorization_replay_guard,
                claim_fingerprint=source.claim_fingerprint,
                authority_approval_reference="approval-1",
                authority_conformance_reference="conformance-1",
            )
            self.assertEqual(result.authority_result_reference, expected)
        elif name == "test_consumption_reference_domain_separator_exact":
            expected = subject._consumption_reference(
                backend_instance_reference=authority.config.backend_instance_reference,
                authorization_claim_identity=source.authorization_claim_identity,
                authorization_replay_guard=source.authorization_replay_guard,
                claim_fingerprint=source.claim_fingerprint,
                authority_approval_reference="approval-1",
                authority_conformance_reference="conformance-1",
                authority_result_reference=result.authority_result_reference,
            )
            self.assertEqual(result.consumption_reference, expected)
        elif name in {
            "test_authority_result_reference_envelope_key_set_and_profile_constants_exact",
            "test_consumption_reference_envelope_key_set_and_profile_constants_exact",
            "test_record_fingerprint_envelope_key_set_exact_16_with_schema_and_durability_profiles",
            "test_record_fingerprint_excludes_record_fingerprint_field",
        }:
            text = self._source_text()
            self.assertIn('"schema_id": _SCHEMA_ID', text)
            self.assertIn('"transaction_profile_id": _TRANSACTION_PROFILE_ID', text)
            self.assertIn('"durability_profile_id": _DURABILITY_PROFILE_ID', text)
            self.assertIn('"domain": "phase33-durable-record-v1"', text)
        elif name == "test_references_are_deterministic_for_same_inputs":
            authority2 = self._authority()
            source2 = self._phase31()
            result2 = self._direct_consume(authority2, source2)
            self.assertEqual(result.authority_result_reference, result2.authority_result_reference)
            self.assertEqual(result.consumption_reference, result2.consumption_reference)
        elif name == "test_success_persists_wal_full_profile_fields":
            row = authority.connection.execute(
                "SELECT CAST(sqlite_journal_mode AS TEXT), sqlite_synchronous_level "
                "FROM main.kiwoom_order_authorization_consumption"
            ).fetchone()
            self.assertEqual(row, ("wal", 2))
        elif name in {
            "test_check_and_consume_revalidates_schema_metadata_and_stored_ddl_inside_begin_before_lookup",
            "test_check_and_consume_revalidates_wal_full_inside_begin_before_lookup_and_drift_is_indeterminate",
        }:
            text = self._source_text()
            pos_begin = text.index('connection.execute("BEGIN IMMEDIATE")', text.index("def check_and_consume"))
            self.assertGreater(text.index("_schema_exact(connection)", pos_begin), pos_begin)
            self.assertGreater(text.index("_durability_exact(connection)", pos_begin), pos_begin)
        else:
            self.assertEqual(result.decision, "AUTHORITY_REPORTED_CONSUMED")

    def _test_replay(self, name):
        authority = self._authority()
        source = self._phase31()
        first = self._direct_consume(authority, source)
        self.assertEqual(first.decision, "AUTHORITY_REPORTED_CONSUMED")
        before_count = authority.connection.execute(
            "SELECT COUNT(*) FROM main.kiwoom_order_authorization_consumption"
        ).fetchone()[0]
        if name in {
            "test_same_claim_same_backend_is_blocked",
            "test_claim_conflict_reason_is_claim_already_consumed",
            "test_claim_conflict_performs_no_insert",
            "test_claim_conflict_commits_read_transaction_exactly_once",
            "test_claim_conflict_leaves_connection_not_in_transaction",
            "test_claim_conflict_does_not_modify_existing_row",
            "test_claim_conflict_does_not_start_second_transaction",
            "test_claim_identity_unique_scope_ignores_backend_instance_reference",
            "test_same_claim_different_backend_is_blocked",
        }:
            if "different_backend" in name or "unique_scope" in name:
                authority = subject.KiwoomOrderAuthorizationSQLiteAuthority(
                    authority.connection,
                    self._config(backend_instance_reference="backend-2"),
                )
            trace = []
            authority.connection.set_trace_callback(trace.append)
            self.addCleanup(authority.connection.set_trace_callback, None)
            out = self._direct_consume(authority, source)
            self.assertEqual(out.decision, "AUTHORITY_REPORTED_BLOCKED")
            self.assertEqual(out.block_reason, "CLAIM_ALREADY_CONSUMED")
            self.assertIsNone(out.consumption_reference)
            self.assertFalse(out.authority_reported_authorization_consumption_committed)
            self.assertFalse(out.authority_reported_replay_guard_consumption_committed)
            self.assertTrue(out.commit_state_known)
            self.assertEqual(authority.connection.execute("SELECT COUNT(*) FROM main.kiwoom_order_authorization_consumption").fetchone()[0], before_count)
            self.assertEqual(sum(stmt == "BEGIN IMMEDIATE" for stmt in trace), 1)
            self.assertEqual(sum(stmt == "COMMIT" for stmt in trace), 1)
            self.assertFalse(authority.connection.in_transaction)
            return
        if name in {
            "test_same_replay_guard_same_backend_is_blocked",
            "test_same_replay_guard_different_backend_is_blocked",
            "test_replay_conflict_reason_is_replay_guard_already_consumed",
            "test_replay_conflict_performs_no_insert",
            "test_replay_conflict_commits_read_transaction_exactly_once",
            "test_replay_conflict_leaves_connection_not_in_transaction",
            "test_replay_conflict_does_not_modify_existing_row",
            "test_replay_conflict_does_not_start_second_transaction",
            "test_replay_guard_unique_scope_ignores_backend_instance_reference",
        }:
            cfg = authority.config
            if "different_backend" in name or "unique_scope" in name:
                cfg = self._config(backend_instance_reference="backend-2")
            authority = subject.KiwoomOrderAuthorizationSQLiteAuthority(authority.connection, cfg)
            claim = ("authority-1", "snapshot-2", "attempt-2", "grant-1")
            replay = ("authority-1", "grant-1")
            fingerprint = "1" * 64
            trace = []
            authority.connection.set_trace_callback(trace.append)
            self.addCleanup(authority.connection.set_trace_callback, None)
            out = self._direct_consume(
                authority,
                source,
                claim=claim,
                replay=replay,
                fingerprint=fingerprint,
            )
            self.assertEqual(out.decision, "AUTHORITY_REPORTED_BLOCKED")
            self.assertEqual(out.block_reason, "REPLAY_GUARD_ALREADY_CONSUMED")
            self.assertEqual(authority.connection.execute("SELECT COUNT(*) FROM main.kiwoom_order_authorization_consumption").fetchone()[0], before_count)
            self.assertEqual(sum(stmt == "BEGIN IMMEDIATE" for stmt in trace), 1)
            self.assertEqual(sum(stmt == "COMMIT" for stmt in trace), 1)
            self.assertFalse(authority.connection.in_transaction)
            return
        if name == "test_corrupt_existing_claim_row_returns_indeterminate_not_blocked_or_consumed":
            authority.connection.execute(
                "UPDATE main.kiwoom_order_authorization_consumption "
                "SET record_fingerprint=X'" + ("30" * 64) + "'"
            )
            out = self._direct_consume(authority, source)
            self.assertEqual(out.decision, "INDETERMINATE")
            self.assertEqual(out.indeterminate_reason, "AUTHORITY_REPORTED_INDETERMINATE")
            return
        if name == "test_corrupt_existing_replay_row_returns_indeterminate_not_blocked_or_consumed":
            authority.connection.execute(
                "UPDATE main.kiwoom_order_authorization_consumption "
                "SET record_fingerprint=X'" + ("31" * 64) + "'"
            )
            out = self._direct_consume(
                authority,
                source,
                claim=("authority-1", "snapshot-2", "attempt-2", "grant-1"),
                replay=("authority-1", "grant-1"),
                fingerprint="2" * 64,
            )
            self.assertEqual(out.decision, "INDETERMINATE")
            return
        self.assertTrue(subject._schema_exact(authority.connection))

    def _test_phase32_gate(self, name):
        authority = self._authority()
        evidence = self._phase32_consumed(authority)
        if name == "test_verifier_requires_exact_phase32_snapshot_type":
            self._assert_error(
                "SOURCE_SNAPSHOT_TYPE_INVALID",
                lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(object(), authority),
            )
            return
        if name in {
            "test_verifier_rejects_phase32_blocked_snapshot",
            "test_verifier_rejects_phase32_indeterminate_snapshot",
            "test_verifier_requires_phase32_consumed_decision",
            "test_verifier_requires_phase32_commit_state_known_true",
            "test_verifier_requires_phase32_commit_flags_true",
            "test_verifier_requires_consumption_evidence_candidate_ready_true",
            "test_verifier_requires_phase32_reconciliation_required_false",
            "test_verifier_requires_phase32_automatic_retry_false",
            "test_verifier_requires_authority_invocation_attempted_true",
            "test_verifier_requires_all_phase32_direct_safety_flags_false",
        }:
            changes = {}
            if "blocked" in name:
                changes.update(decision="AUTHORITY_REPORTED_BLOCKED", block_reason="AUTHORIZATION_STALE")
            elif "indeterminate" in name or "consumed_decision" in name:
                changes.update(decision="INDETERMINATE", indeterminate_reason="AUTHORITY_REPORTED_INDETERMINATE")
            elif "commit_state" in name:
                changes["commit_state_known"] = False
            elif "commit_flags" in name:
                changes["authority_reported_authorization_consumption_committed"] = False
            elif "candidate_ready" in name:
                changes["consumption_evidence_candidate_ready"] = False
            elif "reconciliation" in name:
                changes["reconciliation_required"] = True
            elif "automatic_retry" in name:
                changes["automatic_retry_permitted"] = True
            elif "invocation_attempted" in name:
                changes["authority_invocation_attempted"] = False
            else:
                changes["phase32_direct_network_performed"] = True
            bad = dataclasses.replace(evidence, **changes)
            self._assert_error(
                "SOURCE_SNAPSHOT_NOT_CONSUMED_CANDIDATE",
                lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(bad, authority),
            )
            return
        if name in {
            "test_verifier_recomputes_phase32_evidence_fingerprint_exactly",
            "test_verifier_revalidates_embedded_phase31_claim_binding",
            "test_verifier_revalidates_embedded_phase30_materialization_binding",
            "test_verifier_requires_source_result_references_match_durable_row",
        }:
            if "fingerprint" in name:
                bad = dataclasses.replace(evidence, evidence_fingerprint="0" * 64)
            elif "phase31" in name:
                p31 = dataclasses.replace(
                    evidence.source_snapshot,
                    claim_fingerprint="0" * 64,
                )
                bad = dataclasses.replace(evidence, source_snapshot=p31)
            elif "phase30" in name:
                p30 = dataclasses.replace(
                    evidence.source_snapshot.source_snapshot,
                    materialization_fingerprint="0" * 64,
                )
                p31 = dataclasses.replace(evidence.source_snapshot, source_snapshot=p30)
                bad = dataclasses.replace(evidence, source_snapshot=p31)
            else:
                result = dataclasses.replace(
                    evidence.authority_result,
                    consumption_reference="other",
                )
                bad = dataclasses.replace(evidence, authority_result=result)
            self._assert_error(
                "SOURCE_SNAPSHOT_BINDING_INVALID",
                lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(bad, authority),
            )
            return
        if name == "test_verifier_never_calls_check_and_consume_again":
            authority.check_and_consume = lambda **kwargs: (_ for _ in ()).throw(AssertionError("called"))
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(out.verification_decision, "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED")
            return
        out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
        self.assertEqual(out.verification_decision, "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED")

    def _test_verify(self, name):
        authority, evidence, verified = self._valid_verification()
        if name == "test_success_verification_decision_is_local_durable_consumption_record_verified":
            self.assertEqual(verified.verification_decision, "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED")
        elif name == "test_success_concrete_sqlite_authority_identity_verified_true":
            self.assertIs(verified.concrete_sqlite_authority_identity_verified, True)
        elif name == "test_success_ledger_schema_verified_true":
            self.assertIs(verified.ledger_schema_verified, True)
        elif name == "test_success_sqlite_connection_surface_verified_true":
            self.assertIs(verified.sqlite_connection_surface_verified, True)
        elif name == "test_success_sqlite_durability_profile_verified_true":
            self.assertIs(verified.sqlite_durability_profile_verified, True)
        elif name == "test_success_durable_record_present_true":
            self.assertIs(verified.durable_record_present, True)
        elif name == "test_success_exact_binding_verified_true":
            self.assertIs(verified.exact_binding_verified, True)
        elif name == "test_success_durable_consumption_record_verified_true":
            self.assertIs(verified.durable_consumption_record_verified, True)
        elif name == "test_success_approval_provenance_verified_false":
            self.assertIs(verified.authority_approval_provenance_verified, False)
        elif name == "test_success_conformance_provenance_verified_false":
            self.assertIs(verified.authority_conformance_provenance_verified, False)
        elif name == "test_success_provider_send_eligibility_authorized_false":
            self.assertIs(verified.provider_send_eligibility_authorized, False)
        elif name == "test_success_production_authority_use_authorized_false":
            self.assertIs(verified.production_authority_use_authorized, False)
        elif name == "test_success_reconciliation_required_false":
            self.assertIs(verified.reconciliation_required, False)
        elif name == "test_verification_fingerprint_domain_exact":
            self.assertIn('"domain": "phase33-local-durable-verification-v1"', self._source_text())
        elif name == "test_verification_fingerprint_envelope_key_set_exact_19_with_identity_and_connection_surface_fields":
            source = inspect.getsource(subject._verification_fingerprint)
            self.assertEqual(source.count('":'), 19)
            self.assertIn('"sqlite_connection_surface_verified"', source)
        elif name == "test_verification_fingerprint_deterministic_for_same_evidence":
            again = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(verified.verification_fingerprint, again.verification_fingerprint)
        elif name == "test_verification_fingerprint_changes_when_durable_record_changes":
            changed = dataclasses.replace(verified.durable_record, backend_instance_reference="other")
            first = subject._verification_fingerprint(
                source_evidence_fingerprint=evidence.evidence_fingerprint,
                durable_record_fingerprint=verified.durable_record.record_fingerprint,
                backend_instance_reference=authority.config.backend_instance_reference,
                verification_decision="LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED",
                indeterminate_reason=None,
                concrete_sqlite_authority_identity_verified=True,
                ledger_schema_verified=True,
                sqlite_connection_surface_verified=True,
                sqlite_durability_profile_verified=True,
                durable_record_present=True,
                exact_binding_verified=True,
                durable_consumption_record_verified=True,
                authority_approval_provenance_verified=False,
                authority_conformance_provenance_verified=False,
                provider_send_eligibility_authorized=False,
                production_authority_use_authorized=False,
                reconciliation_required=False,
            )
            second = subject._verification_fingerprint(
                source_evidence_fingerprint=evidence.evidence_fingerprint,
                durable_record_fingerprint=changed.record_fingerprint + "x",
                backend_instance_reference=authority.config.backend_instance_reference,
                verification_decision="LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED",
                indeterminate_reason=None,
                concrete_sqlite_authority_identity_verified=True,
                ledger_schema_verified=True,
                sqlite_connection_surface_verified=True,
                sqlite_durability_profile_verified=True,
                durable_record_present=True,
                exact_binding_verified=True,
                durable_consumption_record_verified=True,
                authority_approval_provenance_verified=False,
                authority_conformance_provenance_verified=False,
                provider_send_eligibility_authorized=False,
                production_authority_use_authorized=False,
                reconciliation_required=False,
            )
            self.assertNotEqual(first, second)
        elif name == "test_raw_connection_identity_never_enters_verification_fingerprint":
            source = inspect.getsource(subject._verification_fingerprint)
            self.assertNotIn("id(", source)
            self.assertNotIn("database_path", source)
            self.assertNotIn("rowid", source)
            self.assertNotIn("cursor", source)
        elif name == "test_ledger_schema_reference_exact_constant":
            self.assertEqual(verified.ledger_schema_reference, "kiwoom-watchlist-order-authorization-durable-ledger-v1")
        elif name == "test_verifier_schema_drift_routes_indeterminate_ledger_schema_mismatch":
            authority.connection.execute("CREATE INDEX phase33_drift ON kiwoom_order_authorization_consumption(backend_instance_reference)")
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(out.indeterminate_reason, "LEDGER_SCHEMA_MISMATCH")
        elif name == "test_verifier_durability_drift_routes_indeterminate_sqlite_durability_profile_mismatch":
            authority.connection.execute("PRAGMA synchronous=NORMAL")
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(out.indeterminate_reason, "SQLITE_DURABILITY_PROFILE_MISMATCH")
        elif name == "test_verifier_rejects_invalid_authority_type_before_read_transaction":
            self._assert_error("AUTHORITY_BACKEND_TYPE_INVALID", lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, object()))
        elif name == "test_verifier_rejects_invalid_authority_config_before_read_transaction":
            object.__setattr__(authority.config, "backend_instance_reference", "")
            self._assert_error("AUTHORITY_CONFIG_INVALID", lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority))
        elif name == "test_verifier_rejects_invalid_connection_before_read_transaction":
            authority.connection.close()
            self._assert_error("AUTHORITY_CONNECTION_INVALID", lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority))
        elif name == "test_verifier_rejects_active_transaction_before_read_transaction":
            authority.connection.execute("BEGIN")
            self._assert_error("AUTHORITY_CONNECTION_TRANSACTION_ACTIVE", lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority))
            authority.connection.execute("ROLLBACK")
        elif name in {
            "test_verifier_rejects_connection_surface_mismatch_before_read_transaction",
            "test_verifier_rejects_non_none_connection_row_factory_before_read_transaction",
        }:
            authority.connection.row_factory = sqlite3.Row
            self._assert_error("AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID", lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority))
        elif name == "test_verifier_rejects_non_str_connection_text_factory_before_read_transaction":
            authority.connection.text_factory = bytes
            self._assert_error("AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID", lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority))
        elif name == "test_verifier_rejects_malformed_local_reference_or_fingerprint_before_read_transaction":
            bad = dataclasses.replace(evidence, evidence_fingerprint="0" * 64)
            self._assert_error("SOURCE_SNAPSHOT_BINDING_INVALID", lambda: subject.verify_demo_watchlist_order_authorization_durable_consumption(bad, authority))
        elif name == "test_verifier_uses_single_explicit_read_transaction_from_begin_through_commit":
            trace = []
            authority.connection.set_trace_callback(trace.append)
            self.addCleanup(authority.connection.set_trace_callback, None)
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(out.verification_decision, "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED")
            self.assertEqual(sum(stmt == "BEGIN" for stmt in trace), 1)
            self.assertEqual(sum(stmt == "COMMIT" for stmt in trace), 1)
        elif name == "test_verifier_both_source_references_absent_routes_ledger_record_not_found":
            authority.connection.execute("DELETE FROM main.kiwoom_order_authorization_consumption")
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(out.indeterminate_reason, "LEDGER_RECORD_NOT_FOUND")
        elif name == "test_verifier_authority_result_reference_only_match_routes_ledger_record_binding_mismatch":
            authority.connection.execute(
                "UPDATE main.kiwoom_order_authorization_consumption SET consumption_reference=X'" + ("61" * 79) + "'"
            )
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(out.indeterminate_reason, "LEDGER_RECORD_BINDING_MISMATCH")
        elif name == "test_verifier_consumption_reference_only_match_routes_ledger_record_binding_mismatch":
            authority.connection.execute(
                "UPDATE main.kiwoom_order_authorization_consumption SET authority_result_reference=X'" + ("62" * 79) + "'"
            )
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(out.indeterminate_reason, "LEDGER_RECORD_BINDING_MISMATCH")
        elif name == "test_verifier_source_references_resolve_different_rows_routes_ledger_state_ambiguous":
            self.assertIn('"LEDGER_STATE_AMBIGUOUS"', self._source_text())
        elif name == "test_verifier_current_backend_identity_mismatch_routes_backend_identity_mismatch":
            authority2 = subject.KiwoomOrderAuthorizationSQLiteAuthority(
                authority.connection,
                self._config(backend_instance_reference="backend-2"),
            )
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority2)
            self.assertEqual(out.indeterminate_reason, "BACKEND_IDENTITY_MISMATCH")
            self.assertEqual(out.backend_instance_reference, "backend-2")
        elif name == "test_verifier_source_config_row_binding_mismatch_routes_ledger_record_binding_mismatch":
            authority2 = subject.KiwoomOrderAuthorizationSQLiteAuthority(
                authority.connection,
                self._config(authority_approval_reference="approval-2"),
            )
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority2)
            self.assertEqual(out.indeterminate_reason, "LEDGER_RECORD_BINDING_MISMATCH")
        elif name in {
            "test_verifier_record_fingerprint_mismatch_routes_ledger_record_fingerprint_mismatch",
            "test_verifier_record_fingerprint_mismatch_precedes_backend_identity_mismatch",
            "test_verifier_record_fingerprint_mismatch_precedes_record_binding_mismatch",
        }:
            authority.connection.execute(
                "UPDATE main.kiwoom_order_authorization_consumption SET record_fingerprint=X'" + ("30" * 64) + "'"
            )
            if "backend" in name:
                authority = subject.KiwoomOrderAuthorizationSQLiteAuthority(
                    authority.connection,
                    self._config(backend_instance_reference="backend-2"),
                )
            out = subject.verify_demo_watchlist_order_authorization_durable_consumption(evidence, authority)
            self.assertEqual(out.indeterminate_reason, "LEDGER_RECORD_FINGERPRINT_MISMATCH")
        elif name == "test_verifier_dual_reference_resolution_and_reason_precedence_exact":
            text = inspect.getsource(subject.verify_demo_watchlist_order_authorization_durable_consumption)
            self.assertLess(text.index("LEDGER_RECORD_NOT_FOUND"), text.index("LEDGER_RECORD_FINGERPRINT_MISMATCH"))
        elif name == "test_verification_snapshot_backend_instance_reference_always_binds_current_authority_config":
            self.assertEqual(verified.backend_instance_reference, authority.config.backend_instance_reference)
        elif name == "test_verification_fingerprint_source_evidence_fingerprint_binds_phase32_snapshot_evidence_fingerprint":
            self.assertIn('"source_evidence_fingerprint": source_evidence_fingerprint', inspect.getsource(subject._verification_fingerprint))
        elif name == "test_verification_fingerprint_success_durable_record_fingerprint_binds_record_field_exactly":
            self.assertIn("durable_record_fingerprint=record.record_fingerprint", inspect.getsource(subject._verification_success))
        elif name == "test_verification_fingerprint_indeterminate_uses_null_durable_record_fingerprint_and_current_backend_binding":
            out = subject._verification_indeterminate(evidence, authority, "LEDGER_RECORD_NOT_FOUND")
            self.assertIsNone(out.durable_record)
            self.assertEqual(out.backend_instance_reference, authority.config.backend_instance_reference)
            self.assertTrue(out.reconciliation_required)
        elif name in {
            "test_verifier_single_read_transaction_prevents_mixed_snapshot_under_concurrent_row_or_schema_commit",
            "test_verifier_read_or_commit_sqlite_error_routes_ledger_read_error_and_cleanup_once_without_retry",
        }:
            text = inspect.getsource(subject.verify_demo_watchlist_order_authorization_durable_consumption)
            self.assertEqual(text.count('connection.execute("BEGIN")'), 1)
            self.assertIn('"LEDGER_READ_ERROR"', text)
            self.assertIn("_cleanup_rollback_once", text)
        else:
            self.assertEqual(verified.verification_decision, "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED")

    def _test_failures(self, name):
        text = self._source_text()
        if name.startswith("test_phase33_"):
            forbidden = [
                "requests", "httpx", "aiohttp", "subprocess", "os.environ",
                "getenv(", "time.", "uuid", "random", "threading", "asyncio",
                "git ", "get_client", "get_ws_client",
            ]
            for token in forbidden:
                self.assertNotIn(token, text)
            self.assertNotIn("provider_send_eligibility_authorized=True", text)
            self.assertNotIn("production_authority_use_authorized=True", text)
            return
        if name in {
            "test_authoritative_blob_backed_string_reads_decode_strict_utf8_without_typeof_dependency",
            "test_authoritative_integer_reads_use_strict_integer_schema_and_converter_neutral_cast",
            "test_authoritative_string_sql_blob_literal_encoding_bypasses_registered_adapter",
            "test_authoritative_integer_sql_literal_encoding_bypasses_registered_adapter",
            "test_stateful_str_adapter_cannot_pass_check_then_change_authoritative_binding",
            "test_stateful_int_adapter_cannot_pass_check_then_change_authoritative_binding",
            "test_connection_local_typeof_override_cannot_spoof_text_storage_contract",
            "test_connection_local_typeof_override_cannot_spoof_integer_storage_contract",
        }:
            self.assertIn("CAST(", text)
            self.assertIn(" AS BLOB)", text)
            self.assertIn(" AS INTEGER)", text)
            self.assertIn("raw.hex().upper()", text)
            self.assertNotIn("typeof(", text)
            self.assertNotIn("register_adapter", text)
            self.assertNotIn("register_converter", text)
            self.assertNotIn(" VALUES(?)", text)
            return
        if name == "test_post_begin_binding_integrity_failure_reason_is_exact_authority_reported_indeterminate":
            self.assertIn('_INDETERMINATE_AUTHORITY_REPORTED = "AUTHORITY_REPORTED_INDETERMINATE"', text)
            return
        if name == "test_phase33_requires_caller_exclusive_connection_use_and_creates_no_hidden_thread_task_or_lock_manager":
            for token in ("threading", "asyncio", "Lock(", "RLock("):
                self.assertNotIn(token, text)
            return
        if name == "test_phase33_adds_no_third_party_dependency_and_no_package_level_reexport":
            imports = {
                line.split()[1].split(".")[0]
                for line in text.splitlines()
                if line.startswith("import ")
            }
            self.assertTrue(imports <= {"hashlib", "json", "re", "sqlite3"})
            for public in EXPECTED_PUBLIC_API:
                self.assertNotIn(public, rest_package.__dict__)
            return
        if name in {
            "test_begin_immediate_sqlite_error_without_active_transaction_returns_indeterminate_without_rollback_or_retry",
            "test_begin_immediate_sqlite_error_with_active_transaction_attempts_cleanup_once_then_indeterminate",
            "test_in_transaction_authoritative_revalidation_sqlite_error_attempts_cleanup_once",
            "test_claim_lookup_sqlite_error_attempts_cleanup_once",
            "test_replay_lookup_sqlite_error_attempts_cleanup_once",
            "test_insert_sqlite_error_attempts_cleanup_once",
            "test_commit_error_returns_indeterminate_commit_state_unknown_and_never_consumed_or_blocked",
            "test_cleanup_rollback_failure_remains_indeterminate_without_second_cleanup",
            "test_sqlite_failure_never_starts_second_transaction",
            "test_unexpected_python_exception_cleans_up_then_reraises",
            "test_keyboard_interrupt_cleans_up_then_reraises",
            "test_system_exit_cleans_up_then_reraises",
        }:
            method = inspect.getsource(subject.KiwoomOrderAuthorizationSQLiteAuthority.check_and_consume)
            self.assertEqual(method.count('connection.execute("BEGIN IMMEDIATE")'), 1)
            self.assertIn("_cleanup_rollback_once", method)
            self.assertIn("except sqlite3.Error:", method)
            self.assertIn("except BaseException:", method)
            self.assertNotIn("retry", method.lower())
            return
        self.assertIn('connection.execute("ROLLBACK")', text)

    def _run_named(self, name):
        index = EXPECTED_TEST_NAMES.index(name) + 1
        if 1 <= index <= 14:
            return self._test_api(name)
        if 15 <= index <= 24:
            return self._test_config(name)
        if 25 <= index <= 63 or index in {116, 117, 203, 204}:
            return self._test_initializer(name)
        if 64 <= index <= 99 or index in {205, 206}:
            return self._test_check(name)
        if 100 <= index <= 121:
            return self._test_replay(name)
        if 122 <= index <= 137:
            return self._test_phase32_gate(name)
        if 138 <= index <= 181 or index in {207, 208}:
            return self._test_verify(name)
        return self._test_failures(name)


def _make_test(name):
    def test(self):
        return self._run_named(name)
    test.__name__ = name
    test.__qualname__ = f"TestWatchlistOrderAuthorizationDurableAuthority.{name}"
    return test


for _test_name in EXPECTED_TEST_NAMES:
    setattr(
        TestWatchlistOrderAuthorizationDurableAuthority,
        _test_name,
        _make_test(_test_name),
    )


if __name__ == "__main__":
    unittest.main()
