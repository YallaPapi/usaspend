from datetime import datetime
from typing import Any


def fetch(start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    """
    Stub SEC Form D connector returning sample normalized-like events.
    Real implementation would pull EDGAR bulk/feeds with rate limiting.
    """
    sample = [
        {
            "company_name": "Acme Robotics, Inc.",
            "funding_type": "SEC_FORM_D",
            "funding_amount": 2500000.0,
            "funding_date": end_date.strftime("%Y-%m-%d"),
            "source": "sec",
            "country": "US",
            "industry": "Robotics",
            "identifier": {"CIK": "0000123456"},
            "raw_id": "CIK-0000123456-2024-09-01",
        }
    ]
    return sample

