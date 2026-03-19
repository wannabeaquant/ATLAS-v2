from __future__ import annotations

from dataclasses import dataclass

from .models import AnalystView


@dataclass
class PolicyMutationSuggestion:
    agent_name: str
    current_policy_version: str
    problem_statement: str
    suggested_change: str


def suggest_policy_mutation(views: list[AnalystView]) -> PolicyMutationSuggestion | None:
    if not views:
        return None
    weakest = min(views, key=lambda item: item.conviction)
    return PolicyMutationSuggestion(
        agent_name=weakest.agent_name,
        current_policy_version=weakest.policy_version,
        problem_statement=(
            f"Lowest-confidence recommendation was {weakest.ticker} at conviction {weakest.conviction}."
        ),
        suggested_change=(
            "Tighten candidate selection by requiring stronger factor alignment before producing a thesis."
        ),
    )
