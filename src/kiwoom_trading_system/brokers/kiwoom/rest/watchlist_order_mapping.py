"""Map Phase 24 account-validated intents to Kiwoom REST buy-order request shapes."""

from __future__ import annotations

from dataclasses import dataclass

from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.orders.watchlist_account_validation import (
    WatchlistAccountValidationDecision,
    WatchlistAccountValidationSnapshot,
    WatchlistCandidateAccountValidation,
)
from kiwoom_trading_system.orders.watchlist_order_intent import (
    WatchlistOrderIntentSide,
    WatchlistOrderIntentStyle,
)
from kiwoom_trading_system.orders.watchlist_order_permission import (
    WatchlistOrderPermissionDecision,
)
from kiwoom_trading_system.risk import WatchlistRiskDecision
from kiwoom_trading_system.strategies import WatchlistSignalDecision


KIWOOM_BUY_ORDER_API_ID = "kt10000"
KIWOOM_ORDER_API_PATH = "/api/dostk/ordr"

_PROVIDER_FIELD_MAX_LENGTHS = {
    "dmst_stex_tp": 3,
    "stk_cd": 12,
    "ord_qty": 12,
    "ord_uv": 12,
    "trde_tp": 2,
    "cond_uv": 12,
}

_PASS_REASON = "ACCOUNT_VALIDATION_OK"
_QUANTITY_BLOCK_REASON = "MAX_ORDERABLE_QUANTITY_INSUFFICIENT"
_BUYING_POWER_BLOCK_REASON = "BUYING_POWER_INSUFFICIENT"


class KiwoomOrderMappingError(ValueError):
    """Raised when Phase 25 mapping input or provider shape violates the contract."""


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise KiwoomOrderMappingError(f"{field_name} must be a string.")
    if not value.strip():
        raise KiwoomOrderMappingError(
            f"{field_name} must not be empty or whitespace."
        )


def _require_nonnegative_int(value: object, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise KiwoomOrderMappingError(
            f"{field_name} must be a non-negative exact integer."
        )


def _require_positive_int(value: object, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise KiwoomOrderMappingError(
            f"{field_name} must be a positive exact integer."
        )


def _require_provider_string(
    value: object,
    field_name: str,
    *,
    required: bool,
) -> None:
    if not isinstance(value, str):
        raise KiwoomOrderMappingError(
            f"{field_name} must be a provider string."
        )
    if required and not value:
        raise KiwoomOrderMappingError(
            f"{field_name} must not be empty."
        )
    max_length = _PROVIDER_FIELD_MAX_LENGTHS[field_name]
    if len(value) > max_length:
        raise KiwoomOrderMappingError(
            f"{field_name} exceeds provider Length {max_length}."
        )


@dataclass(frozen=True, slots=True)
class KiwoomBuyOrderRequest:
    """Immutable Kiwoom kt10000 request body shape."""

    dmst_stex_tp: str
    stk_cd: str
    ord_qty: str
    ord_uv: str
    trde_tp: str
    cond_uv: str

    def __post_init__(self) -> None:
        _require_provider_string(
            self.dmst_stex_tp,
            "dmst_stex_tp",
            required=True,
        )
        _require_provider_string(self.stk_cd, "stk_cd", required=True)
        _require_provider_string(self.ord_qty, "ord_qty", required=True)
        _require_provider_string(self.ord_uv, "ord_uv", required=False)
        _require_provider_string(self.trde_tp, "trde_tp", required=True)
        _require_provider_string(self.cond_uv, "cond_uv", required=False)

        if self.dmst_stex_tp not in {"KRX", "NXT", "SOR"}:
            raise KiwoomOrderMappingError(
                "dmst_stex_tp must be KRX, NXT, or SOR."
            )
        if not self.ord_qty.isdecimal() or int(self.ord_qty) <= 0:
            raise KiwoomOrderMappingError(
                "ord_qty must encode a positive integer."
            )
        if self.trde_tp == "3":
            if self.ord_uv != "":
                raise KiwoomOrderMappingError(
                    "MARKET ord_uv must be empty."
                )
        elif self.trde_tp == "0":
            if not self.ord_uv.isdecimal() or int(self.ord_uv) <= 0:
                raise KiwoomOrderMappingError(
                    "LIMIT ord_uv must encode a positive integer."
                )
        else:
            raise KiwoomOrderMappingError(
                "trde_tp must be 0 or 3 in Phase 25."
            )
        if self.cond_uv != "":
            raise KiwoomOrderMappingError(
                "cond_uv must be empty in Phase 25."
            )


@dataclass(frozen=True, slots=True)
class WatchlistCandidateKiwoomOrderMapping:
    """Immutable provider mapping for one Phase 24 PASSED candidate."""

    source_rank: int
    stock_code: str
    stock_name: str
    exchange_scope: str
    realtime_type: str
    signal_decision: WatchlistSignalDecision
    venue: MarketVenue
    signal_reason_code: str
    risk_decision: WatchlistRiskDecision
    risk_reason_code: str
    order_permission_decision: WatchlistOrderPermissionDecision
    order_permission_reason_code: str
    order_side: WatchlistOrderIntentSide
    order_style: WatchlistOrderIntentStyle
    requested_quantity: int
    limit_price: int | None
    order_intent_reason_code: str
    account_validation_decision: WatchlistAccountValidationDecision
    account_validation_reason_code: str
    reservation_amount: int
    max_orderable_quantity: int
    remaining_buying_power_after: int
    request: KiwoomBuyOrderRequest

    def __post_init__(self) -> None:
        if type(self.request) is not KiwoomBuyOrderRequest:
            raise KiwoomOrderMappingError(
                "request must be KiwoomBuyOrderRequest."
            )
        if self.venue.value != self.request.dmst_stex_tp:
            raise KiwoomOrderMappingError(
                "candidate/request venue identity mismatch."
            )
        if self.stock_code != self.request.stk_cd:
            raise KiwoomOrderMappingError(
                "candidate/request stock_code identity mismatch."
            )
        if str(self.requested_quantity) != self.request.ord_qty:
            raise KiwoomOrderMappingError(
                "candidate/request quantity identity mismatch."
            )
        if self.order_style is WatchlistOrderIntentStyle.MARKET:
            if self.request.trde_tp != "3" or self.request.ord_uv != "":
                raise KiwoomOrderMappingError(
                    "candidate/request MARKET mapping mismatch."
                )
        elif self.order_style is WatchlistOrderIntentStyle.LIMIT:
            if (
                self.request.trde_tp != "0"
                or self.request.ord_uv != str(self.limit_price)
            ):
                raise KiwoomOrderMappingError(
                    "candidate/request LIMIT mapping mismatch."
                )
        else:
            raise KiwoomOrderMappingError(
                "candidate order_style is not supported."
            )


@dataclass(frozen=True, slots=True)
class WatchlistKiwoomOrderMappingSnapshot:
    """Immutable ordered Phase 25 Kiwoom request mapping snapshot."""

    mappings: tuple[WatchlistCandidateKiwoomOrderMapping, ...]
    candidate_count: int
    no_signal_count: int
    risk_checked_count: int
    risk_clear_count: int
    risk_blocked_count: int
    permission_checked_count: int
    order_permitted_count: int
    order_denied_count: int
    intent_planned_count: int
    market_order_count: int
    limit_order_count: int
    validation_checked_count: int
    validation_passed_count: int
    validation_blocked_count: int
    mapping_count: int
    initial_available_buying_power: int
    total_reserved_buying_power: int
    remaining_buying_power: int
    account_context_id: str
    evidence_snapshot_id: str
    realtime_type: str


def _validate_count_contract(snapshot: WatchlistAccountValidationSnapshot) -> None:
    count_fields = (
        "candidate_count",
        "no_signal_count",
        "risk_checked_count",
        "risk_clear_count",
        "risk_blocked_count",
        "permission_checked_count",
        "order_permitted_count",
        "order_denied_count",
        "intent_planned_count",
        "market_order_count",
        "limit_order_count",
        "validation_checked_count",
        "validation_passed_count",
        "validation_blocked_count",
    )
    for field_name in count_fields:
        _require_nonnegative_int(getattr(snapshot, field_name), field_name)

    if snapshot.candidate_count != (
        snapshot.no_signal_count + snapshot.risk_checked_count
    ):
        raise KiwoomOrderMappingError(
            "candidate_count violates the Phase 20 invariant."
        )
    if snapshot.risk_checked_count != (
        snapshot.risk_clear_count + snapshot.risk_blocked_count
    ):
        raise KiwoomOrderMappingError(
            "risk counts violate the Phase 21 invariant."
        )
    if snapshot.permission_checked_count != snapshot.risk_clear_count:
        raise KiwoomOrderMappingError(
            "permission_checked_count violates the Phase 22 invariant."
        )
    if snapshot.permission_checked_count != (
        snapshot.order_permitted_count + snapshot.order_denied_count
    ):
        raise KiwoomOrderMappingError(
            "permission counts violate the Phase 22 invariant."
        )
    if snapshot.intent_planned_count != snapshot.order_permitted_count:
        raise KiwoomOrderMappingError(
            "intent_planned_count violates the Phase 23 invariant."
        )
    if snapshot.intent_planned_count != (
        snapshot.market_order_count + snapshot.limit_order_count
    ):
        raise KiwoomOrderMappingError(
            "order style counts violate the Phase 23 invariant."
        )
    if snapshot.validation_checked_count != snapshot.intent_planned_count:
        raise KiwoomOrderMappingError(
            "validation_checked_count violates the Phase 24 invariant."
        )
    if snapshot.validation_checked_count != (
        snapshot.validation_passed_count
        + snapshot.validation_blocked_count
    ):
        raise KiwoomOrderMappingError(
            "validation counts violate the Phase 24 invariant."
        )


def _validate_candidate_common(
    candidate: WatchlistCandidateAccountValidation,
    snapshot: WatchlistAccountValidationSnapshot,
) -> None:
    if type(candidate) is not WatchlistCandidateAccountValidation:
        raise KiwoomOrderMappingError(
            "validations must contain WatchlistCandidateAccountValidation."
        )
    _require_positive_int(candidate.source_rank, "source_rank")
    _require_nonempty_string(candidate.stock_code, "stock_code")
    _require_nonempty_string(candidate.stock_name, "stock_name")
    _require_nonempty_string(candidate.exchange_scope, "exchange_scope")
    _require_nonempty_string(candidate.realtime_type, "realtime_type")
    _require_nonempty_string(candidate.signal_reason_code, "signal_reason_code")
    _require_nonempty_string(candidate.risk_reason_code, "risk_reason_code")
    _require_nonempty_string(
        candidate.order_permission_reason_code,
        "order_permission_reason_code",
    )
    _require_nonempty_string(
        candidate.order_intent_reason_code,
        "order_intent_reason_code",
    )
    _require_nonempty_string(
        candidate.account_validation_reason_code,
        "account_validation_reason_code",
    )

    if candidate.realtime_type != snapshot.realtime_type:
        raise KiwoomOrderMappingError(
            "candidate realtime_type does not match snapshot."
        )
    if type(candidate.signal_decision) is not WatchlistSignalDecision:
        raise KiwoomOrderMappingError(
            "signal_decision must be WatchlistSignalDecision."
        )
    if candidate.signal_decision is not WatchlistSignalDecision.ENTRY_CANDIDATE:
        raise KiwoomOrderMappingError(
            "Phase 24 validation must originate from ENTRY_CANDIDATE."
        )
    if candidate.venue is not None and type(candidate.venue) is not MarketVenue:
        raise KiwoomOrderMappingError(
            "venue must be MarketVenue or None."
        )
    if type(candidate.risk_decision) is not WatchlistRiskDecision:
        raise KiwoomOrderMappingError(
            "risk_decision must be WatchlistRiskDecision."
        )
    if candidate.risk_decision is not WatchlistRiskDecision.RISK_CLEAR:
        raise KiwoomOrderMappingError(
            "Phase 24 validation must originate from RISK_CLEAR."
        )
    if (
        type(candidate.order_permission_decision)
        is not WatchlistOrderPermissionDecision
    ):
        raise KiwoomOrderMappingError(
            "order_permission_decision must be WatchlistOrderPermissionDecision."
        )
    if (
        candidate.order_permission_decision
        is not WatchlistOrderPermissionDecision.ORDER_PERMITTED
    ):
        raise KiwoomOrderMappingError(
            "Phase 24 validation must originate from ORDER_PERMITTED."
        )
    if type(candidate.order_side) is not WatchlistOrderIntentSide:
        raise KiwoomOrderMappingError(
            "order_side must be WatchlistOrderIntentSide."
        )
    if candidate.order_side is not WatchlistOrderIntentSide.BUY:
        raise KiwoomOrderMappingError("order_side must be BUY.")
    if type(candidate.order_style) is not WatchlistOrderIntentStyle:
        raise KiwoomOrderMappingError(
            "order_style must be WatchlistOrderIntentStyle."
        )

    _require_positive_int(candidate.requested_quantity, "requested_quantity")
    if candidate.order_style is WatchlistOrderIntentStyle.MARKET:
        if candidate.limit_price is not None:
            raise KiwoomOrderMappingError(
                "MARKET limit_price must be None."
            )
    elif candidate.order_style is WatchlistOrderIntentStyle.LIMIT:
        _require_positive_int(candidate.limit_price, "LIMIT limit_price")
    else:
        raise KiwoomOrderMappingError(
            "order_style is not supported."
        )

    if (
        type(candidate.account_validation_decision)
        is not WatchlistAccountValidationDecision
    ):
        raise KiwoomOrderMappingError(
            "account_validation_decision must be WatchlistAccountValidationDecision."
        )
    _require_positive_int(candidate.reservation_amount, "reservation_amount")
    _require_nonnegative_int(
        candidate.max_orderable_quantity,
        "max_orderable_quantity",
    )
    _require_nonnegative_int(
        candidate.remaining_buying_power_after,
        "remaining_buying_power_after",
    )


def _validate_provider_candidate(
    candidate: WatchlistCandidateAccountValidation,
) -> None:
    if type(candidate.venue) is not MarketVenue:
        raise KiwoomOrderMappingError(
            "PASSED candidate venue must be MarketVenue."
        )

    venue_text = candidate.venue.value
    _require_provider_string(
        venue_text,
        "dmst_stex_tp",
        required=True,
    )
    _require_provider_string(
        candidate.stock_code,
        "stk_cd",
        required=True,
    )

    quantity_text = str(candidate.requested_quantity)
    _require_provider_string(
        quantity_text,
        "ord_qty",
        required=True,
    )

    if candidate.order_style is WatchlistOrderIntentStyle.MARKET:
        order_price_text = ""
        trade_type = "3"
    elif candidate.order_style is WatchlistOrderIntentStyle.LIMIT:
        order_price_text = str(candidate.limit_price)
        trade_type = "0"
    else:
        raise KiwoomOrderMappingError(
            "order_style is not supported."
        )

    _require_provider_string(
        order_price_text,
        "ord_uv",
        required=False,
    )
    _require_provider_string(
        trade_type,
        "trde_tp",
        required=True,
    )
    _require_provider_string("", "cond_uv", required=False)


def _validate_snapshot(snapshot: object) -> WatchlistAccountValidationSnapshot:
    if type(snapshot) is not WatchlistAccountValidationSnapshot:
        raise KiwoomOrderMappingError(
            "snapshot must be WatchlistAccountValidationSnapshot."
        )

    if type(snapshot.validations) is not tuple:
        raise KiwoomOrderMappingError(
            "snapshot validations must be a tuple."
        )
    _validate_count_contract(snapshot)

    _require_nonnegative_int(
        snapshot.initial_available_buying_power,
        "initial_available_buying_power",
    )
    _require_nonnegative_int(
        snapshot.total_reserved_buying_power,
        "total_reserved_buying_power",
    )
    _require_nonnegative_int(
        snapshot.remaining_buying_power,
        "remaining_buying_power",
    )
    _require_nonempty_string(snapshot.account_context_id, "account_context_id")
    _require_nonempty_string(
        snapshot.evidence_snapshot_id,
        "evidence_snapshot_id",
    )
    _require_nonempty_string(snapshot.realtime_type, "realtime_type")

    if len(snapshot.validations) != snapshot.validation_checked_count:
        raise KiwoomOrderMappingError(
            "validation tuple length does not match validation_checked_count."
        )

    seen_source_ranks: set[int] = set()
    passed_count = 0
    blocked_count = 0
    market_count = 0
    limit_count = 0
    remaining = snapshot.initial_available_buying_power
    reserved = 0

    for candidate in snapshot.validations:
        _validate_candidate_common(candidate, snapshot)

        if candidate.source_rank in seen_source_ranks:
            raise KiwoomOrderMappingError(
                "duplicate source_rank is not allowed."
            )
        seen_source_ranks.add(candidate.source_rank)

        if candidate.order_style is WatchlistOrderIntentStyle.MARKET:
            market_count += 1
        elif candidate.order_style is WatchlistOrderIntentStyle.LIMIT:
            limit_count += 1

        quantity_short = (
            candidate.requested_quantity
            > candidate.max_orderable_quantity
        )
        buying_power_short = candidate.reservation_amount > remaining

        if (
            candidate.account_validation_decision
            is WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED
        ):
            passed_count += 1
            if quantity_short or buying_power_short:
                raise KiwoomOrderMappingError(
                    "PASSED candidate violates Phase 24 buying-power rules."
                )
            if candidate.account_validation_reason_code != _PASS_REASON:
                raise KiwoomOrderMappingError(
                    "PASSED candidate reason code mismatch."
                )
            remaining -= candidate.reservation_amount
            reserved += candidate.reservation_amount
            if candidate.remaining_buying_power_after != remaining:
                raise KiwoomOrderMappingError(
                    "PASSED remaining_buying_power_after mismatch."
                )
            _validate_provider_candidate(candidate)
        elif (
            candidate.account_validation_decision
            is WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED
        ):
            blocked_count += 1
            expected_reason = None
            if quantity_short:
                expected_reason = _QUANTITY_BLOCK_REASON
            elif buying_power_short:
                expected_reason = _BUYING_POWER_BLOCK_REASON
            else:
                raise KiwoomOrderMappingError(
                    "BLOCKED candidate has no Phase 24 shortage condition."
                )
            if candidate.account_validation_reason_code != expected_reason:
                raise KiwoomOrderMappingError(
                    "BLOCKED candidate reason code mismatch."
                )
            if candidate.remaining_buying_power_after != remaining:
                raise KiwoomOrderMappingError(
                    "BLOCKED candidate must not consume buying power."
                )
        else:
            raise KiwoomOrderMappingError(
                "account_validation_decision is not supported."
            )

    if passed_count != snapshot.validation_passed_count:
        raise KiwoomOrderMappingError(
            "validation_passed_count does not match validations."
        )
    if blocked_count != snapshot.validation_blocked_count:
        raise KiwoomOrderMappingError(
            "validation_blocked_count does not match validations."
        )
    if market_count != snapshot.market_order_count:
        raise KiwoomOrderMappingError(
            "market_order_count does not match validations."
        )
    if limit_count != snapshot.limit_order_count:
        raise KiwoomOrderMappingError(
            "limit_order_count does not match validations."
        )
    if reserved != snapshot.total_reserved_buying_power:
        raise KiwoomOrderMappingError(
            "total_reserved_buying_power does not match PASSED reservations."
        )
    if remaining != snapshot.remaining_buying_power:
        raise KiwoomOrderMappingError(
            "remaining_buying_power does not match cumulative validation."
        )
    if snapshot.initial_available_buying_power != (
        snapshot.total_reserved_buying_power
        + snapshot.remaining_buying_power
    ):
        raise KiwoomOrderMappingError(
            "buying-power summary violates the Phase 24 invariant."
        )

    return snapshot


def _build_request(
    candidate: WatchlistCandidateAccountValidation,
) -> KiwoomBuyOrderRequest:
    if type(candidate.venue) is not MarketVenue:
        raise KiwoomOrderMappingError(
            "PASSED candidate venue must be MarketVenue."
        )
    if candidate.order_style is WatchlistOrderIntentStyle.MARKET:
        order_price = ""
        trade_type = "3"
    elif candidate.order_style is WatchlistOrderIntentStyle.LIMIT:
        order_price = str(candidate.limit_price)
        trade_type = "0"
    else:
        raise KiwoomOrderMappingError(
            "order_style is not supported."
        )
    return KiwoomBuyOrderRequest(
        dmst_stex_tp=candidate.venue.value,
        stk_cd=candidate.stock_code,
        ord_qty=str(candidate.requested_quantity),
        ord_uv=order_price,
        trde_tp=trade_type,
        cond_uv="",
    )


def _build_mapping(
    candidate: WatchlistCandidateAccountValidation,
) -> WatchlistCandidateKiwoomOrderMapping:
    return WatchlistCandidateKiwoomOrderMapping(
        source_rank=candidate.source_rank,
        stock_code=candidate.stock_code,
        stock_name=candidate.stock_name,
        exchange_scope=candidate.exchange_scope,
        realtime_type=candidate.realtime_type,
        signal_decision=candidate.signal_decision,
        venue=candidate.venue,
        signal_reason_code=candidate.signal_reason_code,
        risk_decision=candidate.risk_decision,
        risk_reason_code=candidate.risk_reason_code,
        order_permission_decision=candidate.order_permission_decision,
        order_permission_reason_code=candidate.order_permission_reason_code,
        order_side=candidate.order_side,
        order_style=candidate.order_style,
        requested_quantity=candidate.requested_quantity,
        limit_price=candidate.limit_price,
        order_intent_reason_code=candidate.order_intent_reason_code,
        account_validation_decision=candidate.account_validation_decision,
        account_validation_reason_code=candidate.account_validation_reason_code,
        reservation_amount=candidate.reservation_amount,
        max_orderable_quantity=candidate.max_orderable_quantity,
        remaining_buying_power_after=candidate.remaining_buying_power_after,
        request=_build_request(candidate),
    )


def build_watchlist_kiwoom_order_mapping_snapshot(
    snapshot: WatchlistAccountValidationSnapshot,
) -> WatchlistKiwoomOrderMappingSnapshot:
    """Return an immutable Kiwoom request mapping snapshot for Phase 24 PASSED items."""

    validated = _validate_snapshot(snapshot)

    mappings = tuple(
        _build_mapping(candidate)
        for candidate in validated.validations
        if (
            candidate.account_validation_decision
            is WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED
        )
    )

    if len(mappings) != validated.validation_passed_count:
        raise KiwoomOrderMappingError(
            "mapping_count does not match validation_passed_count."
        )

    return WatchlistKiwoomOrderMappingSnapshot(
        mappings=mappings,
        candidate_count=validated.candidate_count,
        no_signal_count=validated.no_signal_count,
        risk_checked_count=validated.risk_checked_count,
        risk_clear_count=validated.risk_clear_count,
        risk_blocked_count=validated.risk_blocked_count,
        permission_checked_count=validated.permission_checked_count,
        order_permitted_count=validated.order_permitted_count,
        order_denied_count=validated.order_denied_count,
        intent_planned_count=validated.intent_planned_count,
        market_order_count=validated.market_order_count,
        limit_order_count=validated.limit_order_count,
        validation_checked_count=validated.validation_checked_count,
        validation_passed_count=validated.validation_passed_count,
        validation_blocked_count=validated.validation_blocked_count,
        mapping_count=len(mappings),
        initial_available_buying_power=validated.initial_available_buying_power,
        total_reserved_buying_power=validated.total_reserved_buying_power,
        remaining_buying_power=validated.remaining_buying_power,
        account_context_id=validated.account_context_id,
        evidence_snapshot_id=validated.evidence_snapshot_id,
        realtime_type=validated.realtime_type,
    )


__all__ = [
    "KIWOOM_BUY_ORDER_API_ID",
    "KIWOOM_ORDER_API_PATH",
    "KiwoomOrderMappingError",
    "KiwoomBuyOrderRequest",
    "WatchlistCandidateKiwoomOrderMapping",
    "WatchlistKiwoomOrderMappingSnapshot",
    "build_watchlist_kiwoom_order_mapping_snapshot",
]
