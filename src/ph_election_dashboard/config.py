from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "election_year": datetime.now().year,
    "current_election_type": "national",
    "data_files": {
        "national": "national_election_results.csv",
        "local": "local_election_results.csv",
        "barangay": "barangay_election_results.csv",
    },
    "data_source": "sqlite",
    "auto_refresh": True,
    "cache_ttl": 300,
    "log_level": "INFO",
}


def find_project_root(start: Path | None = None) -> Path:
    env_root = os.getenv("PH_ELECTION_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    candidates: list[Path] = []
    if start is not None:
        candidates.append(start)
    candidates.append(Path(__file__))
    candidates.append(Path.cwd())

    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        for parent in [resolved, *resolved.parents]:
            if (parent / "pyproject.toml").exists():
                return parent
    return Path.cwd().resolve()


@dataclass(frozen=True)
class Paths:
    project_root: Path
    config_dir: Path
    data_dir: Path
    log_dir: Path
    config_file: Path
    providers_file: Path
    db_path: Path

    @classmethod
    def from_env(cls) -> Paths:
        root = find_project_root()
        config_dir = Path(os.getenv("PH_ELECTION_CONFIG_DIR", root / "config"))
        data_dir = Path(os.getenv("PH_ELECTION_DATA_DIR", root / "data"))
        log_dir = Path(os.getenv("PH_ELECTION_LOG_DIR", root / "logs"))
        config_file = Path(
            os.getenv("PH_ELECTION_CONFIG_FILE", config_dir / "config.json")
        )
        providers_file = Path(
            os.getenv("PH_ELECTION_PROVIDERS_FILE", config_dir / "providers.json")
        )
        db_path = Path(os.getenv("PH_ELECTION_DB_PATH", data_dir / "election.db"))
        return cls(
            project_root=root,
            config_dir=config_dir,
            data_dir=data_dir,
            log_dir=log_dir,
            config_file=config_file,
            providers_file=providers_file,
            db_path=db_path,
        )

    def ensure_dirs(self) -> None:
        for directory in (
            self.config_dir,
            self.data_dir,
            self.log_dir,
            self.db_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def get_paths() -> Paths:
    return Paths.from_env()


def setup_logger(
    log_level: str = "INFO",
    log_dir: Path | None = None,
    log_to_file: bool = True,
) -> logging.Logger:
    logger = logging.getLogger("ph_election_dashboard")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    for handler in list(logger.handlers):
        handler.close()
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_to_file and log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "election_dashboard.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def merge_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    if not config:
        return merged
    for key, value in config.items():
        if key == "data_files" and isinstance(value, dict):
            merged["data_files"].update(value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or get_paths().config_file
    if not config_path.exists():
        return merge_config(None)
    try:
        with config_path.open(encoding="utf-8") as handle:
            return merge_config(json.load(handle))
    except (json.JSONDecodeError, OSError):
        return merge_config(None)
