from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import re

from .watchlist_order_send_request import WatchlistOrderSendRequestSnapshot

__all__ = [
    "WatchlistOrderAuthorizationConsumptionClaimError",
    "KiwoomOrderAuthorizationConsumptionClaimContext",
    "WatchlistOrderAuthorizationConsumptionClaimSnapshot",
    "build_demo_watchlist_order_authorization_consumption_claim_snapshot",
]


class WatchlistOrderAuthorizationConsumptionClaimError(RuntimeError):
    pass


@dataclass(frozen=True)
class KiwoomOrderAuthorizationConsumptionClaimContext:
    authorization_authority_reference: str
    authorization_evidence_snapshot_id: str
    submission_attempt_reference: str
    send_authorization_reference: str


@dataclass(frozen=True)
class WatchlistOrderAuthorizationConsumptionClaimSnapshot:
    source_snapshot: WatchlistOrderSendRequestSnapshot
    context: KiwoomOrderAuthorizationConsumptionClaimContext
    authorization_claim_identity: tuple[str, str, str, str]
    authorization_replay_guard: tuple[str, str]
    claim_fingerprint: str
    claim_prepared: bool
    authorization_consumption_committed: bool
    post_permitted: bool
    automatic_retry_permitted: bool
    network_performed: bool
    order_submitted: bool


_PROVIDER_BODY_KEYS = frozenset(
    {"dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"}
)
_LOWER_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def _raise(code: str) -> None:
    raise WatchlistOrderAuthorizationConsumptionClaimError(code)


def _is_binding_reference(value: object) -> bool:
    if type(value) is not str:
        return False
    if not 1 <= len(value) <= 128:
        return False
    if not value.strip():
        return False
    return not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _is_phase29_opaque_reference(value: object) -> bool:
    return type(value) is str and bool(value) and bool(value.strip())


def _source_structure_valid(source_snapshot: WatchlistOrderSendRequestSnapshot) -> bool:
    if source_snapshot.environment != "demo":
        return False
    if source_snapshot.side != "BUY":
        return False
    if source_snapshot.exchange != "KRX":
        return False
    if source_snapshot.api_id != "kt10000":
        return False
    if source_snapshot.http_method != "POST":
        return False
    if source_snapshot.api_path != "/api/dostk/ordr":
        return False

    body = source_snapshot.body
    if not isinstance(body, Mapping):
        return False
    if set(body.keys()) != _PROVIDER_BODY_KEYS:
        return False
    if any(type(key) is not str for key in body.keys()):
        return False
    if any(type(value) is not str for value in body.values()):
        return False
    if body["dmst_stex_tp"] != "KRX":
        return False
    if body["cond_uv"] != "":
        return False
    if body["trde_tp"] == "0":
        if body["ord_uv"] == "":
            return False
    elif body["trde_tp"] == "3":
        if body["ord_uv"] != "":
            return False
    else:
        return False

    if not _is_binding_reference(source_snapshot.source_attempt_ref):
        return False
    if not _is_binding_reference(source_snapshot.authorization_evidence_ref):
        return False
    if type(source_snapshot.materialization_fingerprint) is not str:
        return False
    if _LOWER_HEX_64.fullmatch(source_snapshot.materialization_fingerprint) is None:
        return False
    return True


def _source_safety_valid(source_snapshot: WatchlistOrderSendRequestSnapshot) -> bool:
    return all(
        value is False
        for value in (
            source_snapshot.transport_allowed,
            source_snapshot.credential_accessed,
            source_snapshot.network_performed,
            source_snapshot.account_accessed,
            source_snapshot.order_submitted,
        )
    )


def _expected_materialization_fingerprint(
    source_snapshot: WatchlistOrderSendRequestSnapshot,
) -> str:
    envelope = {
        "environment": source_snapshot.environment,
        "side": source_snapshot.side,
        "exchange": source_snapshot.exchange,
        "api_id": source_snapshot.api_id,
        "http_method": source_snapshot.http_method,
        "api_path": source_snapshot.api_path,
        "body": dict(source_snapshot.body),
        "source_attempt_ref": source_snapshot.source_attempt_ref,
        "authorization_evidence_ref": source_snapshot.authorization_evidence_ref,
    }
    canonical = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _claim_fingerprint(
    materialization_fingerprint: str,
    authorization_claim_identity: tuple[str, str, str, str],
    authorization_replay_guard: tuple[str, str],
) -> str:
    envelope = {
        "materialization_fingerprint": materialization_fingerprint,
        "authorization_claim_identity": authorization_claim_identity,
        "authorization_replay_guard": authorization_replay_guard,
    }
    canonical = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_demo_watchlist_order_authorization_consumption_claim_snapshot(
    source_snapshot: WatchlistOrderSendRequestSnapshot,
    context: KiwoomOrderAuthorizationConsumptionClaimContext,
) -> WatchlistOrderAuthorizationConsumptionClaimSnapshot:
    if type(source_snapshot) is not WatchlistOrderSendRequestSnapshot:
        _raise("SOURCE_SNAPSHOT_TYPE_INVALID")

    if not _source_structure_valid(source_snapshot):
        _raise("SOURCE_SNAPSHOT_STRUCTURE_INVALID")

    if not _source_safety_valid(source_snapshot):
        _raise("SOURCE_SNAPSHOT_SAFETY_INVALID")

    if source_snapshot.materialization_fingerprint != _expected_materialization_fingerprint(source_snapshot):
        _raise("SOURCE_MATERIALIZATION_FINGERPRINT_INVALID")

    if type(context) is not KiwoomOrderAuthorizationConsumptionClaimContext:
        _raise("CONTEXT_TYPE_INVALID")

    if not _is_phase29_opaque_reference(context.authorization_authority_reference):
        _raise("AUTHORIZATION_AUTHORITY_REFERENCE_INVALID")

    if not _is_binding_reference(context.authorization_evidence_snapshot_id):
        _raise("AUTHORIZATION_EVIDENCE_SNAPSHOT_ID_INVALID")

    if not _is_binding_reference(context.submission_attempt_reference):
        _raise("SUBMISSION_ATTEMPT_REFERENCE_INVALID")

    if not _is_phase29_opaque_reference(context.send_authorization_reference):
        _raise("SEND_AUTHORIZATION_REFERENCE_INVALID")

    if context.submission_attempt_reference != source_snapshot.source_attempt_ref:
        _raise("SUBMISSION_ATTEMPT_REFERENCE_MISMATCH")

    if context.authorization_evidence_snapshot_id != source_snapshot.authorization_evidence_ref:
        _raise("AUTHORIZATION_EVIDENCE_REFERENCE_MISMATCH")

    authorization_claim_identity = (
        context.authorization_authority_reference,
        context.authorization_evidence_snapshot_id,
        context.submission_attempt_reference,
        context.send_authorization_reference,
    )
    authorization_replay_guard = (
        context.authorization_authority_reference,
        context.send_authorization_reference,
    )
    claim_fingerprint = _claim_fingerprint(
        source_snapshot.materialization_fingerprint,
        authorization_claim_identity,
        authorization_replay_guard,
    )

    return WatchlistOrderAuthorizationConsumptionClaimSnapshot(
        source_snapshot=source_snapshot,
        context=context,
        authorization_claim_identity=authorization_claim_identity,
        authorization_replay_guard=authorization_replay_guard,
        claim_fingerprint=claim_fingerprint,
        claim_prepared=True,
        authorization_consumption_committed=False,
        post_permitted=False,
        automatic_retry_permitted=False,
        network_performed=False,
        order_submitted=False,
    )
