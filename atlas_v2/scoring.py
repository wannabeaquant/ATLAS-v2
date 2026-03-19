from __future__ import annotations

from contextlib import closing
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .storage import Storage


@dataclass
class ScoreSummary:
    recommendations: int
    avg_conviction: float
    avg_weight: float
    avg_realized_return_5d: float
    hit_rate_pct: float


def score_database(db_path: Path) -> ScoreSummary:
    Storage(db_path).initialize()
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(AVG(conviction), 0),
                COALESCE(AVG(weight), 0),
                COALESCE(AVG(
                    CASE
                        WHEN realized_return_5d IS NULL THEN NULL
                        WHEN side = 'LONG' THEN realized_return_5d
                        ELSE -realized_return_5d
                    END
                ), 0),
                COALESCE(AVG(
                    CASE
                        WHEN realized_return_5d IS NULL THEN NULL
                        WHEN side = 'LONG' AND realized_return_5d > 0 THEN 1.0
                        WHEN side = 'SHORT' AND realized_return_5d < 0 THEN 1.0
                        ELSE 0.0
                    END
                ) * 100, 0)
            FROM recommendations
            """
        ).fetchone()
    recommendations, avg_conviction, avg_weight, avg_realized_return_5d, hit_rate_pct = row or (0, 0.0, 0.0, 0.0, 0.0)
    return ScoreSummary(
        recommendations=int(recommendations),
        avg_conviction=round(float(avg_conviction), 2),
        avg_weight=round(float(avg_weight), 4),
        avg_realized_return_5d=round(float(avg_realized_return_5d), 4),
        hit_rate_pct=round(float(hit_rate_pct), 2),
    )
