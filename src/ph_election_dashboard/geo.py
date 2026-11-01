from __future__ import annotations

import json
import re
from importlib import resources
from typing import Any

import pandas as pd
import plotly.express as px

REGION_FILE = "ph_regions.geojson"
ISLAND_FILE = "ph_island_groups.geojson"
LEVEL_REGION = "region"
LEVEL_ISLAND = "island_group"

REGION_ALIASES = {
    "ncr": "1300000000",
    "metro manila": "1300000000",
    "national capital region": "1300000000",
    "car": "1400000000",
    "cordillera": "1400000000",
    "barmm": "1900000000",
    "armm": "1900000000",
    "mimaropa": "1700000000",
    "nir": "1800000000",
    "negros island region": "1800000000",
    "calabarzon": "400000000",
    "bicol": "500000000",
    "bicol region": "500000000",
    "soccsksargen": "1200000000",
    "caraga": "1600000000",
    "zamboanga peninsula": "900000000",
    "davao region": "1100000000",
    "northern mindanao": "1000000000",
    "western visayas": "600000000",
    "central visayas": "700000000",
    "eastern visayas": "800000000",
    "central luzon": "300000000",
    "cagayan valley": "200000000",
    "ilocos region": "100000000",
    "region i": "100000000",
    "region ii": "200000000",
    "region iii": "300000000",
    "region iv a": "400000000",
    "region iv b": "1700000000",
    "region v": "500000000",
    "region vi": "600000000",
    "region vii": "700000000",
    "region viii": "800000000",
    "region ix": "900000000",
    "region x": "1000000000",
    "region xi": "1100000000",
    "region xii": "1200000000",
    "region xiii": "1600000000",
}
ISLAND_ALIASES = {
    "luzon": "Luzon",
    "visayas": "Visayas",
    "mindanao": "Mindanao",
}


def _normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def load_geojson(file_name: str) -> dict[str, Any]:
    path = resources.files("ph_election_dashboard.geo_data").joinpath(file_name)
    with path.open(encoding="utf-8") as handle:
        geojson = json.load(handle)
    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        if "adm1_psgc" in properties:
            feature["id"] = str(properties["adm1_psgc"])
        elif "island_group" in properties:
            feature["id"] = str(properties["island_group"])
    return geojson


def _region_lookup(geojson: dict[str, Any]) -> dict[str, str]:
    lookup = dict(REGION_ALIASES)
    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        code = str(properties.get("adm1_psgc", ""))
        name = str(properties.get("adm1_en", ""))
        if not code or not name:
            continue
        lookup[_normalize(name)] = code
        lookup[_normalize(code)] = code
        lookup[_normalize(code.zfill(10))] = code
        short = re.sub(r"\s*\(.*?\)\s*", " ", name)
        lookup[_normalize(short)] = code
    return lookup


def _island_lookup(geojson: dict[str, Any]) -> dict[str, str]:
    lookup = dict(ISLAND_ALIASES)
    for feature in geojson.get("features", []):
        name = str(feature.get("properties", {}).get("island_group", ""))
        if name:
            lookup[_normalize(name)] = name
    return lookup


def _source_column(frame: pd.DataFrame) -> str | None:
    for column in ("region", "region_focus"):
        if column in frame.columns and frame[column].notna().any():
            return column
    return None


def aggregate_for_map(
    frame: pd.DataFrame, level: str
) -> tuple[pd.DataFrame, list[str]]:
    column = _source_column(frame)
    if column is None or frame.empty:
        return pd.DataFrame(columns=["label", "geo_id", "total_votes"]), []

    if level == LEVEL_REGION:
        lookup = _region_lookup(load_geojson(REGION_FILE))
    elif level == LEVEL_ISLAND:
        lookup = _island_lookup(load_geojson(ISLAND_FILE))
    else:
        raise ValueError(f"Unknown map level: {level}")

    working = frame.copy()
    working["_label"] = working[column].astype("string").str.strip()
    working = working[working["_label"].notna() & (working["_label"] != "")]
    grouped = working.groupby("_label", as_index=False)["total_votes"].sum()

    rows = []
    unmapped = []
    for record in grouped.to_dict("records"):
        label = str(record["_label"])
        geo_id = lookup.get(_normalize(label))
        if geo_id is None:
            unmapped.append(label)
        else:
            rows.append(
                {
                    "label": label,
                    "geo_id": geo_id,
                    "total_votes": int(record["total_votes"]),
                }
            )
    result = pd.DataFrame(rows, columns=["label", "geo_id", "total_votes"])
    if not result.empty:
        result = result.groupby("geo_id", as_index=False, sort=False).agg(
            label=("label", "first"),
            total_votes=("total_votes", "sum"),
        )
        result = result[["label", "geo_id", "total_votes"]]
    return result, sorted(set(unmapped))


def available_map_levels(frame: pd.DataFrame) -> list[str]:
    scored = []
    for order, level in enumerate((LEVEL_REGION, LEVEL_ISLAND)):
        aggregated, _ = aggregate_for_map(frame, level)
        if not aggregated.empty:
            scored.append((-len(aggregated), order, level))
    scored.sort()
    return [level for _, _, level in scored]


def build_choropleth(frame: pd.DataFrame, level: str):
    aggregated, unmapped = aggregate_for_map(frame, level)
    if aggregated.empty:
        return None, unmapped
    file_name = REGION_FILE if level == LEVEL_REGION else ISLAND_FILE
    geojson = load_geojson(file_name)
    title = "Votes by Region" if level == LEVEL_REGION else "Votes by Island Group"
    figure = px.choropleth(
        aggregated,
        geojson=geojson,
        locations="geo_id",
        featureidkey="id",
        color="total_votes",
        hover_name="label",
        color_continuous_scale="Blues",
        labels={"total_votes": "Total Votes"},
        title=title,
    )
    figure.update_geos(fitbounds="locations", visible=False)
    figure.update_layout(
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        coloraxis_colorbar_title="Votes",
    )
    return figure, unmapped
