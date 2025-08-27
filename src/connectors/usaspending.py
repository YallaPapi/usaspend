from datetime import datetime
from typing import Any, Dict, List

import os
import time

import requests

from ..mappings.usaspending import map_record_to_canonical


BASE_URL = os.environ.get("USASPENDING_BASE", "https://api.usaspending.gov")
SEARCH_PATH = "/api/v2/search/spending_by_award/"


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "usaspend-harvester/0.1",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch USAspending awards within [start_date, end_date] using the public API.
    Paginates through results and maps each record to the canonical event schema.
    """
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    url = BASE_URL.rstrip("/") + SEARCH_PATH

    page = 1
    limit = int(os.environ.get("USASPENDING_PAGE_SIZE", "100"))
    max_pages = int(os.environ.get("USASPENDING_MAX_PAGES", "10"))  # safety bound for MVP
    sleep_s = float(os.environ.get("USASPENDING_PAGE_SLEEP", "0.3"))

    payload: Dict[str, Any] = {
        "filters": {
            "time_period": [{"start_date": start_str, "end_date": end_str}],
            # We can broaden to include all award types; defaults suffice for MVP.
        },
        "limit": limit,
        "page": page,
        "fields": [
            "Award ID",
            "Recipient Name",
            "Recipient UEI",
            "Recipient DUNS",
            "NAICS Code",
            "Award Amount",
            "Action Date",
            "Award Type",
        ],
        "sort": "Action Date",
        "order": "desc",
    }

    results: List[Dict[str, Any]] = []
    for _ in range(max_pages):
        payload["page"] = page
        data = _post_json(url, payload)
        recs = data.get("results") or []
        for rec in recs:
            mapped = map_record_to_canonical(rec)
            # Filter invalid entries lacking a company_name
            if mapped.get("company_name"):
                results.append(mapped)
        meta = data.get("page_metadata") or {}
        has_next = bool(meta.get("hasNext"))
        if not has_next or not recs:
            break
        page += 1
        time.sleep(sleep_s)

    return results
