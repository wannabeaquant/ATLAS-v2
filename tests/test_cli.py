from __future__ import annotations

from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from atlas_v2.config import load_settings
from atlas_v2.pipeline import run_pipeline
from atlas_v2.scoring import score_database


class AtlasV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "prompts").mkdir()
        sample_root = Path(__file__).resolve().parents[1] / "atlas_v2" / "sample_data"
        target_sample = self.root / "atlas_v2" / "sample_data"
        target_sample.mkdir(parents=True)
        for source in sample_root.rglob("*.json"):
            dest = target_sample / source.relative_to(sample_root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_mock_run_and_score(self) -> None:
        settings = load_settings(self.root)
        result = run_pipeline(settings)
        self.assertTrue(result.actions)
        summary = score_database(settings.db_path)
        self.assertGreater(summary.recommendations, 0)
        self.assertGreater(summary.hit_rate_pct, 0)

        with closing(sqlite3.connect(settings.db_path)) as conn:
            rows = conn.execute("SELECT ticker, realized_return_5d FROM recommendations").fetchall()
        self.assertTrue(any(row[1] is not None for row in rows))


if __name__ == "__main__":
    unittest.main()
