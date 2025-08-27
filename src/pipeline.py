from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from .alerts.email import send_email
from .connectors import CONNECTORS
from .storage import add_funding_event, get_conn, init_db, log_ingest_run, upsert_company


def run_sources(sources: Iterable[str], window_years: int = 3) -> None:
    init_db()
    end = datetime.utcnow().date()
    start = (end.replace(year=end.year - window_years))

    for source in sources:
        run_one_source(source, start, end)


def run_one_source(source: str, start_date, end_date) -> None:
    started = datetime.utcnow().isoformat()
    status = "success"
    fetched = 0
    normalized = 0
    errors = None
    try:
        if source not in CONNECTORS:
            raise ValueError(f"Unknown source: {source}")
        events = CONNECTORS[source](start_date, end_date)
        fetched = len(events)
        with get_conn() as conn:
            for ev in events:
                name = str(ev.get("company_name", "")).strip()
                if not name:
                    continue
                date = str(ev.get("funding_date"))
                country = ev.get("country")
                domain = (ev.get("identifier") or {}).get("domain")
                cid = upsert_company(conn, name=name, country=country, seen_date=date, domain=domain)
                add_funding_event(
                    conn,
                    company_id=cid,
                    funding_type=ev.get("funding_type"),
                    amount=float(ev["funding_amount"]) if ev.get("funding_amount") is not None else None,
                    date=date,
                    source=ev.get("source", source),
                    raw_id=ev.get("raw_id"),
                )
                normalized += 1
    except Exception as e:  # noqa: BLE001
        status = "failed"
        errors = str(e)
    finally:
        finished = datetime.utcnow().isoformat()
        with get_conn() as conn:
            log_ingest_run(
                conn,
                source=source,
                started_at=started,
                finished_at=finished,
                status=status,
                records_fetched=fetched,
                records_normalized=normalized,
                errors=errors,
            )
        if status != "success":
            err = send_email(
                subject=f"Ingest failed: {source}",
                body=f"Source: {source}\nStart: {started}\nEnd: {finished}\nFetched: {fetched}\nNormalized: {normalized}\nErrors: {errors}",
            )
            if err:
                print(err)

