# Funding Data Harvester (usaspend)

Code-only pipeline to ingest and normalize public funding data (SEC Form D, USAspending, SBIR) and export a deduped company list.

## Quickstart

- Python 3.11+
- Optional: `pip install -r requirements.txt`
- Set env (copy `.env.example` to `.env`). For email alerts, set `SMTP_*` and `ALERT_*`.

Run once:

```
python -m src.cli run
```

Schedule daily (APScheduler):

```
python -m src.cli schedule --cron "0 2 * * *"
```

Export CSV:

```
python -m src.cli export
```

DB is SQLite at `data/app.db` by default. Configure via `DB_PATH`.

Note: `.env` is gitignored; use `.env.example` for structure.

## Structure

- `src/connectors/`: source fetchers (USAspending implemented; SEC/SBIR stubs)
- `src/pipeline.py`: normalize/store/log + email alerts on failure
- `src/scheduler.py`: in-process scheduler (APScheduler or fallback loop)
- `src/storage.py`: SQLite schema and helpers
- `exports/`: CSV outputs
- `data/`: local database

## Config (env)

- Optional USAspending tuning:
  - `USASPENDING_BASE` (default: `https://api.usaspending.gov`)
  - `USASPENDING_PAGE_SIZE` (default: `100`)
  - `USASPENDING_MAX_PAGES` (default: `10` safeguard)
  - `USASPENDING_PAGE_SLEEP` (default: `0.3` seconds between pages)

## Roadmap
See `docs/tasks.md` for the detailed task breakdown and phases.
