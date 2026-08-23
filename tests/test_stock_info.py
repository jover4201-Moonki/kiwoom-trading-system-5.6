from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kiwoom_trading_system.brokers.kiwoom.rest import stock_info


class ReturnCodeTests(unittest.TestCase):
    def test_official_success_values(self) -> None:
        self.assertTrue(stock_info._is_success_return_code(None))
        self.assertTrue(stock_info._is_success_return_code(0))
        self.assertTrue(stock_info._is_success_return_code("0"))

    def test_failure_values(self) -> None:
        self.assertFalse(stock_info._is_success_return_code(True))
        self.assertFalse(stock_info._is_success_return_code(1))
        self.assertFalse(stock_info._is_success_return_code("-1"))
        self.assertFalse(stock_info._is_success_return_code(""))
        self.assertFalse(stock_info._is_success_return_code("invalid"))


class DemoEnvironmentTests(unittest.TestCase):
    def test_demo_environment_passes(self) -> None:
        selection = SimpleNamespace(mode="demo")

        with (
            patch.object(stock_info, "describe_selection", return_value=selection),
            patch.object(
                stock_info,
                "get_base_url",
                return_value="https://mockapi.kiwoom.com",
            ),
        ):
            result = stock_info.ensure_demo_environment()

        self.assertEqual(
            result,
            ("demo", "https://mockapi.kiwoom.com"),
        )

    def test_real_environment_is_blocked(self) -> None:
        selection = SimpleNamespace(mode="real")

        with (
            patch.object(stock_info, "describe_selection", return_value=selection),
            patch.object(
                stock_info,
                "get_base_url",
                return_value="https://api.kiwoom.com",
            ),
        ):
            with self.assertRaises(
                stock_info.DemoEnvironmentRequiredError
            ):
                stock_info.ensure_demo_environment()

    def test_wrong_demo_base_url_is_blocked(self) -> None:
        selection = SimpleNamespace(mode="demo")

        with (
            patch.object(stock_info, "describe_selection", return_value=selection),
            patch.object(
                stock_info,
                "get_base_url",
                return_value="https://example.invalid",
            ),
        ):
            with self.assertRaises(
                stock_info.DemoEnvironmentRequiredError
            ):
                stock_info.ensure_demo_environment()


class StockBasicInfoTests(unittest.TestCase):
    def test_rejects_non_string_code(self) -> None:
        with self.assertRaises(TypeError):
            stock_info.get_stock_basic_info(5930)  # type: ignore[arg-type]

    def test_rejects_blank_code(self) -> None:
        with self.assertRaises(ValueError):
            stock_info.get_stock_basic_info("   ")

    def test_rejects_invalid_timeout(self) -> None:
        with self.assertRaises(ValueError):
            stock_info.get_stock_basic_info(
                "005930",
                timeout_seconds=0,
            )

    def test_successful_api_call(self) -> None:
        response_body = {
            "return_code": 0,
            "return_msg": "success",
            "stk_cd": "005930",
            "stk_nm": "Samsung Electronics",
        }

        response = SimpleNamespace(body=response_body)

        client = Mock()
        client.fetch_page.return_value = response

        with (
            patch.object(
                stock_info,
                "ensure_demo_environment",
                return_value=(
                    "demo",
                    "https://mockapi.kiwoom.com",
                ),
            ) as demo_check,
            patch.object(
                stock_info,
                "get_client",
                return_value=client,
            ) as client_factory,
        ):
            result = stock_info.get_stock_basic_info(" 005930 ")

        demo_check.assert_called_once_with()
        client_factory.assert_called_once_with(timeout_seconds=30)

        client.fetch_page.assert_called_once_with(
            api_id="ka10001",
            path="/api/dostk/stkinfo",
            body={"stk_cd": "005930"},
            cont_yn=None,
            next_key=None,
        )

        self.assertEqual(result["return_code"], 0)
        self.assertEqual(result["stk_cd"], "005930")
        self.assertIsNot(result, response_body)

    def test_none_return_code_matches_official_example(self) -> None:
        client = Mock()
        client.fetch_page.return_value = SimpleNamespace(
            body={
                "return_code": None,
                "stk_cd": "005930",
            }
        )

        with (
            patch.object(
                stock_info,
                "ensure_demo_environment",
                return_value=(
                    "demo",
                    "https://mockapi.kiwoom.com",
                ),
            ),
            patch.object(
                stock_info,
                "get_client",
                return_value=client,
            ),
        ):
            result = stock_info.get_stock_basic_info("005930")

        self.assertIsNone(result["return_code"])

    def test_nonzero_return_code_raises(self) -> None:
        client = Mock()
        client.fetch_page.return_value = SimpleNamespace(
            body={
                "return_code": -100,
                "return_msg": "test error",
            }
        )

        with (
            patch.object(
                stock_info,
                "ensure_demo_environment",
                return_value=(
                    "demo",
                    "https://mockapi.kiwoom.com",
                ),
            ),
            patch.object(
                stock_info,
                "get_client",
                return_value=client,
            ),
        ):
            with self.assertRaises(
                stock_info.StockInfoResponseError
            ) as context:
                stock_info.get_stock_basic_info("005930")

        self.assertEqual(context.exception.return_code, -100)
        self.assertEqual(context.exception.return_msg, "test error")

    def test_non_dict_body_raises(self) -> None:
        client = Mock()
        client.fetch_page.return_value = SimpleNamespace(
            body=["unexpected"]
        )

        with (
            patch.object(
                stock_info,
                "ensure_demo_environment",
                return_value=(
                    "demo",
                    "https://mockapi.kiwoom.com",
                ),
            ),
            patch.object(
                stock_info,
                "get_client",
                return_value=client,
            ),
        ):
            with self.assertRaises(TypeError):
                stock_info.get_stock_basic_info("005930")


if __name__ == "__main__":
    unittest.main()
