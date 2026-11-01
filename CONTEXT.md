# Project Context

## Purpose

A local Streamlit dashboard for exploring fictional Philippine election sample
data. It is a demo and portfolio project, not an official results system.

## Architecture

- `app.py` is a Streamlit shim that adds `src/` to `sys.path`.
- `src/ph_election_dashboard/app.py` composes the UI.
- `config.py` owns paths, defaults, and logging.
- `data.py` owns CSV loading, normalization, and validation.
- `db.py` owns the SQLite schema and seeding.
- `filters.py` owns filter state and application.
- `charts.py` owns Plotly chart builders.
- `geo.py` owns GeoJSON loading and label aliases.
- `ai.py` owns provider definitions, prompts, HTTP calls, and fallback.
- `geo_data/` holds the bundled GeoJSON boundary files.

## Data Flow

CSV -> normalization and validation -> SQLite seed/read -> filters -> charts,
tables, maps, and AI summary. CSV remains the source of truth. SQLite is a local
read cache keyed by file path, mtime, and size.

## Commands

```bash
uv sync --extra dev
uv run streamlit run app.py
uv run ph-election-dashboard
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Decisions

- Keep a local-demo scope. No auth, roles, or hosted multi-user deployment.
- Use SQLite instead of a database server so a clean checkout needs no services.
- Bundle GeoJSON so maps work offline.
- Support any OpenAI-compatible endpoint for provider flexibility. Add native
  Gemini and Anthropic adapters.
- Never persist provider keys. Read them from environment variables or a
  session-only password field.
- Keep CSV as the source of truth so operators can edit files by hand.

## Gotchas

- Streamlit runs `app.py` as a script, so use absolute package imports, not
  relative imports.
- `st.cache_data` must be cleared when the data signature changes.
- `st.fragment` is used for auto refresh. Tests set `auto_refresh` to `false`.
- The GeoJSON feature `id` is set to the PSGC code or island-group name at load
  time so Plotly can match locations.
- The bundled data package is named `geo_data`, not `data`, to avoid shadowing
  the `data.py` module.
- Boundary files carry CC BY-IGO attribution requirements.

## Known Limitations

- Sample data is fictional and small.
- SQLite has no concurrent-writer story beyond Streamlit's single-process use.
- AI providers can change model names. Models are editable in the UI.
