import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal

from kiwoom_trading_system.market_data.realtime_trade import (
    AggressorSide,
    MarketVenue,
    normalize_trade_entry,
)
from kiwoom_trading_system.state.realtime_trade_state import (
    RealtimeTradeStateError,
    update_realtime_trade_state,
)


class RealtimeTradeStateTests(unittest.TestCase):
    def test_first_trade_initializes_state(self):
        trade = _make_trade(price="+100", volume="+3")

        state = update_realtime_trade_state(None, trade)

        self.assertEqual(state.schema_version, 1)
        self.assertEqual(state.instrument_code, "005930")
        self.assertIs(state.venue, MarketVenue.KRX)
        self.assertEqual(state.first_trade_at, trade.trade_at)
        self.assertEqual(state.last_trade_at, trade.trade_at)
        self.assertEqual(state.first_price_krw, 100)
        self.assertEqual(state.last_price_krw, 100)
        self.assertEqual(state.high_price_krw, 100)
        self.assertEqual(state.low_price_krw, 100)
        self.assertEqual(state.trade_count, 1)

    def test_side_counts_and_volumes_are_aggregated(self):
        state = update_realtime_trade_state(
            None,
            _make_trade(time="090000", volume="+3"),
        )
        state = update_realtime_trade_state(
            state,
            _make_trade(time="090001", volume="-2"),
        )
        state = update_realtime_trade_state(
            state,
            _make_trade(time="090002", volume="0"),
        )

        self.assertEqual(state.trade_count, 3)
        self.assertEqual(state.buy_trade_count, 1)
        self.assertEqual(state.sell_trade_count, 1)
        self.assertEqual(state.unknown_trade_count, 1)
        self.assertEqual(state.total_trade_volume, 5)
        self.assertEqual(state.buy_trade_volume, 3)
        self.assertEqual(state.sell_trade_volume, 2)
        self.assertEqual(state.net_aggressor_volume, 1)

    def test_price_range_last_value_and_vwap_are_updated(self):
        state = update_realtime_trade_state(
            None,
            _make_trade(
                time="090000",
                price="+100",
                volume="+3",
            ),
        )
        state = update_realtime_trade_state(
            state,
            _make_trade(
                time="090001",
                price="+110",
                volume="-2",
            ),
        )
        state = update_realtime_trade_state(
            state,
            _make_trade(
                time="090002",
                price="+90",
                volume="0",
            ),
        )

        self.assertEqual(state.first_price_krw, 100)
        self.assertEqual(state.last_price_krw, 90)
        self.assertEqual(state.high_price_krw, 110)
        self.assertEqual(state.low_price_krw, 90)
        self.assertEqual(state.observed_trade_value_krw, 520)
        self.assertEqual(
            state.volume_weighted_average_price_krw,
            Decimal("104"),
        )

    def test_zero_volume_keeps_vwap_unavailable(self):
        state = update_realtime_trade_state(
            None,
            _make_trade(price="+100", volume="0"),
        )

        self.assertEqual(state.total_trade_volume, 0)
        self.assertEqual(state.observed_trade_value_krw, 0)
        self.assertIsNone(
            state.volume_weighted_average_price_krw
        )

    def test_different_instrument_is_rejected(self):
        state = update_realtime_trade_state(
            None,
            _make_trade(),
        )

        with self.assertRaisesRegex(
            RealtimeTradeStateError,
            "instrument_code",
        ):
            update_realtime_trade_state(
                state,
                _make_trade(
                    time="090001",
                    item="000660",
                ),
            )

    def test_different_venue_is_rejected(self):
        state = update_realtime_trade_state(
            None,
            _make_trade(),
        )

        with self.assertRaisesRegex(
            RealtimeTradeStateError,
            "venue",
        ):
            update_realtime_trade_state(
                state,
                _make_trade(
                    time="090001",
                    item="005930_NX",
                ),
            )

    def test_out_of_order_trade_is_rejected(self):
        state = update_realtime_trade_state(
            None,
            _make_trade(time="090001"),
        )

        with self.assertRaisesRegex(
            RealtimeTradeStateError,
            "older",
        ):
            update_realtime_trade_state(
                state,
                _make_trade(time="090000"),
            )

        self.assertEqual(state.trade_count, 1)

    def test_equal_trade_time_is_allowed(self):
        state = update_realtime_trade_state(
            None,
            _make_trade(
                time="090000",
                volume="+1",
            ),
        )

        updated = update_realtime_trade_state(
            state,
            _make_trade(
                time="090000",
                volume="-1",
            ),
        )

        self.assertEqual(updated.trade_count, 2)
        self.assertEqual(
            updated.last_trade_at,
            state.last_trade_at,
        )

    def test_state_is_frozen_and_previous_state_is_unchanged(self):
        state = update_realtime_trade_state(
            None,
            _make_trade(),
        )
        updated = update_realtime_trade_state(
            state,
            _make_trade(
                time="090001",
                price="+110",
            ),
        )

        with self.assertRaises(FrozenInstanceError):
            state.trade_count = 99

        self.assertEqual(state.trade_count, 1)
        self.assertEqual(state.last_price_krw, 100)
        self.assertEqual(updated.trade_count, 2)
        self.assertEqual(updated.last_price_krw, 110)

    def test_invalid_normalized_trade_invariants_are_rejected(self):
        trade = _make_trade()
        invalid_cases = (
            (
                "realtime_type",
                replace(trade, realtime_type="0C"),
                "realtime_type",
            ),
            (
                "instrument_code",
                replace(trade, instrument_code=""),
                "instrument_code",
            ),
            (
                "price_krw",
                replace(trade, price_krw=0),
                "price_krw",
            ),
            (
                "trade_volume",
                replace(trade, trade_volume=2),
                "volume fields",
            ),
            (
                "trade_at",
                replace(
                    trade,
                    trade_at=trade.trade_at.replace(tzinfo=None),
                ),
                "trade_at",
            ),
            (
                "received_at",
                replace(
                    trade,
                    received_at=trade.received_at.replace(tzinfo=None),
                ),
                "received_at",
            ),
            (
                "aggressor_side",
                replace(
                    trade,
                    aggressor_side=AggressorSide.SELL,
                ),
                "aggressor side",
            ),
        )

        for case_name, invalid_trade, message_pattern in invalid_cases:
            with self.subTest(case=case_name):
                with self.assertRaisesRegex(
                    RealtimeTradeStateError,
                    message_pattern,
                ):
                    update_realtime_trade_state(None, invalid_trade)

    def test_unsupported_state_schema_is_rejected(self):
        state = update_realtime_trade_state(None, _make_trade())
        unsupported_state = replace(state, schema_version=2)

        with self.assertRaisesRegex(
            RealtimeTradeStateError,
            "schema version",
        ):
            update_realtime_trade_state(
                unsupported_state,
                _make_trade(time="090001"),
            )

    def test_invalid_argument_types_are_rejected(self):
        trade = _make_trade()

        with self.assertRaises(TypeError):
            update_realtime_trade_state(
                "invalid",
                trade,
            )

        with self.assertRaises(TypeError):
            update_realtime_trade_state(
                None,
                object(),
            )


def _make_trade(
    *,
    time: str = "090000",
    price: str = "+100",
    volume: str = "+1",
    item: str = "005930",
):
    return normalize_trade_entry(
        {
            "type": "0B",
            "name": "주식체결",
            "item": item,
            "values": {
                "20": time,
                "10": price,
                "15": volume,
            },
        },
        received_at=datetime(
            2026,
            8,
            24,
            tzinfo=UTC,
        ),
    )


if __name__ == "__main__":
    unittest.main()
