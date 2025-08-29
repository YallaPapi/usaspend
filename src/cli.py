from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import csv

from .pipeline import run_sources
from .scheduler import schedule_in_process
from .storage import fetch_company_events, get_conn, init_db


DEFAULT_SOURCES = ["usaspending"]


def cmd_run(args: argparse.Namespace) -> None:
    sources = args.sources or DEFAULT_SOURCES
    run_sources(sources=sources, window_years=args.window_years)


def cmd_schedule(args: argparse.Namespace) -> None:
    if args.sources:
        sources = [s.strip() for s in args.sources]
    else:
        sources = DEFAULT_SOURCES
    schedule_in_process(sources=sources, cron=args.cron, interval_seconds=args.interval)


def cmd_export(args: argparse.Namespace) -> None:
    init_db()
    with get_conn() as conn:
        rows = fetch_company_events(conn)
    out_dir = Path("exports")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d")
    out_path = out_dir / f"companies_{ts}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["company_name", "country", "domain", "funding_type", "funding_amount", "funding_date", "source"])
        for r in rows:
            writer.writerow([
                r["name"],
                r["country"],
                r["domain"],
                r["funding_type"],
                r["amount"],
                r["date"],
                r["source"],
            ])
    print(f"Export written: {out_path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="funding-harvester", description="Funding Data Harvester CLI")
    sub = p.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run ingestion pipeline once")
    p_run.add_argument("--sources", nargs="*", help=f"Sources to run (default: {','.join(DEFAULT_SOURCES)})")
    p_run.add_argument("--window-years", type=int, default=3, help="Lookback window in years (default: 3)")
    p_run.set_defaults(func=cmd_run)

    p_sched = sub.add_parser("schedule", help="Run pipeline on a schedule")
    p_sched.add_argument("--sources", nargs="*", help=f"Sources to run (default: {','.join(DEFAULT_SOURCES)})")
    p_sched.add_argument("--cron", help="Cron expression (uses APScheduler if installed). Default: '0 2 * * *'")
    p_sched.add_argument("--interval", type=int, help="Fixed interval in seconds (fallback if no APScheduler)")
    p_sched.set_defaults(func=cmd_schedule)

    p_export = sub.add_parser("export", help="Export normalized dataset to CSV")
    p_export.set_defaults(func=cmd_export)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
