from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hyperbot.config import load_config
from hyperbot.grid_backtest import GridBacktestConfig, grid_backtest_result_to_dict, run_grid_backtest
from hyperbot.historical_prices import HistoricalPriceClient, parse_lookback


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest a simple grid strategy on Hyperliquid candles.")
    parser.add_argument("--config", default="config/testnet.yaml", help="Path to the YAML config file.")
    parser.add_argument("--symbol", default=None, help="Ticker to backtest, for example BTC.")
    parser.add_argument("--interval-minutes", type=int, required=True, help="Candle interval in minutes.")
    parser.add_argument("--lookback", required=True, help="Historical window, for example 90m, 6h, 7d, or 1w.")
    parser.add_argument("--lower-price", required=True, help="Lower grid price in USD.")
    parser.add_argument("--upper-price", required=True, help="Upper grid price in USD.")
    parser.add_argument("--grid-count", type=int, required=True, help="Number of grid price levels.")
    parser.add_argument("--grid-spacing", required=True, help="Distance between adjacent grid levels in USD.")
    parser.add_argument("--budget-usd", required=True, help="Total quote budget to allocate.")
    parser.add_argument("--fee-rate", default="0", help="Per-trade fee rate as a decimal, for example 0.0004.")
    parser.add_argument("--include-trades", action="store_true", help="Include every simulated trade in JSON output.")
    args = parser.parse_args()

    config = load_config(args.config)
    symbol = (args.symbol or config.symbol).upper()
    client = HistoricalPriceClient(config)
    candles = client.fetch_candles(
        symbol=symbol,
        interval_minutes=args.interval_minutes,
        lookback=parse_lookback(args.lookback),
    )

    backtest_config = GridBacktestConfig(
        lower_price=Decimal(args.lower_price),
        upper_price=Decimal(args.upper_price),
        grid_count=args.grid_count,
        grid_spacing=Decimal(args.grid_spacing),
        budget_usd=Decimal(args.budget_usd),
        fee_rate=Decimal(args.fee_rate),
    )
    result = run_grid_backtest(candles, backtest_config)
    result_payload = grid_backtest_result_to_dict(result)
    if not args.include_trades:
        result_payload.pop("trades", None)
        result_payload.pop("open_positions", None)

    payload = {
        "symbol": symbol,
        "interval_minutes": args.interval_minutes,
        "lookback": args.lookback,
        "candle_count": len(candles),
        "grid": {
            "lower_price": args.lower_price,
            "upper_price": args.upper_price,
            "grid_count": args.grid_count,
            "grid_spacing": args.grid_spacing,
            "budget_usd": args.budget_usd,
            "fee_rate": args.fee_rate,
        },
        "result": result_payload,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
