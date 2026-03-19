from __future__ import annotations

import json
from pathlib import Path

from .models import MarketRow, MarketSnapshot


def load_snapshot(path: Path) -> MarketSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [MarketRow(**row) for row in payload["rows"]]
    return MarketSnapshot(
        as_of=payload["as_of"],
        regime_hint=payload["regime_hint"],
        rows=rows,
    )


def load_snapshots(directory: Path) -> list[MarketSnapshot]:
    return [load_snapshot(path) for path in sorted(directory.glob("*.json"))]
