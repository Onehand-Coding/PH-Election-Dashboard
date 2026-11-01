# PH Election Dashboard Finish-Out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-commit PH Election Dashboard into a correct, installable local demo with working filters, maps, exports, auto refresh, SQLite reads, flexible AI providers, tests, CI, and accurate docs.

**Architecture:** A `src`-layout Python package splits concerns into config, data, db, filters, geo, charts, ai, and app modules. Streamlit is only the UI layer. CSV files remain the source of truth, SQLite is a local read cache, and bundled GeoJSON drives the maps.

**Tech Stack:** Python 3.10+, Streamlit 1.40+, pandas, Plotly, SQLite (stdlib), requests, python-dotenv, pytest, ruff, uv, GitHub Actions.

**Git policy:** The user has not asked for commits. Do not run any `git commit`, `git push`, or `git add` command unless the user explicitly requests it. The commit steps in the source plan template are intentionally omitted.

---

## File Map

Create or replace:

- `pyproject.toml`
- `app.py`
- `.gitignore`
- `.env.example`
- `config/providers.example.json`
- `src/config.py` (delete after moving its logic)
- `src/ph_election_dashboard/__init__.py`
- `src/ph_election_dashboard/__main__.py`
- `src/ph_election_dashboard/config.py`
- `src/ph_election_dashboard/data.py`
- `src/ph_election_dashboard/db.py`
- `src/ph_election_dashboard/filters.py`
- `src/ph_election_dashboard/geo.py`
- `src/ph_election_dashboard/charts.py`
- `src/ph_election_dashboard/ai.py`
- `src/ph_election_dashboard/app.py`
- `src/ph_election_dashboard/launcher.py`
- `src/ph_election_dashboard/geo_data/__init__.py`
- `src/ph_election_dashboard/geo_data/ph_regions.geojson`
- `src/ph_election_dashboard/geo_data/ph_island_groups.geojson`
- `tests/conftest.py`
- `tests/test_config.py`
- `tests/test_data.py`
- `tests/test_db.py`
- `tests/test_filters.py`
- `tests/test_geo.py`
- `tests/test_charts.py`
- `tests/test_ai.py`
- `tests/test_app_smoke.py`
- `.github/workflows/ci.yml`
- `README.md`
- `CONTEXT.md`
- `THIRD_PARTY_NOTICES.md`
- `docs/geo-data.md`
- `data/README_DATA.md`
- `config/config.json`

Do not touch:

- `LICENSE`
- The three sample CSV files, except for schema-compatible additions if a task explicitly says so.

---

## Task 1: Package Skeleton and Entry Points

**Files:**
- Modify: `pyproject.toml`
- Create: `app.py`
- Create: `src/ph_election_dashboard/__init__.py`
- Create: `src/ph_election_dashboard/__main__.py`
- Create: `src/ph_election_dashboard/launcher.py`
- Modify: `.gitignore`

- [ ] **Step 1: Replace `pyproject.toml`**

```toml
[project]
name = "ph-election-dashboard"
version = "0.2.0"
description = "A dashboard for Philippine election sample data"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [
    { name = "Onehand Coding", email = "onehand.coding433@gmail.com" },
]
dependencies = [
    "pandas>=2.0",
    "streamlit>=1.40",
    "plotly>=5.0",
    "python-dotenv>=1.0",
    "requests>=2.31",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ph_election_dashboard"]

[project.optional-dependencies]
dev = [
    "pytest>=8.4",
    "pytest-mock>=3.14",
    "ruff>=0.6",
]

[project.scripts]
ph-election-dashboard = "ph_election_dashboard.launcher:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Create the root Streamlit shim at `app.py`**

```python
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ph_election_dashboard.app import main  # noqa: E402

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `src/ph_election_dashboard/__init__.py`**

```python
"""Philippine election sample-data dashboard."""

__version__ = "0.2.0"
```

- [ ] **Step 4: Create `src/ph_election_dashboard/__main__.py`**

```python
from ph_election_dashboard.launcher import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create `src/ph_election_dashboard/launcher.py`**

```python
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    app_path = Path(__file__).resolve().parent / "app.py"
    src_path = str(app_path.parent.parent)
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing else src_path + os.pathsep + existing
    try:
        return subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(app_path)],
            env=env,
        )
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Replace `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
build/
dist/
.pytest_cache/
.ruff_cache/

# Secrets and local state
.env
.env.*
!.env.example
data/election.db
data/election.db-*
logs/
.streamlit/

# OS and editors
.DS_Store
.sublime-workspace/
```

- [ ] **Step 7: Install and verify imports**

Run:

```bash
uv sync --extra dev
uv run python -c "import ph_election_dashboard; print(ph_election_dashboard.__version__)"
```

Expected:

```text
0.2.0
```

---

## Task 2: Config Module

**Files:**
- Create: `src/ph_election_dashboard/config.py`
- Delete: `src/config.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

- [ ] **Step 2: Write the failing config tests in `tests/test_config.py`**

```python
import json

from ph_election_dashboard import config


def test_merge_config_overrides_defaults():
    merged = config.merge_config({"election_year": 2030, "data_files": {"national": "x.csv"}})
    assert merged["election_year"] == 2030
    assert merged["data_files"]["national"] == "x.csv"
    assert merged["data_files"]["local"] == "local_election_results.csv"


def test_load_config_returns_defaults_when_missing(tmp_path):
    merged = config.load_config(tmp_path / "missing.json")
    assert merged["data_source"] == "sqlite"
    assert merged["auto_refresh"] is True


def test_load_config_merges_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"election_year": 2028, "data_source": "csv"}))
    merged = config.load_config(path)
    assert merged["election_year"] == 2028
    assert merged["data_source"] == "csv"
    assert merged["cache_ttl"] == 300


def test_paths_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PH_ELECTION_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PH_ELECTION_CONFIG_FILE", str(tmp_path / "config" / "config.json"))
    monkeypatch.setenv("PH_ELECTION_DB_PATH", str(tmp_path / "db" / "election.db"))
    monkeypatch.setenv("PH_ELECTION_LOG_DIR", str(tmp_path / "logs"))
    paths = config.Paths.from_env()
    assert paths.data_dir == tmp_path / "data"
    assert paths.config_file == tmp_path / "config" / "config.json"
    assert paths.db_path == tmp_path / "db" / "election.db"
    assert paths.log_dir == tmp_path / "logs"


def test_ensure_dirs_creates_directories(tmp_path):
    paths = config.Paths(
        project_root=tmp_path,
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        config_file=tmp_path / "config" / "config.json",
        providers_file=tmp_path / "config" / "providers.json",
        db_path=tmp_path / "data" / "election.db",
    )
    paths.ensure_dirs()
    assert paths.config_dir.is_dir()
    assert paths.data_dir.is_dir()
    assert paths.log_dir.is_dir()
    assert paths.db_path.parent.is_dir()


def test_setup_logger_writes_file(tmp_path):
    logger = config.setup_logger("INFO", tmp_path)
    logger.info("hello")
    assert (tmp_path / "election_dashboard.log").exists()
    for handler in list(logger.handlers):
        handler.close()
    logger.handlers.clear()
```

- [ ] **Step 3: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_config.py -q
```

Expected: FAIL with `ImportError` or `AttributeError` because `config.py` does not exist yet.

- [ ] **Step 4: Create `src/ph_election_dashboard/config.py`**

```python
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
```

- [ ] **Step 5: Delete the old top-level config module**

Run:

```bash
rm src/config.py
```

- [ ] **Step 6: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/test_config.py -q
```

Expected: all config tests pass.

---

## Task 3: Data Normalization and Validation

**Files:**
- Create: `src/ph_election_dashboard/data.py` (normalization portion only)
- Create: `tests/test_data.py`

- [ ] **Step 1: Write the failing normalization tests in `tests/test_data.py`**

```python
import pandas as pd

from ph_election_dashboard import data


def test_normalize_headers_aliases_and_case():
    frame = pd.DataFrame(
        {
            "Candidate": ["Alice"],
            "Position": ["Senator"],
            "Party": ["Party A"],
            "Votes": ["100"],
            "Municipality": ["Manila"],
        }
    )
    result = data.normalize_dataframe(frame)
    assert result.ok
    assert list(result.dataframe.columns) == data.CANONICAL_COLUMNS
    assert result.dataframe.loc[0, "candidate_name"] == "Alice"
    assert result.dataframe.loc[0, "total_votes"] == 100
    assert result.dataframe.loc[0, "municipality_city"] == "Manila"


def test_missing_required_column_is_fatal():
    frame = pd.DataFrame({"Position": ["Senator"], "Votes": [100]})
    result = data.normalize_dataframe(frame)
    assert not result.ok
    assert "candidate_name" in result.errors[0]


def test_invalid_votes_are_dropped_with_warning():
    frame = pd.DataFrame(
        {
            "Position": ["Senator", "Senator"],
            "Candidate_Name": ["Alice", "Bob"],
            "Total_Votes": ["100", "not-a-number"],
        }
    )
    result = data.normalize_dataframe(frame)
    assert result.ok
    assert len(result.dataframe) == 1
    assert result.dataframe.loc[0, "candidate_name"] == "Alice"
    assert any("Dropped 1 row" in warning for warning in result.warnings)


def test_blank_required_fields_are_dropped():
    frame = pd.DataFrame(
        {
            "Position": ["Senator", ""],
            "Candidate_Name": ["Alice", "Bob"],
            "Total_Votes": [100, 90],
        }
    )
    result = data.normalize_dataframe(frame)
    assert len(result.dataframe) == 1
    assert result.dataframe.loc[0, "candidate_name"] == "Alice"
    assert any("blank" in warning for warning in result.warnings)


def test_empty_frame_is_an_error():
    result = data.normalize_dataframe(pd.DataFrame())
    assert not result.ok
    assert result.errors


def test_read_csv_missing_file(tmp_path):
    result = data.read_csv(tmp_path / "missing.csv")
    assert not result.ok
    assert "not found" in result.errors[0]


def test_read_csv_success(tmp_path):
    path = tmp_path / "votes.csv"
    path.write_text(
        "Position,Candidate_Name,Party,Total_Votes,Region\n"
        "Senator,Alice,Party A,100,Luzon\n"
    )
    result = data.read_csv(path)
    assert result.ok
    assert len(result.dataframe) == 1
    assert result.dataframe.loc[0, "region"] == "Luzon"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_data.py -q
```

Expected: FAIL with `ImportError` or `AttributeError`.

- [ ] **Step 3: Create the normalization portion of `src/ph_election_dashboard/data.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

CANONICAL_COLUMNS = [
    "position",
    "candidate_name",
    "party",
    "total_votes",
    "region",
    "region_focus",
    "province",
    "municipality_city",
    "barangay",
]
REQUIRED_COLUMNS = ["position", "candidate_name", "total_votes"]
TEXT_COLUMNS = [column for column in CANONICAL_COLUMNS if column != "total_votes"]
COLUMN_ALIASES = {
    "candidate": "candidate_name",
    "name": "candidate_name",
    "votes": "total_votes",
    "vote_count": "total_votes",
    "municipality": "municipality_city",
    "city": "municipality_city",
}


@dataclass
class LoadResult:
    dataframe: pd.DataFrame
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def empty_frame() -> pd.DataFrame:
    frame = pd.DataFrame(
        {column: pd.Series(dtype="object") for column in CANONICAL_COLUMNS}
    )
    frame["total_votes"] = pd.Series(dtype="int64")
    return frame


def _normalize_header(value: object) -> str:
    key = "_".join(str(value).strip().lower().replace("-", " ").split())
    return COLUMN_ALIASES.get(key, key)


def normalize_headers(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = {column: _normalize_header(column) for column in frame.columns}
    result = frame.rename(columns=renamed)
    return result.loc[:, ~result.columns.duplicated(keep="first")]


def normalize_dataframe(frame: pd.DataFrame) -> LoadResult:
    warnings: list[str] = []
    errors: list[str] = []

    if frame is None or frame.empty:
        return LoadResult(empty_frame(), warnings, ["The data file is empty."])

    frame = normalize_headers(frame.copy())
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        message = f"Missing required column(s): {', '.join(missing)}"
        return LoadResult(empty_frame(), warnings, [message])

    for column in CANONICAL_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame = frame[CANONICAL_COLUMNS].copy()

    for column in TEXT_COLUMNS:
        frame[column] = frame[column].astype("string").str.strip()
        frame.loc[frame[column] == "", column] = pd.NA

    votes = pd.to_numeric(frame["total_votes"], errors="coerce")
    invalid_votes = votes.isna() | (votes < 0)
    if invalid_votes.any():
        warnings.append(
            "Dropped "
            f"{int(invalid_votes.sum())} row(s) with missing, non-numeric, "
            "or negative votes."
        )
        frame = frame.loc[~invalid_votes].copy()
        votes = votes.loc[~invalid_votes]
    frame["total_votes"] = votes.astype("int64")

    blank_required = frame["position"].isna() | frame["candidate_name"].isna()
    if blank_required.any():
        warnings.append(
            "Dropped "
            f"{int(blank_required.sum())} row(s) with a blank position or candidate name."
        )
        frame = frame.loc[~blank_required].copy()

    if frame.empty:
        errors.append("No valid rows remain after validation.")

    return LoadResult(frame.reset_index(drop=True), warnings, errors)


def read_csv(path: Path) -> LoadResult:
    if not path.exists():
        return LoadResult(empty_frame(), [], [f"Data file not found: {path}"])
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return LoadResult(empty_frame(), [], [f"Could not read {path}: {exc}"])
    return normalize_dataframe(frame)
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/test_data.py -q
```

Expected: all data tests pass.

---

## Task 4: SQLite Storage Layer

**Files:**
- Create: `src/ph_election_dashboard/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing database tests in `tests/test_db.py`**

```python
import pandas as pd

from ph_election_dashboard import db


def sample_frame():
    return pd.DataFrame(
        {
            "position": ["Senator", "Senator"],
            "candidate_name": ["Alice", "Bob"],
            "party": ["Party A", "Party B"],
            "total_votes": [100, 90],
            "region": ["Luzon", "Visayas"],
            "region_focus": [None, None],
            "province": [None, None],
            "municipality_city": [None, None],
            "barangay": [None, None],
        }
    )


def test_initialize_sets_schema_version(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    db.initialize(connection)
    assert db.schema_version(connection) == db.SCHEMA_VERSION
    connection.close()


def test_replace_and_read_round_trip(tmp_path):
    source = tmp_path / "votes.csv"
    source.write_text("x")
    connection = db.connect(tmp_path / "test.db")
    db.initialize(connection)
    count = db.replace_election_type(
        connection,
        "national",
        sample_frame(),
        source,
        *db.file_signature(source),
    )
    result = db.read_election_data(connection, "national")
    assert count == 2
    assert result["candidate_name"].tolist() == ["Alice", "Bob"]
    assert result["total_votes"].tolist() == [100, 90]
    connection.close()


def test_needs_seed_detects_changes(tmp_path):
    source = tmp_path / "votes.csv"
    source.write_text("x")
    connection = db.connect(tmp_path / "test.db")
    db.initialize(connection)
    mtime_ns, size_bytes = db.file_signature(source)
    assert db.needs_seed(connection, "national", source, mtime_ns, size_bytes)
    db.replace_election_type(
        connection, "national", sample_frame(), source, mtime_ns, size_bytes
    )
    assert not db.needs_seed(connection, "national", source, mtime_ns, size_bytes)
    assert db.needs_seed(connection, "national", source, mtime_ns, size_bytes + 1)
    connection.close()


def test_election_types_are_isolated(tmp_path):
    source = tmp_path / "votes.csv"
    source.write_text("x")
    connection = db.connect(tmp_path / "test.db")
    db.initialize(connection)
    signature = db.file_signature(source)
    db.replace_election_type(
        connection, "national", sample_frame(), source, *signature
    )
    db.replace_election_type(
        connection, "local", sample_frame().head(1), source, *signature
    )
    assert len(db.read_election_data(connection, "national")) == 2
    assert len(db.read_election_data(connection, "local")) == 1
    connection.close()


def test_read_missing_type_returns_empty_frame(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    db.initialize(connection)
    result = db.read_election_data(connection, "barangay")
    assert result.empty
    assert "candidate_name" in result.columns
    connection.close()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_db.py -q
```

Expected: FAIL with `ImportError` or `AttributeError`.

- [ ] **Step 3: Create `src/ph_election_dashboard/db.py`**

```python
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCHEMA_VERSION = 1
RESULT_COLUMNS = [
    "position",
    "candidate_name",
    "party",
    "total_votes",
    "region",
    "region_focus",
    "province",
    "municipality_city",
    "barangay",
]


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS election_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            election_type TEXT NOT NULL,
            position TEXT NOT NULL,
            candidate_name TEXT NOT NULL,
            party TEXT,
            total_votes INTEGER NOT NULL,
            region TEXT,
            region_focus TEXT,
            province TEXT,
            municipality_city TEXT,
            barangay TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_results_type_position
            ON election_results (election_type, position);
        CREATE INDEX IF NOT EXISTS idx_results_type_region
            ON election_results (election_type, region);
        CREATE TABLE IF NOT EXISTS source_state (
            election_type TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            mtime_ns INTEGER NOT NULL,
            size_bytes INTEGER NOT NULL,
            row_count INTEGER NOT NULL,
            loaded_at TEXT NOT NULL
        );
        """
    )
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()


def file_signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def needs_seed(
    connection: sqlite3.Connection,
    election_type: str,
    source_path: Path,
    mtime_ns: int,
    size_bytes: int,
) -> bool:
    row = connection.execute(
        "SELECT source_path, mtime_ns, size_bytes "
        "FROM source_state WHERE election_type = ?",
        (election_type,),
    ).fetchone()
    if row is None:
        return True
    return (
        row["source_path"] != str(source_path)
        or row["mtime_ns"] != mtime_ns
        or row["size_bytes"] != size_bytes
    )


def _optional(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def replace_election_type(
    connection: sqlite3.Connection,
    election_type: str,
    frame: pd.DataFrame,
    source_path: Path,
    mtime_ns: int,
    size_bytes: int,
) -> int:
    rows = []
    for record in frame[RESULT_COLUMNS].to_dict("records"):
        rows.append(
            (
                election_type,
                str(record["position"]),
                str(record["candidate_name"]),
                _optional(record["party"]),
                int(record["total_votes"]),
                _optional(record["region"]),
                _optional(record["region_focus"]),
                _optional(record["province"]),
                _optional(record["municipality_city"]),
                _optional(record["barangay"]),
            )
        )

    with connection:
        connection.execute(
            "DELETE FROM election_results WHERE election_type = ?",
            (election_type,),
        )
        connection.executemany(
            """
            INSERT INTO election_results
                (election_type, position, candidate_name, party, total_votes,
                 region, region_focus, province, municipality_city, barangay)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO source_state
                (election_type, source_path, mtime_ns, size_bytes, row_count,
                 loaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                election_type,
                str(source_path),
                mtime_ns,
                size_bytes,
                len(rows),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return len(rows)


def read_election_data(
    connection: sqlite3.Connection, election_type: str
) -> pd.DataFrame:
    frame = pd.read_sql_query(
        """
        SELECT position, candidate_name, party, total_votes, region,
               region_focus, province, municipality_city, barangay
        FROM election_results
        WHERE election_type = ?
        ORDER BY position, total_votes DESC
        """,
        connection,
        params=(election_type,),
    )
    if frame.empty:
        frame = pd.DataFrame(
            {column: pd.Series(dtype="object") for column in RESULT_COLUMNS}
        )
        frame["total_votes"] = pd.Series(dtype="int64")
    return frame


def schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0])
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/test_db.py -q
```

Expected: all database tests pass.

## Task 5: Data Loader and Signatures

**Files:**
- Modify: `src/ph_election_dashboard/data.py`
- Modify: `tests/test_data.py`

- [ ] **Step 1: Append the failing loader tests to `tests/test_data.py`**

Add `import os` and `from ph_election_dashboard import config` to the existing
import block at the top of `tests/test_data.py`, then append:

```python
def make_paths(tmp_path):
    return config.Paths(
        project_root=tmp_path,
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        config_file=tmp_path / "config" / "config.json",
        providers_file=tmp_path / "config" / "providers.json",
        db_path=tmp_path / "data" / "election.db",
    )


def write_national(tmp_path, body):
    paths = make_paths(tmp_path)
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    path = paths.data_dir / "national_election_results.csv"
    path.write_text(
        "Position,Candidate_Name,Party,Total_Votes,Region\n" + body
    )
    return paths, path


def test_load_csv_mode(tmp_path):
    paths, _ = write_national(tmp_path, "Senator,Alice,Party A,100,Luzon\n")
    config_data = {
        "data_files": {"national": "national_election_results.csv"},
        "data_source": "csv",
    }
    result = data.load_election_data("national", config_data, paths)
    assert result.ok
    assert len(result.dataframe) == 1
    assert not paths.db_path.exists()


def test_load_sqlite_mode_seeds_and_reseeds(tmp_path):
    paths, path = write_national(tmp_path, "Senator,Alice,Party A,100,Luzon\n")
    config_data = {
        "data_files": {"national": "national_election_results.csv"},
        "data_source": "sqlite",
    }
    first = data.load_election_data("national", config_data, paths)
    assert first.ok
    assert len(first.dataframe) == 1
    assert paths.db_path.exists()

    path.write_text(
        "Position,Candidate_Name,Party,Total_Votes,Region\n"
        "Senator,Alice,Party A,100,Luzon\n"
        "Senator,Bob,Party B,90,Visayas\n"
    )
    os.utime(path, ns=(1_000_000_000, 1_000_000_000))
    second = data.load_election_data("national", config_data, paths)
    assert second.ok
    assert len(second.dataframe) == 2


def test_force_rebuild(tmp_path):
    paths, _ = write_national(tmp_path, "Senator,Alice,Party A,100,Luzon\n")
    config_data = {
        "data_files": {"national": "national_election_results.csv"},
        "data_source": "sqlite",
    }
    data.load_election_data("national", config_data, paths)
    rebuilt = data.load_election_data(
        "national", config_data, paths, force_rebuild=True
    )
    assert rebuilt.ok
    assert len(rebuilt.dataframe) == 1


def test_data_signature_changes_when_file_changes(tmp_path):
    paths, path = write_national(tmp_path, "Senator,Alice,Party A,100,Luzon\n")
    config_data = {"data_files": {"national": "national_election_results.csv"}}
    first = data.data_signature(config_data, paths)
    path.write_text(
        "Position,Candidate_Name,Party,Total_Votes,Region\n"
        "Senator,Alice,Party A,100,Luzon\n"
        "Senator,Bob,Party B,90,Visayas\n"
    )
    second = data.data_signature(config_data, paths)
    assert first != second


def test_rebuild_database_returns_messages(tmp_path):
    paths, _ = write_national(tmp_path, "Senator,Alice,Party A,100,Luzon\n")
    config_data = {
        "data_files": {"national": "national_election_results.csv"},
        "data_source": "sqlite",
    }
    messages = data.rebuild_database(config_data, paths)
    assert messages == ["national: 1 rows"]


def test_missing_configured_file_is_an_error(tmp_path):
    paths = make_paths(tmp_path)
    config_data = {"data_files": {"national": "missing.csv"}}
    result = data.load_election_data("national", config_data, paths)
    assert not result.ok
    assert "not found" in result.errors[0]


def test_unknown_election_type_is_an_error(tmp_path):
    paths = make_paths(tmp_path)
    result = data.load_election_data("national", {"data_files": {}}, paths)
    assert not result.ok
    assert "No data file configured" in result.errors[0]


def test_to_csv_bytes_contains_only_given_columns():
    frame = pd.DataFrame(
        {"candidate_name": ["Alice"], "total_votes": [100], "party": ["A"]}
    )
    payload = data.to_csv_bytes(frame, ["candidate_name", "total_votes"])
    text = payload.decode("utf-8")
    assert text.startswith("candidate_name,total_votes")
    assert "Alice" in text
    assert "party" not in text
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_data.py -q
```

Expected: FAIL because `load_election_data`, `data_signature`, and `rebuild_database` do not exist.

- [ ] **Step 3: Add loader imports and functions to `src/ph_election_dashboard/data.py`**

Add these imports at the top of the existing file:

```python
from ph_election_dashboard import db
from ph_election_dashboard.config import Paths, get_paths
```

Append these functions to the end of the file:

```python
def load_election_data(
    election_type: str,
    config: dict,
    paths: Paths | None = None,
    *,
    force_rebuild: bool = False,
) -> LoadResult:
    paths = paths or get_paths()
    file_name = config.get("data_files", {}).get(election_type)
    if not file_name:
        return LoadResult(
            empty_frame(),
            [],
            [f"No data file configured for election type '{election_type}'."],
        )

    csv_path = paths.data_dir / file_name
    source = str(config.get("data_source", "sqlite")).lower()
    if source == "csv":
        return read_csv(csv_path)

    normalized = read_csv(csv_path)
    if not normalized.ok:
        return normalized

    mtime_ns, size_bytes = db.file_signature(csv_path)
    connection = db.connect(paths.db_path)
    try:
        db.initialize(connection)
        if force_rebuild or db.needs_seed(
            connection, election_type, csv_path, mtime_ns, size_bytes
        ):
            db.replace_election_type(
                connection,
                election_type,
                normalized.dataframe,
                csv_path,
                mtime_ns,
                size_bytes,
            )
        frame = db.read_election_data(connection, election_type)
    finally:
        connection.close()
    return LoadResult(frame, normalized.warnings, [])


def rebuild_database(config: dict, paths: Paths | None = None) -> list[str]:
    paths = paths or get_paths()
    messages: list[str] = []
    for election_type, file_name in config.get("data_files", {}).items():
        result = load_election_data(
            election_type, config, paths, force_rebuild=True
        )
        if result.ok:
            messages.append(f"{election_type}: {len(result.dataframe)} rows")
        else:
            messages.append(f"{election_type}: {result.errors[0]}")
    return messages


def to_csv_bytes(frame: pd.DataFrame, columns: list[str]) -> bytes:
    return frame[columns].to_csv(index=False).encode("utf-8")


def data_signature(
    config: dict, paths: Paths | None = None
) -> tuple[tuple[str, int, int], ...]:
    paths = paths or get_paths()
    entries: list[tuple[str, int, int]] = []
    for election_type, file_name in config.get("data_files", {}).items():
        path = paths.data_dir / file_name
        if path.exists():
            stat = path.stat()
            entries.append((election_type, stat.st_mtime_ns, stat.st_size))
        else:
            entries.append((election_type, 0, 0))
    return tuple(entries)
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/test_data.py -q
```

Expected: all data and loader tests pass.

---

## Task 6: Filters

**Files:**
- Create: `src/ph_election_dashboard/filters.py`
- Create: `tests/test_filters.py`

- [ ] **Step 1: Write the failing filter tests in `tests/test_filters.py`**

```python
import pandas as pd

from ph_election_dashboard.filters import ALL, ElectionFilters, available_filter_columns


def sample_frame():
    return pd.DataFrame(
        {
            "position": ["Senator", "Senator", "Governor"],
            "candidate_name": ["Alice", "Bob", "Carla"],
            "total_votes": [100, 90, 80],
            "region": ["Luzon", "Visayas", "Luzon"],
            "province": ["Bulacan", "Cebu", None],
        }
    )


def test_available_filter_columns():
    assert available_filter_columns(sample_frame()) == ["position", "region", "province"]


def test_position_filter_changes_rows():
    filters = ElectionFilters(sample_frame())
    filters.set("position", "Senator")
    result = filters.apply()
    assert result["candidate_name"].tolist() == ["Alice", "Bob"]


def test_all_selector_does_not_filter():
    filters = ElectionFilters(sample_frame())
    filters.set("position", ALL)
    assert len(filters.apply()) == 3


def test_location_filters_combine():
    filters = ElectionFilters(sample_frame())
    filters.set("position", "Senator")
    filters.set("region", "Luzon")
    assert filters.apply()["candidate_name"].tolist() == ["Alice"]


def test_candidate_search_is_case_insensitive():
    filters = ElectionFilters(sample_frame())
    filters.set_search("ALI")
    assert filters.apply()["candidate_name"].tolist() == ["Alice"]


def test_reset_clears_filters_and_search():
    filters = ElectionFilters(sample_frame())
    filters.set("position", "Senator")
    filters.set_search("Alice")
    filters.reset()
    assert filters.selections == {}
    assert filters.search == ""
    assert len(filters.apply()) == 3


def test_options_are_sorted_and_include_all():
    filters = ElectionFilters(sample_frame())
    assert filters.options("region") == [ALL, "Luzon", "Visayas"]


def test_missing_column_is_ignored():
    frame = pd.DataFrame({"position": ["Senator"], "candidate_name": ["A"], "total_votes": [1]})
    filters = ElectionFilters(frame)
    assert filters.options("region") == [ALL]
    filters.set("region", "Luzon")
    assert "region" not in filters.selections
    assert len(filters.apply()) == 1
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_filters.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `src/ph_election_dashboard/filters.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

ALL = "All"
FILTER_COLUMNS = ["position", "region", "province", "municipality_city", "barangay"]


def available_filter_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in FILTER_COLUMNS if column in frame.columns]


@dataclass
class ElectionFilters:
    dataframe: pd.DataFrame
    selections: dict[str, str] = field(default_factory=dict)
    search: str = ""

    def options(self, column: str) -> list[str]:
        if column not in self.dataframe.columns:
            return [ALL]
        values = self.dataframe[column].dropna().astype(str).str.strip()
        values = values[values != ""]
        return [ALL, *sorted(values.unique().tolist())]

    def set(self, column: str, value: str) -> None:
        if column in self.dataframe.columns and value != ALL:
            self.selections[column] = value
        else:
            self.selections.pop(column, None)

    def set_search(self, value: str) -> None:
        self.search = value.strip()

    def reset(self) -> None:
        self.selections.clear()
        self.search = ""

    def apply(self) -> pd.DataFrame:
        result = self.dataframe
        for column, value in self.selections.items():
            if value != ALL and column in result.columns:
                result = result[result[column].astype("string") == value]
        if self.search and "candidate_name" in result.columns:
            needle = self.search.lower()
            mask = (
                result["candidate_name"]
                .astype("string")
                .str.lower()
                .str.contains(needle, na=False, regex=False)
            )
            result = result[mask]
        return result.reset_index(drop=True)
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/test_filters.py -q
```

Expected: all filter tests pass.

---

## Task 7: Geo Aliases and Map Data

**Files:**
- Create: `src/ph_election_dashboard/geo_data/__init__.py`
- Create: `src/ph_election_dashboard/geo_data/ph_regions.geojson`
- Create: `src/ph_election_dashboard/geo_data/ph_island_groups.geojson`
- Create: `src/ph_election_dashboard/geo.py`
- Create: `tests/test_geo.py`

- [ ] **Step 1: Create the geo_data package marker and download the GeoJSON files**

Create `src/ph_election_dashboard/geo_data/__init__.py`:

```python
"""Bundled GeoJSON boundary data."""
```

Run:

```bash
mkdir -p src/ph_election_dashboard/geo_data
curl -fsSL -o src/ph_election_dashboard/geo_data/ph_regions.geojson \
  https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/latest/geojson/country/lowres/country.0.001.json
curl -fsSL -o src/ph_election_dashboard/geo_data/ph_island_groups.geojson \
  https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/latest/geojson/islandgroups/lowres/islandgroups.0.001.json
```

Expected:

```bash
wc -c src/ph_election_dashboard/geo_data/ph_regions.geojson
# about 600875

wc -c src/ph_election_dashboard/geo_data/ph_island_groups.geojson
# about 492756
```

- [ ] **Step 2: Write the failing geo tests in `tests/test_geo.py`**

```python
import pandas as pd
import pytest

from ph_election_dashboard import geo


def test_load_region_geojson_sets_ids():
    geojson = geo.load_geojson(geo.REGION_FILE)
    assert len(geojson["features"]) == 18
    assert all("id" in feature for feature in geojson["features"])


def test_region_level_maps_aliases_and_reports_unmapped():
    frame = pd.DataFrame(
        {
            "region": ["NCR", "Region III", "Luzon"],
            "total_votes": [10, 20, 30],
        }
    )
    aggregated, unmapped = geo.aggregate_for_map(frame, geo.LEVEL_REGION)
    assert aggregated["geo_id"].tolist() == ["1300000000", "300000000"]
    assert aggregated["total_votes"].tolist() == [10, 20]
    assert unmapped == ["Luzon"]


def test_island_group_level_maps_luzon():
    frame = pd.DataFrame({"region": ["Luzon", "NCR"], "total_votes": [30, 10]})
    aggregated, unmapped = geo.aggregate_for_map(frame, geo.LEVEL_ISLAND)
    assert aggregated["geo_id"].tolist() == ["Luzon"]
    assert unmapped == ["NCR"]


def test_psgc_code_input_maps():
    frame = pd.DataFrame({"region": ["1300000000"], "total_votes": [5]})
    aggregated, _ = geo.aggregate_for_map(frame, geo.LEVEL_REGION)
    assert aggregated["geo_id"].tolist() == ["1300000000"]


def test_available_map_levels_order():
    frame = pd.DataFrame({"region": ["NCR", "Luzon"], "total_votes": [10, 20]})
    assert geo.available_map_levels(frame) == [
        geo.LEVEL_REGION,
        geo.LEVEL_ISLAND,
    ]


def test_region_focus_is_a_fallback_source():
    frame = pd.DataFrame({"region_focus": ["Visayas"], "total_votes": [50]})
    aggregated, _ = geo.aggregate_for_map(frame, geo.LEVEL_ISLAND)
    assert aggregated["geo_id"].tolist() == ["Visayas"]


def test_build_choropleth_returns_figure():
    frame = pd.DataFrame({"region": ["NCR"], "total_votes": [10]})
    figure, unmapped = geo.build_choropleth(frame, geo.LEVEL_REGION)
    assert figure is not None
    assert unmapped == []


def test_unknown_map_level_raises():
    with pytest.raises(ValueError):
        geo.aggregate_for_map(pd.DataFrame({"region": ["NCR"]}), "unknown")
```

- [ ] **Step 3: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_geo.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Create `src/ph_election_dashboard/geo.py`**

```python
from __future__ import annotations

import json
import re
from importlib import resources
from typing import Any

import pandas as pd
import plotly.express as px

REGION_FILE = "ph_regions.geojson"
ISLAND_FILE = "ph_island_groups.geojson"
LEVEL_REGION = "region"
LEVEL_ISLAND = "island_group"

REGION_ALIASES = {
    "ncr": "1300000000",
    "metro manila": "1300000000",
    "national capital region": "1300000000",
    "car": "1400000000",
    "cordillera": "1400000000",
    "barmm": "1900000000",
    "armm": "1900000000",
    "mimaropa": "1700000000",
    "nir": "1800000000",
    "negros island region": "1800000000",
    "calabarzon": "400000000",
    "bicol": "500000000",
    "bicol region": "500000000",
    "soccsksargen": "1200000000",
    "caraga": "1600000000",
    "zamboanga peninsula": "900000000",
    "davao region": "1100000000",
    "northern mindanao": "1000000000",
    "western visayas": "600000000",
    "central visayas": "700000000",
    "eastern visayas": "800000000",
    "central luzon": "300000000",
    "cagayan valley": "200000000",
    "ilocos region": "100000000",
    "region i": "100000000",
    "region ii": "200000000",
    "region iii": "300000000",
    "region iv a": "400000000",
    "region iv b": "1700000000",
    "region v": "500000000",
    "region vi": "600000000",
    "region vii": "700000000",
    "region viii": "800000000",
    "region ix": "900000000",
    "region x": "1000000000",
    "region xi": "1100000000",
    "region xii": "1200000000",
    "region xiii": "1600000000",
}
ISLAND_ALIASES = {
    "luzon": "Luzon",
    "visayas": "Visayas",
    "mindanao": "Mindanao",
}


def _normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def load_geojson(file_name: str) -> dict[str, Any]:
    path = resources.files("ph_election_dashboard.geo_data").joinpath(file_name)
    with path.open(encoding="utf-8") as handle:
        geojson = json.load(handle)
    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        if "adm1_psgc" in properties:
            feature["id"] = str(properties["adm1_psgc"])
        elif "island_group" in properties:
            feature["id"] = str(properties["island_group"])
    return geojson


def _region_lookup(geojson: dict[str, Any]) -> dict[str, str]:
    lookup = dict(REGION_ALIASES)
    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        code = str(properties.get("adm1_psgc", ""))
        name = str(properties.get("adm1_en", ""))
        if not code or not name:
            continue
        lookup[_normalize(name)] = code
        lookup[_normalize(code)] = code
        short = re.sub(r"\s*\(.*?\)\s*", " ", name)
        lookup[_normalize(short)] = code
    return lookup


def _island_lookup(geojson: dict[str, Any]) -> dict[str, str]:
    lookup = dict(ISLAND_ALIASES)
    for feature in geojson.get("features", []):
        name = str(feature.get("properties", {}).get("island_group", ""))
        if name:
            lookup[_normalize(name)] = name
    return lookup


def _source_column(frame: pd.DataFrame) -> str | None:
    for column in ("region", "region_focus"):
        if column in frame.columns and frame[column].notna().any():
            return column
    return None


def aggregate_for_map(
    frame: pd.DataFrame, level: str
) -> tuple[pd.DataFrame, list[str]]:
    column = _source_column(frame)
    if column is None or frame.empty:
        return pd.DataFrame(columns=["label", "geo_id", "total_votes"]), []

    if level == LEVEL_REGION:
        lookup = _region_lookup(load_geojson(REGION_FILE))
    elif level == LEVEL_ISLAND:
        lookup = _island_lookup(load_geojson(ISLAND_FILE))
    else:
        raise ValueError(f"Unknown map level: {level}")

    working = frame.copy()
    working["_label"] = working[column].astype("string").str.strip()
    working = working[
        working["_label"].notna() & (working["_label"] != "")
    ]
    grouped = working.groupby("_label", as_index=False)["total_votes"].sum()

    rows = []
    unmapped = []
    for record in grouped.to_dict("records"):
        label = str(record["_label"])
        geo_id = lookup.get(_normalize(label))
        if geo_id is None:
            unmapped.append(label)
        else:
            rows.append(
                {
                    "label": label,
                    "geo_id": geo_id,
                    "total_votes": int(record["total_votes"]),
                }
            )
    return (
        pd.DataFrame(rows, columns=["label", "geo_id", "total_votes"]),
        sorted(set(unmapped)),
    )


def available_map_levels(frame: pd.DataFrame) -> list[str]:
    levels = []
    for level in (LEVEL_REGION, LEVEL_ISLAND):
        aggregated, _ = aggregate_for_map(frame, level)
        if not aggregated.empty:
            levels.append(level)
    return levels


def build_choropleth(frame: pd.DataFrame, level: str):
    aggregated, unmapped = aggregate_for_map(frame, level)
    if aggregated.empty:
        return None, unmapped
    file_name = REGION_FILE if level == LEVEL_REGION else ISLAND_FILE
    geojson = load_geojson(file_name)
    title = "Votes by Region" if level == LEVEL_REGION else "Votes by Island Group"
    figure = px.choropleth(
        aggregated,
        geojson=geojson,
        locations="geo_id",
        featureidkey="id",
        color="total_votes",
        hover_name="label",
        color_continuous_scale="Blues",
        labels={"total_votes": "Total Votes"},
        title=title,
    )
    figure.update_geos(fitbounds="locations", visible=False)
    figure.update_layout(
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        coloraxis_colorbar_title="Votes",
    )
    return figure, unmapped
```

- [ ] **Step 5: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/test_geo.py -q
```

Expected: all geo tests pass.

---

## Task 8: Charts

**Files:**
- Create: `src/ph_election_dashboard/charts.py`
- Create: `tests/test_charts.py`

- [ ] **Step 1: Write the failing chart tests in `tests/test_charts.py`**

```python
import pandas as pd

from ph_election_dashboard import charts
from ph_election_dashboard.filters import ALL


def sample_frame():
    return pd.DataFrame(
        {
            "position": ["Senator", "Senator", "Governor"],
            "candidate_name": ["Alice", "Bob", "Carla"],
            "party": ["Party A", "Party B", "Party A"],
            "total_votes": [100, 90, 200],
            "region": ["Luzon", "Visayas", "Luzon"],
        }
    )


def test_resolve_position_with_all_picks_highest_total():
    subset, position = charts.resolve_position(sample_frame(), ALL)
    assert position == "Governor"
    assert subset["candidate_name"].tolist() == ["Carla"]


def test_resolve_position_respects_selection():
    subset, position = charts.resolve_position(sample_frame(), "Senator")
    assert position == "Senator"
    assert len(subset) == 2


def test_top_candidates_bar_returns_figure():
    figure, position = charts.top_candidates_bar(sample_frame(), "Senator")
    assert figure is not None
    assert position == "Senator"


def test_party_pie_requires_two_parties():
    one_party = pd.DataFrame(
        {
            "position": ["Senator"],
            "candidate_name": ["Alice"],
            "party": ["Party A"],
            "total_votes": [100],
        }
    )
    assert charts.party_pie(one_party, "Senator") is None


def test_party_pie_returns_figure_with_two_parties():
    assert charts.party_pie(sample_frame(), "Senator") is not None


def test_regional_bar_returns_figure():
    assert charts.regional_bar(sample_frame()) is not None


def test_regional_bar_without_region_returns_none():
    frame = pd.DataFrame(
        {
            "position": ["Senator"],
            "candidate_name": ["Alice"],
            "total_votes": [1],
        }
    )
    assert charts.regional_bar(frame) is None


def test_empty_frame_returns_none():
    empty = pd.DataFrame(columns=["position", "candidate_name", "total_votes"])
    figure, position = charts.top_candidates_bar(empty, ALL)
    assert figure is None
    assert position is None
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_charts.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `src/ph_election_dashboard/charts.py`**

```python
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ph_election_dashboard import geo
from ph_election_dashboard.filters import ALL


def resolve_position(
    frame: pd.DataFrame, selected: str | None
) -> tuple[pd.DataFrame, str | None]:
    if selected and selected != ALL:
        return frame[frame["position"] == selected], selected
    if frame.empty or "position" not in frame.columns:
        return frame, None
    totals = frame.groupby("position")["total_votes"].sum().sort_values(
        ascending=False
    )
    if totals.empty:
        return frame, None
    position = str(totals.index[0])
    return frame[frame["position"] == position], position


def top_candidates_bar(
    frame: pd.DataFrame, selected_position: str | None = ALL
) -> tuple[go.Figure | None, str | None]:
    subset, position = resolve_position(frame, selected_position)
    if subset.empty:
        return None, position
    subset = subset.sort_values("total_votes", ascending=False).head(15)
    color = (
        "party"
        if "party" in subset.columns and subset["party"].notna().any()
        else None
    )
    hover = ["candidate_name", "position", "total_votes"]
    if color:
        hover.append("party")
    figure = px.bar(
        subset,
        x="candidate_name",
        y="total_votes",
        color=color,
        hover_data=hover,
        title=f"Top Candidates for {position}" if position else "Top Candidates",
        labels={
            "candidate_name": "Candidate",
            "total_votes": "Total Votes",
            "party": "Party",
        },
    )
    figure.update_layout(
        xaxis_title="Candidate",
        yaxis_title="Total Votes",
        xaxis_tickangle=-35,
    )
    return figure, position


def party_pie(
    frame: pd.DataFrame, selected_position: str | None = ALL
) -> go.Figure | None:
    subset, position = resolve_position(frame, selected_position)
    if subset.empty or "party" not in subset.columns:
        return None
    party_votes = (
        subset.dropna(subset=["party"])
        .groupby("party", as_index=False)["total_votes"]
        .sum()
    )
    if party_votes.empty:
        return None
    total = party_votes["total_votes"].sum()
    party_votes = party_votes[party_votes["total_votes"] > total * 0.01]
    if len(party_votes) < 2:
        return None
    return px.pie(
        party_votes,
        names="party",
        values="total_votes",
        hole=0.3,
        title=(
            f"Party Vote Share for {position}"
            if position
            else "Party Vote Share"
        ),
    )


def regional_bar(frame: pd.DataFrame) -> go.Figure | None:
    if frame.empty or "region" not in frame.columns:
        return None
    summary = (
        frame.dropna(subset=["region"])
        .groupby("region", as_index=False)["total_votes"]
        .sum()
        .sort_values("total_votes", ascending=False)
    )
    if summary.empty:
        return None
    figure = px.bar(
        summary,
        x="region",
        y="total_votes",
        title="Total Votes per Region",
        labels={"region": "Region", "total_votes": "Total Votes"},
    )
    figure.update_layout(xaxis_tickangle=-35)
    return figure


def choropleth(frame: pd.DataFrame, level: str):
    return geo.build_choropleth(frame, level)
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/test_charts.py -q
```

Expected: all chart tests pass.

## Task 9: Flexible AI Providers

**Files:**
- Create: `src/ph_election_dashboard/ai.py`
- Create: `tests/test_ai.py`

- [ ] **Step 1: Write the failing AI tests in `tests/test_ai.py`**

```python
import json

import pandas as pd

from ph_election_dashboard import ai


def sample_frame():
    return pd.DataFrame(
        {
            "position": ["Senator"] * 6,
            "candidate_name": [f"Candidate {index}" for index in range(1, 7)],
            "party": ["Party A", "Party B", "Party A", "Party B", "Party A", "Party B"],
            "total_votes": [60, 50, 40, 30, 20, 10],
            "region": ["Luzon", "Visayas", "Luzon", "Visayas", "Luzon", "Visayas"],
        }
    )


def test_provider_key_lookup(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    provider = ai.BUILTIN_PROVIDERS["openai"]
    assert provider.api_key() == "secret"
    assert provider.configured() is True


def test_provider_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = ai.BUILTIN_PROVIDERS["openai"]
    assert provider.api_key() is None
    assert provider.configured() is False


def test_ollama_does_not_require_key():
    assert ai.BUILTIN_PROVIDERS["ollama"].configured() is True


def test_load_custom_providers(tmp_path):
    path = tmp_path / "providers.json"
    path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "name": "lmstudio",
                        "kind": "openai",
                        "base_url": "http://localhost:1234/v1",
                        "api_key_env": None,
                        "model": "local-model",
                    }
                ]
            }
        )
    )
    providers = ai.load_custom_providers(path)
    assert providers["lmstudio"].kind == "openai"
    assert providers["lmstudio"].configured() is True


def test_available_providers_merges_custom(tmp_path):
    path = tmp_path / "providers.json"
    path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "name": "myprovider",
                        "kind": "openai",
                        "base_url": "http://example.test/v1",
                        "api_key_env": "MY_KEY",
                        "model": "my-model",
                    }
                ]
            }
        )
    )
    providers = ai.available_providers(path)
    assert "openai" in providers
    assert "myprovider" in providers


def test_build_stats_aggregates():
    stats = ai.build_stats(sample_frame(), "national")
    assert stats["rows"] == 6
    assert stats["total_votes"] == 210
    assert stats["top_candidates"][0]["candidate"] == "Candidate 1"
    assert stats["party_shares"]


def test_build_prompt_uses_only_top_five():
    stats = ai.build_stats(sample_frame(), "national")
    prompt = ai.build_prompt(stats)
    assert "Candidate 1" in prompt
    assert "Candidate 6" not in prompt
    assert "Rows: 6" in prompt


def test_fallback_summary_mentions_top_candidate():
    stats = ai.build_stats(sample_frame(), "national")
    summary = ai.fallback_summary(stats)
    assert "Candidate 1" in summary
    assert "Total votes" in summary


def test_generate_summary_without_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = ai.generate_summary(
        sample_frame(), "national", ai.BUILTIN_PROVIDERS["openai"], "gpt-4o-mini"
    )
    assert result.used_fallback is True
    assert "Candidate 1" in result.text


def test_generate_summary_openai_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Model summary"}}]}

    def fake_post(url, headers, json, timeout):
        assert url == "https://api.openai.com/v1/chat/completions"
        assert headers["Authorization"] == "Bearer secret"
        assert json["model"] == "gpt-4o-mini"
        return FakeResponse()

    monkeypatch.setattr(ai.requests, "post", fake_post)
    result = ai.generate_summary(
        sample_frame(), "national", ai.BUILTIN_PROVIDERS["openai"], "gpt-4o-mini"
    )
    assert result.used_fallback is False
    assert result.text == "Model summary"


def test_generate_summary_error_is_redacted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret")

    class FakeResponse:
        status_code = 401

        def json(self):
            return {}

    monkeypatch.setattr(ai.requests, "post", lambda *args, **kwargs: FakeResponse())
    result = ai.generate_summary(
        sample_frame(), "national", ai.BUILTIN_PROVIDERS["openai"], "gpt-4o-mini"
    )
    assert result.used_fallback is True
    assert result.error == "HTTP 401"
    assert "super-secret" not in result.error


def test_redact_replaces_secret():
    assert ai.redact("key=super-secret", "super-secret") == "key=***"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_ai.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `src/ph_election_dashboard/ai.py`**

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import requests

from ph_election_dashboard import geo

ProviderKind = Literal["openai", "anthropic", "gemini"]


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Provider:
    name: str
    kind: ProviderKind
    base_url: str
    api_key_env: str | None
    default_model: str
    headers: dict[str, str] = field(default_factory=dict)
    key_required: bool = True

    def api_key(self, override: str | None = None) -> str | None:
        if override and override.strip():
            return override.strip()
        if self.api_key_env:
            value = os.getenv(self.api_key_env, "").strip()
            if value:
                return value
        return None

    def configured(self, override: str | None = None) -> bool:
        return not self.key_required or bool(self.api_key(override))


BUILTIN_PROVIDERS: dict[str, Provider] = {
    "gemini": Provider(
        "gemini",
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta",
        "GEMINI_API_KEY",
        "gemini-2.5-flash",
    ),
    "openai": Provider(
        "openai",
        "openai",
        "https://api.openai.com/v1",
        "OPENAI_API_KEY",
        "gpt-4o-mini",
    ),
    "openrouter": Provider(
        "openrouter",
        "openai",
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        "openai/gpt-4o-mini",
        headers={
            "HTTP-Referer": (
                "https://github.com/Onehand-Coding/PH-Election-Dashboard"
            ),
            "X-Title": "PH Election Dashboard",
        },
    ),
    "groq": Provider(
        "groq",
        "openai",
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        "llama-3.3-70b-versatile",
    ),
    "anthropic": Provider(
        "anthropic",
        "anthropic",
        "https://api.anthropic.com/v1",
        "ANTHROPIC_API_KEY",
        "claude-3-5-haiku-latest",
    ),
    "ollama": Provider(
        "ollama",
        "openai",
        "http://localhost:11434/v1",
        None,
        "llama3.1",
        key_required=False,
    ),
}


@dataclass
class SummaryResult:
    text: str
    used_fallback: bool
    error: str | None = None


def load_custom_providers(path: Path) -> dict[str, Provider]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = payload.get("providers", []) if isinstance(payload, dict) else []
    providers: dict[str, Provider] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            name = str(item["name"]).strip()
            kind = str(item["kind"]).strip().lower()
            base_url = str(item["base_url"]).strip()
            model = str(item["model"]).strip()
        except KeyError:
            continue
        if not name or kind not in ("openai", "anthropic", "gemini"):
            continue
        key_env = item.get("api_key_env") or None
        providers[name] = Provider(
            name=name,
            kind=kind,  # type: ignore[arg-type]
            base_url=base_url,
            api_key_env=str(key_env) if key_env else None,
            default_model=model,
            headers={
                str(key): str(value)
                for key, value in (item.get("headers") or {}).items()
            },
            key_required=bool(key_env),
        )
    return providers


def available_providers(custom_path: Path | None = None) -> dict[str, Provider]:
    providers = dict(BUILTIN_PROVIDERS)
    if custom_path is not None:
        providers.update(load_custom_providers(custom_path))
    return providers


def _location_filters_text(location_filters: dict[str, str] | None) -> str:
    if not location_filters:
        return ""
    parts = [
        f"{key}: {value}"
        for key, value in sorted(location_filters.items())
        if value
    ]
    return ", ".join(parts)


def build_stats(
    frame: pd.DataFrame,
    election_type: str,
    position_filter: str | None = None,
    location_filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    if frame.empty:
        return {
            "election_type": election_type,
            "position_filter": position_filter,
            "location_filters": location_filters or {},
            "rows": 0,
            "total_votes": 0,
            "positions": [],
            "top_candidates": [],
            "party_shares": [],
            "region_totals": [],
            "map_mapped": 0,
            "map_unmapped": 0,
        }

    levels = geo.available_map_levels(frame)
    if levels:
        mapped_frame, unmapped_labels = geo.aggregate_for_map(frame, levels[0])
        map_mapped = len(mapped_frame)
        map_unmapped = len(unmapped_labels)
    else:
        map_mapped = 0
        map_unmapped = 0

    top = frame.sort_values("total_votes", ascending=False).head(5)
    party_shares = []
    party_frame = frame.dropna(subset=["party"])
    if not party_frame.empty:
        totals = party_frame.groupby("party")["total_votes"].sum()
        total_votes = int(totals.sum())
        if total_votes:
            party_shares = [
                {
                    "party": str(party),
                    "votes": int(votes),
                    "share": round(int(votes) / total_votes * 100, 1),
                }
                for party, votes in totals.sort_values(
                    ascending=False
                ).items()
            ]

    region_totals = []
    if "region" in frame.columns:
        region_frame = frame.dropna(subset=["region"])
        if not region_frame.empty:
            region_totals = [
                {"region": str(region), "votes": int(votes)}
                for region, votes in region_frame.groupby("region")[
                    "total_votes"
                ]
                .sum()
                .sort_values(ascending=False)
                .items()
            ]

    return {
        "election_type": election_type,
        "position_filter": position_filter,
        "location_filters": location_filters or {},
        "rows": int(len(frame)),
        "total_votes": int(frame["total_votes"].sum()),
        "positions": sorted(
            frame["position"].dropna().astype(str).unique().tolist()
        ),
        "top_candidates": [
            {
                "candidate": str(record["candidate_name"]),
                "position": str(record["position"]),
                "party": (
                    None if pd.isna(record["party"]) else str(record["party"])
                ),
                "votes": int(record["total_votes"]),
            }
            for record in top.to_dict("records")
        ],
        "party_shares": party_shares,
        "region_totals": region_totals,
        "map_mapped": map_mapped,
        "map_unmapped": map_unmapped,
    }


def build_prompt(stats: dict[str, Any]) -> str:
    location = _location_filters_text(stats.get("location_filters"))
    lines = [
        "You are writing a short, neutral summary of Philippine election "
        "sample data.",
        "Use only the aggregate statistics below. Do not invent candidates, "
        "parties, or totals.",
        "Write 4 to 6 sentences in plain English. Mention the leading "
        "candidates, party shares, and any close race.",
        "",
        f"Election level: {stats.get('election_type', 'unknown')}",
        f"Position filter: {stats.get('position_filter') or 'All'}",
        f"Location filter: {location or 'None'}",
        f"Rows: {stats.get('rows', 0)}",
        f"Total votes: {stats.get('total_votes', 0):,}",
        "",
        "Top candidates:",
    ]
    for item in stats.get("top_candidates", []):
        lines.append(
            f"- {item['candidate']} ({item['position']}, "
            f"{item['party'] or 'no party'}): {item['votes']:,} votes"
        )
    if stats.get("party_shares"):
        lines.append("")
        lines.append("Party vote shares:")
        for item in stats["party_shares"]:
            lines.append(f"- {item['party']}: {item['share']}%")
    if stats.get("region_totals"):
        lines.append("")
        lines.append("Regional totals:")
        for item in stats["region_totals"][:10]:
            lines.append(f"- {item['region']}: {item['votes']:,} votes")
    return "\n".join(lines)


def fallback_summary(stats: dict[str, Any]) -> str:
    if stats.get("rows", 0) == 0:
        return "No data is available for the current selection."
    lines = [
        f"**{str(stats.get('election_type', 'election')).title()} summary**",
    ]
    context = []
    if (
        stats.get("position_filter")
        and stats["position_filter"] != "All"
    ):
        context.append(f"position {stats['position_filter']}")
    location = _location_filters_text(stats.get("location_filters"))
    if location:
        context.append(location)
    if context:
        lines.append("- Context: " + "; ".join(context))
    lines.extend(
        [
            f"- Rows: {stats['rows']:,}",
            f"- Total votes: {stats['total_votes']:,}",
        ]
    )
    if stats.get("top_candidates"):
        lines.append("- Top candidates:")
        for item in stats["top_candidates"][:3]:
            party = f" ({item['party']})" if item.get("party") else ""
            lines.append(
                f"  - {item['candidate']}{party}: {item['votes']:,} votes"
            )
    if stats.get("party_shares"):
        lines.append("- Party vote share:")
        for item in stats["party_shares"][:4]:
            lines.append(f"  - {item['party']}: {item['share']}%")
    top = stats.get("top_candidates", [])
    if len(top) >= 2 and stats["total_votes"]:
        margin = top[0]["votes"] - top[1]["votes"]
        if margin / stats["total_votes"] < 0.05:
            lines.append(
                "- Close race: the top two are separated by "
                f"{margin:,} votes."
            )
    lines.append(
        f"- Map coverage: {stats.get('map_mapped', 0)} mapped label(s), "
        f"{stats.get('map_unmapped', 0)} unmapped label(s)."
    )
    return "\n".join(lines)


def redact(text: str, secret: str | None) -> str:
    if not secret:
        return text
    return text.replace(secret, "***")


def _post(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    try:
        response = requests.post(
            url, headers=headers, json=payload, timeout=timeout
        )
    except requests.RequestException as exc:
        raise ProviderError(type(exc).__name__) from exc
    if response.status_code >= 400:
        raise ProviderError(f"HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("Invalid JSON response") from exc


def _generate(
    provider: Provider,
    model: str,
    prompt: str,
    api_key: str | None,
    timeout: int,
) -> str:
    base = provider.base_url.rstrip("/")
    headers = {"Content-Type": "application/json", **provider.headers}

    if provider.kind == "openai":
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You summarize election data accurately and neutrally."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        }
        data = _post(
            f"{base}/chat/completions",
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Malformed OpenAI-compatible response") from exc

    if provider.kind == "anthropic":
        if api_key:
            headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        payload = {
            "model": model,
            "max_tokens": 700,
            "system": "You summarize election data accurately and neutrally.",
            "messages": [{"role": "user", "content": prompt}],
        }
        data = _post(
            f"{base}/messages",
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        try:
            return str(data["content"][0]["text"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Malformed Anthropic response") from exc

    if provider.kind == "gemini":
        if not api_key:
            raise ProviderError("Missing API key")
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 700,
            },
        }
        data = _post(
            f"{base}/models/{model}:generateContent?key={api_key}",
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        try:
            return str(
                data["candidates"][0]["content"]["parts"][0]["text"]
            ).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Malformed Gemini response") from exc

    raise ProviderError(f"Unsupported provider kind: {provider.kind}")


def generate_summary(
    frame: pd.DataFrame,
    election_type: str,
    provider: Provider,
    model: str,
    position_filter: str | None = None,
    location_filters: dict[str, str] | None = None,
    api_key_override: str | None = None,
    timeout: int = 30,
) -> SummaryResult:
    stats = build_stats(
        frame, election_type, position_filter, location_filters
    )
    fallback = fallback_summary(stats)
    api_key = provider.api_key(api_key_override)
    if not provider.configured(api_key_override):
        return SummaryResult(fallback, used_fallback=True)
    try:
        text = _generate(
            provider, model, build_prompt(stats), api_key, timeout
        )
    except ProviderError as exc:
        return SummaryResult(
            fallback,
            used_fallback=True,
            error=redact(str(exc), api_key),
        )
    if not text:
        return SummaryResult(
            fallback, used_fallback=True, error="Empty response"
        )
    return SummaryResult(text, used_fallback=False)
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/test_ai.py -q
```

Expected: all AI tests pass.

---

## Task 10: Streamlit App, Auto Refresh, and Smoke Test

**Files:**
- Replace: `src/ph_election_dashboard/app.py`
- Create: `tests/test_app_smoke.py`

- [ ] **Step 1: Write the failing smoke test in `tests/test_app_smoke.py`**

```python
import json
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Position,Candidate_Name,Party,Total_Votes,Region\n" + body)


def test_app_runs_and_filters(tmp_path, monkeypatch):
    st.cache_data.clear()
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    log_dir = tmp_path / "logs"
    write_csv(
        data_dir / "national_election_results.csv",
        "Senator,Alice,Party A,100,Luzon\n"
        "Governor,Bob,Party B,90,Visayas\n",
    )
    write_csv(
        data_dir / "local_election_results.csv",
        "Mayor,Carla,Party A,50,Luzon\n",
    )
    write_csv(
        data_dir / "barangay_election_results.csv",
        "Kagawad,Dino,Party B,10,Luzon\n",
    )
    config = {
        "election_year": 2025,
        "current_election_type": "national",
        "data_files": {
            "national": "national_election_results.csv",
            "local": "local_election_results.csv",
            "barangay": "barangay_election_results.csv",
        },
        "data_source": "csv",
        "auto_refresh": False,
        "cache_ttl": 300,
        "log_level": "ERROR",
    }
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    config_path.write_text(json.dumps(config))

    monkeypatch.setenv("PH_ELECTION_DATA_DIR", str(data_dir))
    monkeypatch.setenv("PH_ELECTION_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("PH_ELECTION_DB_PATH", str(data_dir / "election.db"))
    monkeypatch.setenv("PH_ELECTION_LOG_DIR", str(log_dir))

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    app.run()
    assert not app.exception
    assert len(app.dataframe) == 1
    assert len(app.dataframe[0].value) == 2

    position = next(box for box in app.selectbox if box.label == "Position")
    position.set_value("Senator").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/test_app_smoke.py -q
```

Expected: FAIL because the old `app.py` imports the removed top-level `config` module or the new UI does not exist.

- [ ] **Step 3: Replace `src/ph_election_dashboard/app.py`**

```python
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from ph_election_dashboard import ai, charts, data, geo
from ph_election_dashboard.config import (
    Paths,
    get_paths,
    load_config,
    setup_logger,
)
from ph_election_dashboard.filters import (
    ALL,
    ElectionFilters,
    available_filter_columns,
)

load_dotenv()

MAP_ATTRIBUTION = (
    "Boundaries: Philippine Statistics Authority (PSA) and NAMRIA through "
    "OCHA COD-AB, CC BY-IGO. GeoJSON prepared by "
    "faeldon/philippines-json-maps."
)


@st.cache_data(show_spinner=False)
def _cached_config(config_file: str, mtime_ns: int) -> dict:
    return load_config(Path(config_file))


@st.cache_data(show_spinner=False)
def _cached_data(
    election_type: str,
    data_source: str,
    signature: tuple,
    data_dir: str,
    config_file: str,
    db_path: str,
) -> data.LoadResult:
    paths = Paths(
        project_root=Path(data_dir).parent,
        config_dir=Path(config_file).parent,
        data_dir=Path(data_dir),
        log_dir=Path(data_dir).parent / "logs",
        config_file=Path(config_file),
        providers_file=Path(config_file).parent / "providers.json",
        db_path=Path(db_path),
    )
    config = load_config(Path(config_file))
    config["data_source"] = data_source
    return data.load_election_data(election_type, config, paths)


def _render_ai(
    frame,
    election_type: str,
    selected_position: str,
    filters: ElectionFilters,
    paths: Paths,
) -> None:
    st.sidebar.header("AI summary")
    providers = ai.available_providers(paths.providers_file)
    provider_names = [*providers.keys(), "custom"]
    provider_name = st.sidebar.selectbox(
        "Provider", provider_names, key="ai_provider"
    )

    if provider_name == "custom":
        kind = st.sidebar.selectbox(
            "API type", ["openai", "anthropic", "gemini"], key="custom_kind"
        )
        base_url = st.sidebar.text_input(
            "Base URL",
            value="http://localhost:1234/v1",
            key="custom_base_url",
        )
        model = st.sidebar.text_input(
            "Model", value="local-model", key="custom_model"
        )
        key_override = st.sidebar.text_input(
            "API key (session only)",
            type="password",
            key="custom_key",
        )
        provider = ai.Provider(
            "custom", kind, base_url, None, model, key_required=True
        )
    else:
        provider = providers[provider_name]
        model_env = f"{provider_name.upper().replace('-', '_')}_MODEL"
        model = st.sidebar.text_input(
            "Model",
            value=os.getenv(model_env, provider.default_model),
            key=f"model_{provider_name}",
        )
        key_override = st.sidebar.text_input(
            "API key override (session only)",
            type="password",
            key=f"key_{provider_name}",
        )

    if not st.sidebar.checkbox("Show AI summary", key="show_ai_summary"):
        return

    location_filters = {
        key: value
        for key, value in filters.selections.items()
        if key in ("region", "province", "municipality_city", "barangay")
    }
    total_votes = int(frame["total_votes"].sum()) if not frame.empty else 0
    cache_key = (
        provider_name,
        model,
        election_type,
        selected_position,
        tuple(sorted(location_filters.items())),
        len(frame),
        total_votes,
    )
    cached = st.session_state.get("ai_summary")
    if cached is None or cached["key"] != cache_key:
        with st.spinner("Generating summary..."):
            result = ai.generate_summary(
                frame,
                election_type,
                provider,
                model,
                selected_position,
                location_filters,
                key_override,
            )
        st.session_state["ai_summary"] = {"key": cache_key, "result": result}
        cached = st.session_state["ai_summary"]

    result = cached["result"]
    st.subheader("AI summary")
    st.markdown(result.text)
    if result.used_fallback:
        st.caption(
            "Showing the deterministic summary. Configure an API key for a "
            "model-generated summary."
        )
    if result.error:
        st.caption(f"AI request failed: {result.error}")


def main() -> None:
    st.set_page_config(
        page_title="Philippine Election Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    paths = get_paths()
    paths.ensure_dirs()
    config_mtime = (
        paths.config_file.stat().st_mtime_ns
        if paths.config_file.exists()
        else 0
    )
    config = _cached_config(str(paths.config_file), config_mtime)
    logger = setup_logger(str(config.get("log_level", "INFO")), paths.log_dir)
    logger.info("Starting Philippine Election Dashboard")

    st.sidebar.title("PH Election Dashboard")
    message = st.session_state.pop("_db_message", None)
    if message:
        st.sidebar.success(message)

    data_files = config.get("data_files", {})
    if not data_files:
        st.error("No data files are configured in config.json.")
        st.stop()

    election_types = list(data_files.keys())
    default_index = (
        election_types.index(config["current_election_type"])
        if config.get("current_election_type") in election_types
        else 0
    )
    election_type = st.sidebar.radio(
        "Election level",
        options=election_types,
        index=default_index,
        key="election_type",
    )
    data_source = st.sidebar.selectbox(
        "Data source",
        options=["sqlite", "csv"],
        index=0 if config.get("data_source", "sqlite") == "sqlite" else 1,
        key="data_source",
    )
    auto_refresh = st.sidebar.checkbox(
        "Auto refresh on file changes",
        value=bool(config.get("auto_refresh", True)),
        key="auto_refresh",
    )

    signature = data.data_signature(config, paths)
    result = _cached_data(
        election_type,
        data_source,
        signature,
        str(paths.data_dir),
        str(paths.config_file),
        str(paths.db_path),
    )
    if result.errors:
        for error in result.errors:
            st.error(error)
        st.stop()

    frame = result.dataframe
    if result.warnings:
        with st.expander("Data warnings", expanded=False):
            for warning in result.warnings:
                st.warning(warning)

    st.title(
        f"{config.get('election_year', '')} Philippine "
        f"{election_type.replace('_', ' ').title()} Election Dashboard"
    )
    st.caption("Sample data only. This is not an official COMELEC result set.")

    filter_columns = available_filter_columns(frame)
    if st.session_state.pop("_reset_filters", False):
        for column in filter_columns:
            st.session_state[f"filter_{column}"] = ALL
        st.session_state["candidate_search"] = ""

    filters = ElectionFilters(frame)
    st.sidebar.header("Filters")
    for column in filter_columns:
        options = filters.options(column)
        key = f"filter_{column}"
        if st.session_state.get(key) not in options:
            st.session_state[key] = ALL
        selected = st.sidebar.selectbox(
            column.replace("_", " ").title(), options, key=key
        )
        filters.set(column, selected)
    filters.set_search(
        st.sidebar.text_input("Search candidate", key="candidate_search")
    )
    if st.sidebar.button("Reset filters", key="reset_filters"):
        st.session_state["_reset_filters"] = True
        st.rerun()

    filtered = filters.apply()
    selected_position = filters.selections.get("position", ALL)

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", f"{len(filtered):,}")
    col2.metric(
        "Total votes",
        f"{int(filtered['total_votes'].sum()) if not filtered.empty else 0:,}",
    )
    col3.metric(
        "Candidates",
        f"{filtered['candidate_name'].nunique() if not filtered.empty else 0:,}",
    )

    display_columns = [
        column
        for column in [
            "candidate_name",
            "position",
            "party",
            "total_votes",
            "region",
            "province",
            "municipality_city",
            "barangay",
        ]
        if column in filtered.columns
    ]
    st.subheader("Filtered results")
    st.dataframe(
        filtered[display_columns].sort_values(
            "total_votes", ascending=False
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download filtered CSV",
        data=data.to_csv_bytes(filtered, display_columns),
        file_name=f"{election_type}_filtered.csv",
        mime="text/csv",
        key="download_csv",
    )

    st.header("Visualizations")
    bar, position = charts.top_candidates_bar(filtered, selected_position)
    if bar is None:
        st.info("No chart data for the current selection.")
    else:
        if selected_position == ALL and position:
            st.caption(
                "Showing the position with the most votes: "
                f"{position}. Choose a position in the sidebar to change it."
            )
        st.plotly_chart(bar, use_container_width=True)

    pie = charts.party_pie(filtered, selected_position)
    if pie is not None:
        st.plotly_chart(pie, use_container_width=True)

    if election_type in ("local", "barangay"):
        regional = charts.regional_bar(filtered)
        if regional is not None:
            st.plotly_chart(regional, use_container_width=True)

    levels = geo.available_map_levels(filtered)
    if levels:
        st.subheader("Geographic map")
        level = st.radio(
            "Map grouping",
            options=levels,
            horizontal=True,
            key="map_level",
        )
        figure, unmapped = geo.build_choropleth(filtered, level)
        if figure is not None:
            st.plotly_chart(figure, use_container_width=True)
        if unmapped:
            st.caption(f"Unmapped labels: {', '.join(unmapped)}")
        st.caption(MAP_ATTRIBUTION)
    else:
        st.caption(
            "No region or island-group labels matched the bundled map data."
        )

    _render_ai(filtered, election_type, selected_position, filters, paths)

    st.sidebar.markdown("---")
    if st.sidebar.button("Refresh data", key="refresh_data"):
        st.cache_data.clear()
        st.rerun()
    if st.sidebar.button("Rebuild database", key="rebuild_db"):
        messages = data.rebuild_database(config, paths)
        st.session_state["_db_message"] = "Rebuilt: " + "; ".join(messages)
        st.cache_data.clear()
        st.rerun()
    st.sidebar.caption(
        f"Data source: {data_source}. SQLite reads are seeded from the "
        "configured CSV files."
    )

    if auto_refresh:
        @st.fragment(run_every="3s")
        def _watch_data(current_signature: tuple) -> None:
            if data.data_signature(config, paths) != current_signature:
                st.cache_data.clear()
                st.rerun()

        _watch_data(signature)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the smoke test and verify it passes**

Run:

```bash
uv run pytest tests/test_app_smoke.py -q
```

Expected: PASS.

- [ ] **Step 5: Run the whole suite**

Run:

```bash
uv run pytest -q
```

Expected: all tests pass.

---

## Task 11: Ruff, Lock File, and CI

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `uv.lock` (generated)

- [ ] **Step 1: Format and lint locally**

Run:

```bash
uv run ruff check . --fix
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
```

Expected: no remaining lint errors and no formatting changes needed on the second check.

- [ ] **Step 2: Refresh the lock file**

Run:

```bash
uv lock
```

Expected: `uv.lock` updates to remove `google-generativeai` and its now-unused transitive packages, and to add `requests` as a direct dependency.

- [ ] **Step 3: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Set up uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check .

      - name: Format check
        run: uv run ruff format --check .

      - name: Test
        run: uv run pytest
```

- [ ] **Step 4: Verify the CI commands locally**

Run:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Expected: all commands exit 0.

---

## Task 12: Documentation and Project Memory

**Files:**
- Replace: `README.md`
- Create: `.env.example`
- Create: `config/providers.example.json`
- Replace: `config/config.json`
- Replace: `data/README_DATA.md`
- Create: `docs/geo-data.md`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `CONTEXT.md`

- [ ] **Step 1: Replace `README.md`**

```markdown
# PH Election Dashboard

A local Streamlit dashboard for exploring Philippine election sample data. It
provides working filters, interactive charts, regional and island-group maps,
CSV export, data-change auto refresh, a SQLite read cache, and an optional AI
summary that supports multiple providers.

> This project ships fictional sample data. It is not an official COMELEC
> result set.

## Features

- Filter by position, region, province, municipality or city, and barangay.
- Search candidates by name.
- View bar charts, party vote shares, regional totals, and a choropleth map.
- Download the filtered table as CSV.
- Reload automatically when a source CSV changes.
- Read from SQLite by default, with CSV as a fallback source.
- Generate an AI summary with Gemini, OpenAI, OpenRouter, Groq, Anthropic,
  Ollama, or a custom provider.
- Fall back to a deterministic summary when no API key is configured.

## Quick Start

Requirements: Python 3.10+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/Onehand-Coding/PH-Election-Dashboard.git
cd PH-Election-Dashboard
uv sync --extra dev
uv run streamlit run app.py
```

The app opens at <http://localhost:8501>.

You can also launch it through the installed console script:

```bash
uv run ph-election-dashboard
```

## Configuration

`config/config.json` controls the app:

```json
{
  "election_year": 2025,
  "current_election_type": "national",
  "data_files": {
    "national": "national_election_results.csv",
    "local": "local_election_results.csv",
    "barangay": "barangay_election_results.csv"
  },
  "data_source": "sqlite",
  "auto_refresh": true,
  "cache_ttl": 300,
  "log_level": "INFO"
}
```

Set `data_source` to `csv` to bypass SQLite. The SQLite file is created at
`data/election.db` and is rebuilt automatically when a CSV changes. The
"Rebuild database" button forces a full reseed.

### Path overrides

These environment variables are useful for tests and alternate deployments:

- `PH_ELECTION_PROJECT_ROOT`
- `PH_ELECTION_CONFIG_DIR`
- `PH_ELECTION_DATA_DIR`
- `PH_ELECTION_LOG_DIR`
- `PH_ELECTION_CONFIG_FILE`
- `PH_ELECTION_PROVIDERS_FILE`
- `PH_ELECTION_DB_PATH`

## AI Providers

Copy `.env.example` to `.env` and fill in one or more keys:

```bash
cp .env.example .env
```

| Provider | Environment variable | Default model |
| --- | --- | --- |
| Gemini | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| OpenRouter | `OPENROUTER_API_KEY` | `openai/gpt-4o-mini` |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-5-haiku-latest` |
| Ollama | none | `llama3.1` |

Select the provider and model in the sidebar. A session-only key field is
available when you do not want to write the key to `.env`. Keys are never
logged or persisted by the app.

### Custom providers

Copy `config/providers.example.json` to `config/providers.json` and add an
entry. Custom entries reference keys by environment variable name, never by
value:

```json
{
  "providers": [
    {
      "name": "lmstudio",
      "kind": "openai",
      "base_url": "http://localhost:1234/v1",
      "api_key_env": null,
      "model": "local-model"
    }
  ]
}
```

Supported `kind` values: `openai` (any OpenAI-compatible endpoint), `anthropic`,
and `gemini`. The custom form in the sidebar accepts a session-only key.

## Data Schema

CSV headers are normalized to lowercase snake case. These aliases are accepted:

- `Candidate`, `Name` -> `candidate_name`
- `Votes`, `Vote_Count` -> `total_votes`
- `Municipality`, `City` -> `municipality_city`

Required columns: `position`, `candidate_name`, `total_votes`.

Optional columns: `party`, `region`, `region_focus`, `province`,
`municipality_city`, `barangay`.

Rows with non-numeric or negative votes, or blank required text, are dropped
with a warning. See `data/README_DATA.md` for details.

## Map Data

The choropleth uses bundled GeoJSON for the 18 regions and 3 island groups. It
matches labels such as `NCR`, `Metro Manila`, `Region III`, `Region VII`,
`Luzon`, `Visayas`, and `Mindanao`. Unmatched labels are listed below the map.

Boundaries come from the Philippine Statistics Authority (PSA) and the National
Mapping and Resource Information Authority (NAMRIA), distributed through OCHA's
Philippines administrative boundaries (COD-AB) under CC BY-IGO. The GeoJSON was
prepared by `faeldon/philippines-json-maps`. See `docs/geo-data.md` and
`THIRD_PARTY_NOTICES.md`.

## Architecture

```
app.py                              Streamlit entry point
src/ph_election_dashboard/
  app.py                            UI composition
  config.py                         paths, defaults, logging
  data.py                           CSV loading, normalization, validation
  db.py                             SQLite schema and seeding
  filters.py                        filter state and application
  charts.py                         Plotly chart builders
  geo.py                            GeoJSON loading and label aliases
  ai.py                             provider registry and summaries
```

The app loads CSV files, normalizes and validates them, seeds a SQLite cache,
and reads the selected election level from SQLite. Filters and charts operate
on the resulting DataFrame. The AI layer sends only aggregate statistics to the
configured provider.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

CI runs the same commands on push and pull request.

## Troubleshooting

- **No data loaded:** check `data_files` in `config/config.json` and confirm the
  CSV exists under `data/`.
- **Map is empty:** confirm the `region` values match a region or island-group
  name. Unmapped labels are shown below the map.
- **AI summary is deterministic:** no key is configured, or the request failed.
  Check the caption below the summary.
- **Stale data:** leave auto refresh enabled, or press "Rebuild database".

## License

MIT. See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
```

- [ ] **Step 2: Create `.env.example`**

```bash
# Gemini
GEMINI_API_KEY=

# OpenAI
OPENAI_API_KEY=

# OpenRouter
OPENROUTER_API_KEY=

# Groq
GROQ_API_KEY=

# Anthropic
ANTHROPIC_API_KEY=

# Optional model overrides
GEMINI_MODEL=gemini-2.5-flash
OPENAI_MODEL=gpt-4o-mini
OPENROUTER_MODEL=openai/gpt-4o-mini
GROQ_MODEL=llama-3.3-70b-versatile
ANTHROPIC_MODEL=claude-3-5-haiku-latest
OLLAMA_MODEL=llama3.1

# Optional path overrides
# PH_ELECTION_DATA_DIR=./data
# PH_ELECTION_DB_PATH=./data/election.db
# PH_ELECTION_CONFIG_FILE=./config/config.json
# PH_ELECTION_LOG_DIR=./logs
```

- [ ] **Step 3: Create `config/providers.example.json`**

```json
{
  "providers": [
    {
      "name": "lmstudio",
      "kind": "openai",
      "base_url": "http://localhost:1234/v1",
      "api_key_env": null,
      "model": "local-model"
    },
    {
      "name": "my-openai-compatible",
      "kind": "openai",
      "base_url": "https://api.example.com/v1",
      "api_key_env": "MY_PROVIDER_API_KEY",
      "model": "my-model"
    }
  ]
}
```

- [ ] **Step 4: Replace `config/config.json`**

```json
{
  "election_year": 2025,
  "current_election_type": "national",
  "data_files": {
    "national": "national_election_results.csv",
    "local": "local_election_results.csv",
    "barangay": "barangay_election_results.csv"
  },
  "data_source": "sqlite",
  "auto_refresh": true,
  "cache_ttl": 300,
  "log_level": "INFO"
}
```

- [ ] **Step 5: Replace `data/README_DATA.md`**

```markdown
# Election Data Format

The dashboard reads CSV files listed in `config/config.json`. Headers are
normalized to lowercase snake case, and spaces or hyphens become underscores.

## Columns

| Column | Required | Notes |
| --- | --- | --- |
| `position` | yes | For example Senator, Governor, Barangay Captain |
| `candidate_name` | yes | Candidate or party-list name |
| `total_votes` | yes | Non-negative integer |
| `party` | no | Blank or `Independent` allowed |
| `region` | no | Region or island-group label |
| `region_focus` | no | Fallback label for national data |
| `province` | no | |
| `municipality_city` | no | |
| `barangay` | no | |

Accepted aliases:

- `Candidate`, `Name` -> `candidate_name`
- `Votes`, `Vote_Count` -> `total_votes`
- `Municipality`, `City` -> `municipality_city`

## Validation

- Missing required columns stop the page with an error.
- Rows with missing, non-numeric, or negative votes are dropped with a warning.
- Rows with a blank position or candidate name are dropped with a warning.
- Duplicate rows are kept.

## Region Labels

The map accepts region names such as `Region III (Central Luzon)`, short forms
such as `Region III`, aliases such as `NCR` and `Metro Manila`, island groups
`Luzon`, `Visayas`, and `Mindanao`, and PSGC region codes such as
`1300000000`. Unmatched labels are reported below the map.
```

- [ ] **Step 6: Create `docs/geo-data.md`**

```markdown
# Boundary Data

The dashboard bundles two GeoJSON files in
`src/ph_election_dashboard/geo_data/`:

- `ph_regions.geojson`: 18 regions, from
  `https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/latest/geojson/country/lowres/country.0.001.json`
- `ph_island_groups.geojson`: 3 island groups, from
  `https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/latest/geojson/islandgroups/lowres/islandgroups.0.001.json`

Retrieved: 2026-11-01.

The GeoJSON was prepared by `faeldon/philippines-json-maps` (MIT). The
underlying boundaries come from the Philippine Statistics Authority (PSA) and
the National Mapping and Resource Information Authority (NAMRIA), distributed
through OCHA's Philippines administrative boundaries (COD-AB), licensed
CC BY-IGO.

If you republish the map, credit PSA and NAMRIA through OCHA's COD-AB. The app
displays this attribution below every map.
```

- [ ] **Step 7: Create `THIRD_PARTY_NOTICES.md`**

```markdown
# Third-Party Notices

## Philippine administrative boundaries

The bundled GeoJSON files in `src/ph_election_dashboard/geo_data/` contain
administrative boundaries from the Philippine Statistics Authority (PSA) and
the National Mapping and Resource Information Authority (NAMRIA), distributed
through OCHA's Philippines administrative boundaries (COD-AB).

License: CC BY-IGO,
<http://creativecommons.org/licenses/by/3.0/igo/legalcode>.

GeoJSON preparation: `faeldon/philippines-json-maps` (MIT),
<https://github.com/faeldon/philippines-json-maps>.

The dashboard displays this attribution below every map.
```

- [ ] **Step 8: Create `CONTEXT.md`**

```markdown
# Project Context

## Purpose

A local Streamlit dashboard for exploring fictional Philippine election sample
data. It is a demo and portfolio project, not an official results system.

## Architecture

- `app.py` is a Streamlit shim that adds `src/` to `sys.path`.
- `src/ph_election_dashboard/app.py` composes the UI.
- `config.py` owns paths, defaults, and logging.
- `data.py` owns CSV loading, normalization, and validation.
- `db.py` owns the SQLite schema and seeding.
- `filters.py` owns filter state and application.
- `charts.py` owns Plotly chart builders.
- `geo.py` owns GeoJSON loading and label aliases.
- `ai.py` owns provider definitions, prompts, HTTP calls, and fallback.

## Data Flow

CSV -> normalization and validation -> SQLite seed/read -> filters -> charts,
tables, maps, and AI summary. CSV remains the source of truth. SQLite is a local
read cache keyed by file path, mtime, and size.

## Commands

```bash
uv sync --extra dev
uv run streamlit run app.py
uv run ph-election-dashboard
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Decisions

- Keep a local-demo scope. No auth, roles, or hosted multi-user deployment.
- Use SQLite instead of a database server so a clean checkout needs no services.
- Bundle GeoJSON so maps work offline.
- Support any OpenAI-compatible endpoint for provider flexibility. Add native
  Gemini and Anthropic adapters.
- Never persist provider keys. Read them from environment variables or a
  session-only password field.
- Keep CSV as the source of truth so operators can edit files by hand.

## Gotchas

- Streamlit runs `app.py` as a script, so use absolute package imports, not
  relative imports.
- `st.cache_data` must be cleared when the data signature changes.
- `st.fragment` is used for auto refresh. Tests set `auto_refresh` to `false`.
- The GeoJSON feature `id` is set to the PSGC code or island-group name at load
  time so Plotly can match locations.
- Boundary files carry CC BY-IGO attribution requirements.

## Known Limitations

- Sample data is fictional and small.
- SQLite has no concurrent-writer story beyond Streamlit's single-process use.
- AI providers can change model names. Models are editable in the UI.
```

- [ ] **Step 9: Verify docs contain no stale commands**

Run:

```bash
grep -RInE "requirements.txt|streamlit run app.py|google-generativeai|gemini-pro" README.md CONTEXT.md docs data config || true
```

Expected: no matches except possibly `streamlit run app.py` if it is still valid. It is valid, so treat that as acceptable. The old `requirements.txt`, `google-generativeai`, and `gemini-pro` references must be gone.

---

## Task 13: Final Verification

- [ ] **Step 1: Install, lint, format, and test**

Run:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Expected: all commands exit 0 and all tests pass.

- [ ] **Step 2: Verify the package build includes the GeoJSON**

Run:

```bash
rm -rf dist build
uv build
python -m zipfile -l dist/*.whl | grep -E "geojson|ph_election_dashboard/config.py"
```

Expected: both `.geojson` files and `ph_election_dashboard/config.py` appear in the wheel listing.

- [ ] **Step 3: Verify the app starts headlessly**

Run:

```bash
uv run streamlit run app.py --server.headless true --server.port 8599 &
pid=$!
sleep 6
curl -fsS http://localhost:8599/_stcore/health
kill $pid
```

Expected: `ok` is printed.

- [ ] **Step 3b: Verify auto refresh with a temporary data directory**

Run in one terminal:

```bash
mkdir -p /tmp/ph-verify/data /tmp/ph-verify/config /tmp/ph-verify/logs
cp data/national_election_results.csv /tmp/ph-verify/data/
cp config/config.json /tmp/ph-verify/config/config.json
PH_ELECTION_DATA_DIR=/tmp/ph-verify/data \
PH_ELECTION_CONFIG_FILE=/tmp/ph-verify/config/config.json \
PH_ELECTION_LOG_DIR=/tmp/ph-verify/logs \
PH_ELECTION_DB_PATH=/tmp/ph-verify/data/election.db \
uv run streamlit run app.py --server.headless true --server.port 8599
```

Open <http://localhost:8599> in a browser, note the Rows metric, append a row to
`/tmp/ph-verify/data/national_election_results.csv`, wait 5 seconds, and confirm
the Rows metric increases without pressing Refresh. Stop the server and remove
`/tmp/ph-verify`.

Expected: the table and Rows metric update automatically.

- [ ] **Step 4: Verify the console script exists**

Run:

```bash
uv run python -c "from ph_election_dashboard.launcher import main; print(callable(main))"
```

Expected:

```text
True
```

- [ ] **Step 5: Map the acceptance criteria to evidence**

Check each item from the spec:

1. Clean checkout runs with `uv sync --extra dev` and `uv run streamlit run app.py`: Step 3.
2. `uv run ph-election-dashboard` launches: the console script is declared in `pyproject.toml` and wired to `launcher.main`; Step 4 confirms the callable.
3. Filters change table and charts: `tests/test_filters.py` and `tests/test_app_smoke.py`.
4. Choropleth renders for regions and island groups: `tests/test_geo.py`.
5. CSV export downloads filtered rows: `data.to_csv_bytes` is covered by `tests/test_data.py` and used by the download button in `app.py`.
6. Auto refresh on CSV change: `st.fragment` watcher in `app.py`, the signature test in `tests/test_data.py`, and the manual check in Step 3b.
7. Deterministic and provider AI summaries: `tests/test_ai.py`.
8. Lint, format, and tests pass: Step 1.
9. Docs match implementation: Task 12.
10. Secrets and local state are ignored: `.gitignore` in Task 1.

- [ ] **Step 6: Report status**

Summarize:

- Files changed.
- Test and lint results.
- Any unverified item, with the exact command needed to verify it.

Do not commit or push unless the user explicitly asks.

---

## Implementation Notes

These deviations from the plan were made during execution and are reflected in the code:

- The bundled GeoJSON package is `src/ph_election_dashboard/geo_data/`, not `data/`, because a
  package named `data` shadows the `data.py` module.
- `src/ph_election_dashboard/gemini_integration.py` was deleted. Its responsibilities moved to
  `ai.py`.
- `available_filter_columns` hides columns that contain only null or blank values, so national
  data does not show empty province, municipality, or barangay filters.
- `available_map_levels` sorts by mapped-label coverage, so national data defaults to the island
  group map when that covers more rows.
- Session-state widget values are validated before rendering. Switching election levels no longer
  leaves a filter or map-level widget pointing at a value that no longer exists.
- Auto refresh and filter behavior were verified in a live browser against a temporary data
  directory.

Post-review fixes:

- The AI summary cache key now includes a SHA-256 fingerprint of the active API key and the
  provider kind and base URL, so entering a key after seeing the fallback triggers a new call.
  Failed AI calls are not cached, so a retry is possible.
- `config/providers.json` is git-ignored.
- SQLite initialization drops and recreates cache tables when the schema version or required
  columns do not match. A stale cache can no longer block startup.
- Geo lookup accepts zero-padded PSGC codes and merges labels that resolve to the same region.
- Gemini keys are sent in the `x-goog-api-key` header instead of the URL query string.
- Provider parsing ignores non-dict `headers`, and AI stats tolerate a missing `party` column.
- `cache_ttl` was removed because the signature-based cache does not use it.
- The custom provider form has a `Requires API key` checkbox for local no-key endpoints.
- `python -m ph_election_dashboard` now propagates the launcher exit code.
- Smoke tests cover reset, candidate search, election-level switching, SQLite mode, and AI cache
  invalidation when the key changes.


