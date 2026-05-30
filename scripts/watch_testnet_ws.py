from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hyperbot.config import load_config
from hyperbot.ws import HyperliquidWebSocketClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch Hyperliquid WebSocket market data without placing orders.")
    parser.add_argument("--config", default="config/testnet.yaml", help="Path to the YAML config file.")
    parser.add_argument("--subscription", choices=["allMids", "l2Book"], default="allMids")
    parser.add_argument("--symbol", default=None, help="Symbol for l2Book subscriptions.")
    parser.add_argument("--max-messages", type=int, default=1, help="Stop after this many messages.")
    args = parser.parse_args()

    config = load_config(args.config)
    client = HyperliquidWebSocketClient(config)
    received = 0

    def on_message(message: dict) -> None:
        nonlocal received
        received += 1
        print(json.dumps(message, ensure_ascii=False))
        if received >= args.max_messages:
            client.stop()

    if args.subscription == "allMids":
        client.subscribe_all_mids(on_message)
    else:
        client.subscribe_l2_book((args.symbol or config.symbol).upper(), on_message)

    client.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
