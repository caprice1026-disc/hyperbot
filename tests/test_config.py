from pathlib import Path

import pytest

from hyperbot.config import ConfigError, load_config


def test_loads_testnet_config_from_yaml():
    config = load_config(Path("config/testnet.yaml"))

    assert config.environment == "testnet"
    assert config.symbol == "BTC"
    assert config.network.rest_url == "https://api.hyperliquid-testnet.xyz"
    assert config.network.websocket_url == "wss://api.hyperliquid-testnet.xyz/ws"
    assert config.request_timeout_seconds == 10.0
    assert config.websocket.reconnect_max_attempts == 5


def test_rejects_unknown_environment(tmp_path):
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(
        "\n".join(
            [
                "environment: staging",
                "symbol: btc",
                "network:",
                "  rest_url: https://example.invalid",
                "  websocket_url: wss://example.invalid/ws",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="environment"):
        load_config(config_path)
