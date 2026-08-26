from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

from kiwoom_trading_system.brokers.kiwoom.rest import volume_ranking as rest


DEFAULT_CANDIDATE_LIMIT = 20
MIN_CANDIDATE_LIMIT = 1
MAX_CANDIDATE_LIMIT = 100

_EXCHANGE_SCOPES = {"1": "KRX", "2": "NXT", "3": "INTEGRATED"}


@dataclass(frozen=True, slots=True)
class VolumeRankingCandidate:
    stock_code: str
    stock_name: str
    raw_current_price: str
    current_price: int
    current_price_sign: str
    change_rate_pct: Decimal
    trade_quantity: int
    trade_turnover_rate_pct: Decimal
    raw_trade_amount: str
    trade_amount_million_krw: int
    exchange_scope: str
    raw_row: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class VolumeRankingMetrics:
    valid_candidate_count: int
    invalid_row_count: int
    duplicate_row_count: int
    excluded_by_limit_count: int


@dataclass(frozen=True, slots=True)
class VolumeRankingResult:
    candidates: tuple[VolumeRankingCandidate, ...]
    metrics: VolumeRankingMetrics
    raw_response: Mapping[str, object]
    request_metadata: Mapping[str, object]


def _freeze_snapshot(value: Any) -> Any:
    if isinstance(value, Mapping):
        copied = {
            key: _freeze_snapshot(item)
            for key, item in dict(value).items()
        }
        return MappingProxyType(copied)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_snapshot(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_snapshot(item) for item in value)
    return value


def _required_text(row: Mapping[str, object], name: str) -> str:
    value = row[name]
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} is required.")
    return value


def _nonnegative_int(raw: str, name: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer string.") from exc
    if value < 0:
        raise ValueError(f"{name} must not be negative.")
    return value


def _finite_decimal(raw: str, name: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a decimal string.") from exc
    if not value.is_finite():
        raise ValueError(f"{name} must be finite.")
    return value


def _exchange_scope(request_metadata: Mapping[str, object]) -> str:
    stex_tp = request_metadata["stex_tp"]
    if not isinstance(stex_tp, str):
        raise TypeError("stex_tp must be a string.")
    try:
        return _EXCHANGE_SCOPES[stex_tp]
    except KeyError as exc:
        raise ValueError(f"unsupported stex_tp: {stex_tp!r}.") from exc


def _normalize_row(
    row: object,
    *,
    exchange_scope: str,
) -> VolumeRankingCandidate:
    if not isinstance(row, Mapping):
        raise TypeError("volume-ranking row must be a mapping.")
    stock_code = _required_text(row, "stk_cd").strip()
    stock_name = _required_text(row, "stk_nm").strip()
    raw_current_price = _required_text(row, "cur_prc")
    raw_change_rate = _required_text(row, "flu_rt")
    raw_trade_quantity = _required_text(row, "trde_qty")
    raw_turnover_rate = _required_text(row, "trde_tern_rt")
    raw_trade_amount = _required_text(row, "trde_amt")

    try:
        current_price = abs(int(raw_current_price))
    except ValueError as exc:
        raise ValueError("cur_prc must be an integer string.") from exc

    if raw_current_price.startswith("-"):
        current_price_sign = "-"
    elif raw_current_price.startswith("+"):
        current_price_sign = "+"
    else:
        current_price_sign = ""

    return VolumeRankingCandidate(
        stock_code=stock_code,
        stock_name=stock_name,
        raw_current_price=raw_current_price,
        current_price=current_price,
        current_price_sign=current_price_sign,
        change_rate_pct=_finite_decimal(raw_change_rate, "flu_rt"),
        trade_quantity=_nonnegative_int(raw_trade_quantity, "trde_qty"),
        trade_turnover_rate_pct=_finite_decimal(
            raw_turnover_rate,
            "trde_tern_rt",
        ),
        raw_trade_amount=raw_trade_amount,
        trade_amount_million_krw=_nonnegative_int(
            raw_trade_amount,
            "trde_amt",
        ),
        exchange_scope=exchange_scope,
        raw_row=_freeze_snapshot(row),
    )


def _validated_limit(candidate_limit: object) -> int:
    if isinstance(candidate_limit, bool) or not isinstance(candidate_limit, int):
        raise TypeError("candidate_limit must be an integer.")
    if not MIN_CANDIDATE_LIMIT <= candidate_limit <= MAX_CANDIDATE_LIMIT:
        raise ValueError(
            "candidate_limit must be between "
            f"{MIN_CANDIDATE_LIMIT} and {MAX_CANDIDATE_LIMIT}."
        )
    return candidate_limit


def normalize_volume_ranking(
    response: Mapping[str, object],
    request_metadata: Mapping[str, object],
    *,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> VolumeRankingResult:
    limit = _validated_limit(candidate_limit)
    if not isinstance(response, Mapping):
        raise TypeError("response must be a mapping.")
    if not isinstance(request_metadata, Mapping):
        raise TypeError("request_metadata must be a mapping.")
    rows = response[rest.RESPONSE_KEY]
    if not isinstance(rows, (list, tuple)):
        raise TypeError(f"{rest.RESPONSE_KEY} must be a list or tuple.")

    scope = _exchange_scope(request_metadata)
    raw_response = _freeze_snapshot(response)
    frozen_request = _freeze_snapshot(request_metadata)

    normalized_rows: list[VolumeRankingCandidate] = []
    invalid_row_count = 0
    for row in rows:
        try:
            normalized_rows.append(_normalize_row(row, exchange_scope=scope))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            invalid_row_count += 1

    unique_candidates: list[VolumeRankingCandidate] = []
    seen_codes: set[str] = set()
    duplicate_row_count = 0
    for candidate in normalized_rows:
        if candidate.stock_code in seen_codes:
            duplicate_row_count += 1
            continue
        seen_codes.add(candidate.stock_code)
        unique_candidates.append(candidate)

    excluded_by_limit_count = max(0, len(unique_candidates) - limit)
    candidates = tuple(unique_candidates[:limit])
    metrics = VolumeRankingMetrics(
        valid_candidate_count=len(candidates),
        invalid_row_count=invalid_row_count,
        duplicate_row_count=duplicate_row_count,
        excluded_by_limit_count=excluded_by_limit_count,
    )
    return VolumeRankingResult(
        candidates=candidates,
        metrics=metrics,
        raw_response=raw_response,
        request_metadata=frozen_request,
    )


def fetch_volume_ranking_candidates(
    *,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    timeout_seconds: int = 30,
    **request_values: str,
) -> VolumeRankingResult:
    request = rest.build_volume_ranking_request(**request_values)
    response = rest.get_daily_volume_ranking(
        **request,
        timeout_seconds=timeout_seconds,
    )
    return normalize_volume_ranking(
        response,
        request,
        candidate_limit=candidate_limit,
    )


__all__ = [
    "DEFAULT_CANDIDATE_LIMIT",
    "MIN_CANDIDATE_LIMIT",
    "MAX_CANDIDATE_LIMIT",
    "VolumeRankingCandidate",
    "VolumeRankingMetrics",
    "VolumeRankingResult",
    "fetch_volume_ranking_candidates",
    "normalize_volume_ranking",
]
