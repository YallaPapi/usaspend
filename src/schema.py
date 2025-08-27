from __future__ import annotations

from datetime import datetime, date
from typing import Any, Optional


def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def normalize_date(value: Any) -> Optional[str]:
    """
    Normalize various date inputs to ISO date string (YYYY-MM-DD).
    Accepts datetime/date/str; returns None if not parseable.
    """
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if not s:
        return None
    # Try common formats
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    # Last resort: if already looks like YYYY-MM-DD
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def canonical_event(
    company_name: str,
    funding_type: Optional[str],
    funding_amount: Optional[float],
    funding_date: Any,
    source: str,
    country: Optional[str] = None,
    industry: Optional[str] = None,
    identifier: Optional[dict[str, Any]] = None,
    raw_id: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "company_name": normalize_text(company_name) or "",
        "funding_type": normalize_text(funding_type),
        "funding_amount": float(funding_amount) if funding_amount is not None else None,
        "funding_date": normalize_date(funding_date),
        "source": source,
        "country": normalize_text(country),
        "industry": normalize_text(industry),
        "identifier": identifier or {},
        "raw_id": normalize_text(raw_id),
    }


__all__ = [
    "normalize_text",
    "normalize_date",
    "canonical_event",
]

