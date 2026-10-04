import asyncio as _asyncio
from abc import ABC as _ABC, abstractmethod as _abstractmethod
from collections.abc import Mapping as _Mapping
from dataclasses import dataclass as _dataclass, field as _field
from datetime import datetime as _datetime, timezone as _timezone
from enum import Enum as _Enum
import hashlib as _hashlib
import inspect as _inspect
import json as _json
import math as _math
import re as _re
from typing import Any as _Any

from . import watchlist_order_provider_send_execution_gate as _phase35


__all__ = (
    "WatchlistOrderProviderSubmissionBoundaryError",
    "KiwoomOrderProviderSubmissionOutcome",
    "Phase36SubmissionRegistryState",
    "Phase36SubmissionApprovalEvidence",
    "Phase36ProviderExecutionContext",
    "Phase36AtomicSubmissionRegistry",
    "KiwoomOrderProviderSubmissionReceipt",
    "submit_demo_watchlist_order_once",
)


class WatchlistOrderProviderSubmissionBoundaryError(RuntimeError):
    pass


class KiwoomOrderProviderSubmissionOutcome(str, _Enum):
    BLOCKED_BEFORE_SEND = "BLOCKED_BEFORE_SEND"
    CONFIRMED_ACCEPTED = "CONFIRMED_ACCEPTED"
    CONFIRMED_NOT_ACCEPTED = "CONFIRMED_NOT_ACCEPTED"
    AMBIGUOUS_UNRESOLVED = "AMBIGUOUS_UNRESOLVED"


class Phase36SubmissionRegistryState(str, _Enum):
    AVAILABLE = "AVAILABLE"
    CLAIMED_PRE_SEND = "CLAIMED_PRE_SEND"
    IN_FLIGHT = "IN_FLIGHT"
    ABORTED_BEFORE_SEND = "ABORTED_BEFORE_SEND"
    CONFIRMED_ACCEPTED = "CONFIRMED_ACCEPTED"
    CONFIRMED_NOT_ACCEPTED = "CONFIRMED_NOT_ACCEPTED"
    AMBIGUOUS_UNRESOLVED = "AMBIGUOUS_UNRESOLVED"


@_dataclass(frozen=True, slots=True)
class Phase36SubmissionApprovalEvidence:
    approval_id: str
    issued_at_utc: str
    not_before_utc: str
    expires_at_utc: str
    readiness_fingerprint: str
    request_fingerprint: str
    source_attempt_ref: str
    authorization_evidence_ref: str
    scope_fingerprint: str
    credential_ownership_evidence_fingerprint: str
    account_ownership_evidence_fingerprint: str
    one_shot_authorized: bool
    approval_fingerprint: str


class _KiwoomSdkLocalCredentialAccountResolver:
    def __init__(
        self,
        *,
        profile_alias: str,
        credential_ref_id: str,
        account_ref_id: str,
        credential_ownership_evidence_fingerprint: str,
        account_ownership_evidence_fingerprint: str,
        profile_loader: object | None = None,
        secret_provider: object | None = None,
        credential_fingerprint: object | None = None,
    ) -> None:
        if type(profile_alias) is not str or not profile_alias.strip():
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_PROFILE_ALIAS_INVALID"
            )
        if len(profile_alias.strip()) > 64:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_PROFILE_ALIAS_INVALID"
            )
        if type(credential_ref_id) is not str or not credential_ref_id.strip():
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CREDENTIAL_REF_INVALID"
            )
        if type(account_ref_id) is not str or not account_ref_id.strip():
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_ACCOUNT_REF_INVALID"
            )
        if (
            type(credential_ownership_evidence_fingerprint) is not str
            or _re.fullmatch(
                r"[0-9a-fA-F]{64}",
                credential_ownership_evidence_fingerprint,
            )
            is None
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CREDENTIAL_FINGERPRINT_INVALID"
            )
        if (
            type(account_ownership_evidence_fingerprint) is not str
            or _re.fullmatch(
                r"[0-9a-fA-F]{64}",
                account_ownership_evidence_fingerprint,
            )
            is None
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_ACCOUNT_FINGERPRINT_INVALID"
            )

        self._profile_alias = profile_alias.strip()
        self._credential_ref_id = credential_ref_id
        self._account_ref_id = account_ref_id
        self._credential_ownership_evidence_fingerprint = (
            credential_ownership_evidence_fingerprint
        )
        self._account_ownership_evidence_fingerprint = (
            account_ownership_evidence_fingerprint
        )

        if (
            profile_loader is None
            or secret_provider is None
            or credential_fingerprint is None
        ):
            try:
                from kiwoom.core.auth import KiwoomAuth as _KiwoomAuth
                from kiwoom.core.profiles import get_profile as _get_profile
                from kiwoom.core.secrets import (
                    default_secret_provider as _default_secret_provider,
                )
            except Exception as exc:
                raise WatchlistOrderProviderSubmissionBoundaryError(
                    "STAGE7_KIWOOM_SDK_UNAVAILABLE"
                ) from exc

            if profile_loader is None:
                profile_loader = _get_profile
            if secret_provider is None:
                secret_provider = _default_secret_provider(
                    profile=self._profile_alias,
                )
            if credential_fingerprint is None:
                credential_fingerprint = _KiwoomAuth._credential_fingerprint

        self._profile_loader = profile_loader
        self._secret_provider = secret_provider
        self._credential_fingerprint = credential_fingerprint

    def __repr__(self) -> str:
        return (
            "_KiwoomSdkLocalCredentialAccountResolver("
            "secret_safe=True)"
        )

    async def resolve(
        self,
        *,
        credential_ref_id: str,
        account_ref_id: str,
    ) -> dict[str, str]:
        if (
            credential_ref_id != self._credential_ref_id
            or account_ref_id != self._account_ref_id
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_REFERENCE_BINDING_MISMATCH"
            )

        try:
            profile = self._profile_loader(self._profile_alias)
        except Exception as exc:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_LOCAL_PROFILE_RESOLUTION_FAILED"
            ) from exc

        if (
            getattr(profile, "alias", None) != self._profile_alias
            or getattr(profile, "mode", None) != "demo"
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_DEMO_PROFILE_BINDING_MISMATCH"
            )

        try:
            credentials = self._secret_provider.get_credentials("demo")
        except Exception as exc:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_LOCAL_CREDENTIAL_READ_FAILED"
            ) from exc

        if credentials is None:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_LOCAL_CREDENTIALS_MISSING"
            )

        try:
            actual_fingerprint = self._credential_fingerprint(credentials)
        except Exception as exc:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CREDENTIAL_FINGERPRINT_FAILED"
            ) from exc

        if (
            type(actual_fingerprint) is not str
            or actual_fingerprint
            != self._credential_ownership_evidence_fingerprint
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CREDENTIAL_OWNERSHIP_MISMATCH"
            )

        return {
            "mode": "demo",
            "credential_ref_id": self._credential_ref_id,
            "account_ref_id": self._account_ref_id,
            "credential_ownership_evidence_fingerprint":
                self._credential_ownership_evidence_fingerprint,
            "account_ownership_evidence_fingerprint":
                self._account_ownership_evidence_fingerprint,
        }


class _KiwoomSdkCachedTokenProvider:
    def __init__(
        self,
        *,
        profile_alias: str,
        token_store: object | None = None,
        now_utc: object | None = None,
        minimum_validity_seconds: float = 600.0,
    ) -> None:
        if type(profile_alias) is not str or not profile_alias.strip():
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_PROFILE_ALIAS_INVALID"
            )
        if len(profile_alias.strip()) > 64:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_PROFILE_ALIAS_INVALID"
            )
        if (
            isinstance(minimum_validity_seconds, bool)
            or not isinstance(minimum_validity_seconds, (int, float))
            or not _math.isfinite(float(minimum_validity_seconds))
            or float(minimum_validity_seconds) < 0.0
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_TOKEN_MINIMUM_VALIDITY_INVALID"
            )

        self._profile_alias = profile_alias.strip()
        self._minimum_validity_seconds = float(
            minimum_validity_seconds
        )

        if token_store is None:
            try:
                from kiwoom.core.token_store import (
                    FileTokenStore as _FileTokenStore,
                )
            except Exception as exc:
                raise WatchlistOrderProviderSubmissionBoundaryError(
                    "STAGE7_KIWOOM_SDK_UNAVAILABLE"
                ) from exc

            token_store = _FileTokenStore()

        self._token_store = token_store
        self._now_utc = (
            now_utc
            if now_utc is not None
            else lambda: _datetime.now(_timezone.utc)
        )

    def __repr__(self) -> str:
        return "_KiwoomSdkCachedTokenProvider(secret_safe=True)"

    async def acquire(
        self,
        *,
        resolved: object,
    ) -> dict[str, str]:
        expected_keys = {
            "mode",
            "credential_ref_id",
            "account_ref_id",
            "credential_ownership_evidence_fingerprint",
            "account_ownership_evidence_fingerprint",
        }

        if not isinstance(resolved, _Mapping):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_RESOLVED_BINDING_INVALID"
            )

        try:
            if set(resolved.keys()) != expected_keys:
                raise WatchlistOrderProviderSubmissionBoundaryError(
                    "STAGE7_RESOLVED_BINDING_INVALID"
                )

            mode = resolved["mode"]
            credential_ref_id = resolved["credential_ref_id"]
            account_ref_id = resolved["account_ref_id"]
            credential_fingerprint = (
                resolved[
                    "credential_ownership_evidence_fingerprint"
                ]
            )
            account_fingerprint = (
                resolved[
                    "account_ownership_evidence_fingerprint"
                ]
            )
        except (KeyError, TypeError) as exc:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_RESOLVED_BINDING_INVALID"
            ) from exc

        if mode != "demo":
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_RESOLVED_MODE_NOT_DEMO"
            )

        for value, code in (
            (
                credential_ref_id,
                "STAGE7_CREDENTIAL_REF_INVALID",
            ),
            (
                account_ref_id,
                "STAGE7_ACCOUNT_REF_INVALID",
            ),
        ):
            if type(value) is not str or not value.strip():
                raise WatchlistOrderProviderSubmissionBoundaryError(code)

        for value, code in (
            (
                credential_fingerprint,
                "STAGE7_CREDENTIAL_FINGERPRINT_INVALID",
            ),
            (
                account_fingerprint,
                "STAGE7_ACCOUNT_FINGERPRINT_INVALID",
            ),
        ):
            if (
                type(value) is not str
                or _re.fullmatch(r"[0-9a-fA-F]{64}", value) is None
            ):
                raise WatchlistOrderProviderSubmissionBoundaryError(code)

        try:
            record = self._token_store.peek(
                "demo",
                profile=self._profile_alias,
            )
        except Exception as exc:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CACHED_TOKEN_READ_FAILED"
            ) from exc

        if record is None:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CACHED_TOKEN_MISSING"
            )

        if (
            getattr(record, "mode", None) != "demo"
            or getattr(record, "profile", None) != self._profile_alias
            or getattr(record, "credential_fingerprint", None)
            != credential_fingerprint
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CACHED_TOKEN_BINDING_MISMATCH"
            )

        token_type = getattr(record, "token_type", None)
        token = getattr(record, "access_token", None)

        if (
            type(token_type) is not str
            or token_type.lower() != "bearer"
            or type(token) is not str
            or not token
            or token != token.strip()
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CACHED_TOKEN_INVALID"
            )

        expires_at = getattr(record, "expires_at", None)

        try:
            now = self._now_utc()
        except Exception as exc:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CLOCK_FAILED"
            ) from exc

        if (
            not isinstance(expires_at, _datetime)
            or expires_at.tzinfo is None
            or not isinstance(now, _datetime)
            or now.tzinfo is None
        ):
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CACHED_TOKEN_EXPIRY_INVALID"
            )

        remaining_seconds = (
            expires_at.astimezone(_timezone.utc)
            - now.astimezone(_timezone.utc)
        ).total_seconds()

        if remaining_seconds <= self._minimum_validity_seconds:
            raise WatchlistOrderProviderSubmissionBoundaryError(
                "STAGE7_CACHED_TOKEN_NOT_REUSABLE"
            )

        return {
            "token": token,
            "mode": "demo",
            "credential_ref_id": credential_ref_id,
            "account_ref_id": account_ref_id,
            "credential_ownership_evidence_fingerprint":
                credential_fingerprint,
            "account_ownership_evidence_fingerprint":
                account_fingerprint,
        }


@_dataclass(frozen=True, slots=True)
class Phase36ProviderExecutionContext:
    mode: str
    base_url: str
    credential_ref_id: str
    account_ref_id: str
    credential_ownership_evidence_fingerprint: str
    account_ownership_evidence_fingerprint: str
    runtime_credential_account_access_authorized: bool
    auth_network_authorized: bool
    provider_network_authorized: bool
    actual_kt10000_post_authorized: bool
    test_execution: bool
    timeout_seconds: float
    resolver: object = _field(repr=False)
    token_provider: object = _field(repr=False)
    readiness_revalidator: object = _field(repr=False)
    transport: object = _field(repr=False)
    cleanup: object = _field(repr=False)
    clock: object = _field(repr=False)


class Phase36AtomicSubmissionRegistry(_ABC):
    @property
    @_abstractmethod
    def is_durable(self) -> bool:
        raise NotImplementedError

    @property
    @_abstractmethod
    def test_only(self) -> bool:
        raise NotImplementedError

    @_abstractmethod
    async def claim(
        self,
        *,
        attempt_fingerprint: str,
        claim_fingerprint: str,
    ) -> bool:
        raise NotImplementedError

    @_abstractmethod
    async def compare_and_set(
        self,
        *,
        attempt_fingerprint: str,
        expected_state: Phase36SubmissionRegistryState,
        new_state: Phase36SubmissionRegistryState,
    ) -> bool:
        raise NotImplementedError

    @_abstractmethod
    async def finalize(
        self,
        *,
        attempt_fingerprint: str,
        expected_state: Phase36SubmissionRegistryState,
        terminal_state: Phase36SubmissionRegistryState,
        receipt: "KiwoomOrderProviderSubmissionReceipt",
    ) -> bool:
        raise NotImplementedError


@_dataclass(frozen=True, slots=True)
class KiwoomOrderProviderSubmissionReceipt:
    attempt_fingerprint: str
    request_fingerprint: str
    readiness_fingerprint: str
    submission_approval_fingerprint: str
    claim_fingerprint: str | None
    mode: str
    endpoint_identity: str
    api_id: str
    normalized_return_code: int | None
    provider_return_msg: str | None
    provider_order_no: str | None
    provider_exchange: str | None
    outcome: KiwoomOrderProviderSubmissionOutcome
    registry_terminal_state: Phase36SubmissionRegistryState | None
    transport_attempt_count: int
    started_at_utc: str
    completed_at_utc: str
    credential_provenance_fingerprint: str | None
    account_provenance_fingerprint: str | None


_DEMO_BASE_URL = "https://mockapi.kiwoom.com"
_API_ID = "kt10000"
_API_PATH = "/api/dostk/ordr"
_ENDPOINT_IDENTITY = _DEMO_BASE_URL + _API_PATH
_CONTENT_TYPE = "application/json;charset=UTF-8"
_PROVIDER_BODY_KEYS = frozenset(
    {"dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"}
)
_HEX64 = _re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_TRANSITIONS = frozenset(
    {
        (
            Phase36SubmissionRegistryState.AVAILABLE,
            Phase36SubmissionRegistryState.CLAIMED_PRE_SEND,
        ),
        (
            Phase36SubmissionRegistryState.CLAIMED_PRE_SEND,
            Phase36SubmissionRegistryState.IN_FLIGHT,
        ),
        (
            Phase36SubmissionRegistryState.CLAIMED_PRE_SEND,
            Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,
        ),
        (
            Phase36SubmissionRegistryState.IN_FLIGHT,
            Phase36SubmissionRegistryState.CONFIRMED_ACCEPTED,
        ),
        (
            Phase36SubmissionRegistryState.IN_FLIGHT,
            Phase36SubmissionRegistryState.CONFIRMED_NOT_ACCEPTED,
        ),
        (
            Phase36SubmissionRegistryState.IN_FLIGHT,
            Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
        ),
    }
)


def _raise(code: str) -> None:
    raise WatchlistOrderProviderSubmissionBoundaryError(code)


def _canonical_sha256(envelope: dict[str, object]) -> str:
    raw = _json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return _hashlib.sha256(raw).hexdigest()


def _is_exact_str(value: object) -> bool:
    return type(value) is str


def _is_nonblank_str(value: object, *, max_length: int = 256) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= max_length
        and bool(value.strip())
        and value == value.strip()
        and not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    )


def _is_hex64(value: object) -> bool:
    return type(value) is str and _HEX64.fullmatch(value) is not None


def _parse_utc(value: object) -> _datetime | None:
    if type(value) is not str or not value.endswith("Z"):
        return None
    try:
        parsed = _datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(_timezone.utc)


def _utc_text(value: _datetime) -> str:
    if type(value) is not _datetime or value.tzinfo is None:
        _raise("CLOCK_VALUE_INVALID")
    value = value.astimezone(_timezone.utc)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _now(context: Phase36ProviderExecutionContext) -> _datetime:
    clock = context.clock
    if not callable(clock):
        _raise("CLOCK_SURFACE_INVALID")
    value = clock()
    if _inspect.isawaitable(value):
        _raise("CLOCK_MUST_BE_SYNCHRONOUS")
    if type(value) is not _datetime or value.tzinfo is None:
        _raise("CLOCK_VALUE_INVALID")
    return value.astimezone(_timezone.utc)


def _request_snapshot(readiness_snapshot: object) -> object | None:
    try:
        source = readiness_snapshot.source_snapshot
        request = source.request_snapshot
    except AttributeError:
        return None
    return request


def _request_body_copy(request: object) -> dict[str, str] | None:
    try:
        body = request.body
    except AttributeError:
        return None
    if not isinstance(body, _Mapping):
        return None
    try:
        keys = tuple(body.keys())
        values = tuple(body.values())
        if set(keys) != _PROVIDER_BODY_KEYS:
            return None
        if any(type(k) is not str for k in keys):
            return None
        if any(type(v) is not str for v in values):
            return None
        copied = {k: body[k] for k in _PROVIDER_BODY_KEYS}
    except (AttributeError, KeyError, TypeError):
        return None
    return copied


def _request_materialization_fingerprint(request: object, body: dict[str, str]) -> str | None:
    try:
        envelope = {
            "environment": request.environment,
            "side": request.side,
            "exchange": request.exchange,
            "api_id": request.api_id,
            "http_method": request.http_method,
            "api_path": request.api_path,
            "body": body,
            "source_attempt_ref": request.source_attempt_ref,
            "authorization_evidence_ref": request.authorization_evidence_ref,
        }
    except AttributeError:
        return None
    if not all(type(v) is str for k, v in envelope.items() if k != "body"):
        return None
    return _canonical_sha256(envelope)


def _phase35_ready_valid(readiness_snapshot: object) -> tuple[bool, dict[str, str] | None]:
    if type(readiness_snapshot) is not _phase35.WatchlistOrderProviderSendExecutionReadinessSnapshot:
        return False, None
    if (
        type(readiness_snapshot.decision)
        is not _phase35.KiwoomOrderProviderSendExecutionReadinessDecision
    ):
        return False, None
    if (
        readiness_snapshot.decision
        is not _phase35.KiwoomOrderProviderSendExecutionReadinessDecision.PROVIDER_SEND_EXECUTION_READY
    ):
        return False, None
    if readiness_snapshot.primary_reason_code is not None:
        return False, None
    if readiness_snapshot.all_reason_codes != ():
        return False, None
    if readiness_snapshot.provider_send_execution_ready is not True:
        return False, None
    if readiness_snapshot.reconciliation_required is not False:
        return False, None
    for value in (
        readiness_snapshot.transport_authorized,
        readiness_snapshot.provider_call_performed,
        readiness_snapshot.actual_kt10000_post_performed,
        readiness_snapshot.credential_lookup_performed,
        readiness_snapshot.account_lookup_performed,
        readiness_snapshot.token_acquisition_performed,
        readiness_snapshot.automatic_retry_permitted,
        readiness_snapshot.retransmission_permitted,
    ):
        if type(value) is not bool or value is not False:
            return False, None
    if not _is_hex64(readiness_snapshot.readiness_fingerprint):
        return False, None
    try:
        expected_readiness = _phase35._readiness_fingerprint(readiness_snapshot)
    except BaseException:
        return False, None
    if readiness_snapshot.readiness_fingerprint != expected_readiness:
        return False, None
    request = _request_snapshot(readiness_snapshot)
    if request is None:
        return False, None
    body = _request_body_copy(request)
    if body is None:
        return False, None
    try:
        if (
            request.environment != "demo"
            or request.side != "BUY"
            or request.exchange != "KRX"
            or request.api_id != _API_ID
            or request.http_method != "POST"
            or request.api_path != _API_PATH
        ):
            return False, None
        if body["dmst_stex_tp"] != "KRX":
            return False, None
        if body["cond_uv"] != "":
            return False, None
        if body["trde_tp"] == "0":
            if not body["ord_uv"]:
                return False, None
        elif body["trde_tp"] == "3":
            if body["ord_uv"] != "":
                return False, None
        else:
            return False, None
        if not body["stk_cd"].strip():
            return False, None
        if not body["ord_qty"].isdigit() or int(body["ord_qty"]) <= 0:
            return False, None
        materialized = _request_materialization_fingerprint(request, body)
        if materialized is None or request.materialization_fingerprint != materialized:
            return False, None
        if readiness_snapshot.phase30_materialization_fingerprint != materialized:
            return False, None
        if readiness_snapshot.source_attempt_ref != request.source_attempt_ref:
            return False, None
        if readiness_snapshot.authorization_evidence_ref != request.authorization_evidence_ref:
            return False, None
        prior = readiness_snapshot.prior_submission_state
        if prior is not None:
            prior_value = getattr(prior, "value", prior)
            if prior_value in {"CONFIRMED_ACCEPTED", "AMBIGUOUS_UNRESOLVED"}:
                return False, None
    except (AttributeError, TypeError, ValueError):
        return False, None
    return True, body


def _approval_fingerprint(evidence: Phase36SubmissionApprovalEvidence) -> str:
    return _canonical_sha256(
        {
            "domain": "phase36-one-shot-submission-approval-v1",
            "approval_id": evidence.approval_id,
            "issued_at_utc": evidence.issued_at_utc,
            "not_before_utc": evidence.not_before_utc,
            "expires_at_utc": evidence.expires_at_utc,
            "readiness_fingerprint": evidence.readiness_fingerprint,
            "request_fingerprint": evidence.request_fingerprint,
            "source_attempt_ref": evidence.source_attempt_ref,
            "authorization_evidence_ref": evidence.authorization_evidence_ref,
            "scope_fingerprint": evidence.scope_fingerprint,
            "credential_ownership_evidence_fingerprint":
                evidence.credential_ownership_evidence_fingerprint,
            "account_ownership_evidence_fingerprint":
                evidence.account_ownership_evidence_fingerprint,
            "one_shot_authorized": evidence.one_shot_authorized,
        }
    )


def _approval_valid(
    readiness_snapshot: _phase35.WatchlistOrderProviderSendExecutionReadinessSnapshot,
    evidence: object,
    now: _datetime,
) -> bool:
    if type(evidence) is not Phase36SubmissionApprovalEvidence:
        return False
    if not _is_nonblank_str(evidence.approval_id, max_length=128):
        return False
    issued = _parse_utc(evidence.issued_at_utc)
    not_before = _parse_utc(evidence.not_before_utc)
    expires = _parse_utc(evidence.expires_at_utc)
    if issued is None or not_before is None or expires is None:
        return False
    if not (issued <= not_before <= expires):
        return False
    if now < not_before or now >= expires:
        return False
    if evidence.one_shot_authorized is not True:
        return False
    request = _request_snapshot(readiness_snapshot)
    if request is None:
        return False
    expected_pairs = (
        (evidence.readiness_fingerprint, readiness_snapshot.readiness_fingerprint),
        (evidence.request_fingerprint, readiness_snapshot.phase30_materialization_fingerprint),
        (evidence.source_attempt_ref, readiness_snapshot.source_attempt_ref),
        (evidence.authorization_evidence_ref, readiness_snapshot.authorization_evidence_ref),
        (evidence.scope_fingerprint, readiness_snapshot.scope_fingerprint),
        (
            evidence.credential_ownership_evidence_fingerprint,
            readiness_snapshot.credential_ownership_evidence_fingerprint,
        ),
        (
            evidence.account_ownership_evidence_fingerprint,
            readiness_snapshot.account_ownership_evidence_fingerprint,
        ),
    )
    for actual, expected in expected_pairs:
        if type(actual) is not str or actual != expected:
            return False
    for fp in (
        evidence.readiness_fingerprint,
        evidence.request_fingerprint,
        evidence.scope_fingerprint,
        evidence.credential_ownership_evidence_fingerprint,
        evidence.account_ownership_evidence_fingerprint,
        evidence.approval_fingerprint,
    ):
        if not _is_hex64(fp):
            return False
    return evidence.approval_fingerprint == _approval_fingerprint(evidence)


def _context_local_valid(
    readiness_snapshot: _phase35.WatchlistOrderProviderSendExecutionReadinessSnapshot,
    context: object,
) -> bool:
    if type(context) is not Phase36ProviderExecutionContext:
        return False
    if context.mode != "demo" or context.base_url.rstrip("/") != _DEMO_BASE_URL:
        return False
    if not _is_nonblank_str(context.credential_ref_id, max_length=128):
        return False
    if not _is_nonblank_str(context.account_ref_id, max_length=128):
        return False
    if not _is_hex64(context.credential_ownership_evidence_fingerprint):
        return False
    if not _is_hex64(context.account_ownership_evidence_fingerprint):
        return False
    if (
        context.credential_ownership_evidence_fingerprint
        != readiness_snapshot.credential_ownership_evidence_fingerprint
    ):
        return False
    if (
        context.account_ownership_evidence_fingerprint
        != readiness_snapshot.account_ownership_evidence_fingerprint
    ):
        return False
    for value in (
        context.runtime_credential_account_access_authorized,
        context.auth_network_authorized,
        context.provider_network_authorized,
        context.actual_kt10000_post_authorized,
        context.test_execution,
    ):
        if type(value) is not bool:
            return False
    if not (
        context.runtime_credential_account_access_authorized
        and context.auth_network_authorized
        and context.provider_network_authorized
        and context.actual_kt10000_post_authorized
    ):
        return False
    if (
        isinstance(context.timeout_seconds, bool)
        or not isinstance(context.timeout_seconds, (int, float))
        or not _math.isfinite(float(context.timeout_seconds))
        or float(context.timeout_seconds) <= 0.0
    ):
        return False
    return True


def _registry_valid(
    registry: object,
    context: Phase36ProviderExecutionContext,
) -> bool:
    if not isinstance(registry, Phase36AtomicSubmissionRegistry):
        return False
    try:
        durable = registry.is_durable
        test_only = registry.test_only
    except BaseException:
        return False
    if type(durable) is not bool or type(test_only) is not bool:
        return False
    if context.test_execution:
        return True
    return durable is True and test_only is False


async def _invoke_method(target: object, method_name: str, /, **kwargs: object) -> object:
    try:
        method = getattr(target, method_name)
    except AttributeError:
        _raise(f"{method_name.upper()}_SURFACE_INVALID")
    if not callable(method):
        _raise(f"{method_name.upper()}_SURFACE_INVALID")
    result = method(**kwargs)
    if _inspect.isawaitable(result):
        return await result
    return result


def _resolved_binding_valid(
    resolved: object,
    context: Phase36ProviderExecutionContext,
) -> bool:
    if not isinstance(resolved, _Mapping):
        return False
    expected_keys = {
        "mode",
        "credential_ref_id",
        "account_ref_id",
        "credential_ownership_evidence_fingerprint",
        "account_ownership_evidence_fingerprint",
    }
    try:
        if set(resolved.keys()) != expected_keys:
            return False
        return (
            resolved["mode"] == "demo"
            and resolved["credential_ref_id"] == context.credential_ref_id
            and resolved["account_ref_id"] == context.account_ref_id
            and resolved["credential_ownership_evidence_fingerprint"]
            == context.credential_ownership_evidence_fingerprint
            and resolved["account_ownership_evidence_fingerprint"]
            == context.account_ownership_evidence_fingerprint
        )
    except (KeyError, TypeError):
        return False


def _token_binding_valid(
    token_material: object,
    context: Phase36ProviderExecutionContext,
) -> tuple[bool, str | None, dict[str, str] | None]:
    if not isinstance(token_material, _Mapping):
        return False, None, None
    expected_keys = {
        "token",
        "mode",
        "credential_ref_id",
        "account_ref_id",
        "credential_ownership_evidence_fingerprint",
        "account_ownership_evidence_fingerprint",
    }
    try:
        if set(token_material.keys()) != expected_keys:
            return False, None, None
        token = token_material["token"]
        if type(token) is not str or not token.strip():
            return False, None, None
        metadata = {
            "mode": token_material["mode"],
            "credential_ref_id": token_material["credential_ref_id"],
            "account_ref_id": token_material["account_ref_id"],
            "credential_ownership_evidence_fingerprint":
                token_material["credential_ownership_evidence_fingerprint"],
            "account_ownership_evidence_fingerprint":
                token_material["account_ownership_evidence_fingerprint"],
        }
        if not _resolved_binding_valid(metadata, context):
            return False, None, None
        return True, token, metadata
    except (KeyError, TypeError):
        return False, None, None


def _attempt_fingerprint(
    readiness_snapshot: _phase35.WatchlistOrderProviderSendExecutionReadinessSnapshot,
    approval: Phase36SubmissionApprovalEvidence,
    context: Phase36ProviderExecutionContext,
) -> str:
    return _canonical_sha256(
        {
            "domain": "phase36-provider-submission-attempt-v1",
            "readiness_fingerprint": readiness_snapshot.readiness_fingerprint,
            "approval_fingerprint": approval.approval_fingerprint,
            "request_fingerprint": readiness_snapshot.phase30_materialization_fingerprint,
            "source_attempt_ref": readiness_snapshot.source_attempt_ref,
            "authorization_evidence_ref": readiness_snapshot.authorization_evidence_ref,
            "credential_ref_id": context.credential_ref_id,
            "account_ref_id": context.account_ref_id,
        }
    )


def _claim_fingerprint(
    attempt_fingerprint: str,
    approval: Phase36SubmissionApprovalEvidence,
) -> str:
    return _canonical_sha256(
        {
            "domain": "phase36-provider-submission-claim-v1",
            "attempt_fingerprint": attempt_fingerprint,
            "approval_fingerprint": approval.approval_fingerprint,
            "one_shot_authorized": approval.one_shot_authorized,
        }
    )


def _normalize_return_code(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if type(value) is int:
        return value
    if type(value) is str:
        text = value.strip()
        if not text:
            return None
        try:
            return int(text, 10)
        except ValueError:
            return None
    return None


def _optional_nonblank(value: object) -> str | None:
    if type(value) is not str:
        return None
    text = value.strip()
    return text if text else None


def _sanitize_message(value: object, *, secret_values: tuple[str, ...]) -> str | None:
    if value is None:
        return None
    text = str(value)
    text = _re.sub(r"(?i)bearer\s+[^\s,;]+", "Bearer [REDACTED]", text)
    text = _re.sub(r"(?i)\b(token|secret|app[_ -]?key)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", text)
    for secret in secret_values:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = "".join(ch if 32 <= ord(ch) != 127 else " " for ch in text)
    text = " ".join(text.split())
    if not text:
        return None
    return text[:256]


def _extract_response(response: object) -> tuple[int | None, object]:
    if isinstance(response, _Mapping):
        status = response.get("status_code")
        body = response.get("body")
    else:
        status = getattr(response, "status_code", None)
        body = getattr(response, "body", None)
    if isinstance(status, bool) or (status is not None and type(status) is not int):
        status = None
    return status, body


def _classify_response(
    response: object,
    *,
    token: str,
) -> tuple[
    KiwoomOrderProviderSubmissionOutcome,
    Phase36SubmissionRegistryState,
    int | None,
    str | None,
    str | None,
    str | None,
]:
    _status, body = _extract_response(response)
    if not isinstance(body, _Mapping):
        return (
            KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
            Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
            None,
            None,
            None,
            None,
        )
    try:
        return_code_raw = body.get("return_code")
        return_msg_raw = body.get("return_msg")
        order_no = _optional_nonblank(body.get("ord_no"))
        exchange = _optional_nonblank(body.get("dmst_stex_tp"))
    except (AttributeError, TypeError):
        return (
            KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
            Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
            None,
            None,
            None,
            None,
        )
    normalized = _normalize_return_code(return_code_raw)
    message = _sanitize_message(return_msg_raw, secret_values=(token,))
    if exchange is not None and exchange != "KRX":
        return (
            KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
            Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
            normalized,
            message,
            order_no,
            exchange,
        )
    if normalized == 0 and order_no is not None:
        return (
            KiwoomOrderProviderSubmissionOutcome.CONFIRMED_ACCEPTED,
            Phase36SubmissionRegistryState.CONFIRMED_ACCEPTED,
            normalized,
            message,
            order_no,
            exchange,
        )
    if normalized is not None and normalized != 0 and order_no is None:
        return (
            KiwoomOrderProviderSubmissionOutcome.CONFIRMED_NOT_ACCEPTED,
            Phase36SubmissionRegistryState.CONFIRMED_NOT_ACCEPTED,
            normalized,
            message,
            None,
            exchange,
        )
    return (
        KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
        Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
        normalized,
        message,
        order_no,
        exchange,
    )


def _receipt(
    *,
    attempt_fingerprint: str,
    request_fingerprint: str,
    readiness_fingerprint: str,
    approval_fingerprint: str,
    claim_fingerprint: str | None,
    outcome: KiwoomOrderProviderSubmissionOutcome,
    terminal_state: Phase36SubmissionRegistryState | None,
    transport_attempt_count: int,
    started_at_utc: str,
    completed_at_utc: str,
    normalized_return_code: int | None = None,
    provider_return_msg: str | None = None,
    provider_order_no: str | None = None,
    provider_exchange: str | None = None,
    credential_provenance_fingerprint: str | None = None,
    account_provenance_fingerprint: str | None = None,
) -> KiwoomOrderProviderSubmissionReceipt:
    return KiwoomOrderProviderSubmissionReceipt(
        attempt_fingerprint=attempt_fingerprint,
        request_fingerprint=request_fingerprint,
        readiness_fingerprint=readiness_fingerprint,
        submission_approval_fingerprint=approval_fingerprint,
        claim_fingerprint=claim_fingerprint,
        mode="demo",
        endpoint_identity=_ENDPOINT_IDENTITY,
        api_id=_API_ID,
        normalized_return_code=normalized_return_code,
        provider_return_msg=provider_return_msg,
        provider_order_no=provider_order_no,
        provider_exchange=provider_exchange,
        outcome=outcome,
        registry_terminal_state=terminal_state,
        transport_attempt_count=transport_attempt_count,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        credential_provenance_fingerprint=credential_provenance_fingerprint,
        account_provenance_fingerprint=account_provenance_fingerprint,
    )


async def _cleanup_best_effort(context: Phase36ProviderExecutionContext) -> None:
    target = context.cleanup
    try:
        method = getattr(target, "cleanup")
    except AttributeError:
        return
    if not callable(method):
        return
    try:
        result = method()
        if _inspect.isawaitable(result):
            await result
    except _asyncio.CancelledError:
        raise
    except BaseException:
        return


async def _best_effort_transition(
    registry: Phase36AtomicSubmissionRegistry,
    *,
    attempt_fingerprint: str,
    expected_state: Phase36SubmissionRegistryState,
    new_state: Phase36SubmissionRegistryState,
) -> bool:
    if (expected_state, new_state) not in _ALLOWED_TRANSITIONS:
        return False
    try:
        result = await registry.compare_and_set(
            attempt_fingerprint=attempt_fingerprint,
            expected_state=expected_state,
            new_state=new_state,
        )
    except BaseException:
        return False
    return result is True


async def _best_effort_finalize(
    registry: Phase36AtomicSubmissionRegistry,
    *,
    attempt_fingerprint: str,
    expected_state: Phase36SubmissionRegistryState,
    terminal_state: Phase36SubmissionRegistryState,
    receipt: KiwoomOrderProviderSubmissionReceipt,
) -> bool:
    if (expected_state, terminal_state) not in _ALLOWED_TRANSITIONS:
        return False
    try:
        result = await registry.finalize(
            attempt_fingerprint=attempt_fingerprint,
            expected_state=expected_state,
            terminal_state=terminal_state,
            receipt=receipt,
        )
    except BaseException:
        return False
    return result is True


async def submit_demo_watchlist_order_once(
    readiness_snapshot,
    submission_approval,
    execution_context,
    submission_registry,
):
    started_fallback = _datetime.now(_timezone.utc)
    context_for_cleanup = (
        execution_context
        if type(execution_context) is Phase36ProviderExecutionContext
        else None
    )
    in_flight = False
    claimed = False
    transport_attempt_count = 0
    attempt_fingerprint = "0" * 64
    claim_fingerprint: str | None = None
    request_fingerprint = (
        getattr(readiness_snapshot, "phase30_materialization_fingerprint", None)
        if readiness_snapshot is not None
        else None
    )
    readiness_fingerprint = (
        getattr(readiness_snapshot, "readiness_fingerprint", None)
        if readiness_snapshot is not None
        else None
    )
    approval_fingerprint = (
        getattr(submission_approval, "approval_fingerprint", None)
        if submission_approval is not None
        else None
    )
    if not _is_hex64(request_fingerprint):
        request_fingerprint = "0" * 64
    if not _is_hex64(readiness_fingerprint):
        readiness_fingerprint = "0" * 64
    if not _is_hex64(approval_fingerprint):
        approval_fingerprint = "0" * 64
    started_at_utc = _utc_text(started_fallback)

    try:
        ready_valid, body = _phase35_ready_valid(readiness_snapshot)
        if not ready_valid or body is None:
            completed = _utc_text(_datetime.now(_timezone.utc))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=request_fingerprint,
                readiness_fingerprint=readiness_fingerprint,
                approval_fingerprint=approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        if type(execution_context) is not Phase36ProviderExecutionContext:
            completed = _utc_text(_datetime.now(_timezone.utc))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=request_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        now = _now(execution_context)
        started_at_utc = _utc_text(now)
        if not _approval_valid(readiness_snapshot, submission_approval, now):
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        if not _context_local_valid(readiness_snapshot, execution_context):
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        if not _registry_valid(submission_registry, execution_context):
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        try:
            resolved = await _invoke_method(
                execution_context.resolver,
                "resolve",
                credential_ref_id=execution_context.credential_ref_id,
                account_ref_id=execution_context.account_ref_id,
            )
        except _asyncio.CancelledError:
            raise
        except BaseException:
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )
        if not _resolved_binding_valid(resolved, execution_context):
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        try:
            token_material = await _invoke_method(
                execution_context.token_provider,
                "acquire",
                resolved=resolved,
            )
        except _asyncio.CancelledError:
            raise
        except BaseException:
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        token_valid, token, token_metadata = _token_binding_valid(
            token_material,
            execution_context,
        )
        if not token_valid or token is None or token_metadata is None:
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        ready_valid_after, body_after = _phase35_ready_valid(readiness_snapshot)
        if not ready_valid_after or body_after != body:
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
            )

        revalidated = await _invoke_method(
            execution_context.readiness_revalidator,
            "validate",
            readiness_snapshot=readiness_snapshot,
            resolved=resolved,
            token_metadata=token_metadata,
            now_utc=_now(execution_context),
        )
        if revalidated is not True:
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
                credential_provenance_fingerprint=
                    execution_context.credential_ownership_evidence_fingerprint,
                account_provenance_fingerprint=
                    execution_context.account_ownership_evidence_fingerprint,
            )

        if not _approval_valid(
            readiness_snapshot,
            submission_approval,
            _now(execution_context),
        ):
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=None,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
                credential_provenance_fingerprint=
                    execution_context.credential_ownership_evidence_fingerprint,
                account_provenance_fingerprint=
                    execution_context.account_ownership_evidence_fingerprint,
            )

        attempt_fingerprint = _attempt_fingerprint(
            readiness_snapshot,
            submission_approval,
            execution_context,
        )
        claim_fingerprint = _claim_fingerprint(
            attempt_fingerprint,
            submission_approval,
        )

        try:
            claim_result = await submission_registry.claim(
                attempt_fingerprint=attempt_fingerprint,
                claim_fingerprint=claim_fingerprint,
            )
        except _asyncio.CancelledError:
            raise
        except Exception:
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=claim_fingerprint,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
                credential_provenance_fingerprint=
                    execution_context.credential_ownership_evidence_fingerprint,
                account_provenance_fingerprint=
                    execution_context.account_ownership_evidence_fingerprint,
            )
        if claim_result is not True:
            completed = _utc_text(_now(execution_context))
            return _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=claim_fingerprint,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=None,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
                credential_provenance_fingerprint=
                    execution_context.credential_ownership_evidence_fingerprint,
                account_provenance_fingerprint=
                    execution_context.account_ownership_evidence_fingerprint,
            )
        claimed = True

        in_flight_result = await submission_registry.compare_and_set(
            attempt_fingerprint=attempt_fingerprint,
            expected_state=Phase36SubmissionRegistryState.CLAIMED_PRE_SEND,
            new_state=Phase36SubmissionRegistryState.IN_FLIGHT,
        )
        if in_flight_result is not True:
            completed = _utc_text(_now(execution_context))
            receipt = _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=claim_fingerprint,
                outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                terminal_state=Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,
                transport_attempt_count=0,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
                credential_provenance_fingerprint=
                    execution_context.credential_ownership_evidence_fingerprint,
                account_provenance_fingerprint=
                    execution_context.account_ownership_evidence_fingerprint,
            )
            finalized = await _best_effort_finalize(
                submission_registry,
                attempt_fingerprint=attempt_fingerprint,
                expected_state=Phase36SubmissionRegistryState.CLAIMED_PRE_SEND,
                terminal_state=Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,
                receipt=receipt,
            )
            if not finalized:
                receipt = _receipt(
                    attempt_fingerprint=attempt_fingerprint,
                    request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                    readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                    approval_fingerprint=submission_approval.approval_fingerprint,
                    claim_fingerprint=claim_fingerprint,
                    outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                    terminal_state=None,
                    transport_attempt_count=0,
                    started_at_utc=started_at_utc,
                    completed_at_utc=completed,
                    credential_provenance_fingerprint=
                        execution_context.credential_ownership_evidence_fingerprint,
                    account_provenance_fingerprint=
                        execution_context.account_ownership_evidence_fingerprint,
                )
            return receipt
        in_flight = True

        headers = {
            "authorization": "Bearer " + token,
            "api-id": _API_ID,
            "Content-Type": _CONTENT_TYPE,
        }
        transport_attempt_count = 1

        try:
            async with _asyncio.timeout(float(execution_context.timeout_seconds)):
                response = await _invoke_method(
                    execution_context.transport,
                    "post_order",
                    base_url=_DEMO_BASE_URL,
                    path=_API_PATH,
                    headers=headers,
                    body=dict(body),
                    retry_on_auth_failure=False,
                )
        except _asyncio.CancelledError:
            raise
        except TimeoutError:
            outcome = KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED
            terminal_state = Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED
            normalized = None
            message = None
            order_no = None
            exchange = None
        except Exception:
            outcome = KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED
            terminal_state = Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED
            normalized = None
            message = None
            order_no = None
            exchange = None
        except BaseException:
            completed = _utc_text(_now(execution_context))
            ambiguous_receipt = _receipt(
                attempt_fingerprint=attempt_fingerprint,
                request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
                readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
                approval_fingerprint=submission_approval.approval_fingerprint,
                claim_fingerprint=claim_fingerprint,
                outcome=KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
                terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
                transport_attempt_count=transport_attempt_count,
                started_at_utc=started_at_utc,
                completed_at_utc=completed,
                credential_provenance_fingerprint=
                    execution_context.credential_ownership_evidence_fingerprint,
                account_provenance_fingerprint=
                    execution_context.account_ownership_evidence_fingerprint,
            )
            await _best_effort_finalize(
                submission_registry,
                attempt_fingerprint=attempt_fingerprint,
                expected_state=Phase36SubmissionRegistryState.IN_FLIGHT,
                terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
                receipt=ambiguous_receipt,
            )
            raise
        else:
            (
                outcome,
                terminal_state,
                normalized,
                message,
                order_no,
                exchange,
            ) = _classify_response(response, token=token)

        completed = _utc_text(_now(execution_context))
        receipt = _receipt(
            attempt_fingerprint=attempt_fingerprint,
            request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
            readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
            approval_fingerprint=submission_approval.approval_fingerprint,
            claim_fingerprint=claim_fingerprint,
            outcome=outcome,
            terminal_state=terminal_state,
            transport_attempt_count=transport_attempt_count,
            started_at_utc=started_at_utc,
            completed_at_utc=completed,
            normalized_return_code=normalized,
            provider_return_msg=message,
            provider_order_no=order_no,
            provider_exchange=exchange,
            credential_provenance_fingerprint=
                execution_context.credential_ownership_evidence_fingerprint,
            account_provenance_fingerprint=
                execution_context.account_ownership_evidence_fingerprint,
        )
        finalized = await _best_effort_finalize(
            submission_registry,
            attempt_fingerprint=attempt_fingerprint,
            expected_state=Phase36SubmissionRegistryState.IN_FLIGHT,
            terminal_state=terminal_state,
            receipt=receipt,
        )
        if finalized:
            return receipt

        ambiguous_receipt = _receipt(
            attempt_fingerprint=attempt_fingerprint,
            request_fingerprint=readiness_snapshot.phase30_materialization_fingerprint,
            readiness_fingerprint=readiness_snapshot.readiness_fingerprint,
            approval_fingerprint=submission_approval.approval_fingerprint,
            claim_fingerprint=claim_fingerprint,
            outcome=KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
            terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
            transport_attempt_count=transport_attempt_count,
            started_at_utc=started_at_utc,
            completed_at_utc=_utc_text(_now(execution_context)),
            normalized_return_code=normalized,
            provider_return_msg=message,
            provider_order_no=order_no,
            provider_exchange=exchange,
            credential_provenance_fingerprint=
                execution_context.credential_ownership_evidence_fingerprint,
            account_provenance_fingerprint=
                execution_context.account_ownership_evidence_fingerprint,
        )
        finalized_ambiguous = await _best_effort_finalize(
            submission_registry,
            attempt_fingerprint=attempt_fingerprint,
            expected_state=Phase36SubmissionRegistryState.IN_FLIGHT,
            terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
            receipt=ambiguous_receipt,
        )
        if finalized_ambiguous:
            return ambiguous_receipt
        _raise("TERMINAL_PERSISTENCE_FAILED_AFTER_SEND")
    except _asyncio.CancelledError:
        if (
            context_for_cleanup is not None
            and claimed
            and attempt_fingerprint != "0" * 64
        ):
            if in_flight:
                cancelled_receipt = _receipt(
                    attempt_fingerprint=attempt_fingerprint,
                    request_fingerprint=request_fingerprint,
                    readiness_fingerprint=readiness_fingerprint,
                    approval_fingerprint=approval_fingerprint,
                    claim_fingerprint=claim_fingerprint,
                    outcome=KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
                    terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
                    transport_attempt_count=transport_attempt_count,
                    started_at_utc=started_at_utc,
                    completed_at_utc=_utc_text(_datetime.now(_timezone.utc)),
                    credential_provenance_fingerprint=
                        context_for_cleanup.credential_ownership_evidence_fingerprint,
                    account_provenance_fingerprint=
                        context_for_cleanup.account_ownership_evidence_fingerprint,
                )
                await _best_effort_finalize(
                    submission_registry,
                    attempt_fingerprint=attempt_fingerprint,
                    expected_state=Phase36SubmissionRegistryState.IN_FLIGHT,
                    terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
                    receipt=cancelled_receipt,
                )
            else:
                aborted_receipt = _receipt(
                    attempt_fingerprint=attempt_fingerprint,
                    request_fingerprint=request_fingerprint,
                    readiness_fingerprint=readiness_fingerprint,
                    approval_fingerprint=approval_fingerprint,
                    claim_fingerprint=claim_fingerprint,
                    outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                    terminal_state=Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,
                    transport_attempt_count=0,
                    started_at_utc=started_at_utc,
                    completed_at_utc=_utc_text(_datetime.now(_timezone.utc)),
                    credential_provenance_fingerprint=
                        context_for_cleanup.credential_ownership_evidence_fingerprint,
                    account_provenance_fingerprint=
                        context_for_cleanup.account_ownership_evidence_fingerprint,
                )
                await _best_effort_finalize(
                    submission_registry,
                    attempt_fingerprint=attempt_fingerprint,
                    expected_state=Phase36SubmissionRegistryState.CLAIMED_PRE_SEND,
                    terminal_state=Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,
                    receipt=aborted_receipt,
                )
        raise
    except BaseException:
        if (
            context_for_cleanup is not None
            and claimed
            and attempt_fingerprint != "0" * 64
        ):
            if in_flight:
                failed_receipt = _receipt(
                    attempt_fingerprint=attempt_fingerprint,
                    request_fingerprint=request_fingerprint,
                    readiness_fingerprint=readiness_fingerprint,
                    approval_fingerprint=approval_fingerprint,
                    claim_fingerprint=claim_fingerprint,
                    outcome=KiwoomOrderProviderSubmissionOutcome.AMBIGUOUS_UNRESOLVED,
                    terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
                    transport_attempt_count=transport_attempt_count,
                    started_at_utc=started_at_utc,
                    completed_at_utc=_utc_text(_datetime.now(_timezone.utc)),
                    credential_provenance_fingerprint=
                        context_for_cleanup.credential_ownership_evidence_fingerprint,
                    account_provenance_fingerprint=
                        context_for_cleanup.account_ownership_evidence_fingerprint,
                )
                await _best_effort_finalize(
                    submission_registry,
                    attempt_fingerprint=attempt_fingerprint,
                    expected_state=Phase36SubmissionRegistryState.IN_FLIGHT,
                    terminal_state=Phase36SubmissionRegistryState.AMBIGUOUS_UNRESOLVED,
                    receipt=failed_receipt,
                )
            else:
                failed_receipt = _receipt(
                    attempt_fingerprint=attempt_fingerprint,
                    request_fingerprint=request_fingerprint,
                    readiness_fingerprint=readiness_fingerprint,
                    approval_fingerprint=approval_fingerprint,
                    claim_fingerprint=claim_fingerprint,
                    outcome=KiwoomOrderProviderSubmissionOutcome.BLOCKED_BEFORE_SEND,
                    terminal_state=Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,
                    transport_attempt_count=0,
                    started_at_utc=started_at_utc,
                    completed_at_utc=_utc_text(_datetime.now(_timezone.utc)),
                    credential_provenance_fingerprint=
                        context_for_cleanup.credential_ownership_evidence_fingerprint,
                    account_provenance_fingerprint=
                        context_for_cleanup.account_ownership_evidence_fingerprint,
                )
                await _best_effort_finalize(
                    submission_registry,
                    attempt_fingerprint=attempt_fingerprint,
                    expected_state=Phase36SubmissionRegistryState.CLAIMED_PRE_SEND,
                    terminal_state=Phase36SubmissionRegistryState.ABORTED_BEFORE_SEND,
                    receipt=failed_receipt,
                )
        raise
    finally:
        if context_for_cleanup is not None:
            await _cleanup_best_effort(context_for_cleanup)
