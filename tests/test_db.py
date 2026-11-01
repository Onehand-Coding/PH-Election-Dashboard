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
    db.replace_election_type(connection, "national", sample_frame(), source, *signature)
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


def test_initialize_rebuilds_old_schema(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    connection.execute(
        "CREATE TABLE election_results (id INTEGER PRIMARY KEY, position TEXT)"
    )
    connection.execute("PRAGMA user_version = 0")
    connection.commit()

    db.initialize(connection)

    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(election_results)")
    }
    assert "region" in columns
    assert db.schema_version(connection) == db.SCHEMA_VERSION
    connection.close()


def test_initialize_rebuilds_future_schema_version(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    db.initialize(connection)
    connection.execute("PRAGMA user_version = 99")
    connection.commit()

    db.initialize(connection)

    assert db.schema_version(connection) == db.SCHEMA_VERSION
    connection.close()
