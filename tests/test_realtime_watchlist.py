from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal
from types import MappingProxyType

import kiwoom_trading_system.screening as screening_package
from kiwoom_trading_system.screening import (
    realtime_watchlist as watchlist,
)
from kiwoom_trading_system.screening.volume_ranking import (
    VolumeRankingCandidate,
    VolumeRankingMetrics,
    VolumeRankingResult,
)


def _candidate(
    code: object,
    *,
    name: str | None = None,
    scope: str = "KRX",
) -> VolumeRankingCandidate:
    return VolumeRankingCandidate(
        stock_code=code,  # type: ignore[arg-type]
        stock_name=name or f"Stock {code}",
        raw_current_price="1000",
        current_price=1000,
        current_price_sign="",
        change_rate_pct=Decimal("1.00"),
        trade_quantity=100,
        trade_turnover_rate_pct=Decimal("2.00"),
        raw_trade_amount="3",
        trade_amount_million_krw=3,
        exchange_scope=scope,
        raw_row=MappingProxyType(
            {"stk_cd": code}
        ),
    )


def _result(
    *candidates: VolumeRankingCandidate,
) -> VolumeRankingResult:
    return VolumeRankingResult(
        candidates=tuple(candidates),
        metrics=VolumeRankingMetrics(
            valid_candidate_count=len(candidates),
            invalid_row_count=0,
            duplicate_row_count=0,
            excluded_by_limit_count=0,
        ),
        raw_response=MappingProxyType({}),
        request_metadata=MappingProxyType(
            {"stex_tp": "1"}
        ),
    )


class RealtimeWatchlistTests(unittest.TestCase):
    def test_default_realtime_type_is_trade_price(
        self,
    ) -> None:
        result = watchlist.build_realtime_watchlist(
            _result()
        )
        self.assertEqual(result.realtime_type, "0B")
        self.assertEqual(
            watchlist.DEFAULT_REALTIME_TYPE,
            "0B",
        )

    def test_preserves_candidate_order_and_source_rank(
        self,
    ) -> None:
        result = watchlist.build_realtime_watchlist(
            _result(
                _candidate("005930"),
                _candidate("000660"),
            )
        )
        self.assertEqual(
            result.stock_codes,
            ("005930", "000660"),
        )
        self.assertEqual(
            tuple(
                item.source_rank
                for item in result.candidates
            ),
            (1, 2),
        )

    def test_preserves_name_and_exchange_scope(
        self,
    ) -> None:
        result = watchlist.build_realtime_watchlist(
            _result(
                _candidate(
                    "005930",
                    name="Samsung",
                    scope="KRX",
                )
            )
        )
        self.assertEqual(
            result.candidates[0].stock_name,
            "Samsung",
        )
        self.assertEqual(
            result.candidates[0].exchange_scope,
            "KRX",
        )

    def test_rejects_non_six_digit_codes_without_aborting(
        self,
    ) -> None:
        invalid_codes: tuple[object, ...] = (
            "",
            "5930",
            "0000660",
            "ABCDEF",
            "００５９３０",
            5930,
        )
        source = [
            _candidate(code)
            for code in invalid_codes
        ]
        source.append(_candidate("005930"))

        result = watchlist.build_realtime_watchlist(
            _result(*source)
        )

        self.assertEqual(
            result.stock_codes,
            ("005930",),
        )
        self.assertEqual(
            result.metrics.invalid_code_count,
            len(invalid_codes),
        )

    def test_duplicate_codes_keep_first_candidate(
        self,
    ) -> None:
        result = watchlist.build_realtime_watchlist(
            _result(
                _candidate(
                    "005930",
                    name="first",
                ),
                _candidate(
                    "005930",
                    name="second",
                ),
            )
        )
        self.assertEqual(
            result.candidates[0].stock_name,
            "first",
        )
        self.assertEqual(
            result.metrics.duplicate_code_count,
            1,
        )

    def test_invalid_first_occurrence_does_not_block_valid_code(
        self,
    ) -> None:
        result = watchlist.build_realtime_watchlist(
            _result(
                _candidate(" 005930"),
                _candidate("005930"),
            )
        )
        self.assertEqual(
            result.stock_codes,
            ("005930",),
        )
        self.assertEqual(
            result.metrics.invalid_code_count,
            1,
        )
        self.assertEqual(
            result.metrics.duplicate_code_count,
            0,
        )

    def test_empty_ranking_result_returns_empty_watchlist(
        self,
    ) -> None:
        result = watchlist.build_realtime_watchlist(
            _result()
        )
        self.assertEqual(result.candidates, ())
        self.assertEqual(result.stock_codes, ())
        self.assertEqual(
            result.metrics.accepted_candidate_count,
            0,
        )

    def test_metrics_reconcile_all_input_candidates(
        self,
    ) -> None:
        result = watchlist.build_realtime_watchlist(
            _result(
                _candidate("005930"),
                _candidate("bad"),
                _candidate("005930"),
                _candidate("000660"),
            )
        )
        metrics = result.metrics

        self.assertEqual(
            metrics.input_candidate_count,
            4,
        )
        self.assertEqual(
            metrics.accepted_candidate_count,
            2,
        )
        self.assertEqual(
            metrics.invalid_code_count,
            1,
        )
        self.assertEqual(
            metrics.duplicate_code_count,
            1,
        )
        self.assertEqual(
            metrics.input_candidate_count,
            metrics.accepted_candidate_count
            + metrics.invalid_code_count
            + metrics.duplicate_code_count,
        )

    def test_result_and_nested_dataclasses_are_frozen(
        self,
    ) -> None:
        result = watchlist.build_realtime_watchlist(
            _result(_candidate("005930"))
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            result.realtime_type = "XX"  # type: ignore[misc]

        with self.assertRaises(
            FrozenInstanceError
        ):
            result.metrics.accepted_candidate_count = 99  # type: ignore[misc]

        with self.assertRaises(
            FrozenInstanceError
        ):
            result.candidates[0].stock_code = "000660"  # type: ignore[misc]

    def test_output_uses_tuples(self) -> None:
        result = watchlist.build_realtime_watchlist(
            _result(_candidate("005930"))
        )
        self.assertIsInstance(
            result.candidates,
            tuple,
        )
        self.assertIsInstance(
            result.stock_codes,
            tuple,
        )

    def test_source_result_is_not_modified(
        self,
    ) -> None:
        source = _result(
            _candidate("005930"),
            _candidate("bad"),
        )
        before = source.candidates

        watchlist.build_realtime_watchlist(source)

        self.assertIs(
            source.candidates,
            before,
        )
        self.assertEqual(
            source.candidates,
            before,
        )

    def test_non_ranking_result_is_rejected(
        self,
    ) -> None:
        for invalid in (
            None,
            (),
            {},
            object(),
        ):
            with self.subTest(
                invalid=invalid
            ):
                with self.assertRaises(
                    TypeError
                ):
                    watchlist.build_realtime_watchlist(
                        invalid
                    )  # type: ignore[arg-type]

    def test_public_package_exports_phase11_contract(
        self,
    ) -> None:
        names = (
            "DEFAULT_REALTIME_TYPE",
            "RealtimeWatchCandidate",
            "RealtimeWatchlistMetrics",
            "RealtimeWatchlist",
            "build_realtime_watchlist",
        )

        for name in names:
            with self.subTest(name=name):
                self.assertIn(
                    name,
                    screening_package.__all__,
                )
                self.assertTrue(
                    hasattr(
                        screening_package,
                        name,
                    )
                )


if __name__ == "__main__":
    unittest.main()
