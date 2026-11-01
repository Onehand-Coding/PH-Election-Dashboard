import pandas as pd
import pytest

from ph_election_dashboard import geo


def test_load_region_geojson_sets_ids():
    geojson = geo.load_geojson(geo.REGION_FILE)
    assert len(geojson["features"]) == 18
    assert all("id" in feature for feature in geojson["features"])


def test_region_level_maps_aliases_and_reports_unmapped():
    frame = pd.DataFrame(
        {
            "region": ["NCR", "Region III", "Luzon"],
            "total_votes": [10, 20, 30],
        }
    )
    aggregated, unmapped = geo.aggregate_for_map(frame, geo.LEVEL_REGION)
    assert aggregated["geo_id"].tolist() == ["1300000000", "300000000"]
    assert aggregated["total_votes"].tolist() == [10, 20]
    assert unmapped == ["Luzon"]


def test_island_group_level_maps_luzon():
    frame = pd.DataFrame({"region": ["Luzon", "NCR"], "total_votes": [30, 10]})
    aggregated, unmapped = geo.aggregate_for_map(frame, geo.LEVEL_ISLAND)
    assert aggregated["geo_id"].tolist() == ["Luzon"]
    assert unmapped == ["NCR"]


def test_psgc_code_input_maps():
    frame = pd.DataFrame({"region": ["1300000000"], "total_votes": [5]})
    aggregated, _ = geo.aggregate_for_map(frame, geo.LEVEL_REGION)
    assert aggregated["geo_id"].tolist() == ["1300000000"]


def test_available_map_levels_order():
    frame = pd.DataFrame({"region": ["NCR", "Luzon"], "total_votes": [10, 20]})
    assert geo.available_map_levels(frame) == [
        geo.LEVEL_REGION,
        geo.LEVEL_ISLAND,
    ]


def test_available_map_levels_prefers_broader_coverage():
    frame = pd.DataFrame(
        {"region": ["NCR", "Luzon", "Visayas"], "total_votes": [10, 20, 30]}
    )
    assert geo.available_map_levels(frame) == [
        geo.LEVEL_ISLAND,
        geo.LEVEL_REGION,
    ]


def test_region_focus_is_a_fallback_source():
    frame = pd.DataFrame({"region_focus": ["Visayas"], "total_votes": [50]})
    aggregated, _ = geo.aggregate_for_map(frame, geo.LEVEL_ISLAND)
    assert aggregated["geo_id"].tolist() == ["Visayas"]


def test_build_choropleth_returns_figure():
    frame = pd.DataFrame({"region": ["NCR"], "total_votes": [10]})
    figure, unmapped = geo.build_choropleth(frame, geo.LEVEL_REGION)
    assert figure is not None
    assert unmapped == []


def test_unknown_map_level_raises():
    with pytest.raises(ValueError):
        geo.aggregate_for_map(pd.DataFrame({"region": ["NCR"]}), "unknown")
