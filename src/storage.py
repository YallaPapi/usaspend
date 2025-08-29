import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .deduplication import DeduplicationEngine


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
        # Create indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_name_country ON companies(name, country);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_domain ON companies(domain);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_last_seen ON companies(last_seen DESC);")
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
        # Create indexes for funding events
        cur.execute("CREATE INDEX IF NOT EXISTS idx_funding_events_company_date ON funding_events(company_id, date DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_funding_events_source_date ON funding_events(source, date DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_funding_events_amount ON funding_events(amount);")
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
        # Create indexes for ingest runs
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ingest_runs_source_started ON ingest_runs(source, started_at DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ingest_runs_status ON ingest_runs(status);")

        # Enable foreign key constraints and optimizations
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA synchronous = NORMAL;")


def upsert_company(conn: sqlite3.Connection, name: str, country: str | None, seen_date: str, domain: str | None = None, identifiers: dict = None) -> int:
    """
    Upsert company with deduplication support.

    Parameters:
        identifiers: Dict containing UEI, DUNS, CIK, etc. for deduplication
    """
    # Extract identifiers if provided
    identifiers = identifiers or {}

    # First, try to find existing company by identifiers (exact match)
    if identifiers:
        for id_type, id_value in identifiers.items():
            if id_value:
                existing_id = _find_company_by_identifier(conn, id_type, id_value)
                if existing_id:
                    # Update the existing company's metadata
                    _update_company_metadata(conn, existing_id, name, country, seen_date, domain)
                    return existing_id

    # No exact identifier match, try name-based deduplication
    dedup_engine = DeduplicationEngine(conn)
    potential_duplicates = dedup_engine.find_duplicate_candidates(
        name, country, identifiers
    )

    # If we found a high-confidence duplicate, merge with it
    if potential_duplicates and potential_duplicates[0].confidence >= 0.85:  # 85% confidence threshold
        duplicate_id = potential_duplicates[0].company_id
        _update_company_metadata(conn, duplicate_id, name, country, seen_date, domain)
        return duplicate_id

    # No satisfactory match found, create new company
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO companies (name, country, domain, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
        (name, country, domain, seen_date, seen_date),
    )
    return int(cur.lastrowid)


def _find_company_by_identifier(conn: sqlite3.Connection, id_type: str, id_value: str) -> int | None:
    """Find company by identifier (placeholder - would need DB schema enhancement)."""
    # In a production system, we'd store identifiers in a separate table
    # For now, return None (no exact identifier matching)
    return None


def _update_company_metadata(conn: sqlite3.Connection, company_id: int, name: str, country: str | None, seen_date: str, domain: str | None):
    """Update company's metadata and dates."""
    cur = conn.cursor()

    # Get current company data
    cur.execute(
        "SELECT first_seen, last_seen FROM companies WHERE id = ?",
        (company_id,)
    )
    row = cur.fetchone()
    if not row:
        return

    first_seen = row["first_seen"] or seen_date
    last_seen = row["last_seen"] or seen_date

    # Update dates
    if seen_date < first_seen:
        first_seen = seen_date
    if seen_date > last_seen:
        last_seen = seen_date

    cur.execute(
        "UPDATE companies SET name = ?, country = ?, domain = ifnull(domain, ?), first_seen = ?, last_seen = ? WHERE id = ?",
        (name, country, domain, first_seen, last_seen, company_id),
    )


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


def add_raw_ingest(conn: sqlite3.Connection, source: str, raw: str, ingested_at: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO raw_ingest (source, raw, ingested_at) VALUES (?, ?, ?)",
        (source, raw, ingested_at),
    )
    return int(cur.lastrowid)
