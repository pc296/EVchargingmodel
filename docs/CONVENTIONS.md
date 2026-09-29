# CONVENTIONS
Purpose: single source of truth for how code in this repo is written.
Last updated: 2026-09-28

## Language and tools
- Python 3.11+ (Streamlit Cloud default). R 4.x for `R/` only.
- Format and lint with `ruff` (line length 100). Type hints on public functions.

## Layout
- `src/evcharge/` library code, importable, no side effects on import.
- `scripts/` entry points only. `tests/` mirrors module names. `R/` for R scripts.
- `data/raw/` is read-only input. `data/processed/` is generated; never hand-edit.
- `streamlit_app.py` at repo root (Streamlit Cloud entry point).

## Naming
- snake_case for functions, columns and files. Column units in names where ambiguous (`dist_dcfc_mi`, `price_c_per_kwh`).
- County key is always `fips` as a 5-character zero-padded string. Year column is `year` (int).

## Data rules
- Always: keep structural zeros (no freeway = 0 miles) distinct from missing values; add an `_imputed` flag column for any imputed value.
- Always: features for year t use only information available at end of year t. Labels use t+1.
- Never: random train/test splits on panel data. Split by time.
- Never: hardcode a number in the app that is not traceable to DATA_SOURCES.md or METHODOLOGY.md.

## Error handling
- Loaders validate expected columns and raise `ValueError` with the file name and missing columns.
- Joins assert expected row counts; unexpected drops raise, not warn.

## Commits
- Conventional commits: `feat:`, `fix:`, `data:`, `docs:`, `test:`, `refactor:`, `chore:`. Imperative mood, under 72 characters in the subject.

## Writing (docs and app text)
- Plain language, no em dashes, no superlatives. Flag uncertainty and assumptions explicitly.
