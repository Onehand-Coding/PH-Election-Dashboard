# PH Election Dashboard: Finish-Out Design

Date: 2026-11-01
Status: Draft for user review
Repo: https://github.com/Onehand-Coding/PH-Election-Dashboard

## Context

The repository is a Streamlit + Plotly dashboard for Philippine election sample data. It has a
single "Initial commit" from July 2025 and has not changed since. Several advertised behaviors do
not work, and the project's own README lists unfinished features.

Known defects:

- Sidebar filters do not affect the data. `get_filters_for_level` builds an `ElectionFilters`
  instance and returns its raw selection dict, while `main` applies a fresh, empty
  `ElectionFilters` instance (app.py lines 114 and 275).
- `src/config.py` lives outside the package and is imported as a top-level module. An installed
  wheel contains only `ph_election_dashboard`, so `config` and `gemini_integration` are lost.
- `pyproject.toml` points pytest at `tests/`, which does not exist.
- README describes the old flat layout, `requirements.txt`, and `streamlit run app.py`, none of
  which match the current tree.
- `google-generativeai` is used with the retired `gemini-pro` model. No fallback provider exists.
- National results expose `region` but the UI looks for `region_focus`, so national filtering is
  absent.
- The only refresh path is a manual button that clears the entire Streamlit cache.

## Goals

1. Make the app correct, installable, and runnable from a clean checkout.
2. Finish the local-demo scope: working filters, richer charts, choropleth maps, CSV export,
   data-change auto refresh, SQLite-backed reads, and an optional AI summary.
3. Support multiple AI providers and user-added providers without code changes.
4. Add a real test suite, linting, and CI.
5. Replace stale docs with accurate setup, configuration, and architecture notes.

## Non-goals

- User authentication, roles, or a hosted multi-user deployment.
- A production database server. SQLite is the local storage layer.
- Live election feeds or scraping. Data still comes from operator-provided CSV files.
- Fabricating official election results. Sample data remains clearly labeled as sample data.
- Rewriting the visual identity. The app keeps the Streamlit look and improves structure.

## Architecture

Target package layout:

```
PH-Election-Dashboard/
  app.py                         # root Streamlit shim, adds src/ to sys.path
  pyproject.toml
  uv.lock
  .env.example
  config/
    config.json
    providers.example.json
  data/
    national_election_results.csv
    local_election_results.csv
    barangay_election_results.csv
    README_DATA.md
  docs/
    geo-data.md
    superpowers/specs/2026-11-01-ph-election-dashboard-finish-design.md
  src/ph_election_dashboard/
    __init__.py
    __main__.py
    app.py                       # Streamlit UI only
    config.py                    # paths, defaults, logging, env access
    data.py                      # load, normalize, validate, source selection
    db.py                        # SQLite schema, seed, rebuild, query
    filters.py                   # ElectionFilters and filter construction
    charts.py                    # Plotly bar, pie, regional, choropleth
    geo.py                       # GeoJSON loading and region alias matching
    ai.py                        # provider registry, prompt building, fallback
    launcher.py                  # streamlit launcher
    geo_data/
      ph_regions.geojson
      ph_island_groups.geojson
  tests/
    conftest.py
    test_config.py
    test_data.py
    test_db.py
    test_filters.py
    test_geo.py
    test_ai.py
    test_app_smoke.py
  .github/workflows/ci.yml
  CONTEXT.md
  THIRD_PARTY_NOTICES.md
```

Responsibilities:

- `config.py`: resolves project root from `pyproject.toml` or `PH_ELECTION_PROJECT_ROOT`,
  exposes paths, default config, and a lazily configured logger. It creates directories only when
  called, not at import time. Tests can override paths with `PH_ELECTION_DATA_DIR`,
  `PH_ELECTION_CONFIG_FILE`, `PH_ELECTION_DB_PATH`, and `PH_ELECTION_LOG_DIR`.
- `data.py`: reads CSV or SQLite, normalizes headers, validates required columns, coerces vote
  counts, and returns a `LoadResult` with `dataframe`, `warnings`, and `errors`.
- `db.py`: owns the SQLite schema and seeding from CSV. It is the only module that writes SQL.
- `filters.py`: holds the selected filter values and applies them to a DataFrame.
- `charts.py`: pure functions that accept DataFrames and return Plotly figures.
- `geo.py`: loads bundled GeoJSON with `importlib.resources`, builds alias lookups, and maps
  region labels to PSGC codes or island-group names.
- `ai.py`: provider definitions, key resolution, prompt creation, HTTP calls, and deterministic
  fallback. It never logs keys.
- `app.py`: composes the UI, owns Streamlit state, and handles display errors.

Data flow:

1. `app.py` resolves config and the selected election type.
2. `data.py` loads from SQLite (default) or CSV. In SQLite mode, `db.py` reseeds when the CSV
   signature changes.
3. `filters.py` applies sidebar selections.
4. `charts.py` renders figures; `geo.py` supplies map geometry.
5. `ai.py` builds a summary from aggregated statistics.

## Data model

Canonical normalized columns:

| Column | Required | Notes |
| --- | --- | --- |
| `position` | yes | Non-empty string |
| `candidate_name` | yes | Non-empty string |
| `total_votes` | yes | Coerced to integer, negatives rejected |
| `party` | no | Blank allowed |
| `region` | no | Region or island-group label |
| `region_focus` | no | Kept for national data compatibility |
| `province` | no | |
| `municipality_city` | no | |
| `barangay` | no | |

Header normalization: lowercase, trim, replace spaces and hyphens with underscores. Aliases:

- `candidate`, `candidate_name`, `name` -> `candidate_name`
- `votes`, `vote_count`, `total_votes` -> `total_votes`
- `municipality`, `city`, `municipality_city` -> `municipality_city`
- `region_focus` remains separate from `region`

Validation behavior:

- Missing required columns are fatal for that election type and surface as a UI error.
- Rows with non-numeric or negative votes are dropped with a warning count.
- Duplicate rows are kept. Deduplication is not safe without a unique key.
- Empty required strings are dropped with a warning count.

SQLite schema (version 1, additive migrations only):

```sql
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS election_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  election_type TEXT NOT NULL,
  position TEXT NOT NULL,
  candidate_name TEXT NOT NULL,
  party TEXT,
  total_votes INTEGER NOT NULL,
  region TEXT,
  region_focus TEXT,
  province TEXT,
  municipality_city TEXT,
  barangay TEXT
);

CREATE INDEX IF NOT EXISTS idx_results_type_position
  ON election_results (election_type, position);
CREATE INDEX IF NOT EXISTS idx_results_type_region
  ON election_results (election_type, region);

CREATE TABLE IF NOT EXISTS source_state (
  election_type TEXT PRIMARY KEY,
  source_path TEXT NOT NULL,
  mtime_ns INTEGER NOT NULL,
  size_bytes INTEGER NOT NULL,
  row_count INTEGER NOT NULL,
  loaded_at TEXT NOT NULL
);
```

`config/config.json` keys:

- `election_year`: displayed in the title.
- `current_election_type`: default election level.
- `data_files`: CSV file name per election level.
- `data_source`: `"sqlite"` (default) or `"csv"`.
- `auto_refresh`: `true` or `false` (default `true`).
- `cache_ttl`: seconds for Streamlit data caching.
- `log_level`: logging level.

Seeding rules:

- Compare `source_state` against the CSV path, mtime, and size.
- On mismatch, delete rows for that election type and insert the normalized rows in one
  transaction.
- A "Rebuild database" action forces reseeding for all election types.
- The database file is `data/election.db` and is git-ignored.

## Filtering

`ElectionFilters` stores the DataFrame and an ordered mapping of column to selected value.

- Filters are generated for each column that exists: `position` always, then `region`,
  `province`, `municipality_city`, `barangay` when present.
- A candidate search box filters on `candidate_name` case-insensitively.
- `"All"` means no restriction.
- The same instance is used to add, display, and apply filters. This fixes the current bug.
- A "Reset filters" button clears selections without clearing the data cache.

## Charts and map

- Bar chart: top 15 candidates for the selected position, colored by party when available.
- Pie chart: party vote share when at least two parties exceed 1 percent of votes.
- Regional summary: total votes per region for local and barangay data.
- Choropleth: aggregate votes by geographic label and render with `plotly.express.choropleth`.
  - Region mode uses `ph_regions.geojson` and `properties.adm1_psgc`.
  - Island-group mode uses `ph_island_groups.geojson` and `properties.island_group`.
  - Alias examples: `NCR`, `Metro Manila` -> National Capital Region; `Region III` ->
    Region III (Central Luzon); `Luzon`, `Visayas`, `Mindanao` -> island groups.
  - The UI offers only map levels with at least one mapped label. Unmapped values are listed in a
    caption so the operator can correct the data.
  - Boundaries are bundled. Attribution: PSA and NAMRIA through OCHA COD-AB, CC BY-IGO.
- CSV export: the filtered table is downloadable as UTF-8 CSV.

## Auto refresh

- A `st.fragment(run_every="3s")` watcher computes a data signature (path, mtime, size).
- When the signature changes, it clears the data cache and calls `st.rerun()`.
- A sidebar toggle enables or disables the watcher. Default: enabled.
- The manual "Refresh data" button remains as a fallback.

## AI providers

Built-in providers:

| Name | Kind | Key variable | Default model |
| --- | --- | --- | --- |
| `gemini` | Gemini REST | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| `openai` | OpenAI-compatible | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `openrouter` | OpenAI-compatible | `OPENROUTER_API_KEY` | `openai/gpt-4o-mini` |
| `groq` | OpenAI-compatible | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `anthropic` | Anthropic Messages | `ANTHROPIC_API_KEY` | `claude-3-5-haiku-latest` |
| `ollama` | OpenAI-compatible | none | `llama3.1` |

Custom providers:

- `config/providers.json` holds a list of provider objects. Each object declares `name`, `kind`
  (`openai`, `anthropic`, or `gemini`), `base_url`, `api_key_env`, `model`, and optional
  `headers`. It references keys by environment variable name only, never by value, so the file is
  safe to commit.
- A session-only "Custom provider" form in the sidebar accepts the same fields plus a password
  input for the key. Session values live in `st.session_state` only and are never written to disk
  or logs.
- `.env` is loaded with `python-dotenv`. `.env.example` lists every supported variable.

Request behavior:

- Use `requests` with a 30 second timeout and no automatic retries.
- Send only aggregated statistics: counts, totals, top candidates, party shares, margins, and
  regional totals. Never send raw personal data.
- On missing key, HTTP error, timeout, or malformed response, render the deterministic fallback
  and a redacted one-line error. Do not raise into the UI.
- Cache the last successful summary in `st.session_state` keyed by provider, model, and filter
  signature.

Deterministic fallback content:

- Election level, position, and location context.
- Top three candidates with party and vote totals.
- Party vote shares above 1 percent.
- Margin and close-race warning when the top two are within 5 percent.
- Number of mapped and unmapped regions.

## Error handling

- Data errors are shown inline with a path and a fix hint.
- Missing optional columns degrade gracefully; missing required columns stop the page with an
  explicit message.
- Chart functions return `None` when data is insufficient; the UI shows a caption instead.
- AI errors never block the page.
- Logs go to `logs/election_dashboard.log`. Logs must not contain API keys, full prompts, or row
  data.

## Testing

Unit tests:

- `test_config.py`: root resolution, env overrides, directory creation, default config merge.
- `test_data.py`: header normalization, aliases, required-column failure, invalid votes, blank
  names, empty files.
- `test_db.py`: first seed, no-op when unchanged, reseed when mtime changes, force rebuild,
  election-type isolation, schema version.
- `test_filters.py`: position and location filters, candidate search, reset, "All" behavior,
  missing columns.
- `test_geo.py`: alias matching for regions and island groups, PSGC code input, unmapped values.
- `test_ai.py`: built-in provider resolution, env key lookup, custom provider parsing, prompt
  contains aggregates and not raw rows, HTTP error fallback, key redaction.
- `test_app_smoke.py`: `streamlit.testing.v1.AppTest` runs the app against temporary data and
  asserts no exceptions, a data table, and working filters.

Commands:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Tooling and CI

- `pyproject.toml`:
  - Python >= 3.10.
  - Dependencies: `pandas`, `streamlit>=1.40`, `plotly`, `python-dotenv`, `requests`.
  - Remove `google-generativeai`.
  - Include package data for the bundled GeoJSON.
  - `[tool.ruff]` line length 88, target py310, rules E, F, I, UP, B.
  - `[tool.pytest.ini_options]` testpaths `tests`.
- CI workflow on push and pull request:
  1. Checkout.
  2. Install Python 3.12 and uv.
  3. `uv sync --extra dev`.
  4. `uv run ruff check .`.
  5. `uv run ruff format --check .`.
  6. `uv run pytest`.

## Documentation

- README: purpose, features, quick start, data schema, AI provider setup, custom providers, map
  attribution, architecture, testing, troubleshooting.
- `.env.example`: provider keys, model overrides, optional path overrides.
- `config/providers.example.json`: a custom OpenAI-compatible provider example.
- `data/README_DATA.md`: canonical schema, aliases, and validation rules.
- `docs/geo-data.md`: source URLs, retrieval date, license, and required attribution.
- `THIRD_PARTY_NOTICES.md`: boundary data attribution.
- `CONTEXT.md`: architecture, commands, decisions, and gotchas.

## Acceptance criteria

1. A clean checkout runs with `uv sync --extra dev` then `uv run streamlit run app.py`.
2. `uv run ph-election-dashboard` also launches the app.
3. Sidebar filters change the table and all charts, including national `region` filtering.
4. The choropleth renders for local and barangay sample data and for national island groups.
5. CSV export downloads exactly the filtered rows.
6. Editing a CSV while auto refresh is on updates the app without a manual refresh.
7. With no AI keys, the deterministic summary renders. With a valid key, the selected provider
   renders a model summary. A custom provider added to `config/providers.json` (referencing an env
   key) and a session-only custom provider both work without code changes.
8. `ruff check`, `ruff format --check`, and `pytest` pass locally and in CI.
9. README, CONTEXT, and data docs match the implementation.
10. `.env`, `data/election.db`, and `logs/` are not committed.

## Risks and mitigations

- Provider model names change. Mitigation: models are editable in the UI and configurable by env.
- GeoJSON labels may not match operator data. Mitigation: alias table, unmapped-value report, and
  a documented schema.
- SQLite adds a moving part. Mitigation: automatic signature-based reseed, a force rebuild action,
  and a CSV fallback via `data_source`.
- Streamlit fragment APIs vary by version. Mitigation: pin `streamlit>=1.40` and test the app with
  `AppTest`.
- Bundled boundaries carry a different license. Mitigation: attribution files and README notice.

## Attribution

Boundary data: Philippine Statistics Authority (PSA) and National Mapping and Resource Information
Authority (NAMRIA), distributed through OCHA's Philippines administrative boundaries (COD-AB),
licensed CC BY-IGO. GeoJSON prepared by `faeldon/philippines-json-maps`. The app must display this
attribution anywhere the map is shown.
