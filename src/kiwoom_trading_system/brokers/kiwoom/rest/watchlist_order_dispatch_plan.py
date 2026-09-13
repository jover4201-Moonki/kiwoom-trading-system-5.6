"""Build a pure Phase 26 Kiwoom demo buy-order dry-run dispatch plan snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_mapping import (
    KIWOOM_BUY_ORDER_API_ID,
    KIWOOM_ORDER_API_PATH,
    KiwoomBuyOrderRequest,
    WatchlistCandidateKiwoomOrderMapping,
    WatchlistKiwoomOrderMappingSnapshot,
)
from kiwoom_trading_system.market_data import MarketVenue


KIWOOM_DEMO_ORDER_BASE_URL = "https://mockapi.kiwoom.com"
KIWOOM_ORDER_HTTP_METHOD = "POST"
KIWOOM_ORDER_CONTENT_TYPE = "application/json;charset=UTF-8"


class KiwoomOrderDispatchPlanError(ValueError):
    """Raised when a Phase 26 dispatch-plan input violates the contract."""


class KiwoomDemoOrderDispatchDecision(str, Enum):
    """Allowed local dry-run dispatch decisions for the Kiwoom demo boundary."""

    DRY_RUN_SUPPORTED = "DRY_RUN_SUPPORTED"
    DRY_RUN_BLOCKED = "DRY_RUN_BLOCKED"


class KiwoomDemoOrderDispatchBlockReason(str, Enum):
    """Allowed reason for a locally blocked Phase 26 demo dispatch."""

    DEMO_VENUE_UNSUPPORTED = "DEMO_VENUE_UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class KiwoomBuyOrderDispatchPlan:
    """Immutable non-sending dispatch metadata for one existing Phase 25 request."""

    base_url: str
    http_method: str
    api_id: str
    api_path: str
    content_type: str
    request: KiwoomBuyOrderRequest
    decision: KiwoomDemoOrderDispatchDecision
    block_reason: KiwoomDemoOrderDispatchBlockReason | None
    send_authorized: bool

    def __post_init__(self) -> None:
        if self.base_url != KIWOOM_DEMO_ORDER_BASE_URL:
            raise KiwoomOrderDispatchPlanError("base_url must be the approved demo URL.")
        if self.http_method != KIWOOM_ORDER_HTTP_METHOD:
            raise KiwoomOrderDispatchPlanError("http_method must be POST.")
        if self.api_id != KIWOOM_BUY_ORDER_API_ID:
            raise KiwoomOrderDispatchPlanError("api_id must match Phase 25.")
        if self.api_path != KIWOOM_ORDER_API_PATH:
            raise KiwoomOrderDispatchPlanError("api_path must match Phase 25.")
        if self.content_type != KIWOOM_ORDER_CONTENT_TYPE:
            raise KiwoomOrderDispatchPlanError(
                "content_type must match the approved JSON content type."
            )
        if type(self.request) is not KiwoomBuyOrderRequest:
            raise TypeError("request must be KiwoomBuyOrderRequest.")
        if type(self.decision) is not KiwoomDemoOrderDispatchDecision:
            raise TypeError("decision must be KiwoomDemoOrderDispatchDecision.")
        if self.block_reason is not None and type(self.block_reason) is not KiwoomDemoOrderDispatchBlockReason:
            raise TypeError(
                "block_reason must be KiwoomDemoOrderDispatchBlockReason or None."
            )
        if type(self.send_authorized) is not bool or self.send_authorized:
            raise KiwoomOrderDispatchPlanError("send_authorized must be exactly False.")

        if self.decision is KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED:
            if self.block_reason is not None:
                raise KiwoomOrderDispatchPlanError(
                    "supported dispatch must not have a block reason."
                )
        elif self.decision is KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED:
            if (
                self.block_reason
                is not KiwoomDemoOrderDispatchBlockReason.DEMO_VENUE_UNSUPPORTED
            ):
                raise KiwoomOrderDispatchPlanError(
                    "blocked dispatch must use DEMO_VENUE_UNSUPPORTED."
                )
        else:
            raise KiwoomOrderDispatchPlanError("unsupported dispatch decision.")


@dataclass(frozen=True, slots=True)
class WatchlistCandidateKiwoomOrderDispatchPlan:
    """Immutable Phase 26 wrapper around one existing Phase 25 mapping."""

    source_mapping: WatchlistCandidateKiwoomOrderMapping
    dispatch_plan: KiwoomBuyOrderDispatchPlan

    def __post_init__(self) -> None:
        if type(self.source_mapping) is not WatchlistCandidateKiwoomOrderMapping:
            raise TypeError(
                "source_mapping must be WatchlistCandidateKiwoomOrderMapping."
            )
        if type(self.dispatch_plan) is not KiwoomBuyOrderDispatchPlan:
            raise TypeError("dispatch_plan must be KiwoomBuyOrderDispatchPlan.")
        if self.dispatch_plan.request is not self.source_mapping.request:
            raise KiwoomOrderDispatchPlanError(
                "dispatch request identity must match source_mapping.request."
            )


@dataclass(frozen=True, slots=True)
class WatchlistKiwoomOrderDispatchPlanSnapshot:
    """Immutable ordered Phase 26 dry-run dispatch-plan snapshot."""

    source_snapshot: WatchlistKiwoomOrderMappingSnapshot
    plans: tuple[WatchlistCandidateKiwoomOrderDispatchPlan, ...]
    candidate_count: int
    dry_run_supported_count: int
    dry_run_blocked_count: int
    send_authorized_count: int

    def __post_init__(self) -> None:
        if type(self.source_snapshot) is not WatchlistKiwoomOrderMappingSnapshot:
            raise TypeError(
                "source_snapshot must be WatchlistKiwoomOrderMappingSnapshot."
            )
        if type(self.plans) is not tuple:
            raise TypeError("plans must be a tuple.")

        for name in (
            "candidate_count",
            "dry_run_supported_count",
            "dry_run_blocked_count",
            "send_authorized_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise KiwoomOrderDispatchPlanError(
                    f"{name} must be a non-negative integer."
                )

        if self.candidate_count != len(self.plans):
            raise KiwoomOrderDispatchPlanError(
                "candidate_count must equal the plans tuple length."
            )
        if self.candidate_count != len(self.source_snapshot.mappings):
            raise KiwoomOrderDispatchPlanError(
                "candidate_count must equal the source mapping tuple length."
            )
        if self.candidate_count != (
            self.dry_run_supported_count + self.dry_run_blocked_count
        ):
            raise KiwoomOrderDispatchPlanError(
                "candidate_count must equal supported plus blocked counts."
            )
        if self.send_authorized_count != 0:
            raise KiwoomOrderDispatchPlanError(
                "send_authorized_count must remain exactly zero."
            )

        supported = 0
        blocked = 0
        for index, item in enumerate(self.plans):
            if type(item) is not WatchlistCandidateKiwoomOrderDispatchPlan:
                raise TypeError(
                    "plans must contain WatchlistCandidateKiwoomOrderDispatchPlan."
                )
            if item.source_mapping is not self.source_snapshot.mappings[index]:
                raise KiwoomOrderDispatchPlanError(
                    "plan ordering or source mapping identity changed."
                )
            if item.dispatch_plan.request is not item.source_mapping.request:
                raise KiwoomOrderDispatchPlanError(
                    "plan request identity changed."
                )
            if item.dispatch_plan.send_authorized:
                raise KiwoomOrderDispatchPlanError(
                    "Phase 26 must never authorize sending."
                )
            if (
                item.dispatch_plan.decision
                is KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED
            ):
                supported += 1
            elif (
                item.dispatch_plan.decision
                is KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED
            ):
                blocked += 1
            else:
                raise KiwoomOrderDispatchPlanError(
                    "plan contains an unsupported dispatch decision."
                )

        if supported != self.dry_run_supported_count:
            raise KiwoomOrderDispatchPlanError(
                "dry_run_supported_count does not match plans."
            )
        if blocked != self.dry_run_blocked_count:
            raise KiwoomOrderDispatchPlanError(
                "dry_run_blocked_count does not match plans."
            )


def _validate_mapping(mapping: object) -> WatchlistCandidateKiwoomOrderMapping:
    if type(mapping) is not WatchlistCandidateKiwoomOrderMapping:
        raise TypeError(
            "snapshot mappings must contain WatchlistCandidateKiwoomOrderMapping."
        )

    if type(mapping.venue) is not MarketVenue:
        raise KiwoomOrderDispatchPlanError(
            "mapping venue must be an exact MarketVenue value."
        )
    if type(mapping.request) is not KiwoomBuyOrderRequest:
        raise TypeError("mapping request must be KiwoomBuyOrderRequest.")

    request = mapping.request
    for field_name in (
        "dmst_stex_tp",
        "stk_cd",
        "ord_qty",
        "ord_uv",
        "trde_tp",
        "cond_uv",
    ):
        if type(getattr(request, field_name)) is not str:
            raise KiwoomOrderDispatchPlanError(
                f"request {field_name} must remain a string."
            )

    if request.dmst_stex_tp != mapping.venue.value:
        raise KiwoomOrderDispatchPlanError(
            "request venue must match source_mapping.venue."
        )
    if request.stk_cd != mapping.stock_code:
        raise KiwoomOrderDispatchPlanError(
            "request stock code must match source_mapping.stock_code."
        )
    if request.ord_qty != str(mapping.requested_quantity):
        raise KiwoomOrderDispatchPlanError(
            "request quantity must match source_mapping.requested_quantity."
        )

    return mapping


def _decision_for_venue(
    venue: MarketVenue,
) -> tuple[
    KiwoomDemoOrderDispatchDecision,
    KiwoomDemoOrderDispatchBlockReason | None,
]:
    if venue is MarketVenue.KRX:
        return (
            KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED,
            None,
        )
    if venue is MarketVenue.NXT or venue is MarketVenue.SOR:
        return (
            KiwoomDemoOrderDispatchDecision.DRY_RUN_BLOCKED,
            KiwoomDemoOrderDispatchBlockReason.DEMO_VENUE_UNSUPPORTED,
        )
    raise KiwoomOrderDispatchPlanError("mapping venue is not supported.")


def build_watchlist_kiwoom_order_dispatch_plan_snapshot(
    snapshot: WatchlistKiwoomOrderMappingSnapshot,
) -> WatchlistKiwoomOrderDispatchPlanSnapshot:
    """Build a local dry-run plan without sending, networking, or remapping."""

    if type(snapshot) is not WatchlistKiwoomOrderMappingSnapshot:
        raise TypeError("snapshot must be WatchlistKiwoomOrderMappingSnapshot.")
    if type(snapshot.mappings) is not tuple:
        raise KiwoomOrderDispatchPlanError("snapshot mappings must be a tuple.")
    if type(snapshot.mapping_count) is not int or snapshot.mapping_count < 0:
        raise KiwoomOrderDispatchPlanError(
            "snapshot mapping_count must be a non-negative integer."
        )
    if snapshot.mapping_count != len(snapshot.mappings):
        raise KiwoomOrderDispatchPlanError(
            "snapshot mapping_count must equal its mapping tuple length."
        )

    validated = tuple(_validate_mapping(mapping) for mapping in snapshot.mappings)

    plans: list[WatchlistCandidateKiwoomOrderDispatchPlan] = []
    supported_count = 0
    blocked_count = 0

    for mapping in validated:
        decision, reason = _decision_for_venue(mapping.venue)
        if decision is KiwoomDemoOrderDispatchDecision.DRY_RUN_SUPPORTED:
            supported_count += 1
        else:
            blocked_count += 1

        dispatch = KiwoomBuyOrderDispatchPlan(
            base_url=KIWOOM_DEMO_ORDER_BASE_URL,
            http_method=KIWOOM_ORDER_HTTP_METHOD,
            api_id=KIWOOM_BUY_ORDER_API_ID,
            api_path=KIWOOM_ORDER_API_PATH,
            content_type=KIWOOM_ORDER_CONTENT_TYPE,
            request=mapping.request,
            decision=decision,
            block_reason=reason,
            send_authorized=False,
        )
        plans.append(
            WatchlistCandidateKiwoomOrderDispatchPlan(
                source_mapping=mapping,
                dispatch_plan=dispatch,
            )
        )

    return WatchlistKiwoomOrderDispatchPlanSnapshot(
        source_snapshot=snapshot,
        plans=tuple(plans),
        candidate_count=len(plans),
        dry_run_supported_count=supported_count,
        dry_run_blocked_count=blocked_count,
        send_authorized_count=0,
    )


__all__ = [
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
]
