from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable

import websocket

from hyperbot.config import BotConfig

WsCallback = Callable[[dict[str, Any]], None]
WebSocketAppFactory = Callable[[str, Callable[[Any], None], Callable[[Any, str], None]], Any]


class HyperliquidWebSocketClient:
    def __init__(
        self,
        config: BotConfig,
        *,
        websocket_app_factory: WebSocketAppFactory | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._websocket_app_factory = websocket_app_factory or _create_websocket_app
        self._sleep = sleep
        self._subscriptions: list[tuple[dict[str, str], WsCallback]] = []
        self._stop_event = threading.Event()
        self._app: Any | None = None
        self.last_error: BaseException | None = None

    def subscribe_all_mids(self, callback: WsCallback) -> None:
        self._subscriptions.append(({"type": "allMids"}, callback))

    def subscribe_l2_book(self, symbol: str, callback: WsCallback) -> None:
        self._subscriptions.append(({"type": "l2Book", "coin": symbol.upper()}, callback))

    def run_forever(self, max_reconnects: int | None = None) -> None:
        reconnect_limit = self._config.websocket.reconnect_max_attempts if max_reconnects is None else max_reconnects
        reconnects = 0

        while not self._stop_event.is_set():
            self._app = self._websocket_app_factory(
                self._config.network.websocket_url,
                self._on_open,
                self._on_message,
            )
            try:
                self.last_error = None
                self._app.run_forever(
                    ping_interval=self._config.websocket.ping_interval_seconds,
                    ping_timeout=self._config.websocket.ping_timeout_seconds,
                )
            except Exception as exc:
                self.last_error = exc

            if self._stop_event.is_set():
                break
            if reconnects >= reconnect_limit:
                break

            reconnects += 1
            delay = self._config.websocket.reconnect_delay_seconds
            if delay > 0:
                self._sleep(delay)

    def stop(self) -> None:
        self._stop_event.set()
        if self._app is not None:
            self._app.close()

    def _on_open(self, ws_app: Any) -> None:
        for subscription, _callback in self._subscriptions:
            ws_app.send(json.dumps({"method": "subscribe", "subscription": subscription}))

    def _on_message(self, _ws_app: Any, message: str) -> None:
        ws_message = json.loads(message)
        identifier = _message_identifier(ws_message)
        if identifier is None:
            return

        for subscription, callback in self._subscriptions:
            if _subscription_identifier(subscription) == identifier:
                callback(ws_message)


def _create_websocket_app(
    url: str,
    on_open: Callable[[Any], None],
    on_message: Callable[[Any, str], None],
) -> websocket.WebSocketApp:
    return websocket.WebSocketApp(url, on_open=on_open, on_message=on_message)


def _subscription_identifier(subscription: dict[str, str]) -> str:
    subscription_type = subscription["type"]
    if subscription_type == "allMids":
        return "allMids"
    if subscription_type == "l2Book":
        return f"l2Book:{subscription['coin'].upper()}"
    raise ValueError(f"Unsupported subscription type: {subscription_type}")


def _message_identifier(message: dict[str, Any]) -> str | None:
    channel = message.get("channel")
    if channel == "allMids":
        return "allMids"
    if channel == "l2Book":
        data = message.get("data")
        if not isinstance(data, dict) or "coin" not in data:
            return None
        return f"l2Book:{str(data['coin']).upper()}"
    return None
