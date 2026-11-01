# PH Election Dashboard

[![CI](https://github.com/Onehand-Coding/PH-Election-Dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/Onehand-Coding/PH-Election-Dashboard/actions/workflows/ci.yml)

A local Streamlit dashboard for exploring Philippine election sample data. It
provides working filters, interactive charts, regional and island-group maps,
CSV export, data-change auto refresh, a SQLite read cache, and an optional AI
summary that supports multiple providers.

> This project ships fictional sample data. It is not an official COMELEC
> result set.

## Features

- Filter by position, region, province, municipality or city, and barangay.
- Search candidates by name.
- View bar charts, party vote shares, regional totals, and a choropleth map.
- Download the filtered table as CSV.
- Reload automatically when a source CSV changes.
- Read from SQLite by default, with CSV as a fallback source.
- Generate an AI summary with Gemini, OpenAI, OpenRouter, Groq, Anthropic,
  Ollama, or a custom provider.
- Fall back to a deterministic summary when no API key is configured.

## Quick Start

Requirements: Python 3.10+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/Onehand-Coding/PH-Election-Dashboard.git
cd PH-Election-Dashboard
uv sync --extra dev
uv run streamlit run app.py
```

The app opens at <http://localhost:8501>.

You can also launch it through the installed console script:

```bash
uv run ph-election-dashboard
```

## Configuration

`config/config.json` controls the app:

```json
{
  "election_year": 2025,
  "current_election_type": "national",
  "data_files": {
    "national": "national_election_results.csv",
    "local": "local_election_results.csv",
    "barangay": "barangay_election_results.csv"
  },
  "data_source": "sqlite",
  "auto_refresh": true,
  "cache_ttl": 300,
  "log_level": "INFO"
}
```

Set `data_source` to `csv` to bypass SQLite. The SQLite file is created at
`data/election.db` and is rebuilt automatically when a CSV changes. The
"Rebuild database" button forces a full reseed.

### Path overrides

These environment variables are useful for tests and alternate deployments:

- `PH_ELECTION_PROJECT_ROOT`
- `PH_ELECTION_CONFIG_DIR`
- `PH_ELECTION_DATA_DIR`
- `PH_ELECTION_LOG_DIR`
- `PH_ELECTION_CONFIG_FILE`
- `PH_ELECTION_PROVIDERS_FILE`
- `PH_ELECTION_DB_PATH`

## AI Providers

Copy `.env.example` to `.env` and fill in one or more keys:

```bash
cp .env.example .env
```

| Provider | Environment variable | Default model |
| --- | --- | --- |
| Gemini | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| OpenRouter | `OPENROUTER_API_KEY` | `openai/gpt-4o-mini` |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-5-haiku-latest` |
| Ollama | none | `llama3.1` |

Select the provider and model in the sidebar. A session-only key field is
available when you do not want to write the key to `.env`. Keys are never
logged or persisted by the app.

### Custom providers

Copy `config/providers.example.json` to `config/providers.json` and add an
entry. Custom entries reference keys by environment variable name, never by
value:

```json
{
  "providers": [
    {
      "name": "lmstudio",
      "kind": "openai",
      "base_url": "http://localhost:1234/v1",
      "api_key_env": null,
      "model": "local-model"
    }
  ]
}
```

Supported `kind` values: `openai` (any OpenAI-compatible endpoint), `anthropic`,
and `gemini`. The custom form in the sidebar accepts a session-only key.

## Data Schema

CSV headers are normalized to lowercase snake case. These aliases are accepted:

- `Candidate`, `Name` -> `candidate_name`
- `Votes`, `Vote_Count` -> `total_votes`
- `Municipality`, `City` -> `municipality_city`

Required columns: `position`, `candidate_name`, `total_votes`.

Optional columns: `party`, `region`, `region_focus`, `province`,
`municipality_city`, `barangay`.

Rows with non-numeric or negative votes, or blank required text, are dropped
with a warning. See `data/README_DATA.md` for details.

## Map Data

The choropleth uses bundled GeoJSON for the 18 regions and 3 island groups. It
matches labels such as `NCR`, `Metro Manila`, `Region III`, `Region VII`,
`Luzon`, `Visayas`, and `Mindanao`. Unmatched labels are listed below the map.

Boundaries come from the Philippine Statistics Authority (PSA) and the National
Mapping and Resource Information Authority (NAMRIA), distributed through OCHA's
Philippines administrative boundaries (COD-AB) under CC BY-IGO. The GeoJSON was
prepared by `faeldon/philippines-json-maps`. See `docs/geo-data.md` and
`THIRD_PARTY_NOTICES.md`.

## Architecture

```
app.py                              Streamlit entry point
src/ph_election_dashboard/
  app.py                            UI composition
  config.py                         paths, defaults, logging
  data.py                           CSV loading, normalization, validation
  db.py                             SQLite schema and seeding
  filters.py                        filter state and application
  charts.py                         Plotly chart builders
  geo.py                            GeoJSON loading and label aliases
  ai.py                             provider registry and summaries
  geo_data/                         bundled GeoJSON
```

The app loads CSV files, normalizes and validates them, seeds a SQLite cache,
and reads the selected election level from SQLite. Filters and charts operate
on the resulting DataFrame. The AI layer sends only aggregate statistics to the
configured provider.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

CI runs the same commands on push and pull request.

## Troubleshooting

- **No data loaded:** check `data_files` in `config/config.json` and confirm the
  CSV exists under `data/`.
- **Map is empty:** confirm the `region` values match a region or island-group
  name. Unmapped labels are shown below the map.
- **AI summary is deterministic:** no key is configured, or the request failed.
  Check the caption below the summary.
- **Stale data:** leave auto refresh enabled, or press "Rebuild database".

## License

MIT. See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
