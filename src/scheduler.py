from __future__ import annotations

import time
from datetime import datetime
from typing import Iterable

from .pipeline import run_sources


def schedule_in_process(sources: Iterable[str], cron: str | None = None, interval_seconds: int | None = None) -> None:
    """
    Lightweight scheduler: if APScheduler is installed, use it; otherwise fallback to a fixed interval loop.
    - cron: a standard cron expression (uses APScheduler if available)
    - interval_seconds: fallback polling interval (e.g., 86400 for daily)
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger

        if not cron:
            # Default: run daily at 02:00 UTC
            cron = "0 2 * * *"
        sched = BlockingScheduler(timezone="UTC")
        trigger = CronTrigger.from_crontab(cron)
        sched.add_job(lambda: run_sources(sources), trigger=trigger, id="pipeline")
        print(f"Scheduler started with cron '{cron}' (APScheduler)")
        sched.start()
    except Exception as e:  # noqa: BLE001
        if interval_seconds is None:
            interval_seconds = 24 * 60 * 60  # daily
        print(
            f"APScheduler unavailable or failed ({e}). Falling back to fixed interval: {interval_seconds}s",
        )
        while True:
            print(f"[{datetime.utcnow().isoformat()}] Running pipeline...")
            run_sources(sources)
            time.sleep(interval_seconds)

