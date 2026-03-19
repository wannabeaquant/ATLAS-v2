from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path

from .models import PortfolioSnapshot, Position, RunResult


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    as_of TEXT NOT NULL,
    regime TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    conviction INTEGER NOT NULL,
    weight REAL NOT NULL,
    realized_return_5d REAL,
    rationale TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS positions (
    ticker TEXT PRIMARY KEY,
    side TEXT NOT NULL,
    units REAL NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL NOT NULL,
    target_weight REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    as_of TEXT PRIMARY KEY,
    cash REAL NOT NULL,
    gross_exposure REAL NOT NULL,
    net_exposure REAL NOT NULL,
    mark_to_market_equity REAL NOT NULL,
    payload_json TEXT NOT NULL
);
"""


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executescript(SCHEMA)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(positions)").fetchall()}
            if "units" not in columns and "shares" in columns:
                conn.execute("ALTER TABLE positions ADD COLUMN units REAL")
                conn.execute("UPDATE positions SET units = CAST(shares AS REAL)")
            conn.commit()

    def reset(self) -> None:
        if self.db_path.exists():
            self.db_path.unlink()

    def save_run(self, result: RunResult) -> None:
        payload = json.dumps(result.to_dict(), ensure_ascii=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs (run_id, as_of, regime, created_at, payload_json) VALUES (?, ?, ?, ?, ?)",
                (result.run_id, result.as_of, result.regime, result.created_at, payload),
            )
            for action in result.actions:
                matching_view = next(item for item in result.analyst_views if item.ticker == action.ticker)
                conn.execute(
                    "INSERT INTO recommendations (run_id, ticker, side, conviction, weight, realized_return_5d, rationale) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        result.run_id,
                        action.ticker,
                        action.side,
                        matching_view.conviction,
                        action.weight,
                        action.realized_return_5d,
                        action.rationale,
                    ),
                )
            conn.commit()

    def fetch_runs(self) -> list[tuple[str, str, str]]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute("SELECT run_id, as_of, regime FROM runs ORDER BY created_at DESC").fetchall()
        return [(str(run_id), str(as_of), str(regime)) for run_id, as_of, regime in rows]

    def load_positions(self) -> list[Position]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT ticker, side, units, entry_price, current_price, target_weight FROM positions ORDER BY ticker"
            ).fetchall()
        return [
            Position(
                ticker=str(ticker),
                side=str(side),
                units=float(units),
                entry_price=float(entry_price),
                current_price=float(current_price),
                target_weight=float(target_weight),
            )
            for ticker, side, units, entry_price, current_price, target_weight in rows
        ]

    def replace_positions(self, positions: list[Position]) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("DELETE FROM positions")
            for position in positions:
                conn.execute(
                    """
                    INSERT INTO positions (ticker, side, units, entry_price, current_price, target_weight, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        position.ticker,
                        position.side,
                        position.units,
                        position.entry_price,
                        position.current_price,
                        position.target_weight,
                    ),
                )
            conn.commit()

    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        payload = json.dumps(
            {
                "as_of": snapshot.as_of,
                "cash": snapshot.cash,
                "gross_exposure": snapshot.gross_exposure,
                "net_exposure": snapshot.net_exposure,
                "mark_to_market_equity": snapshot.mark_to_market_equity,
                "positions": [position.__dict__ for position in snapshot.positions],
            },
            ensure_ascii=True,
        )
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO portfolio_snapshots
                (as_of, cash, gross_exposure, net_exposure, mark_to_market_equity, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.as_of,
                    snapshot.cash,
                    snapshot.gross_exposure,
                    snapshot.net_exposure,
                    snapshot.mark_to_market_equity,
                    payload,
                ),
            )
            conn.commit()

    def load_latest_portfolio_snapshot(self) -> PortfolioSnapshot | None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("SELECT payload_json FROM portfolio_snapshots ORDER BY as_of DESC LIMIT 1").fetchone()
        if row is None:
            return None
        payload = json.loads(str(row[0]))
        return PortfolioSnapshot(
            as_of=str(payload["as_of"]),
            cash=float(payload["cash"]),
            gross_exposure=float(payload["gross_exposure"]),
            net_exposure=float(payload["net_exposure"]),
            mark_to_market_equity=float(payload["mark_to_market_equity"]),
            positions=[Position(**position) for position in payload["positions"]],
        )
