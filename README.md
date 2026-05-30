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
