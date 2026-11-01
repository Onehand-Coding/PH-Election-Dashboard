import json

from ph_election_dashboard import config


def test_merge_config_overrides_defaults():
    merged = config.merge_config(
        {"election_year": 2030, "data_files": {"national": "x.csv"}}
    )
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
    monkeypatch.setenv(
        "PH_ELECTION_CONFIG_FILE", str(tmp_path / "config" / "config.json")
    )
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
