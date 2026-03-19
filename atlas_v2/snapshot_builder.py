from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean, pstdev

from .binance import BinanceClient
from .config import Settings


def load_universe(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct_change(current: float, prior: float) -> float:
    if prior == 0:
        return 0.0
    return (current / prior) - 1.0


def _daily_return_series(closes: list[float]) -> list[float]:
    return [_pct_change(current, prev) for prev, current in zip(closes, closes[1:])]


def _volatility_20d(closes: list[float]) -> float:
    returns = _daily_return_series(closes[-21:])
    if not returns:
        return 0.0
    return pstdev(returns) * math.sqrt(365) * 100


def _trend_strength(closes: list[float]) -> float:
    return _pct_change(closes[-1], mean(closes[-20:]))


def _volume_acceleration(volumes: list[float]) -> float:
    recent = mean(volumes[-5:])
    baseline = mean(volumes[-20:-5]) if len(volumes) >= 20 else mean(volumes[:-5])
    if baseline == 0:
        return 0.0
    return (recent / baseline) - 1.0


def build_snapshot(settings: Settings, client: BinanceClient, lookback_days: int = 30) -> dict:
    universe = load_universe(settings.universe_path)
    rows = []
    raw_ret20 = []
    raw_data: dict[str, tuple[list[float], list[float], dict]] = {}

    for item in universe:
        symbol = item["ticker"]
        ticker_24hr = client.fetch_ticker_24hr(symbol)
        klines = client.fetch_klines(symbol, interval="1d", limit=lookback_days)
        if len(klines) < 21:
            raise RuntimeError(f"Symbol {symbol} has insufficient kline history.")
        closes = [float(kline[4]) for kline in klines]
        quote_volumes = [float(kline[7]) for kline in klines]
        raw_ret20.append(_pct_change(closes[-1], closes[-21]))
        raw_data[symbol] = (closes, quote_volumes, ticker_24hr)

    market_mean = mean(raw_ret20)
    market_std = pstdev(raw_ret20) or 1.0
    as_of = ""

    for item in universe:
        symbol = item["ticker"]
        closes, quote_volumes, ticker_24hr = raw_data[symbol]
        if not as_of:
            as_of = str(ticker_24hr["closeTime"])
        ret_5d = _pct_change(closes[-1], closes[-6])
        ret_20d = _pct_change(closes[-1], closes[-21])
        rel_strength = (ret_20d - market_mean) / market_std
        rows.append(
            {
                "ticker": symbol,
                "sector": item["sector"],
                "price": float(ticker_24hr["lastPrice"]),
                "ret_5d": round(ret_5d, 4),
                "ret_20d": round(ret_20d, 4),
                "rel_strength": round(rel_strength, 4),
                "trend_strength": round(_trend_strength(closes), 4),
                "volume_acceleration": round(_volume_acceleration(quote_volumes), 4),
                "volatility_20d": round(_volatility_20d(closes), 4),
                "avg_daily_value_usd": round(mean(quote_volumes[-20:]), 2),
                "event_risk": bool(item.get("event_risk", False)),
                "forward_return_5d": None,
            }
        )

    return {"as_of": as_of, "regime_hint": "NEUTRAL", "rows": rows}


def write_snapshot(snapshot: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
