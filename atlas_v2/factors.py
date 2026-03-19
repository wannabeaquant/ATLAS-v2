from __future__ import annotations

from .models import Candidate, MarketSnapshot


def score_long_candidate(row) -> float:
    return (
        row.rel_strength * 0.28
        + row.ret_20d * 0.24
        + row.trend_strength * 0.22
        + row.volume_acceleration * 0.18
        - row.volatility_20d * 0.002
    )


def score_short_candidate(row) -> float:
    return (
        -row.rel_strength * 0.28
        - row.ret_20d * 0.24
        - row.trend_strength * 0.22
        - row.volume_acceleration * 0.18
        + row.volatility_20d * 0.002
    )


def build_candidates(snapshot: MarketSnapshot, top_n: int = 6) -> list[Candidate]:
    longs: list[Candidate] = []
    shorts: list[Candidate] = []
    for row in snapshot.rows:
        long_score = score_long_candidate(row)
        short_score = score_short_candidate(row)
        longs.append(
            Candidate(
                ticker=row.ticker,
                sector=row.sector,
                side="LONG",
                factor_score=round(long_score, 4),
                thesis_points=[
                    f"relative strength {row.rel_strength:.2f}",
                    f"20d return {row.ret_20d:.2f}",
                    f"trend strength {row.trend_strength:.2f}",
                    f"volume acceleration {row.volume_acceleration:.2f}",
                ],
            )
        )
        shorts.append(
            Candidate(
                ticker=row.ticker,
                sector=row.sector,
                side="SHORT",
                factor_score=round(short_score, 4),
                thesis_points=[
                    f"relative weakness {row.rel_strength:.2f}",
                    f"20d return {row.ret_20d:.2f}",
                    f"trend strength {row.trend_strength:.2f}",
                    f"volume acceleration {row.volume_acceleration:.2f}",
                ],
            )
        )
    longs.sort(key=lambda item: item.factor_score, reverse=True)
    shorts.sort(key=lambda item: item.factor_score, reverse=True)
    half = max(1, top_n // 2)
    return longs[:half] + shorts[:half]
