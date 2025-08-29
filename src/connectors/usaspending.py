from datetime import datetime
from typing import Any, Dict, List

import os
import time

import requests

from ..mappings.usaspending import map_record_to_canonical
from ..storage import get_conn, add_raw_ingest
from datetime import datetime as _dt


BASE_URL = os.environ.get("USASPENDING_BASE", "https://api.usaspending.gov")
SEARCH_PATH = "/api/v2/search/spending_by_award/"
PAGE_SIZE = int(os.environ.get("USASPENDING_PAGE_SIZE", "100"))
MAX_PAGES = int(os.environ.get("USASPENDING_MAX_PAGES", "10"))
PAGE_SLEEP = float(os.environ.get("USASPENDING_PAGE_SLEEP", "0.3"))
RETRIES = int(os.environ.get("USASPENDING_RETRIES", "3"))
BACKOFF = float(os.environ.get("USASPENDING_BACKOFF", "0.5"))


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "usaspend-harvester/0.1",
    }
    last_err: Exception | None = None
    for attempt in range(1, max(1, RETRIES) + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt >= max(1, RETRIES):
                break
            time.sleep(BACKOFF * (2 ** (attempt - 1)))
    raise last_err  # type: ignore[misc]


def fetch(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch USAspending awards within [start_date, end_date] using the public API.
    Paginates until page_metadata.hasNext is False or MAX_PAGES reached.
    """
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    url = BASE_URL.rstrip("/") + SEARCH_PATH

    page = 1
    results: List[Dict[str, Any]] = []

    contracts_fields = [
        "Award ID",
        "Recipient Name",
        "Award Type",
        "Recipient UEI",
        "Recipient DUNS Number",
        "naics_code",
        "Base Obligation Date",
        "Last Modified Date",
        "obligation",
        "total_obligation",
    ]
    grants_fields = [
        "Award ID",
        "Recipient Name",
        "Award Type",
        "Recipient UEI",
        "Recipient DUNS",
        "NAICS Code",
        "Action Date",
        "Last Modified Date",
        "obligation",
        "total_obligation",
    ]

    groups = [
        ( ["A", "B", "C", "D"], contracts_fields, "Last Modified Date" ),
        ( ["02", "03", "04", "05"], grants_fields, "Action Date" ),
    ]

    for award_type_codes, fields, sort_field in groups:
        group_name = "contracts" if award_type_codes == ["A","B","C","D"] else "grants"
        print(f"[usaspending] Group={group_name} sort='{sort_field}' starting…")
        page = 1
        while page <= MAX_PAGES:
            payload: Dict[str, Any] = {
                "fields": fields,
                "filters": {
                    "time_period": [{"start_date": start_str, "end_date": end_str}],
                    "date_type": "action_date",
                    "award_type_codes": award_type_codes,
                },
                "limit": PAGE_SIZE,
                "page": page,
                "sort": sort_field,
                "order": "desc",
            }

            data = _post_json(url, payload)
            # Persist raw page for traceability (MVP)
        try:
            import json as _json
            with get_conn() as _conn:
                add_raw_ingest(
                    _conn,
                    source="usaspending",
                    raw=_json.dumps(data, ensure_ascii=False),
                    ingested_at=_dt.utcnow().isoformat(),
                )
        except Exception:
            # Non-fatal if raw logging fails
            pass
        recs = data.get("results", [])
        print(f"[usaspending] Group={group_name} page={page} received={len(recs)}")
        for rec in recs:
            mapped = map_record_to_canonical(rec)
            if mapped and mapped.get("company_name"):
                results.append(mapped)

            meta = data.get("page_metadata") or {}
            has_next = bool(meta.get("hasNext"))
            if not has_next:
                print(f"[usaspending] Group={group_name} reached last page at page={page}")
                break
            page += 1
            if PAGE_SLEEP > 0:
                time.sleep(PAGE_SLEEP)
        print(f"[usaspending] Group={group_name} done. total_so_far={len(results)}")

    return results
