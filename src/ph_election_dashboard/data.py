from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ph_election_dashboard import db
from ph_election_dashboard.config import Paths, get_paths

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
            f"{int(blank_required.sum())} row(s) with a blank position "
            "or candidate name."
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
    for election_type in config.get("data_files", {}):
        result = load_election_data(election_type, config, paths, force_rebuild=True)
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
