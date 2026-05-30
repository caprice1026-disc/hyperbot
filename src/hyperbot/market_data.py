from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from hyperbot.config import BotConfig


class MarketDataError(RuntimeError):
    """Raised when market data cannot be fetched or normalized."""


@dataclass(frozen=True)
class BookLevel:
    price: Decimal
    size: Decimal
    count: int


@dataclass(frozen=True)
class OrderBookSnapshot:
    coin: str
    time: int
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]


class HyperliquidMarketData:
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

    def all_mids(self) -> dict[str, Decimal]:
        raw = self._get_info().all_mids()
        if not isinstance(raw, dict):
            raise MarketDataError("allMids response must be a mapping.")

        mids: dict[str, Decimal] = {}
        for symbol, price in raw.items():
            mids[str(symbol).upper()] = _decimal(price, f"allMids.{symbol}")
        return mids

    def mid_price(self, symbol: str) -> Decimal:
        normalized_symbol = symbol.upper()
        mids = self.all_mids()
        try:
            return mids[normalized_symbol]
        except KeyError as exc:
            raise MarketDataError(f"{normalized_symbol} was not present in allMids.") from exc

    def l2_book(self, symbol: str) -> OrderBookSnapshot:
        normalized_symbol = symbol.upper()
        raw = self._get_info().l2_snapshot(normalized_symbol)
        if not isinstance(raw, dict):
            raise MarketDataError("l2Book response must be a mapping.")

        levels = raw.get("levels")
        if not isinstance(levels, list) or len(levels) < 2:
            raise MarketDataError("l2Book response must include bid and ask levels.")

        bids = tuple(_book_level(level, "bid") for level in levels[0])
        asks = tuple(_book_level(level, "ask") for level in levels[1])
        return OrderBookSnapshot(
            coin=str(raw.get("coin", normalized_symbol)).upper(),
            time=int(raw.get("time", 0)),
            bids=bids,
            asks=asks,
        )

    def _get_info(self) -> Any:
        if self._info is None:
            self._info = self._info_factory(self._config)
        return self._info


def _create_info(config: BotConfig) -> Any:
    from hyperliquid.info import Info

    return Info(
        config.network.rest_url,
        skip_ws=True,
        timeout=config.request_timeout_seconds,
    )


def _book_level(raw: Any, side: str) -> BookLevel:
    if not isinstance(raw, dict):
        raise MarketDataError(f"{side} level must be a mapping.")
    return BookLevel(
        price=_decimal(raw.get("px"), f"{side}.px"),
        size=_decimal(raw.get("sz"), f"{side}.sz"),
        count=int(raw.get("n", 0)),
    )


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MarketDataError(f"{field_name} must be a decimal-compatible value.") from exc
