# Funding Data Harvester — Task Breakdown

This plan translates the PRD into concrete, verifiable tasks to reach a working MVP and beyond.

## Phase 1 — MVP (SEC Form D, USAspending, SBIR)

- Repo bootstrap:
  - Initialize Python project layout (`src/`), `pyproject.toml` or `requirements.txt`.
  - Add Dockerfiles and `docker-compose.yml` for API + Postgres.
  - Configure linting/formatting (ruff/black) and basic CI workflow.
  - Acceptance: repo builds locally and via `docker compose up`.

- Data model (PostgreSQL):
  - Tables: `companies`, `funding_events`, `sources`, `identifiers`, `raw_ingest` (JSON), `ingest_runs`.
  - Columns align to unified schema: `company_name`, `funding_type`, `funding_amount`, `funding_date`, `source`, `country`, `industry`, `identifier` (UEI/DUNS/CIK/domain), `first_seen`, `last_seen`.
  - Add indices on identifiers and (`company_name`, `country`).
  - Acceptance: migrations apply; sample inserts/query round-trip.

- Unified schema + mapping:
  - Define canonical schema and per-source field maps in code (`src/schema.py`, `src/mappings/`).
  - Acceptance: unit tests validate mapping of 10+ realistic fixtures per source.

- Ingestion connectors:
  - SEC EDGAR Form D
    - Implement fetch (bulk dataset or feed) with rate limiting (<= 10 rps).
    - Parse fields: issuer name, first sale date, amount, SIC, location, CIK.
    - Store raw payloads in `raw_ingest`, normalized rows in staging table.
    - Acceptance: backfill last 3 years completes; >= 95% records parsed.
  - USAspending.gov
    - Implement POST to `/api/v2/search/spending_by_award/` filtering `action_date >= today-3y` with pagination.
    - Extract: recipient name, UEI/DUNS, NAICS, description, award amount, agency, action date.
    - Acceptance: robust pagination; >= 95% success rate; stores raw + normalized.
  - SBIR/STTR
    - Implement ingestion from public SBIR/STTR datasets/API (open data portal).
    - Map to unified schema: awardee, program, phase, amount, date.
    - Acceptance: last 3 years ingested with mapping coverage documented.

- Normalization & cleaning:
  - Standardize text casing, whitespace, punctuation; country/industry code normalization.
  - Implement date parsing; currency normalization to USD (store original + normalized).
  - Acceptance: transformation functions covered by unit tests; QA spot checks pass.

- Deduplication & entity resolution:
  - Exact match: link by UEI/DUNS/CIK when present.
  - Heuristic: `company_name + country (+ domain if present)`, with similarity threshold.
  - Maintain `first_seen`/`last_seen`; merge funding events under unified company.
  - Optional: prepare for pgvector but not required in MVP.
  - Acceptance: duplicate rate reduced by >= 80% on validation sample.

- Orchestration (MVP, code-only):
  - Provide a Python CLI (`src/cli.py`) to run connectors sequentially or in limited parallel, with a date window arg (default 3y).
  - Use APScheduler in-process for periodic runs by default; document system cron as an alternative.
  - Implement retries with exponential backoff and per-source rate limits.
  - Record `ingest_runs` metadata: start/end, counts, errors, durations.
  - Acceptance: single command/scheduled job runs full pipeline end-to-end.

- Exports:
  - Implement CSV export (`exports/companies_YYYYMMDD.csv`) with canonical columns.
  - Acceptance: export finishes < 10 minutes on representative sample; file opens in Excel.

- Basic query surface:
  - Minimal FastAPI/Flask endpoint for filtering by industry, funding type, country.
  - Acceptance: endpoint returns paginated results from normalized tables.

- Observability:
  - Structured logging, per-source counts, error capture.
  - Summary report at end of run (total ingested, normalized, deduped, exported).

- QA & validation:
  - Build small golden datasets for each source; write unit tests for mapping and dedup.
  - Smoke test script to run pipeline on limited date range.

## Phase 2 — EU CORDIS + RSS feeds + Orchestration Hardening (code-only)

- EU CORDIS ingestion:
  - Implement dataset/API pull for projects with funding in last 3 years.
  - Map organization entities to unified schema.
  - Acceptance: backfill completes; coverage documented.

- RSS/news feeds:
  - Configure curated feeds; fetch & parse entries.
  - NER/company extraction (spaCy) + heuristic linking to companies.
  - Acceptance: precision/recall measured on a labeled sample.

- Code-based orchestration hardening:
  - Promote scheduler to handle per-source DAGs with dependencies and isolated failure domains.
  - Add email alerting (SMTP) on failures or threshold breaches (no Slack requirement).
  - Ensure idempotency of reruns (use run IDs, checkpoints, upserts).
  - Add metrics endpoint or logs for run health; optional Prometheus scraping.
  - Acceptance: scheduled runs are reliable; failures alert via email; safe reruns.

- Optional fuzzy matching improvements:
  - Integrate pgvector or rapidfuzz for better name matching.
  - Acceptance: measurable duplicate reduction vs. MVP.

## Phase 3 — Enrichment

- Domain discovery:
  - Infer company domains from names via public sources (e.g., Clearbit alternatives or web search with caching, OSS-only where feasible).
  - Acceptance: >= 60% domain resolution on sample.

- Contact hooks:
  - Generate export format compatible with Apollo/LinkedIn tooling.
  - Acceptance: downstream import tested successfully.

## Cross-Cutting Tasks

- Security & compliance:
  - Ensure only public/open sources used; add robots/respectful crawling.
  - Document attribution where required.

- Performance:
  - Batch inserts; pagination concurrency with backoff; finish < 10 minutes per full run on target infra.

- Documentation:
  - `README` with setup, env vars, run commands.
  - `docs/architecture.md` diagram of pipeline and tables.
  - Per-source notes in `docs/sources/`.

- Alerts (email):
  - Implement SMTP-based email notifications for failed runs or anomaly thresholds.
  - Env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_FROM`, `ALERT_TO` (comma-separated), `ALERT_MIN_SEVERITY`.
  - Include run summary and error excerpts in the message body; attach log snippet if small.
  - Acceptance: forcing a connector error triggers a test email to `ALERT_TO`.

## Acceptance Criteria Recap (MVP)

- Coverage: >= 95% of official datasets over last 3 years.
- Dedup efficacy: duplicates reduced by >= 80% on validation set.
- Scale: export contains 20k+ unique companies from last 3 years.
- Runtime: full end-to-end run < 10 minutes.
