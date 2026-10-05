from __future__ import annotations

from kiwoom_trading_system.brokers.kiwoom.rest.watchlist_order_provider_submission_boundary import (
    KiwoomOrderProviderSubmissionReceipt,
    WatchlistOrderProviderSubmissionBoundaryError,
    submit_demo_watchlist_order_once,
)

__all__ = ("execute_demo_watchlist_order_once",)


async def execute_demo_watchlist_order_once(
    readiness_snapshot,
    submission_approval,
    execution_context,
    submission_registry,
):
    receipt = await submit_demo_watchlist_order_once(
        readiness_snapshot,
        submission_approval,
        execution_context,
        submission_registry,
    )

    if type(receipt) is not KiwoomOrderProviderSubmissionReceipt:
        raise WatchlistOrderProviderSubmissionBoundaryError(
            "PHASE37_PROVIDER_SUBMISSION_RECEIPT_INVALID"
        )

    transport_attempt_count = receipt.transport_attempt_count

    if (
        type(transport_attempt_count) is not int
        or transport_attempt_count not in (0, 1)
    ):
        raise WatchlistOrderProviderSubmissionBoundaryError(
            "PHASE37_TRANSPORT_ATTEMPT_COUNT_INVALID"
        )

    return receipt
