# Hyperbot

Hyperliquid grid bot project. Phase 1 is intentionally read-only: it loads config, connects to Hyperliquid Testnet, fetches `allMids` and `l2Book`, and can subscribe to WebSocket market data with reconnect handling.

No wallet keys, orders, cancels, or leverage actions are implemented in this phase.

## Setup

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Read Testnet Market Data

```powershell
.\.venv\Scripts\python.exe scripts\run_testnet.py --config config\testnet.yaml --symbol BTC
```

## Watch Testnet WebSocket

```powershell
.\.venv\Scripts\python.exe scripts\watch_testnet_ws.py --config config\testnet.yaml --subscription allMids --max-messages 1
```

## Fetch Historical Prices

Fetch standalone candle data for strategy planning. Supported `--lookback` units are `m`, `h`, `d`, and `w`.

```powershell
.\.venv\Scripts\python.exe scripts\fetch_history.py --config config\testnet.yaml --symbol BTC --interval-minutes 60 --lookback 7d --format csv --output btc_1h.csv
```

## Backtest A Grid

Run a standalone grid backtest against historical candles. `--grid-count` and `--grid-spacing` must match the range: `lower + spacing * (count - 1) == upper`.

```powershell
.\.venv\Scripts\python.exe scripts\run_grid_backtest.py --config config\testnet.yaml --symbol BTC --interval-minutes 60 --lookback 7d --lower-price 65000 --upper-price 75000 --grid-count 5 --grid-spacing 2500 --budget-usd 1000
```

The backtester uses OHLC candles, so it does not know the exact price order inside a candle. To avoid overstating results, it does not sell a position in the same candle where that position was opened.
