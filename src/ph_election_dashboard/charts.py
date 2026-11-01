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
    totals = frame.groupby("position")["total_votes"].sum().sort_values(ascending=False)
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
        "party" if "party" in subset.columns and subset["party"].notna().any() else None
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
        title=(f"Party Vote Share for {position}" if position else "Party Vote Share"),
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
