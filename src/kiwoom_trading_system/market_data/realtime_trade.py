"""Normalize Kiwoom realtime stock trade (0B) payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Any

KST = timezone(timedelta(hours=9), "KST")
REALTIME_TRADE_TYPE = "0B"
_SIGNED_INTEGER = re.compile(r"[+-]?\d+\Z")
_SIGNED_DECIMAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)\Z")


class TradeNormalizationError(ValueError):
    """Raised when a realtime trade payload cannot be normalized safely."""


class MarketVenue(StrEnum):
    KRX = "KRX"
    NXT = "NXT"
    SOR = "SOR"


class AggressorSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


class TradingSession(StrEnum):
    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class NormalizedTrade:
    """Stable v1 representation of one Kiwoom 0B trade event."""

    schema_version: int
    source: str
    realtime_type: str
    source_name: str
    source_item: str
    instrument_code: str
    venue: MarketVenue
    trade_at: datetime
    received_at: datetime
    price_krw: int
    price_sign: int
    change_krw: int | None
    change_rate_pct: Decimal | None
    best_ask_krw: int | None
    best_bid_krw: int | None
    signed_trade_volume: int
    trade_volume: int
    aggressor_side: AggressorSide
    cumulative_volume: int | None
    cumulative_value_million_krw: Decimal | None
    open_krw: int | None
    high_krw: int | None
    low_krw: int | None
    trade_strength_pct: Decimal | None
    session: TradingSession
    day_change_sign_code: str | None
    exchange_code: str | None
    raw_values: Mapping[str, str]


def normalize_trade_packet(
    payload: Mapping[str, Any],
    *,
    received_at: datetime,
) -> tuple[NormalizedTrade, ...]:
    """Normalize every 0B entry in one Kiwoom REAL packet."""

    if not isinstance(payload, Mapping):
        raise TradeNormalizationError("payload must be a mapping")

    if payload.get("trnm") != "REAL":
        raise TradeNormalizationError("payload trnm must be REAL")

    data = payload.get("data")
    if not isinstance(data, list):
        raise TradeNormalizationError("payload data must be a list")

    normalized: list[NormalizedTrade] = []

    for index, entry in enumerate(data):
        if not isinstance(entry, Mapping):
            raise TradeNormalizationError(
                f"data[{index}] must be a mapping"
            )

        if (
            str(entry.get("type", "")).strip().upper()
            != REALTIME_TRADE_TYPE
        ):
            continue

        normalized.append(
            normalize_trade_entry(
                entry,
                received_at=received_at,
            )
        )

    return tuple(normalized)


def normalize_trade_entry(
    entry: Mapping[str, Any],
    *,
    received_at: datetime,
) -> NormalizedTrade:
    """Normalize one Kiwoom 0B data entry without mutating the input."""

    if not isinstance(entry, Mapping):
        raise TradeNormalizationError("entry must be a mapping")

    if (
        str(entry.get("type", "")).strip().upper()
        != REALTIME_TRADE_TYPE
    ):
        raise TradeNormalizationError("entry type must be 0B")

    received_kst = _as_aware_kst(received_at)
    source_item = _required_text(entry.get("item"), "entry item")
    instrument_code, venue = _parse_item(source_item)
    source_name = _optional_text(entry.get("name")) or "주식체결"
    values = _normalize_values(entry.get("values"))

    trade_time_text = _required_value(
        values,
        "20",
        "체결시간",
    )
    trade_at = _trade_datetime(
        received_kst,
        trade_time_text,
    )

    signed_price = _required_int(
        values,
        "10",
        "현재가",
    )
    if signed_price == 0:
        raise TradeNormalizationError(
            "현재가(10) must not be zero"
        )

    signed_volume = _required_int(
        values,
        "15",
        "거래량",
    )

    aggressor_side = (
        AggressorSide.BUY
        if signed_volume > 0
        else AggressorSide.SELL
        if signed_volume < 0
        else AggressorSide.UNKNOWN
    )

    cumulative_volume = _optional_int(
        values,
        "13",
        "누적거래량",
    )
    if (
        cumulative_volume is not None
        and cumulative_volume < 0
    ):
        raise TradeNormalizationError(
            "누적거래량(13) must not be negative"
        )

    cumulative_value = _optional_decimal(
        values,
        "14",
        "누적거래대금",
    )
    if (
        cumulative_value is not None
        and cumulative_value < 0
    ):
        raise TradeNormalizationError(
            "누적거래대금(14) must not be negative"
        )

    return NormalizedTrade(
        schema_version=1,
        source="kiwoom",
        realtime_type=REALTIME_TRADE_TYPE,
        source_name=source_name,
        source_item=source_item,
        instrument_code=instrument_code,
        venue=venue,
        trade_at=trade_at,
        received_at=received_kst,
        price_krw=abs(signed_price),
        price_sign=_sign(signed_price),
        change_krw=_optional_int(
            values,
            "11",
            "전일대비",
        ),
        change_rate_pct=_optional_decimal(
            values,
            "12",
            "등락율",
        ),
        best_ask_krw=_optional_abs_int(
            values,
            "27",
            "최우선매도호가",
        ),
        best_bid_krw=_optional_abs_int(
            values,
            "28",
            "최우선매수호가",
        ),
        signed_trade_volume=signed_volume,
        trade_volume=abs(signed_volume),
        aggressor_side=aggressor_side,
        cumulative_volume=cumulative_volume,
        cumulative_value_million_krw=cumulative_value,
        open_krw=_optional_abs_int(
            values,
            "16",
            "시가",
        ),
        high_krw=_optional_abs_int(
            values,
            "17",
            "고가",
        ),
        low_krw=_optional_abs_int(
            values,
            "18",
            "저가",
        ),
        trade_strength_pct=_optional_decimal(
            values,
            "228",
            "체결강도",
        ),
        session=_parse_session(values.get("290")),
        day_change_sign_code=_optional_text(
            values.get("25")
        ),
        exchange_code=_optional_text(
            values.get("9081")
        ),
        raw_values=MappingProxyType(dict(values)),
    )


def _as_aware_kst(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TradeNormalizationError(
            "received_at must be a datetime"
        )

    if value.tzinfo is None or value.utcoffset() is None:
        raise TradeNormalizationError(
            "received_at must be timezone-aware"
        )

    return value.astimezone(KST)


def _parse_item(
    item: str,
) -> tuple[str, MarketVenue]:
    if re.fullmatch(r"\d{6}", item):
        return item, MarketVenue.KRX

    if re.fullmatch(r"\d{6}_NX", item):
        return item[:6], MarketVenue.NXT

    if re.fullmatch(r"\d{6}_AL", item):
        return item[:6], MarketVenue.SOR

    raise TradeNormalizationError(
        "entry item must use KRX 000000, "
        "NXT 000000_NX, or SOR 000000_AL"
    )


def _normalize_values(
    value: Any,
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise TradeNormalizationError(
            "entry values must be a mapping"
        )

    normalized: dict[str, str] = {}

    for raw_key, raw_value in value.items():
        key = str(raw_key).strip()

        if not key:
            raise TradeNormalizationError(
                "values contains a blank FID"
            )

        if not isinstance(raw_value, str):
            raise TradeNormalizationError(
                f"FID {key} value must be a string"
            )

        normalized[key] = raw_value

    return normalized


def _trade_datetime(
    received_kst: datetime,
    value: str,
) -> datetime:
    text = value.strip()

    if not re.fullmatch(r"\d{6}", text):
        raise TradeNormalizationError(
            "체결시간(20) must use HHmmss"
        )

    hour = int(text[:2])
    minute = int(text[2:4])
    second = int(text[4:])

    try:
        return datetime(
            received_kst.year,
            received_kst.month,
            received_kst.day,
            hour,
            minute,
            second,
            tzinfo=KST,
        )
    except ValueError as exc:
        raise TradeNormalizationError(
            "체결시간(20) is invalid"
        ) from exc


def _required_value(
    values: Mapping[str, str],
    fid: str,
    field_name: str,
) -> str:
    value = values.get(fid)

    if value is None or not value.strip():
        raise TradeNormalizationError(
            f"{field_name}({fid}) is required"
        )

    return value


def _required_text(
    value: Any,
    field_name: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TradeNormalizationError(
            f"{field_name} must be a non-blank string"
        )

    return value.strip().upper()


def _optional_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TradeNormalizationError(
            "optional text value must be a string"
        )

    text = value.strip()
    return text or None


def _required_int(
    values: Mapping[str, str],
    fid: str,
    field_name: str,
) -> int:
    return _parse_int(
        _required_value(
            values,
            fid,
            field_name,
        ),
        fid,
        field_name,
    )


def _optional_int(
    values: Mapping[str, str],
    fid: str,
    field_name: str,
) -> int | None:
    value = values.get(fid)

    if value is None or not value.strip():
        return None

    return _parse_int(
        value,
        fid,
        field_name,
    )


def _optional_abs_int(
    values: Mapping[str, str],
    fid: str,
    field_name: str,
) -> int | None:
    value = _optional_int(
        values,
        fid,
        field_name,
    )

    return None if value is None else abs(value)


def _parse_int(
    value: str,
    fid: str,
    field_name: str,
) -> int:
    text = value.strip()

    if not _SIGNED_INTEGER.fullmatch(text):
        raise TradeNormalizationError(
            f"{field_name}({fid}) is not an integer"
        )

    return int(text)


def _optional_decimal(
    values: Mapping[str, str],
    fid: str,
    field_name: str,
) -> Decimal | None:
    value = values.get(fid)

    if value is None or not value.strip():
        return None

    text = value.strip()

    if not _SIGNED_DECIMAL.fullmatch(text):
        raise TradeNormalizationError(
            f"{field_name}({fid}) is not numeric"
        )

    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise TradeNormalizationError(
            f"{field_name}({fid}) is not numeric"
        ) from exc


def _parse_session(
    value: str | None,
) -> TradingSession:
    text = "" if value is None else value.strip()

    return {
        "1": TradingSession.PRE_MARKET,
        "2": TradingSession.REGULAR,
        "3": TradingSession.AFTER_HOURS,
    }.get(
        text,
        TradingSession.UNKNOWN,
    )


def _sign(value: int) -> int:
    return (
        1
        if value > 0
        else -1
        if value < 0
        else 0
    )