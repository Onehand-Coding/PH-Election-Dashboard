import pandas as pd

from ph_election_dashboard import charts
from ph_election_dashboard.filters import ALL


def sample_frame():
    return pd.DataFrame(
        {
            "position": ["Senator", "Senator", "Governor"],
            "candidate_name": ["Alice", "Bob", "Carla"],
            "party": ["Party A", "Party B", "Party A"],
            "total_votes": [100, 90, 200],
            "region": ["Luzon", "Visayas", "Luzon"],
        }
    )


def test_resolve_position_with_all_picks_highest_total():
    subset, position = charts.resolve_position(sample_frame(), ALL)
    assert position == "Governor"
    assert subset["candidate_name"].tolist() == ["Carla"]


def test_resolve_position_respects_selection():
    subset, position = charts.resolve_position(sample_frame(), "Senator")
    assert position == "Senator"
    assert len(subset) == 2


def test_top_candidates_bar_returns_figure():
    figure, position = charts.top_candidates_bar(sample_frame(), "Senator")
    assert figure is not None
    assert position == "Senator"


def test_party_pie_requires_two_parties():
    one_party = pd.DataFrame(
        {
            "position": ["Senator"],
            "candidate_name": ["Alice"],
            "party": ["Party A"],
            "total_votes": [100],
        }
    )
    assert charts.party_pie(one_party, "Senator") is None


def test_party_pie_returns_figure_with_two_parties():
    assert charts.party_pie(sample_frame(), "Senator") is not None


def test_regional_bar_returns_figure():
    assert charts.regional_bar(sample_frame()) is not None


def test_regional_bar_without_region_returns_none():
    frame = pd.DataFrame(
        {
            "position": ["Senator"],
            "candidate_name": ["Alice"],
            "total_votes": [1],
        }
    )
    assert charts.regional_bar(frame) is None


def test_empty_frame_returns_none():
    empty = pd.DataFrame(columns=["position", "candidate_name", "total_votes"])
    figure, position = charts.top_candidates_bar(empty, ALL)
    assert figure is None
    assert position is None
