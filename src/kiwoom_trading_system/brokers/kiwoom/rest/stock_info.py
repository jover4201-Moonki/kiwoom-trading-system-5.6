from __future__ import annotations

from typing import Any

from kiwoom import get_client
from kiwoom.core.runtime import describe_selection, get_base_url


API_ID = "ka10001"
API_PATH = "/api/dostk/stkinfo"
DEMO_BASE_URL = "https://mockapi.kiwoom.com"


class DemoEnvironmentRequiredError(RuntimeError):
    """Raised when Phase 4 is not running against the demo environment."""


class StockInfoResponseError(RuntimeError):
    """Raised when ka10001 returns a non-success response code."""

    def __init__(self, return_code: object, return_msg: object) -> None:
        super().__init__(
            "Kiwoom ka10001 failed: "
            f"return_code={return_code!r}, return_msg={return_msg!r}"
        )
        self.return_code = return_code
        self.return_msg = return_msg


def _mode_text(value: object) -> str:
    return str(getattr(value, "value", value)).lower()


def _is_success_return_code(value: object) -> bool:
    if value is None:
        return True

    if isinstance(value, bool):
        return False

    if isinstance(value, int):
        return value == 0

    text = str(value).strip()

    if not text:
        return False

    try:
        return int(text) == 0
    except ValueError:
        return False


def ensure_demo_environment() -> tuple[str, str]:
    """Verify that the currently selected Kiwoom profile is demo."""

    selection = describe_selection()
    mode = _mode_text(selection.mode)
    base_url = get_base_url().rstrip("/")

    if mode != "demo":
        raise DemoEnvironmentRequiredError(
            f"Phase 4 requires demo mode, current mode={mode!r}."
        )

    if base_url != DEMO_BASE_URL:
        raise DemoEnvironmentRequiredError(
            "Phase 4 requires the Kiwoom mock REST server, "
            f"current base_url={base_url!r}."
        )

    return mode, base_url


def get_stock_basic_info(
    stk_cd: str,
    *,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Return the raw ka10001 response for one domestic stock code."""

    if not isinstance(stk_cd, str):
        raise TypeError("stk_cd must be a string.")

    code = stk_cd.strip()

    if not code:
        raise ValueError("stk_cd is required.")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero.")

    ensure_demo_environment()

    client = get_client(timeout_seconds=timeout_seconds)

    response = client.fetch_page(
        api_id=API_ID,
        path=API_PATH,
        body={"stk_cd": code},
        cont_yn=None,
        next_key=None,
    )

    if not isinstance(response.body, dict):
        raise TypeError("ka10001 response body must be a dict.")

    result = dict(response.body)

    return_code = result.get("return_code")

    if not _is_success_return_code(return_code):
        raise StockInfoResponseError(
            return_code=return_code,
            return_msg=result.get("return_msg"),
        )

    return result


__all__ = [
    "DemoEnvironmentRequiredError",
    "StockInfoResponseError",
    "ensure_demo_environment",
    "get_stock_basic_info",
]
