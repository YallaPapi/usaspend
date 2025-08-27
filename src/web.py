from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .storage import get_conn, init_db
from .pipeline import run_sources


app = FastAPI(title="usaspend UI")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _start_run_bg(sources: list[str], window_years: int) -> None:
    # Run in a separate thread so the HTTP request returns immediately
    t = threading.Thread(target=run_sources, kwargs={"sources": sources, "window_years": window_years}, daemon=True)
    t.start()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, source: Optional[str] = None, funding_type: Optional[str] = None, q: Optional[str] = None, message: Optional[str] = None):
    # Recent events
    with get_conn() as conn:
        sql = (
            "SELECT c.name, c.country, c.domain, e.funding_type, e.amount, e.date, e.source "
            "FROM companies c JOIN funding_events e ON e.company_id = c.id"
        )
        params: list[object] = []
        where = []
        if source:
            where.append("e.source = ?")
            params.append(source)
        if funding_type:
            where.append("ifnull(e.funding_type,'') = ?")
            params.append(funding_type)
        if q:
            where.append("lower(c.name) LIKE ?")
            params.append(f"%{q.lower()}%")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.date DESC LIMIT 50"
        events = list(conn.execute(sql, params).fetchall())

        runs = list(
            conn.execute(
                "SELECT id, source, started_at, finished_at, status, records_fetched, records_normalized, errors "
                "FROM ingest_runs ORDER BY id DESC LIMIT 20"
            ).fetchall()
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "events": events,
            "runs": runs,
            "filters": {"source": source or "", "funding_type": funding_type or "", "q": q or ""},
            "message": message,
        },
    )


@app.post("/run")
def run_now(sources: str = Form("usaspending"), window_years: int = Form(1)):
    srcs = [s for s in (sources or "").split(",") if s.strip()]
    if not srcs:
        srcs = ["usaspending"]
    _start_run_bg(srcs, window_years)
    return RedirectResponse(url=f"/?message=Started run for {','.join(srcs)}", status_code=303)


# Optional: simple health endpoint
@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

