from dataclasses import dataclass as _dataclass
import hashlib as _hashlib
import json as _json
from types import MappingProxyType as _MappingProxyType
from typing import Mapping as _Mapping

__all__ = (
    "WatchlistOrderSendRequestError",
    "WatchlistOrderSendRequestInput",
    "WatchlistOrderSendRequestSnapshot",
    "build_demo_watchlist_order_send_request_snapshot",
)


class WatchlistOrderSendRequestError(RuntimeError):
    pass


@_dataclass(frozen=True, slots=True)
class WatchlistOrderSendRequestInput:
    environment: str
    side: str
    exchange: str
    stock_code: str
    quantity: int
    order_style: str
    limit_price: int | None
    source_attempt_ref: str
    authorization_evidence_ref: str


@_dataclass(frozen=True, slots=True)
class WatchlistOrderSendRequestSnapshot:
    environment: str
    side: str
    exchange: str
    api_id: str
    http_method: str
    api_path: str
    body: _Mapping[str, str]
    source_attempt_ref: str
    authorization_evidence_ref: str
    materialization_fingerprint: str
    transport_allowed: bool
    credential_accessed: bool
    network_performed: bool
    account_accessed: bool
    order_submitted: bool


def _error(code: str) -> WatchlistOrderSendRequestError:
    return WatchlistOrderSendRequestError(code)


def _has_control(value: str) -> bool:
    return any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in value)


def _valid_reference(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and bool(value.strip())
        and not _has_control(value)
    )


def _fingerprint(
    *,
    environment: str,
    side: str,
    exchange: str,
    api_id: str,
    http_method: str,
    api_path: str,
    body: dict[str, str],
    source_attempt_ref: str,
    authorization_evidence_ref: str,
) -> str:
    envelope = {
        "environment": environment,
        "side": side,
        "exchange": exchange,
        "api_id": api_id,
        "http_method": http_method,
        "api_path": api_path,
        "body": body,
        "source_attempt_ref": source_attempt_ref,
        "authorization_evidence_ref": authorization_evidence_ref,
    }
    canonical = _json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return _hashlib.sha256(canonical).hexdigest()


def build_demo_watchlist_order_send_request_snapshot(
    request: WatchlistOrderSendRequestInput,
) -> WatchlistOrderSendRequestSnapshot:
    if type(request.environment) is not str or request.environment != "demo":
        raise _error("ENVIRONMENT_PROHIBITED")

    if type(request.side) is not str or request.side != "BUY":
        raise _error("SIDE_UNSUPPORTED")

    if type(request.exchange) is not str or request.exchange != "KRX":
        raise _error("DEMO_EXCHANGE_UNSUPPORTED")

    if (
        type(request.stock_code) is not str
        or not (1 <= len(request.stock_code) <= 12)
        or not request.stock_code
        or request.stock_code != request.stock_code.strip()
        or _has_control(request.stock_code)
    ):
        raise _error("STOCK_CODE_INVALID")

    if (
        type(request.quantity) is not int
        or request.quantity <= 0
        or len(str(request.quantity)) > 12
    ):
        raise _error("QUANTITY_INVALID")

    if type(request.order_style) is not str or request.order_style not in ("LIMIT", "MARKET"):
        raise _error("ORDER_STYLE_UNSUPPORTED")

    if request.order_style == "LIMIT":
        if (
            type(request.limit_price) is not int
            or request.limit_price <= 0
            or len(str(request.limit_price)) > 12
        ):
            raise _error("LIMIT_PRICE_INVALID")
    elif request.limit_price is not None:
        raise _error("MARKET_PRICE_MUST_BE_EMPTY")

    if not _valid_reference(request.source_attempt_ref):
        raise _error("SOURCE_ATTEMPT_REF_INVALID")

    if not _valid_reference(request.authorization_evidence_ref):
        raise _error("AUTHORIZATION_EVIDENCE_REF_INVALID")

    if request.order_style == "LIMIT":
        ord_uv = str(request.limit_price)
        trde_tp = "0"
    else:
        ord_uv = ""
        trde_tp = "3"

    body = {
        "dmst_stex_tp": "KRX",
        "stk_cd": request.stock_code,
        "ord_qty": str(request.quantity),
        "ord_uv": ord_uv,
        "trde_tp": trde_tp,
        "cond_uv": "",
    }

    api_id = "kt10000"
    http_method = "POST"
    api_path = "/api/dostk/ordr"

    fingerprint = _fingerprint(
        environment=request.environment,
        side=request.side,
        exchange=request.exchange,
        api_id=api_id,
        http_method=http_method,
        api_path=api_path,
        body=body,
        source_attempt_ref=request.source_attempt_ref,
        authorization_evidence_ref=request.authorization_evidence_ref,
    )

    return WatchlistOrderSendRequestSnapshot(
        environment=request.environment,
        side=request.side,
        exchange=request.exchange,
        api_id=api_id,
        http_method=http_method,
        api_path=api_path,
        body=_MappingProxyType(dict(body)),
        source_attempt_ref=request.source_attempt_ref,
        authorization_evidence_ref=request.authorization_evidence_ref,
        materialization_fingerprint=fingerprint,
        transport_allowed=False,
        credential_accessed=False,
        network_performed=False,
        account_accessed=False,
        order_submitted=False,
    )
