import json

from hyperbot.config import BotConfig, NetworkConfig, WebSocketConfig
from hyperbot.ws import HyperliquidWebSocketClient


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


class FakeWebSocketApp:
    def __init__(self, url, on_open, on_message, run_error=None, messages=None):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.run_error = run_error
        self.messages = messages or []
        self.sent_messages = []
        self.closed = False

    def send(self, message):
        self.sent_messages.append(json.loads(message))

    def close(self):
        self.closed = True

    def run_forever(self, **_kwargs):
        self.on_open(self)
        for message in self.messages:
            self.on_message(self, json.dumps(message))
        if self.run_error is not None:
            raise self.run_error


def test_subscribe_all_mids_sends_subscribe_payload_on_open():
    instances = []

    def factory(url, on_open, on_message):
        app = FakeWebSocketApp(url, on_open, on_message)
        instances.append(app)
        return app

    client = HyperliquidWebSocketClient(make_config(), websocket_app_factory=factory, sleep=lambda _seconds: None)
    client.subscribe_all_mids(lambda _message: None)
    client.run_forever(max_reconnects=0)

    assert instances[0].url == "wss://api.hyperliquid-testnet.xyz/ws"
    assert instances[0].sent_messages == [
        {"method": "subscribe", "subscription": {"type": "allMids"}}
    ]


def test_dispatches_websocket_messages_to_matching_callback():
    received = []

    def factory(url, on_open, on_message):
        return FakeWebSocketApp(
            url,
            on_open,
            on_message,
            messages=[{"channel": "allMids", "data": {"mids": {"BTC": "100000"}}}],
        )

    client = HyperliquidWebSocketClient(make_config(), websocket_app_factory=factory, sleep=lambda _seconds: None)
    client.subscribe_all_mids(received.append)
    client.run_forever(max_reconnects=0)

    assert received == [{"channel": "allMids", "data": {"mids": {"BTC": "100000"}}}]


def test_reconnects_and_resubscribes_after_connection_error():
    instances = []
    run_errors = [RuntimeError("socket dropped"), None]

    def factory(url, on_open, on_message):
        app = FakeWebSocketApp(url, on_open, on_message, run_error=run_errors.pop(0))
        instances.append(app)
        return app

    client = HyperliquidWebSocketClient(make_config(), websocket_app_factory=factory, sleep=lambda _seconds: None)
    client.subscribe_l2_book("btc", lambda _message: None)
    client.run_forever(max_reconnects=1)

    assert len(instances) == 2
    assert instances[0].sent_messages == [
        {"method": "subscribe", "subscription": {"type": "l2Book", "coin": "BTC"}}
    ]
    assert instances[1].sent_messages == [
        {"method": "subscribe", "subscription": {"type": "l2Book", "coin": "BTC"}}
    ]
