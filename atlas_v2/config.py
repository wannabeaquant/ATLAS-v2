from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv(root: Path) -> None:
    dotenv_path = root / ".env"
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    data_dir: Path
    db_path: Path
    snapshot_path: Path
    snapshots_dir: Path
    prompts_dir: Path
    universe_path: Path
    provider: str
    openai_api_key: str | None
    openai_model: str
    binance_rest_base_url: str
    default_cash: float = 1_000_000.0
    max_position_weight: float = 0.12
    max_sector_weight: float = 0.35
    min_liquidity_usd: float = 25_000_000.0
    max_volatility_20d: float = 180.0


def load_settings(root_dir: Path | None = None) -> Settings:
    root = (root_dir or Path(__file__).resolve().parents[1]).resolve()
    _load_dotenv(root)
    data_dir = root / "data"
    prompts_dir = root / "prompts"
    data_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        root_dir=root,
        data_dir=data_dir,
        db_path=data_dir / "atlas_v2.sqlite3",
        snapshot_path=root / "atlas_v2" / "sample_data" / "market_snapshot.json",
        snapshots_dir=root / "atlas_v2" / "sample_data" / "snapshots",
        prompts_dir=prompts_dir,
        universe_path=root / "atlas_v2" / "sample_data" / "universe.json",
        provider=os.environ.get("ATLAS_PROVIDER", "mock"),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        openai_model=os.environ.get("ATLAS_OPENAI_MODEL", "gpt-4.1-mini"),
        binance_rest_base_url=os.environ.get("BINANCE_REST_BASE_URL", "https://api.binance.com"),
    )
