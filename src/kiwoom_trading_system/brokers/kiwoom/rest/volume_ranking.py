from __future__ import annotations

from typing import Any

from kiwoom import get_client
from kiwoom.core.runtime import describe_selection, get_base_url


API_ID = "ka10030"
API_PATH = "/api/dostk/rkinfo"
RESPONSE_KEY = "tdy_trde_qty_upper"
DEMO_BASE_URL = "https://mockapi.kiwoom.com"

_ALLOWED_REQUEST_VALUES = {
    "mrkt_tp": frozenset({"000", "001", "101"}),
    "sort_tp": frozenset({"1", "2", "3"}),
    "mang_stk_incls": frozenset(
        {"0", "1", "3", "4", "5", "6", "7", "8", "9", "11", "12", "13", "14", "15", "16"}
    ),
    "crd_tp": frozenset({"0", "1", "2", "3", "4", "8", "9"}),
    "trde_qty_tp": frozenset({"0", "5", "10", "50", "100", "200", "300", "500", "1000"}),
    "pric_tp": frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"}),
    "trde_prica_tp": frozenset({"0", "1", "3", "4", "10", "30", "50", "100", "300", "500", "1000", "3000", "5000"}),
    "mrkt_open_tp": frozenset({"0", "1", "2", "3"}),
    "stex_tp": frozenset({"1", "2", "3"}),
}


class DemoEnvironmentRequiredError(RuntimeError):
    """Raised when Phase 10 is not running against mockapi."""


class DemoExchangeScopeRequiredError(RuntimeError):
    """Raised before a demo request for an unsupported exchange scope."""


class VolumeRankingResponseError(RuntimeError):
    """Raised when ka10030 returns a non-success response code."""

    def __init__(self, return_code: object, return_msg: object) -> None:
        super().__init__(
            "Kiwoom ka10030 failed: "
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
    selection = describe_selection()
    mode = _mode_text(selection.mode)
    base_url = get_base_url().rstrip("/")
    if mode != "demo":
        raise DemoEnvironmentRequiredError(
            f"Phase 10 requires demo mode, current mode={mode!r}."
        )
    if base_url != DEMO_BASE_URL:
        raise DemoEnvironmentRequiredError(
            "Phase 10 requires the Kiwoom mock REST server, "
            f"current base_url={base_url!r}."
        )
    return mode, base_url


def _validated_request_value(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if value not in _ALLOWED_REQUEST_VALUES[name]:
        raise ValueError(f"unsupported {name}: {value!r}.")
    return value


def build_volume_ranking_request(
    *,
    mrkt_tp: str = "000",
    sort_tp: str = "1",
    mang_stk_incls: str = "1",
    crd_tp: str = "0",
    trde_qty_tp: str = "0",
    pric_tp: str = "0",
    trde_prica_tp: str = "0",
    mrkt_open_tp: str = "0",
    stex_tp: str = "1",
) -> dict[str, str]:
    values = {
        "mrkt_tp": mrkt_tp,
        "sort_tp": sort_tp,
        "mang_stk_incls": mang_stk_incls,
        "crd_tp": crd_tp,
        "trde_qty_tp": trde_qty_tp,
        "pric_tp": pric_tp,
        "trde_prica_tp": trde_prica_tp,
        "mrkt_open_tp": mrkt_open_tp,
        "stex_tp": stex_tp,
    }
    return {
        name: _validated_request_value(name, value)
        for name, value in values.items()
    }


def get_daily_volume_ranking(
    *,
    mrkt_tp: str = "000",
    sort_tp: str = "1",
    mang_stk_incls: str = "1",
    crd_tp: str = "0",
    trde_qty_tp: str = "0",
    pric_tp: str = "0",
    trde_prica_tp: str = "0",
    mrkt_open_tp: str = "0",
    stex_tp: str = "1",
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    request = build_volume_ranking_request(
        mrkt_tp=mrkt_tp,
        sort_tp=sort_tp,
        mang_stk_incls=mang_stk_incls,
        crd_tp=crd_tp,
        trde_qty_tp=trde_qty_tp,
        pric_tp=pric_tp,
        trde_prica_tp=trde_prica_tp,
        mrkt_open_tp=mrkt_open_tp,
        stex_tp=stex_tp,
    )
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
        raise TypeError("timeout_seconds must be an integer.")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero.")

    ensure_demo_environment()
    if request["stex_tp"] != "1":
        raise DemoExchangeScopeRequiredError(
            "Kiwoom mockapi network requests require stex_tp='1' (KRX), "
            f"received {request['stex_tp']!r}."
        )

    client = get_client(timeout_seconds=timeout_seconds)
    response = client.fetch_page(
        api_id=API_ID,
        path=API_PATH,
        body=dict(request),
        cont_yn=None,
        next_key=None,
    )
    if not isinstance(response.body, dict):
        raise TypeError("ka10030 response body must be a dict.")
    result = dict(response.body)
    return_code = result.get("return_code", result.get("returnCode"))
    if return_code is None:
        raise TypeError("ka10030 response body must include return_code.")
    if not _is_success_return_code(return_code):
        raise VolumeRankingResponseError(
            return_code=return_code,
            return_msg=result.get("return_msg", result.get("returnMsg")),
        )
    if not isinstance(result.get(RESPONSE_KEY), list):
        raise TypeError(f"ka10030 {RESPONSE_KEY} must be a list.")
    return result


__all__ = [
    "API_ID",
    "API_PATH",
    "RESPONSE_KEY",
    "DemoEnvironmentRequiredError",
    "DemoExchangeScopeRequiredError",
    "VolumeRankingResponseError",
    "build_volume_ranking_request",
    "ensure_demo_environment",
    "get_daily_volume_ranking",
]
