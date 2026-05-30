from __future__ import annotations

from decimal import Decimal

import pytest

from hyperbot.grid_backtest import (
    BacktestError,
    GridBacktestConfig,
    grid_backtest_result_to_dict,
    grid_levels,
    run_grid_backtest,
)
from hyperbot.historical_prices import Candle


def candle(open_time_ms, open_, high, low, close) -> Candle:
    return Candle(
        symbol="BTC",
        interval="1m",
        open_time_ms=open_time_ms,
        close_time_ms=open_time_ms + 59999,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        trade_count=1,
    )


def test_grid_levels_require_count_and_spacing_to_match_bounds():
    config = GridBacktestConfig(
        lower_price=Decimal("100"),
        upper_price=Decimal("120"),
        grid_count=3,
        grid_spacing=Decimal("10"),
        budget_usd=Decimal("1000"),
    )

    assert grid_levels(config) == (Decimal("100"), Decimal("110"), Decimal("120"))


def test_grid_levels_reject_inconsistent_spacing():
    config = GridBacktestConfig(
        lower_price=Decimal("100"),
        upper_price=Decimal("125"),
        grid_count=3,
        grid_spacing=Decimal("10"),
        budget_usd=Decimal("1000"),
    )

    with pytest.raises(BacktestError, match="upper_price"):
        grid_levels(config)


def test_backtest_buys_grid_level_and_sells_on_later_candle():
    config = GridBacktestConfig(
        lower_price=Decimal("100"),
        upper_price=Decimal("110"),
        grid_count=2,
        grid_spacing=Decimal("10"),
        budget_usd=Decimal("1000"),
    )
    candles = [
        candle(1, "110", "111", "99", "100"),
        candle(2, "100", "111", "100", "110"),
    ]

    result = run_grid_backtest(candles, config)

    assert result.buy_trade_count == 1
    assert result.sell_trade_count == 1
    assert result.open_position_count == 0
    assert result.realized_pnl == Decimal("100")
    assert result.unrealized_pnl == Decimal("0")
    assert result.total_pnl == Decimal("100")
    assert result.roi == Decimal("0.1")


def test_backtest_does_not_sell_new_position_in_same_candle():
    config = GridBacktestConfig(
        lower_price=Decimal("100"),
        upper_price=Decimal("110"),
        grid_count=2,
        grid_spacing=Decimal("10"),
        budget_usd=Decimal("1000"),
    )
    candles = [candle(1, "110", "111", "99", "110")]

    result = run_grid_backtest(candles, config)

    assert result.buy_trade_count == 1
    assert result.sell_trade_count == 0
    assert result.open_position_count == 1
    assert result.realized_pnl == Decimal("0")
    assert result.unrealized_pnl == Decimal("100")
    assert result.total_pnl == Decimal("100")


def test_grid_backtest_result_to_dict_is_json_safe():
    config = GridBacktestConfig(
        lower_price=Decimal("100"),
        upper_price=Decimal("110"),
        grid_count=2,
        grid_spacing=Decimal("10"),
        budget_usd=Decimal("1000"),
    )
    result = run_grid_backtest(
        [
            candle(1, "110", "111", "99", "100"),
            candle(2, "100", "111", "100", "110"),
        ],
        config,
    )

    payload = grid_backtest_result_to_dict(result)

    assert payload["initial_budget"] == "1000"
    assert payload["total_pnl"] == "100"
    assert payload["roi"] == "0.1"
    assert payload["buy_trade_count"] == 1
    assert payload["sell_trade_count"] == 1
    assert payload["trades"][0]["side"] == "buy"
