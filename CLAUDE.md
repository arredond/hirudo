# CLAUDE.md

## Running Python

Always use `uv run` for Python commands:

```bash
uv run python main.py
uv run python -m pytest etl/tests/
uv run ruff format etl/
uv run ruff check etl/
```

## Code style

- All code, variable names, function names, and docstrings must be in English.
- No private functions (no leading `_`) outside of test files.
- Import submodules directly rather than importing symbols from them:
  ```python
  # good
  from utils import crawl
  crawl.scrape_fixed_points()

  # avoid
  from utils.crawl import scrape_fixed_points
  ```
- No variable aliases for DataFrames — use the original name or reassign in place.
- Prefer `pd.read_json` / `pd.read_csv` over `open` + `json.load` when loading data files into DataFrames.

## ETL / database

- The ETL is a single callable function (`run_etl`) designed to run as a Cloud Run job. Keep it that way.
- It is fine to drop and recreate DB tables entirely on each run. Do not add migration logic or column-mapping tracking tables.
- The geocoding cache is stored in the DB and must be checked before any Google Maps API call to avoid redundant spend. Collect all unique addresses across all address fields first, subtract the cached set, then geocode only the remainder.

## Tests

- Run with `uv run python -m pytest etl/tests/`.
- Mock HTTP calls with `responses` and Google Maps client calls via `mocker.patch("googlemaps.Client", ...)`.
- Private helper functions (e.g. `_make_row`) are acceptable inside test files for simple setup logic.
