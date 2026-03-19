from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json

from .binance import BinanceClient
from .config import load_settings
from .evolution import suggest_policy_mutation
from .pipeline import run_pipeline
from .scoring import score_database
from .snapshot_builder import build_snapshot, write_snapshot
from .storage import Storage


def cmd_run(provider: str | None = None, reset_db: bool = False) -> int:
    settings = load_settings()
    if provider:
        settings = replace(settings, provider=provider)
    if reset_db:
        Storage(settings.db_path).reset()
    result = run_pipeline(settings)
    print(json.dumps(result.to_dict(), indent=2))
    return 0


def cmd_score() -> int:
    settings = load_settings()
    summary = score_database(settings.db_path)
    print(json.dumps(asdict(summary), indent=2))
    return 0


def cmd_runs() -> int:
    settings = load_settings()
    storage = Storage(settings.db_path)
    storage.initialize()
    print(json.dumps(storage.fetch_runs(), indent=2))
    return 0


def cmd_portfolio() -> int:
    settings = load_settings()
    storage = Storage(settings.db_path)
    storage.initialize()
    snapshot = storage.load_latest_portfolio_snapshot()
    print(json.dumps(snapshot.__dict__ if snapshot else {}, default=lambda o: o.__dict__, indent=2))
    return 0


def cmd_mutate() -> int:
    settings = load_settings()
    result = run_pipeline(settings)
    suggestion = suggest_policy_mutation(result.analyst_views)
    print(json.dumps(asdict(suggestion) if suggestion else {}, indent=2))
    return 0


def cmd_backtest(provider: str | None = None, reset_db: bool = False) -> int:
    settings = load_settings()
    if provider:
        settings = replace(settings, provider=provider)
    if reset_db:
        Storage(settings.db_path).reset()
    runs = []
    for snapshot_path in sorted(settings.snapshots_dir.glob("*.json")):
        result = run_pipeline(settings, snapshot_path=snapshot_path)
        runs.append(
            {
                "run_id": result.run_id,
                "as_of": result.as_of,
                "actions": len(result.actions),
                "regime": result.regime,
            }
        )
    payload = {"runs": runs, "score": asdict(score_database(settings.db_path))}
    print(json.dumps(payload, indent=2))
    return 0


def cmd_fetch_snapshot(output: str | None = None) -> int:
    settings = load_settings()
    client = BinanceClient(settings.binance_rest_base_url)
    snapshot = build_snapshot(settings, client)
    output_path = settings.snapshot_path if output is None else settings.root_dir / output
    write_snapshot(snapshot, output_path)
    print(json.dumps({"snapshot_path": str(output_path), "rows": len(snapshot["rows"])}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ATLAS v2 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--provider", choices=["mock", "openai"])
    run_parser.add_argument("--reset-db", action="store_true")

    subparsers.add_parser("score")
    subparsers.add_parser("runs")
    subparsers.add_parser("portfolio")
    subparsers.add_parser("mutate")

    backtest_parser = subparsers.add_parser("backtest")
    backtest_parser.add_argument("--provider", choices=["mock", "openai"])
    backtest_parser.add_argument("--reset-db", action="store_true")

    fetch_parser = subparsers.add_parser("fetch-snapshot")
    fetch_parser.add_argument("--output")

    args = parser.parse_args()

    if args.command == "run":
        return cmd_run(args.provider, args.reset_db)
    if args.command == "score":
        return cmd_score()
    if args.command == "runs":
        return cmd_runs()
    if args.command == "portfolio":
        return cmd_portfolio()
    if args.command == "mutate":
        return cmd_mutate()
    if args.command == "backtest":
        return cmd_backtest(args.provider, args.reset_db)
    if args.command == "fetch-snapshot":
        return cmd_fetch_snapshot(args.output)
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
