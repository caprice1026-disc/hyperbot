from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Sequence

from hyperbot.historical_prices import Candle


class BacktestError(ValueError):
    """Raised when a grid backtest cannot be run safely."""


@dataclass(frozen=True)
class GridBacktestConfig:
    lower_price: Decimal
    upper_price: Decimal
    grid_count: int
    grid_spacing: Decimal
    budget_usd: Decimal
    fee_rate: Decimal = Decimal("0")


@dataclass(frozen=True)
class GridTrade:
    side: str
    level_price: Decimal
    execution_price: Decimal
    quantity: Decimal
    gross_value: Decimal
    fee: Decimal
    candle_open_time_ms: int
    pnl: Decimal = Decimal("0")


@dataclass(frozen=True)
class BacktestPosition:
    entry_price: Decimal
    target_price: Decimal
    quantity: Decimal
    cost: Decimal
    entry_time_ms: int


@dataclass(frozen=True)
class GridBacktestResult:
    initial_budget: Decimal
    final_cash: Decimal
    final_inventory: Decimal
    final_equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    roi: Decimal
    open_position_count: int
    buy_trade_count: int
    sell_trade_count: int
    trades: tuple[GridTrade, ...]
    open_positions: tuple[BacktestPosition, ...]


def grid_levels(config: GridBacktestConfig) -> tuple[Decimal, ...]:
    _validate_config(config)
    return tuple(config.lower_price + (config.grid_spacing * Decimal(index)) for index in range(config.grid_count))


def run_grid_backtest(candles: Sequence[Candle], config: GridBacktestConfig) -> GridBacktestResult:
    if not candles:
        raise BacktestError("candles must not be empty.")

    levels = grid_levels(config)
    buy_levels = levels[:-1]
    targets_by_entry = {level: level + config.grid_spacing for level in buy_levels}
    order_budget = config.budget_usd / Decimal(len(buy_levels))
    cash = config.budget_usd
    realized_pnl = Decimal("0")
    trades: list[GridTrade] = []
    positions_by_level: dict[Decimal, BacktestPosition] = {}

    for candle in sorted(candles, key=lambda item: item.open_time_ms):
        sold_levels: set[Decimal] = set()
        for entry_price, position in list(positions_by_level.items()):
            if candle.high >= position.target_price:
                gross_value = position.quantity * position.target_price
                fee = gross_value * config.fee_rate
                net_value = gross_value - fee
                trade_pnl = net_value - position.cost
                cash += net_value
                realized_pnl += trade_pnl
                trades.append(
                    GridTrade(
                        side="sell",
                        level_price=entry_price,
                        execution_price=position.target_price,
                        quantity=position.quantity,
                        gross_value=gross_value,
                        fee=fee,
                        candle_open_time_ms=candle.open_time_ms,
                        pnl=trade_pnl,
                    )
                )
                del positions_by_level[entry_price]
                sold_levels.add(entry_price)

        for level in reversed(buy_levels):
            if level in positions_by_level or level in sold_levels or candle.low > level:
                continue

            fee = order_budget * config.fee_rate
            total_cost = order_budget + fee
            if cash < total_cost:
                continue

            quantity = order_budget / level
            cash -= total_cost
            positions_by_level[level] = BacktestPosition(
                entry_price=level,
                target_price=targets_by_entry[level],
                quantity=quantity,
                cost=total_cost,
                entry_time_ms=candle.open_time_ms,
            )
            trades.append(
                GridTrade(
                    side="buy",
                    level_price=level,
                    execution_price=level,
                    quantity=quantity,
                    gross_value=order_budget,
                    fee=fee,
                    candle_open_time_ms=candle.open_time_ms,
                )
            )

    final_close = candles[-1].close
    final_inventory = sum((position.quantity for position in positions_by_level.values()), Decimal("0"))
    marked_inventory_value = final_inventory * final_close * (Decimal("1") - config.fee_rate)
    final_equity = cash + marked_inventory_value
    total_pnl = final_equity - config.budget_usd
    unrealized_pnl = total_pnl - realized_pnl

    return GridBacktestResult(
        initial_budget=config.budget_usd,
        final_cash=cash,
        final_inventory=final_inventory,
        final_equity=final_equity,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        total_pnl=total_pnl,
        roi=total_pnl / config.budget_usd,
        open_position_count=len(positions_by_level),
        buy_trade_count=sum(1 for trade in trades if trade.side == "buy"),
        sell_trade_count=sum(1 for trade in trades if trade.side == "sell"),
        trades=tuple(trades),
        open_positions=tuple(positions_by_level.values()),
    )


def grid_backtest_result_to_dict(result: GridBacktestResult) -> dict[str, Any]:
    return {
        "initial_budget": str(result.initial_budget),
        "final_cash": str(result.final_cash),
        "final_inventory": str(result.final_inventory),
        "final_equity": str(result.final_equity),
        "realized_pnl": str(result.realized_pnl),
        "unrealized_pnl": str(result.unrealized_pnl),
        "total_pnl": str(result.total_pnl),
        "roi": str(result.roi),
        "open_position_count": result.open_position_count,
        "buy_trade_count": result.buy_trade_count,
        "sell_trade_count": result.sell_trade_count,
        "trades": [
            {
                "side": trade.side,
                "level_price": str(trade.level_price),
                "execution_price": str(trade.execution_price),
                "quantity": str(trade.quantity),
                "gross_value": str(trade.gross_value),
                "fee": str(trade.fee),
                "candle_open_time_ms": trade.candle_open_time_ms,
                "pnl": str(trade.pnl),
            }
            for trade in result.trades
        ],
        "open_positions": [
            {
                "entry_price": str(position.entry_price),
                "target_price": str(position.target_price),
                "quantity": str(position.quantity),
                "cost": str(position.cost),
                "entry_time_ms": position.entry_time_ms,
            }
            for position in result.open_positions
        ],
    }


def _validate_config(config: GridBacktestConfig) -> None:
    if config.lower_price <= 0:
        raise BacktestError("lower_price must be positive.")
    if config.upper_price <= config.lower_price:
        raise BacktestError("upper_price must be greater than lower_price.")
    if config.grid_count < 2:
        raise BacktestError("grid_count must be at least 2.")
    if config.grid_spacing <= 0:
        raise BacktestError("grid_spacing must be positive.")
    if config.budget_usd <= 0:
        raise BacktestError("budget_usd must be positive.")
    if config.fee_rate < 0:
        raise BacktestError("fee_rate must be non-negative.")

    expected_upper = config.lower_price + config.grid_spacing * Decimal(config.grid_count - 1)
    if expected_upper != config.upper_price:
        raise BacktestError("upper_price must equal lower_price + grid_spacing * (grid_count - 1).")
