from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kiwoom_trading_system.brokers.kiwoom.rest import volume_ranking as rest
from kiwoom_trading_system.screening import volume_ranking as screening


def _row(code: str, **changes: object) -> dict[str, object]:
    result: dict[str, object] = {
        "stk_cd": code,
        "stk_nm": f"Stock {code}",
        "cur_prc": "-152000",
        "flu_rt": "-0.07",
        "trde_qty": "34954641",
        "trde_tern_rt": "+48.21",
        "trde_amt": "5308092",
        "nested": {"values": ["original"]},
    }
    result.update(changes)
    return result


class RequestContractTests(unittest.TestCase):
    def test_default_request_uses_safe_values(self) -> None:
        request = rest.build_volume_ranking_request()
        self.assertEqual(request["mang_stk_incls"], "1")
        self.assertEqual(request["stex_tp"], "1")
        self.assertEqual(len(request), 9)

    def test_exchange_schema_accepts_nxt_and_integrated(self) -> None:
        self.assertEqual(
            rest.build_volume_ranking_request(stex_tp="2")["stex_tp"],
            "2",
        )
        self.assertEqual(
            rest.build_volume_ranking_request(stex_tp="3")["stex_tp"],
            "3",
        )

    def test_invalid_request_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            rest.build_volume_ranking_request(mrkt_tp="999")
        with self.assertRaises(TypeError):
            rest.build_volume_ranking_request(sort_tp=1)  # type: ignore[arg-type]


class RestBoundaryTests(unittest.TestCase):
    def test_real_environment_is_blocked_before_client_creation(self) -> None:
        with (
            patch.object(
                rest,
                "describe_selection",
                return_value=SimpleNamespace(mode="real"),
            ),
            patch.object(rest, "get_base_url", return_value="https://api.kiwoom.com"),
            patch.object(rest, "get_client") as client_factory,
        ):
            with self.assertRaises(rest.DemoEnvironmentRequiredError):
                rest.get_daily_volume_ranking()
        client_factory.assert_not_called()

    def test_nxt_and_integrated_are_blocked_before_network(self) -> None:
        for stex_tp in ("2", "3"):
            with self.subTest(stex_tp=stex_tp):
                with (
                    patch.object(
                        rest,
                        "ensure_demo_environment",
                        return_value=("demo", rest.DEMO_BASE_URL),
                    ),
                    patch.object(rest, "get_client") as client_factory,
                ):
                    with self.assertRaises(rest.DemoExchangeScopeRequiredError):
                        rest.get_daily_volume_ranking(stex_tp=stex_tp)
                client_factory.assert_not_called()

    def test_successful_fetch_preserves_exact_request(self) -> None:
        body = {"return_code": 0, rest.RESPONSE_KEY: [_row("005930")]}
        client = Mock()
        client.fetch_page.return_value = SimpleNamespace(body=body)
        with (
            patch.object(
                rest,
                "ensure_demo_environment",
                return_value=("demo", rest.DEMO_BASE_URL),
            ),
            patch.object(rest, "get_client", return_value=client),
        ):
            result = rest.get_daily_volume_ranking(sort_tp="3")
        client.fetch_page.assert_called_once_with(
            api_id="ka10030",
            path="/api/dostk/rkinfo",
            body={
                "mrkt_tp": "000",
                "sort_tp": "3",
                "mang_stk_incls": "1",
                "crd_tp": "0",
                "trde_qty_tp": "0",
                "pric_tp": "0",
                "trde_prica_tp": "0",
                "mrkt_open_tp": "0",
                "stex_tp": "1",
            },
            cont_yn=None,
            next_key=None,
        )
        self.assertIsNot(result, body)

    def test_nonzero_return_code_is_propagated(self) -> None:
        client = Mock()
        client.fetch_page.return_value = SimpleNamespace(
            body={"returnCode": -100, "returnMsg": "error"}
        )
        with (
            patch.object(
                rest,
                "ensure_demo_environment",
                return_value=("demo", rest.DEMO_BASE_URL),
            ),
            patch.object(rest, "get_client", return_value=client),
        ):
            with self.assertRaises(rest.VolumeRankingResponseError) as context:
                rest.get_daily_volume_ranking()
        self.assertEqual(context.exception.return_code, -100)
        self.assertEqual(context.exception.return_msg, "error")

    def test_malformed_response_is_rejected(self) -> None:
        client = Mock()
        with (
            patch.object(
                rest,
                "ensure_demo_environment",
                return_value=("demo", rest.DEMO_BASE_URL),
            ),
            patch.object(rest, "get_client", return_value=client),
        ):
            client.fetch_page.return_value = SimpleNamespace(body=[])
            with self.assertRaises(TypeError):
                rest.get_daily_volume_ranking()
            client.fetch_page.return_value = SimpleNamespace(body={"return_code": 0})
            with self.assertRaises(TypeError):
                rest.get_daily_volume_ranking()
            client.fetch_page.return_value = SimpleNamespace(
                body={rest.RESPONSE_KEY: []}
            )
            with self.assertRaises(TypeError):
                rest.get_daily_volume_ranking()


class NormalizationTests(unittest.TestCase):
    def test_normalizes_official_fields_without_float_or_krw_conversion(self) -> None:
        response = {rest.RESPONSE_KEY: [_row("005930")]}
        result = screening.normalize_volume_ranking(response, {"stex_tp": "1"})
        candidate = result.candidates[0]
        self.assertEqual(candidate.stock_code, "005930")
        self.assertEqual(candidate.raw_current_price, "-152000")
        self.assertEqual(candidate.current_price, 152000)
        self.assertEqual(candidate.current_price_sign, "-")
        self.assertEqual(candidate.change_rate_pct, Decimal("-0.07"))
        self.assertEqual(candidate.trade_turnover_rate_pct, Decimal("+48.21"))
        self.assertEqual(candidate.raw_trade_amount, "5308092")
        self.assertEqual(candidate.trade_amount_million_krw, 5308092)
        self.assertNotEqual(candidate.trade_amount_million_krw, 5308092000000)
        self.assertEqual(candidate.exchange_scope, "KRX")

    def test_api_order_is_preserved(self) -> None:
        rows = [_row("A"), _row("B"), _row("C")]
        result = screening.normalize_volume_ranking(
            {rest.RESPONSE_KEY: rows},
            {"stex_tp": "1"},
        )
        self.assertEqual(
            tuple(candidate.stock_code for candidate in result.candidates),
            ("A", "B", "C"),
        )

    def test_invalid_rows_are_isolated_and_all_rows_are_checked(self) -> None:
        rows = [
            _row("A"),
            _row("BROKEN", cur_prc="invalid"),
            _row("C"),
            _row("ALSO-BROKEN", flu_rt="NaN"),
        ]
        result = screening.normalize_volume_ranking(
            {rest.RESPONSE_KEY: rows},
            {"stex_tp": "1"},
            candidate_limit=1,
        )
        self.assertEqual(result.metrics.valid_candidate_count, 1)
        self.assertEqual(result.metrics.invalid_row_count, 2)
        self.assertEqual(result.metrics.excluded_by_limit_count, 1)

    def test_first_valid_duplicate_is_retained(self) -> None:
        first = _row("A", stk_nm="First")
        second = _row("A", stk_nm="Second")
        result = screening.normalize_volume_ranking(
            {rest.RESPONSE_KEY: [first, second]},
            {"stex_tp": "1"},
        )
        self.assertEqual(result.candidates[0].stock_name, "First")
        self.assertEqual(result.metrics.duplicate_row_count, 1)

    def test_invalid_first_row_does_not_hide_later_valid_duplicate(self) -> None:
        rows = [_row("A", cur_prc="bad"), _row("A", stk_nm="Valid")]
        result = screening.normalize_volume_ranking(
            {rest.RESPONSE_KEY: rows},
            {"stex_tp": "1"},
        )
        self.assertEqual(result.candidates[0].stock_name, "Valid")
        self.assertEqual(result.metrics.invalid_row_count, 1)
        self.assertEqual(result.metrics.duplicate_row_count, 0)

    def test_limit_is_applied_after_validation_and_deduplication(self) -> None:
        rows = [_row("A"), _row("A"), _row("B"), _row("C")]
        result = screening.normalize_volume_ranking(
            {rest.RESPONSE_KEY: rows},
            {"stex_tp": "1"},
            candidate_limit=2,
        )
        self.assertEqual(
            tuple(candidate.stock_code for candidate in result.candidates),
            ("A", "B"),
        )
        self.assertEqual(result.metrics.duplicate_row_count, 1)
        self.assertEqual(result.metrics.excluded_by_limit_count, 1)

    def test_candidate_limit_boundaries_are_enforced(self) -> None:
        response = {rest.RESPONSE_KEY: []}
        screening.normalize_volume_ranking(
            response,
            {"stex_tp": "1"},
            candidate_limit=1,
        )
        screening.normalize_volume_ranking(
            response,
            {"stex_tp": "1"},
            candidate_limit=100,
        )
        for limit in (0, 101):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    screening.normalize_volume_ranking(
                        response,
                        {"stex_tp": "1"},
                        candidate_limit=limit,
                    )
        with self.assertRaises(TypeError):
            screening.normalize_volume_ranking(
                response,
                {"stex_tp": "1"},
                candidate_limit=True,  # type: ignore[arg-type]
            )

    def test_sign_is_preserved_without_direction_inference(self) -> None:
        rows = [
            _row("A", cur_prc="+100"),
            _row("B", cur_prc="100"),
            _row("C", cur_prc="-0"),
        ]
        result = screening.normalize_volume_ranking(
            {rest.RESPONSE_KEY: rows},
            {"stex_tp": "1"},
        )
        self.assertEqual(
            tuple(candidate.current_price_sign for candidate in result.candidates),
            ("+", "", "-"),
        )

    def test_integrated_scope_is_not_market_venue_sor(self) -> None:
        result = screening.normalize_volume_ranking(
            {rest.RESPONSE_KEY: [_row("A")]},
            {"stex_tp": "3"},
        )
        self.assertEqual(result.candidates[0].exchange_scope, "INTEGRATED")
        self.assertNotEqual(result.candidates[0].exchange_scope, "SOR")

    def test_snapshots_are_recursive_immutable_and_detached(self) -> None:
        row = _row("A")
        response = {rest.RESPONSE_KEY: [row], "meta": {"values": [1]}}
        request = {"stex_tp": "1", "filters": {"values": [2]}}
        result = screening.normalize_volume_ranking(response, request)

        row["stk_nm"] = "Changed"
        nested = row["nested"]
        self.assertIsInstance(nested, dict)
        nested["values"].append("changed")  # type: ignore[union-attr]
        response["meta"]["values"].append(3)  # type: ignore[index,union-attr]
        request["filters"]["values"].append(4)  # type: ignore[index,union-attr]

        self.assertEqual(result.candidates[0].stock_name, "Stock A")
        self.assertEqual(result.candidates[0].raw_row["nested"]["values"], ("original",))  # type: ignore[index]
        self.assertEqual(result.raw_response["meta"]["values"], (1,))  # type: ignore[index]
        self.assertEqual(result.request_metadata["filters"]["values"], (2,))  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.raw_response["new"] = "blocked"  # type: ignore[index]
        with self.assertRaises(FrozenInstanceError):
            result.metrics.invalid_row_count = 99  # type: ignore[misc]

    def test_unexpected_normalizer_exception_is_propagated(self) -> None:
        with patch.object(
            screening,
            "_normalize_row",
            side_effect=RuntimeError("unexpected"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                screening.normalize_volume_ranking(
                    {rest.RESPONSE_KEY: [_row("A")]},
                    {"stex_tp": "1"},
                )

    def test_fetch_orchestration_uses_request_snapshot(self) -> None:
        response = {"return_code": 0, rest.RESPONSE_KEY: [_row("A")]}
        with patch.object(
            screening.rest,
            "get_daily_volume_ranking",
            return_value=response,
        ) as fetch:
            result = screening.fetch_volume_ranking_candidates(
                sort_tp="2",
                candidate_limit=1,
            )
        fetch.assert_called_once_with(
            mrkt_tp="000",
            sort_tp="2",
            mang_stk_incls="1",
            crd_tp="0",
            trde_qty_tp="0",
            pric_tp="0",
            trde_prica_tp="0",
            mrkt_open_tp="0",
            stex_tp="1",
            timeout_seconds=30,
        )
        self.assertEqual(result.request_metadata["sort_tp"], "2")


if __name__ == "__main__":
    unittest.main()
