from __future__ import annotations

from .config import Settings
from .models import MarketSnapshot, PortfolioAction, PortfolioSnapshot, Position


class PaperPortfolioEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def apply_actions(
        self,
        current_positions: list[Position],
        actions: list[PortfolioAction],
        snapshot: MarketSnapshot,
        prior_cash: float | None = None,
    ) -> PortfolioSnapshot:
        price_map = {row.ticker: row.price for row in snapshot.rows}
        current_map = {position.ticker: position for position in current_positions}
        cash = self.settings.default_cash if prior_cash is None else prior_cash

        for action in actions:
            px = action.price or price_map[action.ticker]
            if action.action == "HOLD":
                if action.ticker in current_map:
                    current_map[action.ticker].current_price = px
                continue
            if action.action == "CLOSE":
                existing = current_map.pop(action.ticker, None)
                if existing is not None:
                    signed = existing.current_price * existing.units
                    cash += signed if existing.side == "LONG" else -signed
                continue

            signed_trade = px * action.units
            if action.side == "LONG":
                cash -= signed_trade if action.delta_weight >= 0 else -signed_trade
            else:
                cash += signed_trade if action.delta_weight >= 0 else -signed_trade

            target_units = round((self.settings.default_cash * action.target_weight) / px, 6)
            existing = current_map.get(action.ticker)
            if existing is None:
                current_map[action.ticker] = Position(
                    ticker=action.ticker,
                    side=action.side,
                    units=target_units,
                    entry_price=px,
                    current_price=px,
                    target_weight=action.target_weight,
                )
            else:
                existing.units = target_units
                existing.current_price = px
                existing.target_weight = action.target_weight
                existing.side = action.side

        positions = sorted(current_map.values(), key=lambda item: item.ticker)
        gross = 0.0
        net = 0.0
        mtm = cash
        for position in positions:
            position.current_price = price_map.get(position.ticker, position.current_price)
            notional = position.current_price * position.units
            gross += abs(notional) / self.settings.default_cash
            signed = notional if position.side == "LONG" else -notional
            net += signed / self.settings.default_cash
            mtm += signed

        return PortfolioSnapshot(
            as_of=snapshot.as_of,
            cash=round(cash, 2),
            gross_exposure=round(gross, 4),
            net_exposure=round(net, 4),
            mark_to_market_equity=round(mtm, 2),
            positions=positions,
        )
