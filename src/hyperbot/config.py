from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a bot configuration file is missing required values."""


@dataclass(frozen=True)
class NetworkConfig:
    rest_url: str
    websocket_url: str


@dataclass(frozen=True)
class WebSocketConfig:
    reconnect_max_attempts: int = 5
    reconnect_delay_seconds: float = 2.0
    ping_interval_seconds: float = 30.0
    ping_timeout_seconds: float = 10.0


@dataclass(frozen=True)
class BotConfig:
    environment: str
    symbol: str
    network: NetworkConfig
    request_timeout_seconds: float
    websocket: WebSocketConfig


def load_config(path: str | Path) -> BotConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read config file: {config_path}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Config file must contain a YAML mapping.")

    environment = _required_str(raw, "environment").lower()
    if environment not in {"testnet", "mainnet"}:
        raise ConfigError("environment must be either 'testnet' or 'mainnet'.")

    symbol = _required_str(raw, "symbol").upper()
    network_raw = raw.get("network")
    if not isinstance(network_raw, dict):
        raise ConfigError("network must be a mapping.")

    network = NetworkConfig(
        rest_url=_required_str(network_raw, "rest_url"),
        websocket_url=_required_str(network_raw, "websocket_url"),
    )

    websocket_raw = raw.get("websocket", {})
    if websocket_raw is None:
        websocket_raw = {}
    if not isinstance(websocket_raw, dict):
        raise ConfigError("websocket must be a mapping.")

    return BotConfig(
        environment=environment,
        symbol=symbol,
        network=network,
        request_timeout_seconds=_float(raw.get("request_timeout_seconds", 10.0), "request_timeout_seconds"),
        websocket=WebSocketConfig(
            reconnect_max_attempts=_int(
                websocket_raw.get("reconnect_max_attempts", 5),
                "websocket.reconnect_max_attempts",
            ),
            reconnect_delay_seconds=_float(
                websocket_raw.get("reconnect_delay_seconds", 2.0),
                "websocket.reconnect_delay_seconds",
            ),
            ping_interval_seconds=_float(
                websocket_raw.get("ping_interval_seconds", 30.0),
                "websocket.ping_interval_seconds",
            ),
            ping_timeout_seconds=_float(
                websocket_raw.get("ping_timeout_seconds", 10.0),
                "websocket.ping_timeout_seconds",
            ),
        ),
    )


def _required_str(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} must be a non-empty string.")
    return value.strip()


def _float(value: Any, key: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{key} must be a number.") from exc
    if result < 0:
        raise ConfigError(f"{key} must be non-negative.")
    return result


def _int(value: Any, key: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{key} must be an integer.") from exc
    if result < 0:
        raise ConfigError(f"{key} must be non-negative.")
    return result
