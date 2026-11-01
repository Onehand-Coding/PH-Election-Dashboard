import json
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Position,Candidate_Name,Party,Total_Votes,Region\n" + body)


def build_app(tmp_path, monkeypatch, data_source="csv"):
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
        "data_source": data_source,
        "auto_refresh": False,
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
    return app, data_dir


def test_app_runs_filters_searches_resets_and_switches(tmp_path, monkeypatch):
    app, _ = build_app(tmp_path, monkeypatch)
    assert not app.exception
    assert len(app.dataframe) == 1
    assert len(app.dataframe[0].value) == 2

    position = next(box for box in app.selectbox if box.label == "Position")
    position.set_value("Senator").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1

    search = next(box for box in app.text_input if box.label == "Search candidate")
    search.set_value("Alice").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1

    reset = next(button for button in app.button if button.label == "Reset filters")
    reset.click().run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 2

    level = next(radio for radio in app.radio if radio.label == "Election level")
    level.set_value("local").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1


def test_app_sqlite_mode_creates_database(tmp_path, monkeypatch):
    app, data_dir = build_app(tmp_path, monkeypatch, data_source="sqlite")
    assert not app.exception
    assert (data_dir / "election.db").exists()


def test_ai_cache_invalidates_when_key_changes(tmp_path, monkeypatch):
    app, _ = build_app(tmp_path, monkeypatch)
    import ph_election_dashboard.app as app_module

    calls = []

    def fake_generate(*args, **kwargs):
        calls.append(kwargs.get("api_key_override"))
        return app_module.ai.SummaryResult("model summary", used_fallback=False)

    monkeypatch.setattr(app_module.ai, "generate_summary", fake_generate)

    show = next(box for box in app.checkbox if box.label == "Show AI summary")
    show.check().run()
    assert not app.exception
    assert len(calls) == 1

    key_box = next(
        box for box in app.text_input if box.label == "API key override (session only)"
    )
    key_box.set_value("new-secret").run()
    assert not app.exception
    assert len(calls) == 2
