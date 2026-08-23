import copy
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from kiwoom_trading_system.market_data.realtime_trade import (
    AggressorSide,
    KST,
    MarketVenue,
    TradeNormalizationError,
    TradingSession,
    normalize_trade_entry,
    normalize_trade_packet,
)


def sample_entry():
    return {
        "type": "0B",
        "name": "주식체결",
        "item": "005930",
        "values": {
            "20": "165208",
            "10": "-20800",
            "11": "-50",
            "12": "-0.24",
            "27": "-20800",
            "28": "-20700",
            "15": "+82",
            "13": "30379732",
            "14": "632640",
            "16": "20850",
            "17": "+21150",
            "18": "-20450",
            "25": "5",
            "228": "98.92",
            "290": "2",
            "9081": "1",
        },
    }


class RealtimeTradeNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.received_at = datetime(
            2026,
            8,
            24,
            16,
            52,
            9,
            tzinfo=KST,
        )

    def test_official_sample_is_normalized(self):
        trade = normalize_trade_entry(
            sample_entry(),
            received_at=self.received_at,
        )

        self.assertEqual(trade.schema_version, 1)
        self.assertEqual(trade.source, "kiwoom")
        self.assertEqual(
            trade.instrument_code,
            "005930",
        )
        self.assertEqual(
            trade.venue,
            MarketVenue.KRX,
        )
        self.assertEqual(
            trade.trade_at.isoformat(),
            "2026-08-24T16:52:08+09:00",
        )
        self.assertEqual(trade.price_krw, 20800)
        self.assertEqual(trade.price_sign, -1)
        self.assertEqual(trade.change_krw, -50)
        self.assertEqual(
            trade.change_rate_pct,
            Decimal("-0.24"),
        )
        self.assertEqual(trade.best_ask_krw, 20800)
        self.assertEqual(trade.best_bid_krw, 20700)
        self.assertEqual(
            trade.signed_trade_volume,
            82,
        )
        self.assertEqual(trade.trade_volume, 82)
        self.assertEqual(
            trade.aggressor_side,
            AggressorSide.BUY,
        )
        self.assertEqual(
            trade.cumulative_volume,
            30379732,
        )
        self.assertEqual(
            trade.cumulative_value_million_krw,
            Decimal("632640"),
        )
        self.assertEqual(
            trade.trade_strength_pct,
            Decimal("98.92"),
        )
        self.assertEqual(
            trade.session,
            TradingSession.REGULAR,
        )
        self.assertEqual(trade.exchange_code, "1")

    def test_sell_volume_is_preserved(self):
        entry = sample_entry()
        entry["values"]["15"] = "-7"

        trade = normalize_trade_entry(
            entry,
            received_at=self.received_at,
        )

        self.assertEqual(
            trade.signed_trade_volume,
            -7,
        )
        self.assertEqual(trade.trade_volume, 7)
        self.assertEqual(
            trade.aggressor_side,
            AggressorSide.SELL,
        )

    def test_zero_volume_has_unknown_side(self):
        entry = sample_entry()
        entry["values"]["15"] = "0"

        trade = normalize_trade_entry(
            entry,
            received_at=self.received_at,
        )

        self.assertEqual(
            trade.aggressor_side,
            AggressorSide.UNKNOWN,
        )

    def test_venue_suffixes_are_not_mixed(self):
        cases = (
            ("005930", MarketVenue.KRX),
            ("039490_NX", MarketVenue.NXT),
            ("039490_AL", MarketVenue.SOR),
        )

        for item, expected in cases:
            with self.subTest(item=item):
                entry = sample_entry()
                entry["item"] = item

                trade = normalize_trade_entry(
                    entry,
                    received_at=self.received_at,
                )

                self.assertEqual(
                    trade.instrument_code,
                    item[:6],
                )
                self.assertEqual(
                    trade.venue,
                    expected,
                )

    def test_utc_received_time_is_converted_to_kst(self):
        received_at = datetime(
            2026,
            8,
            24,
            7,
            52,
            9,
            tzinfo=timezone.utc,
        )

        trade = normalize_trade_entry(
            sample_entry(),
            received_at=received_at,
        )

        self.assertEqual(
            trade.received_at.isoformat(),
            "2026-08-24T16:52:09+09:00",
        )
        self.assertEqual(trade.trade_at.tzinfo, KST)

    def test_naive_received_time_is_rejected(self):
        with self.assertRaisesRegex(
            TradeNormalizationError,
            "timezone-aware",
        ):
            normalize_trade_entry(
                sample_entry(),
                received_at=datetime(
                    2026,
                    8,
                    24,
                    16,
                    52,
                    9,
                ),
            )

    def test_invalid_item_is_rejected(self):
        entry = sample_entry()
        entry["item"] = "005930_X"

        with self.assertRaises(
            TradeNormalizationError
        ):
            normalize_trade_entry(
                entry,
                received_at=self.received_at,
            )

    def test_missing_core_fids_are_rejected(self):
        for fid in ("20", "10", "15"):
            with self.subTest(fid=fid):
                entry = sample_entry()
                del entry["values"][fid]

                with self.assertRaises(
                    TradeNormalizationError
                ):
                    normalize_trade_entry(
                        entry,
                        received_at=self.received_at,
                    )

    def test_invalid_numeric_value_is_rejected(self):
        entry = sample_entry()
        entry["values"]["10"] = "20,800"

        with self.assertRaisesRegex(
            TradeNormalizationError,
            "not an integer",
        ):
            normalize_trade_entry(
                entry,
                received_at=self.received_at,
            )

    def test_negative_cumulative_values_are_rejected(self):
        for fid in ("13", "14"):
            with self.subTest(fid=fid):
                entry = sample_entry()
                entry["values"][fid] = "-1"

                with self.assertRaises(
                    TradeNormalizationError
                ):
                    normalize_trade_entry(
                        entry,
                        received_at=self.received_at,
                    )

    def test_blank_optional_values_become_none_or_unknown(self):
        entry = sample_entry()

        for fid in (
            "11",
            "12",
            "13",
            "14",
            "228",
            "290",
            "9081",
        ):
            entry["values"][fid] = ""

        trade = normalize_trade_entry(
            entry,
            received_at=self.received_at,
        )

        self.assertIsNone(trade.change_krw)
        self.assertIsNone(trade.change_rate_pct)
        self.assertIsNone(trade.cumulative_volume)
        self.assertIsNone(
            trade.cumulative_value_million_krw
        )
        self.assertIsNone(trade.trade_strength_pct)
        self.assertEqual(
            trade.session,
            TradingSession.UNKNOWN,
        )
        self.assertIsNone(trade.exchange_code)

    def test_packet_normalizes_only_0b_entries(self):
        packet = {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0C",
                    "item": "005930",
                    "values": {},
                },
                sample_entry(),
            ],
        }

        trades = normalize_trade_packet(
            packet,
            received_at=self.received_at,
        )

        self.assertEqual(len(trades), 1)
        self.assertEqual(
            trades[0].realtime_type,
            "0B",
        )

    def test_packet_without_0b_returns_empty_tuple(self):
        packet = {
            "trnm": "REAL",
            "data": [
                {
                    "type": "0C",
                    "item": "005930",
                    "values": {},
                }
            ],
        }

        self.assertEqual(
            normalize_trade_packet(
                packet,
                received_at=self.received_at,
            ),
            (),
        )

    def test_non_real_packet_is_rejected(self):
        with self.assertRaisesRegex(
            TradeNormalizationError,
            "must be REAL",
        ):
            normalize_trade_packet(
                {
                    "trnm": "REG",
                    "data": [],
                },
                received_at=self.received_at,
            )

    def test_packet_data_must_be_a_list(self):
        with self.assertRaisesRegex(
            TradeNormalizationError,
            "must be a list",
        ):
            normalize_trade_packet(
                {
                    "trnm": "REAL",
                    "data": {},
                },
                received_at=self.received_at,
            )

    def test_values_must_contain_strings(self):
        entry = sample_entry()
        entry["values"]["10"] = 20800

        with self.assertRaisesRegex(
            TradeNormalizationError,
            "must be a string",
        ):
            normalize_trade_entry(
                entry,
                received_at=self.received_at,
            )

    def test_input_and_normalized_raw_values_are_protected(self):
        entry = sample_entry()
        original = copy.deepcopy(entry)

        trade = normalize_trade_entry(
            entry,
            received_at=self.received_at,
        )

        self.assertEqual(entry, original)

        entry["values"]["10"] = "+99999"
        self.assertEqual(
            trade.raw_values["10"],
            "-20800",
        )

        with self.assertRaises(TypeError):
            trade.raw_values["10"] = "+1"


if __name__ == "__main__":
    unittest.main()