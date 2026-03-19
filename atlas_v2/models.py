from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class MarketRow:
    ticker: str
    sector: str
    price: float
    ret_5d: float
    ret_20d: float
    rel_strength: float
    trend_strength: float
    volume_acceleration: float
    volatility_20d: float
    avg_daily_value_usd: float
    event_risk: bool = False
    forward_return_5d: float | None = None


@dataclass
class MarketSnapshot:
    as_of: str
    regime_hint: str
    rows: list[MarketRow]


@dataclass
class Candidate:
    ticker: str
    sector: str
    side: str
    factor_score: float
    thesis_points: list[str]


@dataclass
class AnalystView:
    agent_name: str
    ticker: str
    side: str
    conviction: int
    thesis: str
    policy_version: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskDecision:
    approved: bool
    ticker: str
    side: str
    reason: str
    max_weight: float


@dataclass
class PortfolioAction:
    ticker: str
    side: str
    action: str
    target_weight: float
    delta_weight: float
    weight: float
    units: float
    rationale: str
    price: float | None = None
    realized_return_5d: float | None = None


@dataclass
class RunResult:
    run_id: str
    as_of: str
    regime: str
    candidates: list[Candidate]
    analyst_views: list[AnalystView]
    risk_decisions: list[RiskDecision]
    actions: list[PortfolioAction]
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Position:
    ticker: str
    side: str
    units: float
    entry_price: float
    current_price: float
    target_weight: float


@dataclass
class PortfolioSnapshot:
    as_of: str
    cash: float
    gross_exposure: float
    net_exposure: float
    mark_to_market_equity: float
    positions: list[Position]
