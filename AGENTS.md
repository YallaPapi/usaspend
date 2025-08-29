# Repository Guidelines

## Project Structure & Module Organization
- `src/`: application code (CLI, pipeline, storage, web UI)
  - `src/connectors/`: data fetchers (e.g., `usaspending.py`)
  - `src/mappings/`: source→canonical mappers
  - Key modules: `pipeline.py`, `storage.py`, `scheduler.py`, `cli.py`, `web.py`
- `tests/`: pytest suite (e.g., `tests/test_usaspending_*`)
- `templates/`: FastAPI/Jinja templates for the UI
- `data/`: local SQLite database (default `data/app.db`)
- `exports/`: generated CSV exports
- `docs/`: project notes and task plans

## Build, Test, and Development Commands
- Install: `pip install -r requirements.txt`
- Run once: `python -m src.cli run --window-years 3`
- Schedule: `python -m src.cli schedule --cron "0 2 * * *"`
- Export CSV: `python -m src.cli export`
- Web UI (dev): `uvicorn src.web:app --reload`
- Tests: `pytest -q`

## Coding Style & Naming Conventions
- Python 3.11+, 4‑space indentation, UTF‑8.
- Modules/files: `lower_snake_case.py`; functions/vars: `snake_case`; classes: `CapWords`.
- Prefer type hints and small, focused functions. Keep I/O at edges.
- Imports ordered: stdlib → third‑party → local.
- Docstrings for public functions; concise comments for non‑obvious logic.

## Testing Guidelines
- Framework: `pytest`. Add tests beside functionality under `tests/`.
- Name tests `test_<area>_<behavior>.py` and functions `test_<case>()`.
- Use fakes/monkeypatching for network calls (see `tests/test_usaspending_fetch.py`).
- Aim for coverage on new code; test both mapping and control flow.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise scope first line (e.g., `Add FastAPI web UI…`).
- Group related changes; avoid mixing refactors with features.
- PRs: clear description, rationale, and screenshots for UI changes; link issues.
- Include run/test instructions for reviewers and any config/env changes.

## Security & Configuration Tips
- Environment: copy `.env.example` to `.env`. Never commit secrets.
- DB path via `DB_PATH`; email alerts use `SMTP_*` and `ALERT_*`.
- External APIs: respect rate limits; tune via `USASPENDING_*` (see `README.md`).
- Keep default SQLite in `data/` out of version control; export data to `exports/`.

