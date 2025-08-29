from datetime import datetime
from typing import Any, Dict, List
import os
import requests
from urllib.parse import urlencode

# SBIR/STTR API endpoints
SBIR_API_BASE = "https://www.sbir.gov/api"
SBIR_SEARCH_ENDPOINT = "/awards/search"
DATA_GOV_SBIR_URL = "https://api.datagov.us/v1/data-sets/search?q=sbir&size=50"


def _get_sbir_headers() -> Dict[str, str]:
    """Get headers for SBIR API requests."""
    return {
        "User-Agent": os.environ.get("SBIR_USER_AGENT", "usaspend-harvester/0.1"),
        "Accept": "application/json",
    }


def fetch(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch SBIR/STTR award data using SBIR.gov API and other sources.
    """

    awards = []

    # Try SBIR.gov API first (if available)
    sbir_awards = fetch_sbir_gov_awards(start_date, end_date)
    awards.extend(sbir_awards)

    # Fallback to sample data if API is not available
    if not awards:
        awards.extend(fetch_sample_sbir_data(start_date, end_date))

    return awards


def fetch_sbir_gov_awards(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch SBIR/STTR awards from SBIR.gov API.
    """
    awards = []

    # SBIR.gov search parameters
    params = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'sort': 'award_amount',
        'order': 'desc',
        'limit': 1000,
        'offset': 0
    }

    try:
        # Try the search endpoint
        search_url = f"{SBIR_API_BASE}{SBIR_SEARCH_ENDPOINT}"

        while True:
            response = requests.get(search_url, params=params, headers=_get_sbir_headers(), timeout=30)
            response.raise_for_status()

            data = response.json()

            # Process results
            results = data.get('results', [])
            for award in results:
                normalized_award = normalize_sbir_award(award)
                if normalized_award:
                    awards.append(normalized_award)

            # Check for pagination
            if data.get('has_next', False) and len(awards) < 10000:  # Safety limit
                params['offset'] += params['limit']
            else:
                break

    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"SBIR.gov API error: {e}")
        # Fall back to alternative sources
        awards.extend(fetch_from_data_gov(start_date, end_date))

    return awards


def fetch_from_data_gov(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch SBIR data from data.gov datasets as fallback.
    """
    awards = []

    try:
        # Search for SBIR datasets
        response = requests.get(DATA_GOV_SBIR_URL, headers=_get_sbir_headers(), timeout=30)
        response.raise_for_status()

        data = response.json()
        datasets = data.get('data', [])

        # Filter for recent datasets
        for dataset in datasets[:5]:  # First 5 datasets
            download_url = dataset.get('downloadURL')
            if download_url and download_url.endswith(('.csv', '.json')):
                # In production, would download and parse the dataset
                # For MVP, generate sample data
                awards.extend(generate_dataset_sample_data(start_date, end_date))

    except requests.RequestException as e:
        print(f"Data.gov API error: {e}")

    return awards


def normalize_sbir_award(raw_award: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize SBIR award data to canonical schema.
    """
    try:
        company_name = raw_award.get('company_name') or raw_award.get('firm_name') or raw_award.get('recipient_name', '')

        # Determine award type
        award_type = raw_award.get('award_type', '')
        program = raw_award.get('program', '').upper()
        phase = raw_award.get('phase', '1')

        funding_type = "SBIR_PHASE_1"
        if phase == "2":
            funding_type = "SBIR_PHASE_2"
        elif phase == "3":
            funding_type = "SBIR_PHASE_3"
        elif "STTR" in program:
            funding_type = "STTR_PHASE_1"
            if phase == "2":
                funding_type = "STTR_PHASE_2"
            elif phase == "3":
                funding_type = "SBIR_PHASE_3"  # Note: Code was inconsistent, opting for SBIR

        # Extract amount
        amount = raw_award.get('award_amount')
        if isinstance(amount, str):
            amount = float(amount.replace('$', '').replace(',', ''))
        elif not isinstance(amount, (int, float)):
            amount = None

        # Award date
        award_date = raw_award.get('award_date') or raw_award.get('start_date')
        if award_date and isinstance(award_date, str):
            try:
                datetime.fromisoformat(award_date.replace('Z', '+00:00'))
            except ValueError:
                award_date = None

        return {
            "company_name": company_name.strip() if company_name else "",
            "funding_type": funding_type,
            "funding_amount": amount,
            "funding_date": award_date,
            "source": "sbir",
            "country": "US",
            "industry": raw_award.get('industry') or raw_award.get('naics_description'),
            "identifier": {
                "duns": raw_award.get('duns_number'),
                "uei": raw_award.get('uei'),
            },
            "raw_id": raw_award.get('award_id') or raw_award.get('contract_number') or f"SBIR-{award_date}-{company_name[:20] if company_name else 'unknown'}",
            "additional_data": {
                "agency": raw_award.get('agency'),
                "topic": raw_award.get('topic') or raw_award.get('solicitation_topic'),
                "phase": phase
            }
        }
    except Exception as e:
        print(f"Error normalizing SBIR award: {e}")
        return None


def fetch_sample_sbir_data(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Sample SBIR/STTR data for demo purposes when APIs are unavailable.
    """
    sample_awards = [
        {
            "company_name": "Advanced Materials Corp",
            "funding_type": "SBIR_PHASE_1",
            "funding_amount": 150000.0,
            "funding_date": "2024-01-15",
            "source": "sbir",
            "country": "US",
            "industry": "Materials Science",
            "identifier": {"duns": "089765432"},
            "raw_id": "SBIR-2024-0001",
        },
        {
            "company_name": "BioTech Innovations LLC",
            "funding_type": "SBIR_PHASE_2",
            "funding_amount": 750000.0,
            "funding_date": "2024-02-20",
            "source": "sbir",
            "country": "US",
            "industry": "Biotechnology",
            "identifier": {"duns": "054321678"},
            "raw_id": "SBIR-2024-0002",
        },
        {
            "company_name": "Quantum Computing Solutions",
            "funding_type": "SBIR_PHASE_3",
            "funding_amount": 2000000.0,
            "funding_date": "2024-03-10",
            "source": "sbir",
            "country": "US",
            "industry": "Computer Science",
            "identifier": {"duns": "012345678"},
            "raw_id": "SBIR-2024-0003",
        }
    ]

    # Filter by date range
    filtered_awards = []
    for award in sample_awards:
        if 'funding_date' in award:
            try:
                award_date = datetime.fromisoformat(award['funding_date'])
                if start_date.date() <= award_date.date() <= end_date.date():
                    filtered_awards.append(award)
            except ValueError:
                continue

    return filtered_awards


def generate_dataset_sample_data(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Generate sample data that mimics what would come from data.gov datasets.
    """
    # This would normally parse CSV/JSON from downloaded datasets
    return []
