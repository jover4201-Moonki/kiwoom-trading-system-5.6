"""Build an immutable Phase 24 account / buying-power validation snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kiwoom_trading_system.market_data import MarketVenue
from kiwoom_trading_system.orders.watchlist_order_intent import (
    WatchlistCandidateOrderIntent,
    WatchlistOrderIntentSide,
    WatchlistOrderIntentSnapshot,
    WatchlistOrderIntentStyle,
)
from kiwoom_trading_system.orders.watchlist_order_permission import (
    WatchlistOrderPermissionDecision,
)
from kiwoom_trading_system.risk import WatchlistRiskDecision
from kiwoom_trading_system.strategies import WatchlistSignalDecision


class WatchlistAccountValidationError(ValueError):
    """Raised when Phase 24 account validation violates its pure contract."""


class WatchlistAccountValidationDecision(str, Enum):
    """Allowed Phase 24 validation decisions."""

    ACCOUNT_VALIDATION_PASSED = "ACCOUNT_VALIDATION_PASSED"
    ACCOUNT_VALIDATION_BLOCKED = "ACCOUNT_VALIDATION_BLOCKED"


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise WatchlistAccountValidationError(f"{field_name} must be a string.")
    if not value.strip():
        raise WatchlistAccountValidationError(
            f"{field_name} must not be empty or whitespace."
        )


def _require_nonnegative_integer(value: object, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise WatchlistAccountValidationError(
            f"{field_name} must be a non-negative integer."
        )


def _require_positive_integer(value: object, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise WatchlistAccountValidationError(
            f"{field_name} must be a positive integer."
        )


def _validate_order_terms(
    order_side: object,
    order_style: object,
    requested_quantity: object,
    limit_price: object,
    prefix: str,
) -> None:
    if type(order_side) is not WatchlistOrderIntentSide:
        raise WatchlistAccountValidationError(
            f"{prefix} order_side must be WatchlistOrderIntentSide."
        )
    if order_side is not WatchlistOrderIntentSide.BUY:
        raise WatchlistAccountValidationError(f"{prefix} order_side must be BUY.")
    if type(order_style) is not WatchlistOrderIntentStyle:
        raise WatchlistAccountValidationError(
            f"{prefix} order_style must be WatchlistOrderIntentStyle."
        )

    _require_positive_integer(requested_quantity, f"{prefix} requested_quantity")

    if order_style is WatchlistOrderIntentStyle.MARKET:
        if limit_price is not None:
            raise WatchlistAccountValidationError(
                f"{prefix} MARKET limit_price must be None."
            )
    elif order_style is WatchlistOrderIntentStyle.LIMIT:
        _require_positive_integer(limit_price, f"{prefix} LIMIT limit_price")
    else:
        raise WatchlistAccountValidationError(
            f"{prefix} order_style is not supported."
        )


@dataclass(frozen=True, slots=True)
class WatchlistIntentBuyingPowerEvidence:
    """Immutable normalized buying-power evidence for one Phase 23 intent."""

    source_rank: int
    stock_code: str
    exchange_scope: str
    venue: MarketVenue | None
    order_side: WatchlistOrderIntentSide
    order_style: WatchlistOrderIntentStyle
    requested_quantity: int
    limit_price: int | None
    reservation_amount: int
    max_orderable_quantity: int
    account_context_id: str
    evidence_snapshot_id: str

    def __post_init__(self) -> None:
        _validate_evidence(self)


@dataclass(frozen=True, slots=True)
class WatchlistAccountValidationContext:
    """Immutable normalized account context supplied by a future adapter."""

    account_context_id: str
    evidence_snapshot_id: str
    is_fresh: bool
    available_buying_power: int
    evidences: tuple[WatchlistIntentBuyingPowerEvidence, ...]

    def __post_init__(self) -> None:
        _validate_context(self)


@dataclass(frozen=True, slots=True)
class WatchlistCandidateAccountValidation:
    """Immutable Phase 24 validation result for one Phase 23 order intent."""

    source_rank: int
    stock_code: str
    stock_name: str
    exchange_scope: str
    realtime_type: str
    signal_decision: WatchlistSignalDecision
    venue: MarketVenue | None
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


@dataclass(frozen=True, slots=True)
class WatchlistAccountValidationSnapshot:
    """Immutable ordered Phase 24 account-validation snapshot."""

    validations: tuple[WatchlistCandidateAccountValidation, ...]
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
    initial_available_buying_power: int
    total_reserved_buying_power: int
    remaining_buying_power: int
    account_context_id: str
    evidence_snapshot_id: str
    realtime_type: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "validations", tuple(self.validations))


def _validate_evidence(evidence: WatchlistIntentBuyingPowerEvidence) -> None:
    if type(evidence) is not WatchlistIntentBuyingPowerEvidence:
        raise WatchlistAccountValidationError(
            "evidence must be WatchlistIntentBuyingPowerEvidence."
        )

    _require_positive_integer(evidence.source_rank, "evidence source_rank")
    _require_nonempty_string(evidence.stock_code, "evidence stock_code")
    _require_nonempty_string(evidence.exchange_scope, "evidence exchange_scope")

    if evidence.venue is not None and not isinstance(evidence.venue, MarketVenue):
        raise WatchlistAccountValidationError(
            "evidence venue must be MarketVenue or None."
        )

    _validate_order_terms(
        evidence.order_side,
        evidence.order_style,
        evidence.requested_quantity,
        evidence.limit_price,
        "evidence",
    )
    _require_positive_integer(
        evidence.reservation_amount,
        "evidence reservation_amount",
    )
    _require_nonnegative_integer(
        evidence.max_orderable_quantity,
        "evidence max_orderable_quantity",
    )
    _require_nonempty_string(
        evidence.account_context_id,
        "evidence account_context_id",
    )
    _require_nonempty_string(
        evidence.evidence_snapshot_id,
        "evidence evidence_snapshot_id",
    )


def _validate_context(context: WatchlistAccountValidationContext) -> None:
    if type(context) is not WatchlistAccountValidationContext:
        raise WatchlistAccountValidationError(
            "context must be WatchlistAccountValidationContext."
        )

    _require_nonempty_string(context.account_context_id, "context account_context_id")
    _require_nonempty_string(
        context.evidence_snapshot_id,
        "context evidence_snapshot_id",
    )

    if type(context.is_fresh) is not bool:
        raise WatchlistAccountValidationError("context is_fresh must be bool.")
    if context.is_fresh is not True:
        raise WatchlistAccountValidationError("context is_fresh must be True.")

    _require_nonnegative_integer(
        context.available_buying_power,
        "context available_buying_power",
    )

    if type(context.evidences) is not tuple:
        raise WatchlistAccountValidationError("context evidences must be a tuple.")

    for evidence in context.evidences:
        _validate_evidence(evidence)


def _validate_order_intent_snapshot(snapshot: WatchlistOrderIntentSnapshot) -> None:
    if not isinstance(snapshot, WatchlistOrderIntentSnapshot):
        raise WatchlistAccountValidationError(
            "snapshot must be WatchlistOrderIntentSnapshot."
        )

    for field_name in (
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
    ):
        _require_nonnegative_integer(
            getattr(snapshot, field_name),
            f"snapshot {field_name}",
        )

    _require_nonempty_string(snapshot.realtime_type, "snapshot realtime_type")

    if type(snapshot.intents) is not tuple:
        raise WatchlistAccountValidationError("snapshot intents must be a tuple.")

    if snapshot.candidate_count != snapshot.no_signal_count + snapshot.risk_checked_count:
        raise WatchlistAccountValidationError(
            "candidate_count must equal no_signal_count plus risk_checked_count."
        )
    if snapshot.risk_checked_count != snapshot.risk_clear_count + snapshot.risk_blocked_count:
        raise WatchlistAccountValidationError(
            "risk_checked_count must equal risk_clear_count plus risk_blocked_count."
        )
    if snapshot.permission_checked_count != snapshot.risk_clear_count:
        raise WatchlistAccountValidationError(
            "permission_checked_count must equal risk_clear_count."
        )
    if snapshot.permission_checked_count != snapshot.order_permitted_count + snapshot.order_denied_count:
        raise WatchlistAccountValidationError(
            "permission_checked_count must equal order_permitted_count plus order_denied_count."
        )
    if snapshot.intent_planned_count != snapshot.order_permitted_count:
        raise WatchlistAccountValidationError(
            "intent_planned_count must equal order_permitted_count."
        )
    if len(snapshot.intents) != snapshot.intent_planned_count:
        raise WatchlistAccountValidationError(
            "snapshot intents length must equal intent_planned_count."
        )
    if snapshot.market_order_count + snapshot.limit_order_count != snapshot.intent_planned_count:
        raise WatchlistAccountValidationError(
            "market_order_count plus limit_order_count must equal intent_planned_count."
        )

    seen_source_ranks: set[int] = set()
    market_count = 0
    limit_count = 0

    for intent in snapshot.intents:
        if type(intent) is not WatchlistCandidateOrderIntent:
            raise WatchlistAccountValidationError(
                "snapshot intents must contain WatchlistCandidateOrderIntent."
            )

        _require_positive_integer(intent.source_rank, "intent source_rank")
        if intent.source_rank in seen_source_ranks:
            raise WatchlistAccountValidationError(
                "intent source_rank values must be unique."
            )
        seen_source_ranks.add(intent.source_rank)

        for field_name in (
            "stock_code",
            "stock_name",
            "exchange_scope",
            "realtime_type",
            "signal_reason_code",
            "risk_reason_code",
            "order_permission_reason_code",
            "order_intent_reason_code",
        ):
            _require_nonempty_string(
                getattr(intent, field_name),
                f"intent {field_name}",
            )

        if intent.realtime_type != snapshot.realtime_type:
            raise WatchlistAccountValidationError(
                "intent realtime_type must match snapshot realtime_type."
            )
        if (
            type(intent.signal_decision) is not WatchlistSignalDecision
            or intent.signal_decision is not WatchlistSignalDecision.ENTRY_CANDIDATE
        ):
            raise WatchlistAccountValidationError(
                "intent signal_decision must be ENTRY_CANDIDATE."
            )
        if intent.venue is not None and not isinstance(intent.venue, MarketVenue):
            raise WatchlistAccountValidationError(
                "intent venue must be MarketVenue or None."
            )
        if (
            type(intent.risk_decision) is not WatchlistRiskDecision
            or intent.risk_decision is not WatchlistRiskDecision.RISK_CLEAR
        ):
            raise WatchlistAccountValidationError(
                "intent risk_decision must be RISK_CLEAR."
            )
        if (
            type(intent.order_permission_decision) is not WatchlistOrderPermissionDecision
            or intent.order_permission_decision is not WatchlistOrderPermissionDecision.ORDER_PERMITTED
        ):
            raise WatchlistAccountValidationError(
                "intent order_permission_decision must be ORDER_PERMITTED."
            )

        _validate_order_terms(
            intent.order_side,
            intent.order_style,
            intent.requested_quantity,
            intent.limit_price,
            "intent",
        )

        if intent.order_style is WatchlistOrderIntentStyle.MARKET:
            market_count += 1
        elif intent.order_style is WatchlistOrderIntentStyle.LIMIT:
            limit_count += 1

    if market_count != snapshot.market_order_count:
        raise WatchlistAccountValidationError(
            "snapshot market_order_count does not match its intents."
        )
    if limit_count != snapshot.limit_order_count:
        raise WatchlistAccountValidationError(
            "snapshot limit_order_count does not match its intents."
        )


def _validate_context_evidence_identity(
    snapshot: WatchlistOrderIntentSnapshot,
    context: WatchlistAccountValidationContext,
) -> None:
    if len(context.evidences) != snapshot.intent_planned_count:
        raise WatchlistAccountValidationError(
            "context evidences length must equal intent_planned_count."
        )

    seen_evidence_ranks: set[int] = set()

    for intent, evidence in zip(snapshot.intents, context.evidences, strict=True):
        _validate_evidence(evidence)

        if evidence.source_rank in seen_evidence_ranks:
            raise WatchlistAccountValidationError(
                "evidence source_rank values must be unique."
            )
        seen_evidence_ranks.add(evidence.source_rank)

        if evidence.account_context_id != context.account_context_id:
            raise WatchlistAccountValidationError(
                "evidence account_context_id must match context account_context_id."
            )
        if evidence.evidence_snapshot_id != context.evidence_snapshot_id:
            raise WatchlistAccountValidationError(
                "evidence evidence_snapshot_id must match context evidence_snapshot_id."
            )

        identity_pairs = (
            ("source_rank", intent.source_rank, evidence.source_rank),
            ("stock_code", intent.stock_code, evidence.stock_code),
            ("exchange_scope", intent.exchange_scope, evidence.exchange_scope),
            ("venue", intent.venue, evidence.venue),
            ("order_side", intent.order_side, evidence.order_side),
            ("order_style", intent.order_style, evidence.order_style),
            (
                "requested_quantity",
                intent.requested_quantity,
                evidence.requested_quantity,
            ),
            ("limit_price", intent.limit_price, evidence.limit_price),
        )

        for field_name, intent_value, evidence_value in identity_pairs:
            if evidence_value != intent_value:
                raise WatchlistAccountValidationError(
                    f"evidence {field_name} must exactly match its intent."
                )


def build_watchlist_account_validation_snapshot(
    snapshot: WatchlistOrderIntentSnapshot,
    context: WatchlistAccountValidationContext,
) -> WatchlistAccountValidationSnapshot:
    """Validate Phase 23 intents using immutable normalized account evidence."""

    _validate_order_intent_snapshot(snapshot)
    _validate_context(context)
    _validate_context_evidence_identity(snapshot, context)

    remaining_buying_power = context.available_buying_power
    total_reserved_buying_power = 0
    passed_count = 0
    blocked_count = 0
    validations: list[WatchlistCandidateAccountValidation] = []

    for intent, evidence in zip(snapshot.intents, context.evidences, strict=True):
        if intent.requested_quantity > evidence.max_orderable_quantity:
            decision = WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED
            reason_code = "MAX_ORDERABLE_QUANTITY_INSUFFICIENT"
            blocked_count += 1
        elif evidence.reservation_amount > remaining_buying_power:
            decision = WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_BLOCKED
            reason_code = "BUYING_POWER_INSUFFICIENT"
            blocked_count += 1
        else:
            decision = WatchlistAccountValidationDecision.ACCOUNT_VALIDATION_PASSED
            reason_code = "ACCOUNT_VALIDATION_OK"
            remaining_buying_power -= evidence.reservation_amount
            total_reserved_buying_power += evidence.reservation_amount
            passed_count += 1

        validations.append(
            WatchlistCandidateAccountValidation(
                source_rank=intent.source_rank,
                stock_code=intent.stock_code,
                stock_name=intent.stock_name,
                exchange_scope=intent.exchange_scope,
                realtime_type=intent.realtime_type,
                signal_decision=intent.signal_decision,
                venue=intent.venue,
                signal_reason_code=intent.signal_reason_code,
                risk_decision=intent.risk_decision,
                risk_reason_code=intent.risk_reason_code,
                order_permission_decision=intent.order_permission_decision,
                order_permission_reason_code=intent.order_permission_reason_code,
                order_side=intent.order_side,
                order_style=intent.order_style,
                requested_quantity=intent.requested_quantity,
                limit_price=intent.limit_price,
                order_intent_reason_code=intent.order_intent_reason_code,
                account_validation_decision=decision,
                account_validation_reason_code=reason_code,
                reservation_amount=evidence.reservation_amount,
                max_orderable_quantity=evidence.max_orderable_quantity,
                remaining_buying_power_after=remaining_buying_power,
            )
        )

    validation_tuple = tuple(validations)
    checked_count = len(validation_tuple)

    if checked_count != snapshot.intent_planned_count:
        raise WatchlistAccountValidationError(
            "validation_checked_count must equal intent_planned_count."
        )
    if checked_count != passed_count + blocked_count:
        raise WatchlistAccountValidationError(
            "validation_checked_count must equal passed plus blocked counts."
        )
    if (
        context.available_buying_power
        != total_reserved_buying_power + remaining_buying_power
    ):
        raise WatchlistAccountValidationError(
            "initial buying power must equal reserved plus remaining buying power."
        )
    if remaining_buying_power < 0 or total_reserved_buying_power < 0:
        raise WatchlistAccountValidationError(
            "buying-power accounting must not be negative."
        )

    return WatchlistAccountValidationSnapshot(
        validations=validation_tuple,
        candidate_count=snapshot.candidate_count,
        no_signal_count=snapshot.no_signal_count,
        risk_checked_count=snapshot.risk_checked_count,
        risk_clear_count=snapshot.risk_clear_count,
        risk_blocked_count=snapshot.risk_blocked_count,
        permission_checked_count=snapshot.permission_checked_count,
        order_permitted_count=snapshot.order_permitted_count,
        order_denied_count=snapshot.order_denied_count,
        intent_planned_count=snapshot.intent_planned_count,
        market_order_count=snapshot.market_order_count,
        limit_order_count=snapshot.limit_order_count,
        validation_checked_count=checked_count,
        validation_passed_count=passed_count,
        validation_blocked_count=blocked_count,
        initial_available_buying_power=context.available_buying_power,
        total_reserved_buying_power=total_reserved_buying_power,
        remaining_buying_power=remaining_buying_power,
        account_context_id=context.account_context_id,
        evidence_snapshot_id=context.evidence_snapshot_id,
        realtime_type=snapshot.realtime_type,
    )


__all__ = [
    "WatchlistAccountValidationError",
    "WatchlistAccountValidationDecision",
    "WatchlistIntentBuyingPowerEvidence",
    "WatchlistAccountValidationContext",
    "WatchlistCandidateAccountValidation",
    "WatchlistAccountValidationSnapshot",
    "build_watchlist_account_validation_snapshot",
]
