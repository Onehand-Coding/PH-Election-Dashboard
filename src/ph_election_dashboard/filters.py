from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

ALL = "All"
FILTER_COLUMNS = ["position", "region", "province", "municipality_city", "barangay"]


def available_filter_columns(frame: pd.DataFrame) -> list[str]:
    columns = []
    for column in FILTER_COLUMNS:
        if column not in frame.columns:
            continue
        values = frame[column].dropna().astype(str).str.strip()
        if (values != "").any():
            columns.append(column)
    return columns


@dataclass
class ElectionFilters:
    dataframe: pd.DataFrame
    selections: dict[str, str] = field(default_factory=dict)
    search: str = ""

    def options(self, column: str) -> list[str]:
        if column not in self.dataframe.columns:
            return [ALL]
        values = self.dataframe[column].dropna().astype(str).str.strip()
        values = values[values != ""]
        return [ALL, *sorted(values.unique().tolist())]

    def set(self, column: str, value: str) -> None:
        if column in self.dataframe.columns and value != ALL:
            self.selections[column] = value
        else:
            self.selections.pop(column, None)

    def set_search(self, value: str) -> None:
        self.search = value.strip()

    def reset(self) -> None:
        self.selections.clear()
        self.search = ""

    def apply(self) -> pd.DataFrame:
        result = self.dataframe
        for column, value in self.selections.items():
            if value != ALL and column in result.columns:
                result = result[result[column].astype("string") == value]
        if self.search and "candidate_name" in result.columns:
            needle = self.search.lower()
            mask = (
                result["candidate_name"]
                .astype("string")
                .str.lower()
                .str.contains(needle, na=False, regex=False)
            )
            result = result[mask]
        return result.reset_index(drop=True)
