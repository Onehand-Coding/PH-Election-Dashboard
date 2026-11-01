import pandas as pd

from ph_election_dashboard.filters import (
    ALL,
    ElectionFilters,
    available_filter_columns,
)


def sample_frame():
    return pd.DataFrame(
        {
            "position": ["Senator", "Senator", "Governor"],
            "candidate_name": ["Alice", "Bob", "Carla"],
            "total_votes": [100, 90, 80],
            "region": ["Luzon", "Visayas", "Luzon"],
            "province": ["Bulacan", "Cebu", None],
        }
    )


def test_available_filter_columns():
    assert available_filter_columns(sample_frame()) == [
        "position",
        "region",
        "province",
    ]


def test_position_filter_changes_rows():
    filters = ElectionFilters(sample_frame())
    filters.set("position", "Senator")
    result = filters.apply()
    assert result["candidate_name"].tolist() == ["Alice", "Bob"]


def test_all_selector_does_not_filter():
    filters = ElectionFilters(sample_frame())
    filters.set("position", ALL)
    assert len(filters.apply()) == 3


def test_location_filters_combine():
    filters = ElectionFilters(sample_frame())
    filters.set("position", "Senator")
    filters.set("region", "Luzon")
    assert filters.apply()["candidate_name"].tolist() == ["Alice"]


def test_candidate_search_is_case_insensitive():
    filters = ElectionFilters(sample_frame())
    filters.set_search("ALI")
    assert filters.apply()["candidate_name"].tolist() == ["Alice"]


def test_reset_clears_filters_and_search():
    filters = ElectionFilters(sample_frame())
    filters.set("position", "Senator")
    filters.set_search("Alice")
    filters.reset()
    assert filters.selections == {}
    assert filters.search == ""
    assert len(filters.apply()) == 3


def test_all_empty_column_is_hidden():
    frame = pd.DataFrame(
        {
            "position": ["Senator"],
            "candidate_name": ["A"],
            "total_votes": [1],
            "region": [None],
            "province": [""],
        }
    )
    assert available_filter_columns(frame) == ["position"]


def test_options_are_sorted_and_include_all():
    filters = ElectionFilters(sample_frame())
    assert filters.options("region") == [ALL, "Luzon", "Visayas"]


def test_missing_column_is_ignored():
    frame = pd.DataFrame(
        {"position": ["Senator"], "candidate_name": ["A"], "total_votes": [1]}
    )
    filters = ElectionFilters(frame)
    assert filters.options("region") == [ALL]
    filters.set("region", "Luzon")
    assert "region" not in filters.selections
    assert len(filters.apply()) == 1
