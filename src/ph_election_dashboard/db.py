from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCHEMA_VERSION = 1
SCHEMA_COLUMNS = {
    "id",
    "election_type",
    "position",
    "candidate_name",
    "party",
    "total_votes",
    "region",
    "region_focus",
    "province",
    "municipality_city",
    "barangay",
}
SOURCE_COLUMNS = {
    "election_type",
    "source_path",
    "mtime_ns",
    "size_bytes",
    "row_count",
    "loaded_at",
}
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


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _needs_rebuild(connection: sqlite3.Connection) -> bool:
    version = schema_version(connection)
    if version not in (0, SCHEMA_VERSION):
        return True
    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if "election_results" in tables and not SCHEMA_COLUMNS.issubset(
        _table_columns(connection, "election_results")
    ):
        return True
    if "source_state" in tables and not SOURCE_COLUMNS.issubset(
        _table_columns(connection, "source_state")
    ):
        return True
    return False


def initialize(connection: sqlite3.Connection) -> None:
    if _needs_rebuild(connection):
        connection.executescript(
            "DROP TABLE IF EXISTS election_results; DROP TABLE IF EXISTS source_state;"
        )
        connection.commit()
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
