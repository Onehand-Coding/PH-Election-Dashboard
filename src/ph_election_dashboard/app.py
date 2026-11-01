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
    if st.session_state.get("ai_provider") not in provider_names:
        st.session_state["ai_provider"] = provider_names[0]
    provider_name = st.sidebar.selectbox("Provider", provider_names, key="ai_provider")

    if provider_name == "custom":
        kind = st.sidebar.selectbox(
            "API type", ["openai", "anthropic", "gemini"], key="custom_kind"
        )
        base_url = st.sidebar.text_input(
            "Base URL",
            value="http://localhost:1234/v1",
            key="custom_base_url",
        )
        model = st.sidebar.text_input("Model", value="local-model", key="custom_model")
        key_override = st.sidebar.text_input(
            "API key (session only)",
            type="password",
            key="custom_key",
        )
        provider = ai.Provider("custom", kind, base_url, None, model, key_required=True)
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
        paths.config_file.stat().st_mtime_ns if paths.config_file.exists() else 0
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
    if st.session_state.get("election_type") not in election_types:
        st.session_state["election_type"] = election_types[default_index]
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
        filtered[display_columns].sort_values("total_votes", ascending=False),
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
        if st.session_state.get("map_level") not in levels:
            st.session_state["map_level"] = levels[0]
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
        st.caption("No region or island-group labels matched the bundled map data.")

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
