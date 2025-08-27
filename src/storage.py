import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DB_PATH = os.environ.get("DB_PATH", str(Path("data") / "app.db"))


def ensure_dirs() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT,
                domain TEXT,
                first_seen TEXT,
                last_seen TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS funding_events (
                id INTEGER PRIMARY KEY,
                company_id INTEGER NOT NULL,
                funding_type TEXT,
                amount REAL,
                date TEXT,
                source TEXT,
                raw_id TEXT,
                FOREIGN KEY(company_id) REFERENCES companies(id)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_ingest (
                id INTEGER PRIMARY KEY,
                source TEXT,
                raw TEXT,
                ingested_at TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ingest_runs (
                id INTEGER PRIMARY KEY,
                source TEXT,
                started_at TEXT,
                finished_at TEXT,
                status TEXT,
                records_fetched INTEGER,
                records_normalized INTEGER,
                errors TEXT
            );
            """
        )


def upsert_company(conn: sqlite3.Connection, name: str, country: str | None, seen_date: str, domain: str | None = None) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, first_seen, last_seen FROM companies WHERE name = ? AND ifnull(country,'') = ifnull(?, '')",
        (name, country),
    )
    row = cur.fetchone()
    if row:
        first_seen = row["first_seen"] or seen_date
        last_seen = row["last_seen"] or seen_date
        if seen_date < first_seen:
            first_seen = seen_date
        if seen_date > last_seen:
            last_seen = seen_date
        cur.execute(
            "UPDATE companies SET domain = ifnull(domain, ?), first_seen = ?, last_seen = ? WHERE id = ?",
            (domain, first_seen, last_seen, row["id"]),
        )
        return int(row["id"])
    cur.execute(
        "INSERT INTO companies (name, country, domain, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
        (name, country, domain, seen_date, seen_date),
    )
    return int(cur.lastrowid)


def add_funding_event(
    conn: sqlite3.Connection,
    company_id: int,
    funding_type: str | None,
    amount: float | None,
    date: str,
    source: str,
    raw_id: str | None,
) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO funding_events (company_id, funding_type, amount, date, source, raw_id) VALUES (?, ?, ?, ?, ?, ?)",
        (company_id, funding_type, amount, date, source, raw_id),
    )
    return int(cur.lastrowid)


def log_ingest_run(
    conn: sqlite3.Connection,
    source: str,
    started_at: str,
    finished_at: str,
    status: str,
    records_fetched: int,
    records_normalized: int,
    errors: str | None,
) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ingest_runs (source, started_at, finished_at, status, records_fetched, records_normalized, errors)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (source, started_at, finished_at, status, records_fetched, records_normalized, errors),
    )
    return int(cur.lastrowid)


def fetch_company_events(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.id as company_id, c.name, c.country, c.domain, e.funding_type, e.amount, e.date, e.source
        FROM companies c
        JOIN funding_events e ON e.company_id = c.id
        ORDER BY c.name, e.date DESC
        """
    )
    return list(cur.fetchall())

