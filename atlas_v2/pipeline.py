from __future__ import annotations

import uuid

from .agents.deterministic import AnalystAgent, PortfolioManager, RiskAgent
from .config import Settings
from .data import load_snapshot
from .factors import build_candidates
from .llm import MockLLMClient, OpenAIResponsesClient
from .models import RunResult
from .portfolio import PaperPortfolioEngine
from .storage import Storage


def build_llm_client(settings: Settings):
    if settings.provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to the environment or .env file.")
        return OpenAIResponsesClient(api_key=settings.openai_api_key, model=settings.openai_model)
    return MockLLMClient()


def run_pipeline(settings: Settings, snapshot_path=None) -> RunResult:
    snapshot = load_snapshot(snapshot_path or settings.snapshot_path)
    storage = Storage(settings.db_path)
    storage.initialize()
    current_positions = storage.load_positions()
    prior_snapshot = storage.load_latest_portfolio_snapshot()

    candidates = build_candidates(snapshot)
    analyst = AnalystAgent(name="selector_analyst", policy_version="v1", client=build_llm_client(settings))
    views = [analyst.analyze(candidate, snapshot) for candidate in candidates]

    risk_agent = RiskAgent(settings=settings)
    decisions = [risk_agent.review(view, snapshot) for view in views]

    portfolio_manager = PortfolioManager(settings=settings)
    actions = portfolio_manager.build_actions(decisions, views, snapshot, current_positions)
    portfolio_engine = PaperPortfolioEngine(settings=settings)
    portfolio_snapshot = portfolio_engine.apply_actions(
        current_positions=current_positions,
        actions=actions,
        snapshot=snapshot,
        prior_cash=prior_snapshot.cash if prior_snapshot else None,
    )

    result = RunResult(
        run_id=str(uuid.uuid4()),
        as_of=snapshot.as_of,
        regime=snapshot.regime_hint,
        candidates=candidates,
        analyst_views=views,
        risk_decisions=decisions,
        actions=actions,
    )
    storage.save_run(result)
    storage.replace_positions(portfolio_snapshot.positions)
    storage.save_portfolio_snapshot(portfolio_snapshot)
    return result
