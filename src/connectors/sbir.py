from datetime import datetime
from typing import Any


def fetch(start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    """
    Stub SBIR/STTR connector returning sample normalized-like events.
    """
    sample = [
        {
            "company_name": "Nova Bio Labs",
            "funding_type": "SBIR_PHASE_1",
            "funding_amount": 150000.0,
            "funding_date": end_date.strftime("%Y-%m-%d"),
            "source": "sbir",
            "country": "US",
            "industry": "Biotech",
            "identifier": {"DUNS": "123456789"},
            "raw_id": "SBIR-2024-0001",
        }
    ]
    return sample

