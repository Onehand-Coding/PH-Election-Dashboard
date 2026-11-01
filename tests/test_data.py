import os

import pandas as pd

from ph_election_dashboard import config, data


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
    path.write_text("Position,Candidate_Name,Party,Total_Votes,Region\n" + body)
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
