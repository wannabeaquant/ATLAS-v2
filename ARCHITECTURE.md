# ATLAS v2 Architecture

## Core principle

The production trading path should stay deterministic wherever possible. LLMs should rank, explain, or filter candidate setups, but should not own hard risk gates or execution.

## Current modules

- `atlas_v2/data.py`
  Loads normalized crypto snapshots.
- `atlas_v2/binance.py`
  Pulls public market data from Binance REST endpoints.
- `atlas_v2/snapshot_builder.py`
  Builds normalized crypto snapshots from live Binance data.
- `atlas_v2/factors.py`
  Builds deterministic long and short candidates from structured crypto inputs.
- `atlas_v2/llm.py`
  Defines the LLM adapter boundary for thesis generation.
- `atlas_v2/agents/deterministic.py`
  Runs analyst, risk, and portfolio-management agents.
- `atlas_v2/portfolio.py`
  Maintains the paper portfolio and rebalance logic.
- `atlas_v2/storage.py`
  Persists runs, recommendations, positions, and portfolio snapshots to SQLite.
- `atlas_v2/scoring.py`
  Produces score summaries from recorded recommendations.
- `atlas_v2/evolution.py`
  Holds the first policy-mutation hook.

## LLM boundary

When a real model is introduced, the request contract should remain narrow:

- structured snapshot fields
- candidate metadata
- current policy version
- explicit output schema

This keeps the system portable across model providers while keeping the trading loop deterministic.

## Live snapshot path

The primary live path is now:

1. Fetch public Binance 24h ticker and daily kline data
2. Compute 5d/20d returns, relative strength, trend strength, volume acceleration, and 20d volatility
3. Write the normalized snapshot
4. Run the analyst, risk, and portfolio loop
