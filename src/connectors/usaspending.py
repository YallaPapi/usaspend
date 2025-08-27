from datetime import datetime
from typing import Any


def fetch(start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    """
    Stub USAspending connector returning sample normalized-like events.
    Real implementation would call /api/v2/search/spending_by_award/ with pagination.
    """
    sample = [
        {
            "company_name": "Acme Robotics, Inc.",
            "funding_type": "US_GRANT",
            "funding_amount": 500000.0,
            "funding_date": end_date.strftime("%Y-%m-%d"),
            "source": "usaspending",
            "country": "US",
            "industry": "Manufacturing",
            "identifier": {"UEI": "UEI-XYZ123"},
            "raw_id": "USASP-1234567",
        },
        {
            "company_name": "Nova Bio Labs",
            "funding_type": "US_CONTRACT",
            "funding_amount": 1250000.0,
            "funding_date": end_date.strftime("%Y-%m-%d"),
            "source": "usaspending",
            "country": "US",
            "industry": "Biotech",
            "identifier": {"UEI": "UEI-ABC987"},
            "raw_id": "USASP-7654321",
        },
    ]
    return sample

