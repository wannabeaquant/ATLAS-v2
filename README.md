# ATLAS v2

ATLAS v2 is a runnable crypto paper-trading and research scaffold inspired by the public `atlas-gic` methodology, redesigned around deterministic execution, explicit schemas, and auditable scoring.

## Design goals

- Keep the core trading loop deterministic
- Use LLMs only where synthesis helps
- Separate signal generation, risk, and portfolio construction
- Version policy and prompt changes cleanly
- Make every recommendation measurable

## Architecture

```text
crypto market snapshot
    -> candidate engine
    -> analyst layer
    -> risk engine
    -> portfolio engine
    -> recommendations log
    -> scoring and attribution
    -> prompt/policy evolution hooks
```

The current scaffold ships with:

- A deterministic candidate engine for liquid crypto spot pairs
- A real OpenAI Responses API adapter plus a mock fallback
- Public Binance market-data snapshot ingestion
- A persistent paper portfolio and rebalance loop
- SQLite-backed run, recommendation, and portfolio storage
- Crypto sample backtest data with forward returns

## Quick start

```powershell
cd C:\CS\Trading Expts\atlas-v2
python -m atlas_v2.cli fetch-snapshot
python -m atlas_v2.cli run --provider mock --reset-db
python -m atlas_v2.cli portfolio
python -m atlas_v2.cli score
python -m atlas_v2.cli mutate
```

For an OpenAI-backed run:

```powershell
Copy-Item .env.example .env
# fill in OPENAI_API_KEY
python -m atlas_v2.cli fetch-snapshot
python -m atlas_v2.cli run --provider openai --reset-db
```

For a replay/backtest on the bundled sample snapshots:

```powershell
python -m atlas_v2.cli backtest --provider mock --reset-db
```

## Project layout

```text
atlas_v2/
  agents/
  sample_data/
  __init__.py
  binance.py
  cli.py
  config.py
  data.py
  factors.py
  llm.py
  models.py
  pipeline.py
  portfolio.py
  scoring.py
  snapshot_builder.py
  storage.py
```

## What is deliberately missing

- Live order routing
- Exchange-specific execution simulators
- Funding/open-interest/order-book features
- Auto-mutation of prompts in production

Those should be added only after the baseline paper-trading loop is stable and measurable.
