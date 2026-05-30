from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO

import pytest

from hyperbot.config import BotConfig, NetworkConfig, WebSocketConfig
from hyperbot.historical_prices import (
    HistoricalPriceClient,
    HistoricalPriceError,
    candles_to_dicts,
    interval_to_api_value,
    parse_lookback,
    write_candles_csv,
)


def make_config() -> BotConfig:
    return BotConfig(
        environment="testnet",
        symbol="BTC",
        network=NetworkConfig(
            rest_url="https://api.hyperliquid-testnet.xyz",
            websocket_url="wss://api.hyperliquid-testnet.xyz/ws",
        ),
        request_timeout_seconds=10.0,
        websocket=WebSocketConfig(reconnect_max_attempts=5, reconnect_delay_seconds=0.0),
    )


class FakeInfo:
    def __init__(self):
        self.requests = []

    def candles_snapshot(self, symbol, interval, start_time, end_time):
        self.requests.append((symbol, interval, start_time, end_time))
        return [
            {
                "s": "BTC",
                "i": interval,
                "t": 1710000000000,
                "T": 1710000059999,
                "o": "100.0",
                "h": "110.0",
                "l": "95.0",
                "c": "105.0",
                "v": "12.5",
                "n": 3,
            }
        ]


def test_interval_to_api_value_maps_supported_minute_intervals():
    assert interval_to_api_value(1) == "1m"
    assert interval_to_api_value(15) == "15m"
    assert interval_to_api_value(60) == "1h"
    assert interval_to_api_value(1440) == "1d"


def test_interval_to_api_value_rejects_unsupported_minutes():
    with pytest.raises(HistoricalPriceError, match="Unsupported interval"):
        interval_to_api_value(2)


def test_parse_lookback_accepts_minutes_hours_and_days():
    assert parse_lookback("90m") == timedelta(minutes=90)
    assert parse_lookback("6h") == timedelta(hours=6)
    assert parse_lookback("2d") == timedelta(days=2)


def test_fetch_candles_calls_sdk_with_expected_window_and_normalizes_rows():
    fake_info = FakeInfo()
    client = HistoricalPriceClient(make_config(), info=fake_info)
    end_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)

    candles = client.fetch_candles(
        symbol="btc",
        interval_minutes=5,
        lookback=timedelta(minutes=15),
        end_time=end_time,
    )

    expected_end_ms = 1767225600000
    assert fake_info.requests == [("BTC", "5m", expected_end_ms - 15 * 60 * 1000, expected_end_ms)]
    assert len(candles) == 1
    assert candles[0].symbol == "BTC"
    assert candles[0].interval == "5m"
    assert candles[0].open == Decimal("100.0")
    assert candles[0].high == Decimal("110.0")
    assert candles[0].low == Decimal("95.0")
    assert candles[0].close == Decimal("105.0")
    assert candles[0].volume == Decimal("12.5")
    assert candles[0].trade_count == 3


def test_write_candles_csv_writes_header_and_decimal_values():
    fake_info = FakeInfo()
    client = HistoricalPriceClient(make_config(), info=fake_info)
    candles = client.fetch_candles("BTC", 5, timedelta(minutes=5), datetime(2026, 1, 1, tzinfo=UTC))
    output = StringIO()

    write_candles_csv(candles, output)

    lines = output.getvalue().splitlines()
    assert lines[0] == "symbol,interval,open_time_ms,close_time_ms,open,high,low,close,volume,trade_count"
    assert lines[1] == "BTC,5m,1710000000000,1710000059999,100.0,110.0,95.0,105.0,12.5,3"


def test_candles_to_dicts_uses_json_safe_decimal_strings():
    fake_info = FakeInfo()
    client = HistoricalPriceClient(make_config(), info=fake_info)
    candles = client.fetch_candles("BTC", 5, timedelta(minutes=5), datetime(2026, 1, 1, tzinfo=UTC))

    rows = candles_to_dicts(candles)

    assert rows == [
        {
            "symbol": "BTC",
            "interval": "5m",
            "open_time_ms": 1710000000000,
            "close_time_ms": 1710000059999,
            "open": "100.0",
            "high": "110.0",
            "low": "95.0",
            "close": "105.0",
            "volume": "12.5",
            "trade_count": 3,
        }
    ]
