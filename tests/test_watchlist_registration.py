from __future__ import annotations

import unittest
from unittest.mock import patch

from kiwoom_trading_system.brokers.kiwoom import websocket
from kiwoom_trading_system.brokers.kiwoom.websocket.watchlist_registration import (
    DEMO_REGISTRATION_GROUP_NO,
    DEMO_REGISTRATION_REFRESH,
    build_demo_watchlist_registration_request,
)
from kiwoom_trading_system.screening import (
    DEFAULT_REALTIME_TYPE,
    RealtimeWatchCandidate,
    RealtimeWatchlist,
    RealtimeWatchlistMetrics,
)

MODULE_PATH = (
    "kiwoom_trading_system.brokers.kiwoom.websocket."
    "watchlist_registration"
)


def _watchlist(
    codes: tuple[str, ...],
    *,
    scopes: tuple[str, ...] | None = None,
    realtime_type: str = DEFAULT_REALTIME_TYPE,
) -> RealtimeWatchlist:
    normalized_scopes = scopes or tuple("KRX" for _ in codes)
    candidates = tuple(
        RealtimeWatchCandidate(
            source_rank=index,
            stock_code=code,
            stock_name=f"stock-{index}",
            exchange_scope=normalized_scopes[index - 1],
        )
        for index, code in enumerate(codes, start=1)
    )
    return RealtimeWatchlist(
        candidates=candidates,
        metrics=RealtimeWatchlistMetrics(
            input_candidate_count=len(candidates),
            accepted_candidate_count=len(candidates),
            invalid_code_count=0,
            duplicate_code_count=0,
        ),
        realtime_type=realtime_type,
    )


class DemoWatchlistRegistrationRequestTests(unittest.TestCase):
    def test_builds_exact_single_item_reg_request(self) -> None:
        result = build_demo_watchlist_registration_request(
            _watchlist(("005930",))
        )

        self.assertEqual(
            result,
            {
                "trnm": "REG",
                "grp_no": "1",
                "refresh": "1",
                "data": [{"item": ["005930"], "type": ["0B"]}],
            },
        )

    def test_preserves_multiple_item_order(self) -> None:
        result = build_demo_watchlist_registration_request(
            _watchlist(("035420", "005930", "000660"))
        )

        self.assertEqual(
            result["data"][0]["item"],
            ["035420", "005930", "000660"],
        )

    def test_converts_empty_watchlist_without_inventing_server_policy(self) -> None:
        result = build_demo_watchlist_registration_request(_watchlist(()))

        self.assertEqual(result["data"][0]["item"], [])
        self.assertEqual(result["data"][0]["type"], ["0B"])

    def test_does_not_mutate_watchlist(self) -> None:
        watchlist = _watchlist(("035420", "005930"))
        original_candidates = watchlist.candidates
        original_metrics = watchlist.metrics

        build_demo_watchlist_registration_request(watchlist)

        self.assertIs(watchlist.candidates, original_candidates)
        self.assertIs(watchlist.metrics, original_metrics)
        self.assertEqual(watchlist.stock_codes, ("035420", "005930"))

    def test_returned_item_list_is_independent_from_watchlist(self) -> None:
        watchlist = _watchlist(("005930",))

        result = build_demo_watchlist_registration_request(watchlist)
        result["data"][0]["item"].append("000660")

        self.assertEqual(watchlist.stock_codes, ("005930",))

    def test_delegates_to_sdk_builder_with_exact_arguments(self) -> None:
        watchlist = _watchlist(("005930", "000660"))
        sentinel = {"sentinel": True}

        with patch(
            f"{MODULE_PATH}.build_reg_packet",
            return_value=sentinel,
        ) as builder:
            result = build_demo_watchlist_registration_request(watchlist)

        self.assertIs(result, sentinel)
        builder.assert_called_once_with(
            ["005930", "000660"],
            ["0B"],
            group_no="1",
            refresh="1",
        )

    def test_rejects_non_watchlist_input(self) -> None:
        for value in (None, object(), {"stock_codes": ("005930",)}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    TypeError,
                    "watchlist must be a RealtimeWatchlist",
                ):
                    build_demo_watchlist_registration_request(
                        value  # type: ignore[arg-type]
                    )

    def test_rejects_non_default_realtime_type_before_sdk_call(self) -> None:
        watchlist = _watchlist(("005930",), realtime_type="0C")

        with patch(f"{MODULE_PATH}.build_reg_packet") as builder:
            with self.assertRaisesRegex(ValueError, "realtime_type"):
                build_demo_watchlist_registration_request(watchlist)

        builder.assert_not_called()

    def test_public_package_exports_contract(self) -> None:
        self.assertEqual(websocket.DEMO_REGISTRATION_GROUP_NO, "1")
        self.assertEqual(websocket.DEMO_REGISTRATION_REFRESH, "1")
        self.assertIs(
            websocket.build_demo_watchlist_registration_request,
            build_demo_watchlist_registration_request,
        )

    def test_exchange_scope_metadata_does_not_change_packet_shape(self) -> None:
        watchlist = _watchlist(
            ("005930", "000660", "035420"),
            scopes=("KRX", "NXT", "SOR"),
        )

        result = build_demo_watchlist_registration_request(watchlist)

        self.assertEqual(
            result["data"][0]["item"],
            ["005930", "000660", "035420"],
        )
        self.assertEqual(
            tuple(candidate.exchange_scope for candidate in watchlist.candidates),
            ("KRX", "NXT", "SOR"),
        )

    def test_each_call_uses_fresh_item_and_type_lists(self) -> None:
        watchlist = _watchlist(("005930",))

        first = build_demo_watchlist_registration_request(watchlist)
        second = build_demo_watchlist_registration_request(watchlist)

        self.assertIsNot(first["data"][0]["item"], second["data"][0]["item"])
        self.assertIsNot(first["data"][0]["type"], second["data"][0]["type"])

    def test_sdk_error_propagates_without_mutating_input(self) -> None:
        watchlist = _watchlist(("005930",))
        original_candidates = watchlist.candidates

        with patch(
            f"{MODULE_PATH}.build_reg_packet",
            side_effect=RuntimeError("sdk failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "sdk failure"):
                build_demo_watchlist_registration_request(watchlist)

        self.assertIs(watchlist.candidates, original_candidates)
        self.assertEqual(watchlist.stock_codes, ("005930",))


if __name__ == "__main__":
    unittest.main()
