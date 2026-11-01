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
        "Senator,Alice,Party A,100,Luzon\nGovernor,Bob,Party B,90,Visayas\n",
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
