from __future__ import annotations

import json
from urllib import parse, request
from urllib.error import HTTPError, URLError


class BinanceClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def fetch_ticker_24hr(self, symbol: str) -> dict:
        return self._json_get("/api/v3/ticker/24hr", {"symbol": symbol})

    def fetch_klines(self, symbol: str, interval: str = "1d", limit: int = 30) -> list[list]:
        return self._json_get("/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": str(limit)})

    def _json_get(self, path: str, query: dict[str, str]) -> dict | list:
        query_string = parse.urlencode(query)
        url = f"{self.base_url}{path}?{query_string}"
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Binance API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Binance API connection error: {exc}") from exc
