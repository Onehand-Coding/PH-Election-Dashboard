#!/usr/bin/env python3
import os
import json
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px

from gemini_integration import generate_election_summary
from config import (
    PROJECT_ROOT,
    DATA_DIR,
    CONFIG_FILE,
    load_config,
    logger,
    DEFAULT_CONFIG,
)


# --- UI Helper & Plotting Functions ---
class ElectionFilters:
    def __init__(self, df, election_type):
        self.df = df
        self.election_type = election_type
        self.filters = {}

    def add_filter(self, column, label, default="All"):
        if column in self.df.columns:
            options = [default] + sorted(self.df[column].dropna().unique().tolist())
            self.filters[column] = st.sidebar.selectbox(label, options)
        return self

    def apply(self):
        filtered_df = self.df.copy()
        for col, val in self.filters.items():
            if val != "All" and col in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[col] == val]
        return filtered_df


@st.cache_data(ttl=DEFAULT_CONFIG["cache_ttl"])
def load_election_data(election_type, config):
    """Loads election data based on the type specified in the config."""
    if (
        not config
        or "data_files" not in config
        or election_type not in config["data_files"]
    ):
        logger.error(
            f"Data file configuration missing for election type: {election_type}"
        )
        st.error(f"Data file configuration missing for election type: {election_type}")
        return pd.DataFrame()

    file_name = config["data_files"][election_type]
    file_path = os.path.join(DATA_DIR, file_name)

    if not os.path.exists(file_path):
        logger.warning(f"Data file not found: {file_path}")
        st.warning(
            f"Data file not found: {file_path}. Please ensure it exists in the '{DATA_DIR}' directory."
        )
        return pd.DataFrame()
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".json"):
            df = pd.read_json(file_path, orient="records")
        else:
            logger.error(
                f"Unsupported file format: {file_name}. Please use CSV or JSON."
            )
            st.error(f"Unsupported file format: {file_name}. Please use CSV or JSON.")
            return pd.DataFrame()

        # Standardize column names
        df.columns = df.columns.str.replace(" ", "_").str.lower()
        required_cols = ["position", "candidate_name", "total_votes"]
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"Data file {file_name} is missing required column: {col}")
                st.error(f"Data file {file_name} is missing required column: {col}")
                return pd.DataFrame(columns=df.columns)

        df["total_votes"] = (
            pd.to_numeric(df["total_votes"], errors="coerce").fillna(0).astype(int)
        )
        logger.info(f"Successfully loaded data from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        st.error(f"Error loading data from {file_path}: {e}")
        return pd.DataFrame()


def get_filters_for_level(df, election_type, config):
    """Generates filters using ElectionFilters class."""
    filters = ElectionFilters(df, election_type)
    filters.add_filter("position", "Filter by Position:")

    if election_type == "national":
        filters.add_filter("region_focus", "Filter by Region Focus (if applicable):")
    elif election_type == "local":
        filters.add_filter("region", "Filter by Region:")
        filters.add_filter("province", "Filter by Province:")
        filters.add_filter("municipality_city", "Filter by Municipality/City:")
    elif election_type == "barangay":
        filters.add_filter("region", "Filter by Region:")
        filters.add_filter("province", "Filter by Province:")
        filters.add_filter("municipality_city", "Filter by Municipality/City:")
        filters.add_filter("barangay", "Filter by Barangay:")

    return filters.filters


def display_charts(df, election_type, selected_position):
    """Displays charts for the given data."""
    if df.empty:
        st.info("No data to display for the current selection.")
        return

    plot_position = selected_position
    if selected_position == "All":
        if not df["position"].empty:
            plot_position = df["position"].unique()[0]
            st.caption(
                f"Displaying chart for an example position: {plot_position} (as 'All' positions selected)."
            )
        else:
            st.info("No specific position data to chart.")
            return

    pos_df = df[df["position"] == plot_position].sort_values(
        by="total_votes", ascending=False
    )
    if pos_df.empty:
        st.info(f"No data available for position: {plot_position}")
        return

    # Bar Chart
    st.subheader(f"Top Candidates for {plot_position}")
    top_n = min(15, len(pos_df))
    fig_bar = px.bar(
        pos_df.head(top_n),
        x="candidate_name",
        y="total_votes",
        color="party" if "party" in pos_df.columns else None,
        title=f"Vote Counts for {plot_position}",
        labels={
            "candidate_name": "Candidate",
            "total_votes": "Total Votes",
            "party": "Party",
        },
        hover_data=["candidate_name", "total_votes", "party"]
        if "party" in pos_df.columns
        else ["candidate_name", "total_votes"],
    )
    fig_bar.update_layout(xaxis_title="Candidate", yaxis_title="Total Votes")
    st.plotly_chart(fig_bar, use_container_width=True)

    # Pie Chart
    if "party" in pos_df.columns and pos_df["party"].nunique() > 1:
        st.subheader(f"Vote Distribution by Party for {plot_position}")
        party_votes = pos_df.groupby("party")["total_votes"].sum().reset_index()
        party_votes = party_votes[
            party_votes["total_votes"] > party_votes["total_votes"].sum() * 0.01
        ]
        if not party_votes.empty and len(party_votes) > 1:
            fig_pie = px.pie(
                party_votes,
                names="party",
                values="total_votes",
                title=f"Party Vote Share for {plot_position}",
                hole=0.3,
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.caption(
                f"Not enough party diversity or votes to display a meaningful party distribution pie chart for {plot_position}."
            )

    # Regional Summary
    if election_type in ["local", "barangay"] and "region" in df.columns:
        st.subheader("Regional Vote Summary")
        summary_df = (
            df
            if selected_position == "All"
            else df[df["position"] == selected_position]
        )
        if not summary_df.empty and "region" in summary_df.columns:
            regional_summary = (
                summary_df.groupby("region")["total_votes"]
                .sum()
                .reset_index()
                .sort_values(by="total_votes", ascending=False)
            )
            if not regional_summary.empty:
                fig_regional_bar = px.bar(
                    regional_summary,
                    x="region",
                    y="total_votes",
                    title="Total Votes per Region",
                    labels={"region": "Region", "total_votes": "Total Votes"},
                )
                st.plotly_chart(fig_regional_bar, use_container_width=True)
            else:
                st.caption("No regional data to summarize.")
        else:
            st.caption(
                "Regional data not available or applicable for this election type/filter."
            )


# --- Main Application ---
def main():
    st.set_page_config(
        page_title="Philippine Election Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    logger.info("Starting Philippine Election Dashboard")
    config = load_config()
    if not config:
        logger.critical("Failed to load configuration. Stopping application.")
        st.stop()

    election_type = config.get(
        "current_election_type", DEFAULT_CONFIG["current_election_type"]
    )
    election_year = config.get("election_year", DEFAULT_CONFIG["election_year"])

    st.sidebar.title(f"🇵🇭 {election_year} Elections")
    st.sidebar.markdown("---")

    available_election_types = list(config.get("data_files", {}).keys())
    if available_election_types:
        session_election_type = st.sidebar.radio(
            "Select Election Level to View:",
            available_election_types,
            index=available_election_types.index(election_type)
            if election_type in available_election_types
            else 0,
            key="session_election_type_selector",
        )
        if session_election_type != election_type:
            election_type = session_election_type
            st.cache_data.clear()
            config = load_config()
    else:
        st.sidebar.error("No election types defined in data_files configuration.")
        st.stop()

    st.title(
        f"{election_year} Philippine {election_type.replace('_', ' ').capitalize()} Election Dashboard"
    )
    st.markdown(
        f"Displaying results for the **{election_type.replace('_', ' ').capitalize()}** elections. (Last data refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
    )

    df_election_data = load_election_data(election_type, config)
    if df_election_data.empty:
        st.warning(
            f"No data loaded for {election_type} elections. Please check your data files and `config.json`."
        )
        st.markdown(
            "Please ensure your data files are correctly formatted. See `data/README_DATA.md` for details."
        )
        st.stop()

    st.sidebar.markdown("---")
    st.sidebar.header("Filters")
    df_for_filters = df_election_data.copy()
    active_filters = get_filters_for_level(df_for_filters, election_type, config)
    filtered_df = ElectionFilters(df_election_data, election_type).apply()

    if filtered_df.empty:
        st.info("No results match the selected filters.")
    else:
        st.subheader("Filtered Election Results")
        cols_to_display = ["candidate_name", "position", "party", "total_votes"]
        if election_type == "local" or election_type == "barangay":
            cols_to_display.extend(["region", "province", "municipality_city"])
            if election_type == "barangay":
                cols_to_display.append("barangay")
        displayable_cols = [
            col for col in cols_to_display if col in filtered_df.columns
        ]
        st.dataframe(
            filtered_df[displayable_cols].sort_values(
                by="total_votes", ascending=False
            ),
            use_container_width=True,
        )

        st.markdown("---")
        st.header("📊 Visualizations")
        display_charts(
            filtered_df, election_type, active_filters.get("position", "All")
        )

    st.sidebar.markdown("---")
    if st.sidebar.checkbox("Show AI Generated Summary (Beta)", key="show_ai_summary"):
        st.markdown("---")
        st.subheader("🧠 AI Election Highlights")
        with st.spinner("Generating AI summary..."):
            location_filters_for_ai = {
                k: v
                for k, v in active_filters.items()
                if k in ["region", "province", "municipality_city", "barangay"]
                and v != "All"
            }
            ai_summary = generate_election_summary(
                filtered_df,
                election_type,
                position_filter=active_filters.get("position", "All"),
                location_filters=location_filters_for_ai,
            )
            st.markdown(ai_summary)

    st.sidebar.markdown("---")
    if st.sidebar.button("Force Refresh Data", key="refresh_button"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.info(
        f"Dashboard current as of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":
    main()
