from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hyperbot.config import load_config
from hyperbot.market_data import HyperliquidMarketData


def main() -> int:
    parser = argparse.ArgumentParser(description="Read Hyperliquid Testnet market data without placing orders.")
    parser.add_argument("--config", default="config/testnet.yaml", help="Path to the YAML config file.")
    parser.add_argument("--symbol", default=None, help="Symbol to read, for example BTC.")
    args = parser.parse_args()

    config = load_config(args.config)
    symbol = (args.symbol or config.symbol).upper()
    market_data = HyperliquidMarketData(config)

    mid = market_data.mid_price(symbol)
    book = market_data.l2_book(symbol)
    best_bid = book.bids[0] if book.bids else None
    best_ask = book.asks[0] if book.asks else None

    print(f"environment={config.environment}")
    print(f"symbol={symbol}")
    print(f"mid={mid}")
    print(f"best_bid={best_bid.price if best_bid else 'n/a'} size={best_bid.size if best_bid else 'n/a'}")
    print(f"best_ask={best_ask.price if best_ask else 'n/a'} size={best_ask.size if best_ask else 'n/a'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
