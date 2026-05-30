from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable, TextIO

from hyperbot.config import BotConfig


class HistoricalPriceError(ValueError):
    """Raised when historical price parameters or responses are invalid."""


@dataclass(frozen=True)
class Candle:
    symbol: str
    interval: str
    open_time_ms: int
    close_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trade_count: int


_INTERVALS_BY_MINUTES = {
    1: "1m",
    3: "3m",
    5: "5m",
    15: "15m",
    30: "30m",
    60: "1h",
    120: "2h",
    240: "4h",
    480: "8h",
    720: "12h",
    1440: "1d",
    4320: "3d",
    10080: "1w",
}


class HistoricalPriceClient:
    def __init__(
        self,
        config: BotConfig,
        *,
        info: Any | None = None,
        info_factory: Callable[[BotConfig], Any] | None = None,
    ) -> None:
        self._config = config
        self._info = info
        self._info_factory = info_factory or _create_info

    def fetch_candles(
        self,
        symbol: str,
        interval_minutes: int,
        lookback: timedelta,
        end_time: datetime | None = None,
    ) -> tuple[Candle, ...]:
        if lookback <= timedelta(0):
            raise HistoricalPriceError("lookback must be positive.")

        normalized_symbol = symbol.upper()
        interval = interval_to_api_value(interval_minutes)
        end = end_time or datetime.now(UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        end_ms = _to_unix_ms(end)
        start_ms = _to_unix_ms(end - lookback)

        raw_candles = self._get_info().candles_snapshot(normalized_symbol, interval, start_ms, end_ms)
        if not isinstance(raw_candles, list):
            raise HistoricalPriceError("candleSnapshot response must be a list.")

        candles = tuple(_normalize_candle(row, normalized_symbol, interval) for row in raw_candles)
        return tuple(sorted(candles, key=lambda candle: candle.open_time_ms))

    def _get_info(self) -> Any:
        if self._info is None:
            self._info = self._info_factory(self._config)
        return self._info


def interval_to_api_value(interval_minutes: int) -> str:
    try:
        return _INTERVALS_BY_MINUTES[int(interval_minutes)]
    except (KeyError, ValueError) as exc:
        supported = ", ".join(str(value) for value in sorted(_INTERVALS_BY_MINUTES))
        raise HistoricalPriceError(f"Unsupported interval_minutes. Supported intervals: {supported}.") from exc


def parse_lookback(value: str) -> timedelta:
    match = re.fullmatch(r"\s*(\d+)\s*([mhdw])\s*", value, flags=re.IGNORECASE)
    if match is None:
        raise HistoricalPriceError("lookback must look like '90m', '6h', '2d', or '1w'.")

    amount = int(match.group(1))
    unit = match.group(2).lower()
    if amount <= 0:
        raise HistoricalPriceError("lookback amount must be positive.")
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    if unit == "w":
        return timedelta(weeks=amount)
    raise HistoricalPriceError(f"Unsupported lookback unit: {unit}.")


def write_candles_csv(candles: Iterable[Candle], output: str | Path | TextIO) -> None:
    should_close = False
    if isinstance(output, (str, Path)):
        file_obj = Path(output).open("w", encoding="utf-8", newline="")
        should_close = True
    else:
        file_obj = output

    try:
        writer = csv.writer(file_obj)
        writer.writerow(
            [
                "symbol",
                "interval",
                "open_time_ms",
                "close_time_ms",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "trade_count",
            ]
        )
        for candle in candles:
            writer.writerow(
                [
                    candle.symbol,
                    candle.interval,
                    candle.open_time_ms,
                    candle.close_time_ms,
                    str(candle.open),
                    str(candle.high),
                    str(candle.low),
                    str(candle.close),
                    str(candle.volume),
                    candle.trade_count,
                ]
            )
    finally:
        if should_close:
            file_obj.close()


def candles_to_dicts(candles: Iterable[Candle]) -> list[dict[str, Any]]:
    return [
        {
            "symbol": candle.symbol,
            "interval": candle.interval,
            "open_time_ms": candle.open_time_ms,
            "close_time_ms": candle.close_time_ms,
            "open": str(candle.open),
            "high": str(candle.high),
            "low": str(candle.low),
            "close": str(candle.close),
            "volume": str(candle.volume),
            "trade_count": candle.trade_count,
        }
        for candle in candles
    ]


def _create_info(config: BotConfig) -> Any:
    from hyperliquid.info import Info

    return Info(
        config.network.rest_url,
        skip_ws=True,
        timeout=config.request_timeout_seconds,
    )


def _normalize_candle(raw: Any, fallback_symbol: str, fallback_interval: str) -> Candle:
    if not isinstance(raw, dict):
        raise HistoricalPriceError("candle row must be a mapping.")

    return Candle(
        symbol=str(raw.get("s", fallback_symbol)).upper(),
        interval=str(raw.get("i", fallback_interval)),
        open_time_ms=int(raw["t"]),
        close_time_ms=int(raw["T"]),
        open=_decimal(raw["o"], "o"),
        high=_decimal(raw["h"], "h"),
        low=_decimal(raw["l"], "l"),
        close=_decimal(raw["c"], "c"),
        volume=_decimal(raw.get("v", "0"), "v"),
        trade_count=int(raw.get("n", 0)),
    )


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HistoricalPriceError(f"{field_name} must be a decimal-compatible value.") from exc


def _to_unix_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)
