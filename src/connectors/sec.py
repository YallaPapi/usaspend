from datetime import datetime
from typing import Any, Dict, List
import os
import time
import gzip
import zipfile
import tempfile
import requests
from pathlib import Path

# SEC EDGAR API endpoints
EDGAR_BASE = "https://www.sec.gov"
FORM_D_BULK_URL = "https://www.sec.gov/Archives/edgar/daily-index"
QUARTERLY_INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index"
MASTERS_PATH = "Archives/edgar/daily-index/master.{}.idx"
RSS_FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=D&owner=exclude&count=100"


def _get_user_agent() -> str:
    """Get SEC-compliant user agent string."""
    return os.environ.get("SEC_USER_AGENT", "usaspend-harvester/0.1 (mailto:contact@example.com)")


def _download_file(url: str, filepath: Path) -> bool:
    """Download file with SEC-compliant headers."""
    headers = {
        "User-Agent": _get_user_agent(),
        "Accept": "text/plain,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return False


def fetch(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch SEC Form D filings using EDGAR daily index files and parse key data.
    This implementation uses the quarterly bulk data feeds for efficiency.

    For production, this would need to:
    1. Download quarterly index files
    2. Parse master.idx for Form D filings
    3. Download and parse individual filings
    """

    results = []

    # For MVP demo, return sample data with realistic structure
    # TODO: Implement actual bulk data feed parsing
    sample_filings = [
        {
            "company_name": "TechNova Ventures LLC",
            "funding_type": "SEC_FORM_D",
            "funding_amount": 2500000.0,
            "funding_date": "2024-02-15",
            "source": "sec",
            "country": "US",
            "industry": "Technology",
            "identifier": {"CIK": "0001892398"},
            "raw_id": "CIK-0001892398-2024-00123456",
        },
        {
            "company_name": "GreenEnergy Solutions Inc",
            "funding_type": "SEC_FORM_D",
            "funding_amount": 7500000.0,
            "funding_date": "2024-03-22",
            "source": "sec",
            "country": "US",
            "industry": "Energy",
            "identifier": {"CIK": "0001678432"},
            "raw_id": "CIK-0001678432-2024-00567890",
        },
        {
            "company_name": "BioLife Therapeutics Ltd",
            "funding_type": "SEC_FORM_D",
            "funding_amount": 12000000.0,
            "funding_date": "2024-01-10",
            "source": "sec",
            "country": "US",
            "industry": "Healthcare",
            "identifier": {"CIK": "0001345678"},
            "raw_id": "CIK-0001345678-2024-00987654",
        }
    ]

    # Filter by date range (in real implementation, this would come from the data)
    for filing in sample_filings:
        filing_date = datetime.fromisoformat(filing["funding_date"])
        if start_date.date() <= filing_date.date() <= end_date.date():
            results.append(filing)

    return results


def fetch_bulk_quarterly(year: int, quarter: int) -> List[Dict[str, Any]]:
    """
    Fetch Form D data from SEC quarterly bulk data feeds.
    This is the production implementation that would replace the sample data above.

    Args:
        year: 4-digit year
        quarter: Quarter (1-4)

    Returns:
        List of normalized Form D events
    """
    # SEC quarterly index files are available at:
    # https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/master.idx

    master_url = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/master.idx"
    data_dir = Path("data/sec_cache")
    data_dir.mkdir(parents=True, exist_ok=True)

    master_file = data_dir / f"master_{year}_Q{quarter}.idx"

    # Download quarterly master index
    if not _download_file(master_url, master_file):
        print(f"Failed to download {master_url}")
        return []

    # Parse master index for Form D filings
    form_d_filings = []
    with open(master_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # Skip header lines (usually 10-12 lines)
    data_lines = lines[11:]  # Adjust based on actual file format

    for line in data_lines:
        parts = line.strip().split('|')
        if len(parts) >= 4:
            cik, company_name, form_type, date_filed, filename = parts[:5]
            if form_type == 'D':  # Form D filing
                form_d_filings.append({
                    'cik': cik,
                    'company_name': company_name.strip(),
                    'date_filed': date_filed,
                    'filename': filename
                })

    # In production, you would download and parse each Form D filing here
    # For now, return structured data similar to sample
    results = []
    for filing in form_d_filings[:20]:  # Limit for test runs
        # Parse actual filing would extract amount, date, etc. from XML/ASCII
        results.append({
            "company_name": filing['company_name'],
            "funding_type": "SEC_FORM_D",
            "funding_amount": None,  # Would be extracted from filing
            "funding_date": filing['date_filed'],
            "source": "sec",
            "country": "US",
            "industry": None,
            "identifier": {"CIK": filing['cik']},
            "raw_id": f"CIK-{filing['cik']}-{filing['date_filed']}",
        })

    return results
