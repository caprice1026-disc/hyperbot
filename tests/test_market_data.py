from decimal import Decimal

import pytest

from hyperbot.config import BotConfig, NetworkConfig, WebSocketConfig
from hyperbot.market_data import HyperliquidMarketData, MarketDataError


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
        self.l2_requested_symbols = []

    def all_mids(self):
        return {"BTC": "100000.5", "ETH": "3500.25"}

    def l2_snapshot(self, symbol):
        self.l2_requested_symbols.append(symbol)
        return {
            "coin": "BTC",
            "time": 1710000000123,
            "levels": [
                [{"px": "99999.5", "sz": "1.25", "n": 2}],
                [{"px": "100001.0", "sz": "0.75", "n": 1}],
            ],
        }


def test_all_mids_returns_decimal_prices():
    market_data = HyperliquidMarketData(make_config(), info=FakeInfo())

    mids = market_data.all_mids()

    assert mids == {"BTC": Decimal("100000.5"), "ETH": Decimal("3500.25")}


def test_mid_price_returns_requested_symbol_price():
    market_data = HyperliquidMarketData(make_config(), info=FakeInfo())

    assert market_data.mid_price("btc") == Decimal("100000.5")


def test_mid_price_raises_when_symbol_missing():
    market_data = HyperliquidMarketData(make_config(), info=FakeInfo())

    with pytest.raises(MarketDataError, match="DOGE"):
        market_data.mid_price("DOGE")


def test_l2_book_normalizes_bid_and_ask_levels():
    fake_info = FakeInfo()
    market_data = HyperliquidMarketData(make_config(), info=fake_info)

    book = market_data.l2_book("btc")

    assert fake_info.l2_requested_symbols == ["BTC"]
    assert book.coin == "BTC"
    assert book.time == 1710000000123
    assert book.bids[0].price == Decimal("99999.5")
    assert book.bids[0].size == Decimal("1.25")
    assert book.bids[0].count == 2
    assert book.asks[0].price == Decimal("100001.0")
    assert book.asks[0].size == Decimal("0.75")
    assert book.asks[0].count == 1
