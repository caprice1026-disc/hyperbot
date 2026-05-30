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
from hyperbot.historical_prices import HistoricalPriceClient, candles_to_dicts, parse_lookback, write_candles_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch historical Hyperliquid candles without placing orders.")
    parser.add_argument("--config", default="config/testnet.yaml", help="Path to the YAML config file.")
    parser.add_argument("--symbol", default=None, help="Ticker to fetch, for example BTC.")
    parser.add_argument("--interval-minutes", type=int, required=True, help="Candle interval in minutes.")
    parser.add_argument("--lookback", required=True, help="Historical window, for example 90m, 6h, 7d, or 1w.")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format.")
    parser.add_argument("--output", default=None, help="Optional output file path.")
    args = parser.parse_args()

    config = load_config(args.config)
    symbol = (args.symbol or config.symbol).upper()
    client = HistoricalPriceClient(config)
    candles = client.fetch_candles(
        symbol=symbol,
        interval_minutes=args.interval_minutes,
        lookback=parse_lookback(args.lookback),
    )

    if args.format == "csv":
        if args.output is None:
            write_candles_csv(candles, sys.stdout)
        else:
            write_candles_csv(candles, args.output)
        return 0

    payload = candles_to_dicts(candles)
    if args.output is None:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
