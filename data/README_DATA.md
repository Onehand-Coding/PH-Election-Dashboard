# Election Data Format

The dashboard reads CSV files listed in `config/config.json`. Headers are
normalized to lowercase snake case, and spaces or hyphens become underscores.

## Columns

| Column | Required | Notes |
| --- | --- | --- |
| `position` | yes | For example Senator, Governor, Barangay Captain |
| `candidate_name` | yes | Candidate or party-list name |
| `total_votes` | yes | Non-negative integer |
| `party` | no | Blank or `Independent` allowed |
| `region` | no | Region or island-group label |
| `region_focus` | no | Fallback label for national data |
| `province` | no | |
| `municipality_city` | no | |
| `barangay` | no | |

Accepted aliases:

- `Candidate`, `Name` -> `candidate_name`
- `Votes`, `Vote_Count` -> `total_votes`
- `Municipality`, `City` -> `municipality_city`

## Validation

- Missing required columns stop the page with an error.
- Rows with missing, non-numeric, or negative votes are dropped with a warning.
- Rows with a blank position or candidate name are dropped with a warning.
- Duplicate rows are kept.

## Region Labels

The map accepts region names such as `Region III (Central Luzon)`, short forms
such as `Region III`, aliases such as `NCR` and `Metro Manila`, island groups
`Luzon`, `Visayas`, and `Mindanao`, and PSGC region codes such as
`1300000000`. Unmatched labels are reported below the map.
