from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..llm import BaseLLMClient, build_request, to_analyst_view
from ..models import AnalystView, Candidate, MarketSnapshot, PortfolioAction, Position, RiskDecision


@dataclass
class AnalystAgent:
    name: str
    policy_version: str
    client: BaseLLMClient

    def analyze(self, candidate: Candidate, snapshot: MarketSnapshot) -> AnalystView:
        request = build_request(candidate, snapshot, self.policy_version)
        response = self.client.analyze_candidate(request)
        return to_analyst_view(self.name, candidate, response, self.policy_version)


@dataclass
class RiskAgent:
    settings: Settings

    def review(self, view: AnalystView, snapshot: MarketSnapshot) -> RiskDecision:
        row = next(row for row in snapshot.rows if row.ticker == view.ticker)
        if row.avg_daily_value_usd < self.settings.min_liquidity_usd:
            return RiskDecision(False, view.ticker, view.side, "liquidity below threshold", 0.0)
        if row.event_risk:
            return RiskDecision(False, view.ticker, view.side, "event risk active", 0.0)
        if row.volatility_20d > self.settings.max_volatility_20d:
            return RiskDecision(False, view.ticker, view.side, "volatility too high", 0.0)
        conviction_weight = min(self.settings.max_position_weight, view.conviction / 1000)
        return RiskDecision(True, view.ticker, view.side, "approved", round(conviction_weight, 4))


@dataclass
class PortfolioManager:
    settings: Settings

    def build_actions(
        self,
        decisions: list[RiskDecision],
        views: list[AnalystView],
        snapshot: MarketSnapshot,
        current_positions: list[Position],
    ) -> list[PortfolioAction]:
        current_map = {position.ticker: position for position in current_positions}
        price_map = {row.ticker: row for row in snapshot.rows}
        targets: dict[str, tuple[AnalystView, float]] = {}
        actions: list[PortfolioAction] = []
        sector_weights: dict[str, float] = {}

        for decision in decisions:
            if not decision.approved:
                continue
            view = next(item for item in views if item.ticker == decision.ticker)
            row = price_map[decision.ticker]
            current_sector_weight = sector_weights.get(row.sector, 0.0)
            available_sector_capacity = self.settings.max_sector_weight - current_sector_weight
            weight = max(0.0, min(decision.max_weight, available_sector_capacity))
            if weight <= 0:
                continue
            sector_weights[row.sector] = current_sector_weight + weight
            targets[view.ticker] = (view, round(weight, 4))

        for ticker, (view, weight) in targets.items():
            row = price_map[ticker]
            existing = current_map.get(ticker)
            current_weight = existing.target_weight if existing else 0.0
            delta_weight = round(weight - current_weight, 4)
            units = round((self.settings.default_cash * abs(delta_weight)) / row.price, 6)
            action_name = "OPEN" if existing is None else "REBALANCE"
            if abs(delta_weight) < 0.0001:
                action_name = "HOLD"
                units = existing.units if existing else 0.0
            if action_name != "HOLD" and units <= 0:
                continue
            actions.append(
                PortfolioAction(
                    ticker=view.ticker,
                    side=view.side,
                    action=action_name,
                    target_weight=weight,
                    delta_weight=delta_weight,
                    weight=weight,
                    units=units,
                    rationale=view.thesis,
                    price=row.price,
                    realized_return_5d=row.forward_return_5d,
                )
            )

        for ticker, position in current_map.items():
            if ticker in targets or ticker not in price_map:
                continue
            row = price_map[ticker]
            actions.append(
                PortfolioAction(
                    ticker=ticker,
                    side=position.side,
                    action="CLOSE",
                    target_weight=0.0,
                    delta_weight=round(-position.target_weight, 4),
                    weight=0.0,
                    units=position.units,
                    rationale="Ticker no longer in target book.",
                    price=row.price,
                    realized_return_5d=row.forward_return_5d,
                )
            )
        return actions
