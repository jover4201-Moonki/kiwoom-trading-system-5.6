from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from types import SimpleNamespace
import unittest

from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_attempt_preparation as phase28
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_dispatch_plan as phase26
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_mapping as phase25
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_submission_safety as phase27
from kiwoom_trading_system.brokers.kiwoom.rest import watchlist_order_send_authorization as subject


PUBLIC_API = (
    "KiwoomOrderSendAuthorizationError",
    "KiwoomOrderSendAuthorizationState",
    "KiwoomOrderSendAuthorizationDecision",
    "KiwoomOrderSendAuthorizationBlockReason",
    "KiwoomOrderSendAuthorizationContext",
    "WatchlistCandidateKiwoomOrderSendAuthorization",
    "WatchlistKiwoomOrderSendAuthorizationSnapshot",
    "build_watchlist_kiwoom_order_send_authorization_snapshot",
)
PHASE28_PUBLIC_API = (
    "KiwoomOrderAttemptPreparationError",
    "KiwoomOrderPreparationConfirmationState",
    "KiwoomOrderAttemptPreparationDecision",
    "KiwoomOrderAttemptPreparationBlockReason",
    "KiwoomOrderAttemptPreparationContext",
    "WatchlistCandidateKiwoomOrderAttemptPreparation",
    "WatchlistKiwoomOrderAttemptPreparationSnapshot",
    "build_watchlist_kiwoom_order_attempt_preparation_snapshot",
)
PHASE27_PUBLIC_API = (
    "KiwoomOrderSubmissionSafetyError",
    "KiwoomPriorSubmissionState",
    "KiwoomOrderSubmissionSafetyDecision",
    "KiwoomOrderSubmissionSafetyBlockReason",
    "KiwoomOrderSubmissionSafetyContext",
    "WatchlistCandidateKiwoomOrderSubmissionSafety",
    "WatchlistKiwoomOrderSubmissionSafetySnapshot",
    "build_watchlist_kiwoom_order_submission_safety_snapshot",
)
PHASE26_PUBLIC_API = (
    "KIWOOM_DEMO_ORDER_BASE_URL",
    "KIWOOM_ORDER_HTTP_METHOD",
    "KIWOOM_ORDER_CONTENT_TYPE",
    "KiwoomOrderDispatchPlanError",
    "KiwoomDemoOrderDispatchDecision",
    "KiwoomDemoOrderDispatchBlockReason",
    "KiwoomBuyOrderDispatchPlan",
    "WatchlistCandidateKiwoomOrderDispatchPlan",
    "WatchlistKiwoomOrderDispatchPlanSnapshot",
    "build_watchlist_kiwoom_order_dispatch_plan_snapshot",
)
PHASE25_PUBLIC_API = (
    "KIWOOM_BUY_ORDER_API_ID",
    "KIWOOM_ORDER_API_PATH",
    "KiwoomOrderMappingError",
    "KiwoomBuyOrderRequest",
    "WatchlistCandidateKiwoomOrderMapping",
    "WatchlistKiwoomOrderMappingSnapshot",
    "build_watchlist_kiwoom_order_mapping_snapshot",
)
CONTEXT_FIELDS = (
    "source_rank",
    "submission_attempt_reference",
    "authorization_state",
    "send_authorization_reference",
    "authorization_authority_reference",
    "authorization_evidence_snapshot_id",
    "is_fresh",
)
CANDIDATE_FIELDS = (
    "source_preparation",
    "context",
    "decision",
    "block_reason",
    "send_authorized",
    "automatic_retry_permitted",
)
SNAPSHOT_FIELDS = (
    "source_snapshot",
    "authorizations",
    "candidate_count",
    "send_authorized_count",
    "send_blocked_count",
    "authorization_required_count",
    "authorization_stale_count",
    "upstream_blocked_count",
    "automatic_retry_permitted_count",
)
SOURCE_PATH = Path(subject.__file__).resolve()


def _construct(cls, values):
    kwargs = {}
    for field in fields(cls):
        if field.name in values:
            kwargs[field.name] = values[field.name]
        elif field.default is not field.default_factory:  # pragma: no cover - defensive only
            kwargs[field.name] = field.default
        else:
            kwargs[field.name] = None
    return cls(**kwargs)


def _phase28_context(rank=1, prepared=True):
    reference = f"attempt-{rank}" if prepared else None
    return _construct(
        phase28.KiwoomOrderAttemptPreparationContext,
        {
            "source_rank": rank,
            "confirmation_state": (
                phase28.KiwoomOrderPreparationConfirmationState.CONFIRMED_FOR_PREPARATION
                if prepared
                else phase28.KiwoomOrderPreparationConfirmationState.NOT_CONFIRMED
            ),
            "confirmation_reference": f"confirm-{rank}" if prepared else None,
            "submission_attempt_reference": reference,
        },
    )


def _phase28_preparation(rank=1, prepared=True, upstream_blocked=False):
    reference = f"attempt-{rank}" if prepared else None
    context = _phase28_context(rank, prepared)
    source = SimpleNamespace(source_rank=rank, submission_attempt_reference=reference)
    decision = (
        phase28.KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED
        if prepared
        else phase28.KiwoomOrderAttemptPreparationDecision.ATTEMPT_BLOCKED
    )
    block_reason = None
    if not prepared:
        block_reason = (
            phase28.KiwoomOrderAttemptPreparationBlockReason.UPSTREAM_SUBMISSION_BLOCKED
            if upstream_blocked
            else phase28.KiwoomOrderAttemptPreparationBlockReason.CONFIRMATION_REQUIRED
        )
    values = {
        "source_candidate": source,
        "source_evaluation": source,
        "source_plan": source,
        "context": context,
        "decision": decision,
        "block_reason": block_reason,
        "submission_attempt_reference": reference,
        "attempt_prepared": prepared,
        "automatic_retry_permitted": False,
    }
    return _construct(phase28.WatchlistCandidateKiwoomOrderAttemptPreparation, values)


def _phase28_snapshot(preparations=()):
    preparations = tuple(preparations)
    prepared = sum(item.decision is phase28.KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED for item in preparations)
    blocked = len(preparations) - prepared
    confirmation = sum(item.block_reason is phase28.KiwoomOrderAttemptPreparationBlockReason.CONFIRMATION_REQUIRED for item in preparations)
    upstream = sum(item.block_reason is phase28.KiwoomOrderAttemptPreparationBlockReason.UPSTREAM_SUBMISSION_BLOCKED for item in preparations)
    values = {
        "source_snapshot": object(),
        "preparations": preparations,
        "candidate_count": len(preparations),
        "attempt_prepared_count": prepared,
        "prepared_count": prepared,
        "attempt_blocked_count": blocked,
        "blocked_count": blocked,
        "confirmation_required_count": confirmation,
        "upstream_submission_blocked_count": upstream,
        "upstream_blocked_count": upstream,
        "automatic_retry_permitted_count": 0,
    }
    return _construct(phase28.WatchlistKiwoomOrderAttemptPreparationSnapshot, values)


def _named_value(root, name):
    seen = set()
    def visit(value):
        if value is None or isinstance(value, (str, bytes, int, float, bool)):
            return None
        identity = id(value)
        if identity in seen:
            return None
        seen.add(identity)
        if hasattr(value, name):
            return getattr(value, name)
        if hasattr(value, "__dataclass_fields__"):
            for field in fields(value):
                child = getattr(value, field.name)
                if isinstance(child, tuple):
                    for member in child:
                        result = visit(member)
                        if result is not None:
                            return result
                else:
                    result = visit(child)
                    if result is not None:
                        return result
        return None
    return visit(root)


def _authorization_context(preparation, *, authorized=False, fresh=True, send_reference=None, authority="authority-1", snapshot_id="snapshot-1"):
    if authorized and send_reference is None:
        send_reference = "grant-1"
    if not authorized:
        send_reference = None if send_reference is None else send_reference
    return subject.KiwoomOrderSendAuthorizationContext(
        source_rank=_named_value(preparation, "source_rank"),
        submission_attempt_reference=_named_value(preparation, "submission_attempt_reference"),
        authorization_state=(
            subject.KiwoomOrderSendAuthorizationState.AUTHORIZED_FOR_SEND
            if authorized
            else subject.KiwoomOrderSendAuthorizationState.NOT_AUTHORIZED
        ),
        send_authorization_reference=send_reference,
        authorization_authority_reference=authority,
        authorization_evidence_snapshot_id=snapshot_id,
        is_fresh=fresh,
    )


def _build(preparations, contexts=None):
    snapshot = _phase28_snapshot(preparations)
    if contexts is None:
        contexts = tuple(_authorization_context(p) for p in preparations)
    return subject.build_watchlist_kiwoom_order_send_authorization_snapshot(snapshot, tuple(contexts))


def _replace_first_count(snapshot, delta=1):
    for field in fields(snapshot):
        if field.name.endswith("_count") and field.name not in ("candidate_count", "automatic_retry_permitted_count"):
            return replace(snapshot, **{field.name: getattr(snapshot, field.name) + delta})
    raise AssertionError("No mutable aggregate count field found")


def _source_text():
    return SOURCE_PATH.read_text(encoding="utf-8")


def _assert_forbidden_absent(testcase, *tokens):
    text = _source_text().lower()
    for token in tokens:
        testcase.assertNotIn(token.lower(), text)


class Phase29PublicApiTests(unittest.TestCase):
    def test_public_api_exact_eight_symbols(self):
        self.assertEqual(tuple(subject.__all__), PUBLIC_API)

    def test_error_is_runtime_error(self):
        self.assertTrue(issubclass(subject.KiwoomOrderSendAuthorizationError, RuntimeError))

    def test_state_enum_exact_members(self):
        self.assertEqual([(x.name, x.value) for x in subject.KiwoomOrderSendAuthorizationState], [("NOT_AUTHORIZED", "NOT_AUTHORIZED"), ("AUTHORIZED_FOR_SEND", "AUTHORIZED_FOR_SEND")])

    def test_decision_enum_exact_members(self):
        self.assertEqual([(x.name, x.value) for x in subject.KiwoomOrderSendAuthorizationDecision], [("SEND_AUTHORIZED", "SEND_AUTHORIZED"), ("SEND_BLOCKED", "SEND_BLOCKED")])

    def test_block_reason_enum_exact_members(self):
        self.assertEqual([(x.name, x.value) for x in subject.KiwoomOrderSendAuthorizationBlockReason], [("UPSTREAM_ATTEMPT_BLOCKED", "UPSTREAM_ATTEMPT_BLOCKED"), ("SEND_AUTHORIZATION_REQUIRED", "SEND_AUTHORIZATION_REQUIRED"), ("AUTHORIZATION_STALE", "AUTHORIZATION_STALE")])

    def test_context_exact_fields_and_frozen(self):
        self.assertEqual(tuple(f.name for f in fields(subject.KiwoomOrderSendAuthorizationContext)), CONTEXT_FIELDS)
        p = _phase28_preparation()
        c = _authorization_context(p)
        with self.assertRaises(FrozenInstanceError):
            c.source_rank = 9

    def test_candidate_exact_fields_and_frozen(self):
        self.assertEqual(tuple(f.name for f in fields(subject.WatchlistCandidateKiwoomOrderSendAuthorization)), CANDIDATE_FIELDS)
        item = _build((_phase28_preparation(),)).authorizations[0]
        with self.assertRaises(FrozenInstanceError):
            item.send_authorized = True

    def test_snapshot_exact_fields_and_frozen(self):
        self.assertEqual(tuple(f.name for f in fields(subject.WatchlistKiwoomOrderSendAuthorizationSnapshot)), SNAPSHOT_FIELDS)
        snap = _build(())
        with self.assertRaises(FrozenInstanceError):
            snap.candidate_count = 1

    def test_builder_exact_signature(self):
        sig = inspect.signature(subject.build_watchlist_kiwoom_order_send_authorization_snapshot)
        self.assertEqual(tuple(sig.parameters), ("source_snapshot", "contexts"))
        self.assertTrue(all(p.default is inspect.Parameter.empty for p in sig.parameters.values()))
        self.assertFalse(inspect.iscoroutinefunction(subject.build_watchlist_kiwoom_order_send_authorization_snapshot))

    def test_builder_sync_exact_return_type(self):
        result = _build(())
        self.assertIs(type(result), subject.WatchlistKiwoomOrderSendAuthorizationSnapshot)


class Phase29UpstreamIdentityTests(unittest.TestCase):
    def test_rejects_nonexact_source_snapshot_type(self):
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(object(), ())

    def test_rejects_contexts_non_tuple(self):
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot(()), [])

    def test_rejects_nonexact_context_member_type(self):
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((_phase28_preparation(),)), (object(),))

    def test_rejects_missing_context(self):
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((_phase28_preparation(),)), ())

    def test_rejects_extra_context(self):
        p = _phase28_preparation()
        c = _authorization_context(p)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((p,)), (c, c))

    def test_rejects_context_positional_reordering(self):
        p1, p2 = _phase28_preparation(1), _phase28_preparation(2)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((p1, p2)), (_authorization_context(p2), _authorization_context(p1)))

    def test_rejects_source_rank_identity_mismatch(self):
        p = _phase28_preparation()
        c = replace(_authorization_context(p), source_rank=99)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((p,)), (c,))

    def test_rejects_submission_attempt_reference_mismatch(self):
        p = _phase28_preparation()
        c = replace(_authorization_context(p), submission_attempt_reference="wrong")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((p,)), (c,))

    def test_preserves_source_snapshot_identity(self):
        source = _phase28_snapshot((_phase28_preparation(),))
        result = subject.build_watchlist_kiwoom_order_send_authorization_snapshot(source, (_authorization_context(source.preparations[0]),))
        self.assertIs(result.source_snapshot, source)

    def test_preserves_source_preparation_identity(self):
        p = _phase28_preparation()
        result = _build((p,))
        self.assertIs(result.authorizations[0].source_preparation, p)

    def test_preserves_context_identity(self):
        p = _phase28_preparation()
        c = _authorization_context(p)
        result = _build((p,), (c,))
        self.assertIs(result.authorizations[0].context, c)

    def test_accepts_empty_source_with_empty_contexts(self):
        result = subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot(()), ())
        self.assertEqual(result.candidate_count, 0)

    def test_rejects_phase28_preparations_non_tuple(self):
        snap = _phase28_snapshot(())
        bad = replace(snap, preparations=[])
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(bad, ())

    def test_rejects_phase28_nonexact_preparation_member_type(self):
        snap = _phase28_snapshot(())
        bad = replace(snap, preparations=(object(),), candidate_count=1)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(bad, ())

    def test_rejects_phase28_candidate_count_length_mismatch(self):
        snap = _phase28_snapshot((_phase28_preparation(),))
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(replace(snap, candidate_count=2), ())

    def test_rejects_malformed_phase28_snapshot_aggregate(self):
        snap = _replace_first_count(_phase28_snapshot((_phase28_preparation(),)))
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(snap, ())

    def test_rejects_malformed_phase28_preparation_decision_block_reason_invariant(self):
        p = _phase28_preparation()
        bad = replace(p, block_reason=phase28.KiwoomOrderAttemptPreparationBlockReason.CONFIRMATION_REQUIRED)
        snap = _phase28_snapshot((bad,))
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(snap, (_authorization_context(bad),))

    def test_rejects_malformed_phase28_submission_attempt_reference_invariant(self):
        p = _phase28_preparation()
        values = {f.name: getattr(p, f.name) for f in fields(p)}
        if "submission_attempt_reference" in values:
            values["submission_attempt_reference"] = None
        elif "context" in values:
            values["context"] = replace(p.context, submission_attempt_reference=None)
        bad = type(p)(**values)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((bad,)), (_authorization_context(p),))

    def test_rejects_phase28_automatic_retry_invariant_violation(self):
        p = replace(_phase28_preparation(), automatic_retry_permitted=True)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((p,)), (_authorization_context(p),))

    def test_rejects_phase28_snapshot_automatic_retry_count_nonzero(self):
        snap = replace(_phase28_snapshot(()), automatic_retry_permitted_count=1)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(snap, ())

    def test_rejects_malformed_phase28_source_context_reference_identity(self):
        p = _phase28_preparation()
        bad_context = replace(p.context, source_rank=9)
        bad = replace(p, context=bad_context)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(_phase28_snapshot((bad,)), (_authorization_context(p),))


class Phase29AuthorizationEvidenceInvariantTests(unittest.TestCase):
    def test_rejects_raw_string_authorization_state(self):
        p = _phase28_preparation()
        c = replace(_authorization_context(p), authorization_state="NOT_AUTHORIZED")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_authorized_requires_send_reference_exact_str(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p, authorized=True), send_authorization_reference=1)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_authorized_rejects_empty_send_reference(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p, authorized=True), send_authorization_reference="")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_authorized_rejects_whitespace_send_reference(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p, authorized=True), send_authorization_reference="   ")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_not_authorized_requires_none_send_reference(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p), send_authorization_reference="grant")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_authority_reference_requires_exact_str(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p), authorization_authority_reference=1)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_authority_reference_rejects_empty(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p), authorization_authority_reference="")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_authority_reference_rejects_whitespace(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p), authorization_authority_reference="  ")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_snapshot_id_requires_exact_str(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p), authorization_evidence_snapshot_id=1)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_snapshot_id_rejects_empty(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p), authorization_evidence_snapshot_id="")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_snapshot_id_rejects_whitespace(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p), authorization_evidence_snapshot_id="  ")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_is_fresh_requires_exact_bool(self):
        p = _phase28_preparation(); c = replace(_authorization_context(p), is_fresh=1)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p,), (c,))

    def test_rejects_mixed_authority_batch(self):
        p1,p2=_phase28_preparation(1),_phase28_preparation(2); c1=_authorization_context(p1); c2=_authorization_context(p2, authority="authority-2")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p1,p2),(c1,c2))

    def test_rejects_mixed_snapshot_id_batch(self):
        p1,p2=_phase28_preparation(1),_phase28_preparation(2); c1=_authorization_context(p1); c2=_authorization_context(p2, snapshot_id="snapshot-2")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p1,p2),(c1,c2))

    def test_rejects_mixed_freshness_batch(self):
        p1,p2=_phase28_preparation(1),_phase28_preparation(2); c1=_authorization_context(p1); c2=_authorization_context(p2, fresh=False)
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p1,p2),(c1,c2))

    def test_rejects_duplicate_non_none_send_reference(self):
        p1,p2=_phase28_preparation(1),_phase28_preparation(2); c1=_authorization_context(p1,authorized=True,send_reference="g"); c2=_authorization_context(p2,authorized=True,send_reference="g")
        with self.assertRaises(subject.KiwoomOrderSendAuthorizationError): _build((p1,p2),(c1,c2))

    def test_allows_duplicate_none_send_references(self):
        p1,p2=_phase28_preparation(1),_phase28_preparation(2); r=_build((p1,p2)); self.assertEqual(r.authorization_required_count,2)

    def test_allows_distinct_send_references(self):
        p1,p2=_phase28_preparation(1),_phase28_preparation(2); r=_build((p1,p2),(_authorization_context(p1,authorized=True,send_reference="g1"),_authorization_context(p2,authorized=True,send_reference="g2"))); self.assertEqual(r.send_authorized_count,2)

    def test_accepts_valid_authorized_pair(self):
        p=_phase28_preparation(); r=_build((p,),(_authorization_context(p,authorized=True),)); self.assertTrue(r.authorizations[0].send_authorized)

    def test_accepts_valid_not_authorized_pair(self):
        p=_phase28_preparation(); r=_build((p,)); self.assertFalse(r.authorizations[0].send_authorized)

    def test_preserves_send_reference_exactly(self):
        p=_phase28_preparation(); c=_authorization_context(p,authorized=True,send_reference="opaque:Grant-XYZ"); r=_build((p,),(c,)); self.assertEqual(r.authorizations[0].context.send_authorization_reference,"opaque:Grant-XYZ")

    def test_preserves_authority_and_snapshot_exactly(self):
        p=_phase28_preparation(); c=_authorization_context(p,authority="Auth-A",snapshot_id="Snap-A"); r=_build((p,),(c,)); self.assertEqual((r.authorizations[0].context.authorization_authority_reference,r.authorizations[0].context.authorization_evidence_snapshot_id),("Auth-A","Snap-A"))

    def test_candidate_send_authorized_matches_decision(self):
        p=_phase28_preparation(); r=_build((p,),(_authorization_context(p,authorized=True),)); item=r.authorizations[0]; self.assertEqual(item.send_authorized,item.decision is subject.KiwoomOrderSendAuthorizationDecision.SEND_AUTHORIZED)

    def test_candidate_automatic_retry_is_false(self):
        p=_phase28_preparation(); self.assertIs(_build((p,)).authorizations[0].automatic_retry_permitted,False)


class Phase29DecisionMatrixTests(unittest.TestCase):
    def _assert_decision(self, prepared, fresh, authorized, decision, reason, upstream=False):
        p=_phase28_preparation(1,prepared=prepared,upstream_blocked=upstream); c=_authorization_context(p,authorized=authorized,fresh=fresh); item=_build((p,),(c,)).authorizations[0]; self.assertIs(item.decision,decision); self.assertIs(item.block_reason,reason)

    def test_blocked_stale_not_authorized_is_upstream_blocked(self): self._assert_decision(False,False,False,subject.KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED,subject.KiwoomOrderSendAuthorizationBlockReason.UPSTREAM_ATTEMPT_BLOCKED,True)
    def test_blocked_stale_authorized_is_upstream_blocked(self): self._assert_decision(False,False,True,subject.KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED,subject.KiwoomOrderSendAuthorizationBlockReason.UPSTREAM_ATTEMPT_BLOCKED,True)
    def test_blocked_fresh_not_authorized_is_upstream_blocked(self): self._assert_decision(False,True,False,subject.KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED,subject.KiwoomOrderSendAuthorizationBlockReason.UPSTREAM_ATTEMPT_BLOCKED,True)
    def test_blocked_fresh_authorized_is_upstream_blocked(self): self._assert_decision(False,True,True,subject.KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED,subject.KiwoomOrderSendAuthorizationBlockReason.UPSTREAM_ATTEMPT_BLOCKED,True)
    def test_prepared_stale_not_authorized_is_stale(self): self._assert_decision(True,False,False,subject.KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED,subject.KiwoomOrderSendAuthorizationBlockReason.AUTHORIZATION_STALE)
    def test_prepared_stale_authorized_is_stale(self): self._assert_decision(True,False,True,subject.KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED,subject.KiwoomOrderSendAuthorizationBlockReason.AUTHORIZATION_STALE)
    def test_prepared_fresh_not_authorized_requires_authorization(self): self._assert_decision(True,True,False,subject.KiwoomOrderSendAuthorizationDecision.SEND_BLOCKED,subject.KiwoomOrderSendAuthorizationBlockReason.SEND_AUTHORIZATION_REQUIRED)
    def test_prepared_fresh_authorized_is_send_authorized(self): self._assert_decision(True,True,True,subject.KiwoomOrderSendAuthorizationDecision.SEND_AUTHORIZED,None)


class Phase29SnapshotAggregateTests(unittest.TestCase):
    def _mixed(self):
        p1=_phase28_preparation(1); p2=_phase28_preparation(2); p3=_phase28_preparation(3); p4=_phase28_preparation(4,prepared=False,upstream_blocked=True)
        c1=_authorization_context(p1,authorized=True,send_reference="g1"); c2=_authorization_context(p2); c3=_authorization_context(p3); c4=_authorization_context(p4)
        return _build((p1,p2,p3,p4),(c1,c2,c3,c4))
    def _stale(self):
        p1=_phase28_preparation(1); p2=_phase28_preparation(2)
        return _build((p1,p2),(_authorization_context(p1,fresh=False),_authorization_context(p2,authorized=True,fresh=False,send_reference="g2")))
    def test_candidate_count_exact(self): self.assertEqual(self._mixed().candidate_count,4)
    def test_send_authorized_count_exact(self): self.assertEqual(self._mixed().send_authorized_count,1)
    def test_send_blocked_count_exact(self): self.assertEqual(self._mixed().send_blocked_count,3)
    def test_authorization_required_count_exact(self): self.assertEqual(self._mixed().authorization_required_count,2)
    def test_authorization_stale_count_exact(self): self.assertEqual(self._stale().authorization_stale_count,2)
    def test_upstream_blocked_count_exact(self): self.assertEqual(self._mixed().upstream_blocked_count,1)
    def test_automatic_retry_count_zero(self): self.assertEqual(self._mixed().automatic_retry_permitted_count,0)
    def test_candidate_partition_invariant(self):
        r=self._mixed(); self.assertEqual(r.candidate_count,r.send_authorized_count+r.send_blocked_count)
    def test_blocked_reason_sum_invariant(self):
        r=self._mixed(); self.assertEqual(r.send_blocked_count,r.authorization_required_count+r.authorization_stale_count+r.upstream_blocked_count)
    def test_empty_snapshot_all_counts_zero(self):
        r=_build(()); self.assertEqual(tuple(getattr(r,n) for n in SNAPSHOT_FIELDS[2:]),(0,0,0,0,0,0,0))


class Phase29ForbiddenSideEffectTests(unittest.TestCase):
    def test_no_provider_client_call(self): _assert_forbidden_absent(self,"requests.","httpx.","api.kiwoom.com","mockapi.kiwoom.com")
    def test_no_websocket_client_call(self): _assert_forbidden_absent(self,"websocket","websockets.connect")
    def test_no_oauth_or_token_access(self): _assert_forbidden_absent(self,"oauth","access_token","appsecret","secretkey")
    def test_no_dotenv_or_credential_access(self): _assert_forbidden_absent(self,"dotenv","getenv","environ[","credential")
    def test_no_external_network(self): _assert_forbidden_absent(self,"socket.","urlopen","invoke-webrequest","restclient")
    def test_no_account_access(self): _assert_forbidden_absent(self,"account_no","account_number","acnt_no")
    def test_no_order_or_kt10000_call(self): _assert_forbidden_absent(self,"kt10000","/api/dostk/ordr","post(")
    def test_no_consumption_ledger_mutation(self): _assert_forbidden_absent(self,"consumption_ledger","consumed.add","replay_ledger")


class Phase29CompatibilityBoundaryTests(unittest.TestCase):
    def test_phase28_public_api_unchanged(self): self.assertEqual(tuple(phase28.__all__),PHASE28_PUBLIC_API)
    def test_phase27_public_api_unchanged(self): self.assertEqual(tuple(phase27.__all__),PHASE27_PUBLIC_API)
    def test_phase26_public_api_unchanged(self): self.assertEqual(tuple(phase26.__all__),PHASE26_PUBLIC_API)
    def test_phase25_public_api_unchanged(self): self.assertEqual(tuple(phase25.__all__),PHASE25_PUBLIC_API)
    def test_attempt_prepared_does_not_imply_send_authorized(self):
        p=_phase28_preparation(); self.assertIs(p.decision,phase28.KiwoomOrderAttemptPreparationDecision.ATTEMPT_PREPARED); self.assertFalse(_build((p,)).authorizations[0].send_authorized)
    def test_validation_failure_precedes_decision(self):
        p=_phase28_preparation(); snap=replace(_phase28_snapshot((p,)),candidate_count=2); bad=replace(_authorization_context(p),authorization_state="bad")
        with self.assertRaisesRegex(subject.KiwoomOrderSendAuthorizationError,"candidate_count"):
            subject.build_watchlist_kiwoom_order_send_authorization_snapshot(snap,(bad,))
    def test_venue_capability_not_recomputed(self): _assert_forbidden_absent(self,"MarketVenue","venue_capability","dry_run_supported")
    def test_send_authorized_has_no_submission_or_consumption_semantics(self):
        p=_phase28_preparation(); item=_build((p,),(_authorization_context(p,authorized=True),)).authorizations[0]; self.assertTrue(item.send_authorized); _assert_forbidden_absent(self,"submit_order","send_order","consume_authorization","authorization_consumption_committed")


if __name__ == "__main__":
    unittest.main()
