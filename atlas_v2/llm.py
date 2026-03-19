from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

from .models import AnalystView, Candidate, MarketSnapshot


@dataclass
class LLMRequest:
    system_prompt: str
    user_payload: dict[str, Any]
    policy_version: str


class BaseLLMClient:
    def analyze_candidate(self, request_payload: LLMRequest) -> dict[str, Any]:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    def analyze_candidate(self, request_payload: LLMRequest) -> dict[str, Any]:
        candidate = request_payload.user_payload["candidate"]
        conviction = max(40, min(90, int(52 + candidate["factor_score"] * 18)))
        thesis = (
            f"{candidate['ticker']} ranks highly in the crypto factor stack. "
            f"Primary supports: {', '.join(candidate['thesis_points'])}."
        )
        return {
            "conviction": conviction,
            "thesis": thesis,
            "risks": ["Public market data only.", "No funding/order-book features yet."],
            "metadata": {"source": "mock_llm", "policy_version": request_payload.policy_version},
        }


class OpenAIResponsesClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def analyze_candidate(self, request_payload: LLMRequest) -> dict[str, Any]:
        body = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": request_payload.system_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are analyzing liquid crypto spot pairs for a paper-trading workflow.\n"
                                "Return valid JSON matching the schema exactly.\n"
                                f"{json.dumps(request_payload.user_payload, ensure_ascii=True)}"
                            ),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "candidate_analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "conviction": {"type": "integer", "minimum": 1, "maximum": 100},
                            "thesis": {"type": "string"},
                            "risks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "maxItems": 3,
                            },
                            "metadata": {
                                "type": "object",
                                "properties": {
                                    "source": {"type": "string"},
                                    "policy_version": {"type": "string"},
                                },
                                "required": ["source", "policy_version"],
                                "additionalProperties": False,
                            },
                        },
                        "required": ["conviction", "thesis", "risks", "metadata"],
                        "additionalProperties": False,
                    },
                }
            },
        }
        req = request.Request(
            url="https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"OpenAI API connection error: {exc}") from exc

        text = payload.get("output_text")
        if not text:
            raise RuntimeError(f"OpenAI response missing output_text: {payload}")
        return json.loads(text)


def build_request(candidate: Candidate, snapshot: MarketSnapshot, policy_version: str) -> LLMRequest:
    return LLMRequest(
        system_prompt=(
            "You are a crypto market analyst. Convert structured candidate evidence into a concise, "
            "auditable thesis. Do not invent missing facts. Keep the analysis grounded in the "
            "provided crypto snapshot and separate trend from volatility."
        ),
        user_payload={
            "as_of": snapshot.as_of,
            "regime_hint": snapshot.regime_hint,
            "candidate": {
                "ticker": candidate.ticker,
                "sector": candidate.sector,
                "side": candidate.side,
                "factor_score": candidate.factor_score,
                "thesis_points": candidate.thesis_points,
            },
        },
        policy_version=policy_version,
    )


def to_analyst_view(agent_name: str, candidate: Candidate, response: dict[str, Any], policy_version: str) -> AnalystView:
    return AnalystView(
        agent_name=agent_name,
        ticker=candidate.ticker,
        side=candidate.side,
        conviction=int(response["conviction"]),
        thesis=str(response["thesis"]),
        policy_version=policy_version,
        metadata=dict(response.get("metadata", {})) | {"risks": response.get("risks", [])},
    )
