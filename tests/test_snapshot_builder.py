from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from atlas_v2.config import load_settings
from atlas_v2.snapshot_builder import build_snapshot


class FakeBinanceClient:
    def fetch_ticker_24hr(self, symbol: str):
        return {"lastPrice": "100.0", "closeTime": "2026-03-19T00:00:00Z"}

    def fetch_klines(self, symbol: str, interval: str = "1d", limit: int = 30):
        return [
            [0, 0, 0, 0, str(100 + i), 0, 0, str(1000000 + i * 1000)]
            for i in range(limit)
        ]


class SnapshotBuilderTests(unittest.TestCase):
    def test_build_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data").mkdir()
            (root / "prompts").mkdir()
            sample_root = root / "atlas_v2" / "sample_data"
            sample_root.mkdir(parents=True)
            (sample_root / "universe.json").write_text(
                json.dumps(
                    [
                        {"ticker": "BTCUSDT", "sector": "Majors"},
                        {"ticker": "ETHUSDT", "sector": "Majors"},
                    ]
                ),
                encoding="utf-8",
            )
            (sample_root / "snapshots").mkdir()
            (sample_root / "market_snapshot.json").write_text('{"as_of":"2026-03-19T00:00:00Z","regime_hint":"NEUTRAL","rows":[]}', encoding="utf-8")
            settings = load_settings(root)
            snapshot = build_snapshot(settings, FakeBinanceClient())
            self.assertEqual(len(snapshot["rows"]), 2)
            self.assertIn("trend_strength", snapshot["rows"][0])
            self.assertIn("volume_acceleration", snapshot["rows"][0])


if __name__ == "__main__":
    unittest.main()
