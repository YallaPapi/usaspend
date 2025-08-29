"""
Mapping utilities for SEC Form D filings to canonical funding event schema.
"""

from typing import Dict, Any, Optional
from datetime import datetime


def map_form_d_to_canonical(filing_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map SEC Form D filing data to canonical funding event schema.

    Args:
        filing_data: Raw SEC Form D data from EDGAR filing

    Returns:
        Normalized funding event dictionary
    """
    # Extract key fields from Form D filing
    cik = filing_data.get('cik')
    company_name = filing_data.get('company_name', '').strip()
    date_filed = filing_data.get('date_filed', '')

    # Parse filing amount (this would come from the actual form data)
    # Form D has sections for amounts raised
    amount = extract_filing_amount(filing_data)

    # Extract issuer information
    issuer_info = filing_data.get('issuer_info', {})
    industry_code = issuer_info.get('industry_group_type')
    country = 'US'  # SEC filings are US-based by default

    # Convert SIC codes to industry names
    industry = map_sic_to_industry(industry_code)

    return {
        "company_name": company_name,
        "funding_type": "SEC_FORM_D",
        "funding_amount": amount,
        "funding_date": date_filed,  # Use date filed as the event date
        "source": "sec",
        "country": country,
        "industry": industry,
        "identifier": {
            "CIK": cik,
            # Could also include other identifiers if available
        },
        "raw_id": f"CIK-{cik}-{date_filed}" if cik else f"SEC-{date_filed}",
        "additional_data": {
            "sic_code": industry_code,
            "form_type": "D"
        }
    }


def extract_filing_amount(filing_data: Dict[str, Any]) -> Optional[float]:
    """
    Extract the total amount raised from Form D filing data.

    In a real implementation, this would parse the XML or ASCII filing
    to extract the amount fields from the appropriate sections.
    """
    # Placeholder - in production, this would parse actual filing content
    # Form D has fields like:
    # - Total Offering Amount
    # - Amount Sold
    # - Amount Remaining

    amount_fields = ['total_offering_amount', 'amount_sold', 'offering_amount']
    for field in amount_fields:
        amount = filing_data.get(field)
        if amount and isinstance(amount, (int, float)):
            return float(amount)

    # Fallback: try to extract from raw data
    raw_amount = filing_data.get('amount')
    if raw_amount:
        # Clean up amount strings (remove $, commas, etc.)
        if isinstance(raw_amount, str):
            clean_amount = raw_amount.replace('$', '').replace(',', '').strip()
            try:
                return float(clean_amount)
            except ValueError:
                pass

    return None


def map_sic_to_industry(sic_code: Optional[str]) -> Optional[str]:
    """
    Map SIC (Standard Industrial Classification) codes to industry categories.

    This is a simplified mapping - production implementation would use
    the full SIC code database.
    """
    if not sic_code:
        return None

    # Common SIC code ranges
    sic_ranges = {
        ("0100", "0999"): "Agriculture",
        ("1000", "1499"): "Mining",
        ("1500", "1799"): "Construction",
        ("2000", "2399"): "Manufacturing",
        ("2500", "2599"): "Furniture",
        ("2600", "2699"): "Paper",
        ("2700", "2799"): "Publishing",
        ("2800", "2899"): "Chemicals",
        ("3000", "3099"): "Rubber",
        ("3200", "3299"): "Stone",
        ("3300", "3399"): "Primary Metals",
        ("3400", "3499"): "Fabricated Metals",
        ("3500", "3599"): "Industrial Machinery",
        ("3600", "3699"): "Electronic Equipment",
        ("3700", "3799"): "Transportation Equipment",
        ("3800", "3899"): "Measuring Instruments",
        ("3900", "3999"): "Miscellaneous Manufacturing",
        ("4000", "4799"): "Transportation",
        ("4800", "4899"): "Communications",
        ("4900", "4999"): "Utilities",
        ("5000", "5199"): "Wholesale Trade",
        ("5200", "5999"): "Retail Trade",
        ("6000", "6799"): "Finance",
        ("7000", "8999"): "Services",
        ("9000", "9999"): "Public Administration"
    }

    for (min_code, max_code), industry in sic_ranges.items():
        if min_code <= sic_code <= max_code:
            return industry

    return "Other"


def parse_quarterly_index_line(line: str) -> Dict[str, Any]:
    """
    Parse a line from SEC quarterly master index file.

    Format: CIK|Company Name|Form Type|Date Filed|Filename
    """
    parts = line.strip().split('|')
    if len(parts) < 5:
        return {}

    return {
        'cik': parts[0],
        'company_name': parts[1],
        'form_type': parts[2],
        'date_filed': parts[3],
        'filename': parts[4],
        'accession_number': parts[3] if len(parts) > 4 else None
    }


def validate_form_d_data(data: Dict[str, Any]) -> bool:
    """
    Validate that required fields are present for a Form D filing.
    """
    required_fields = ['company_name', 'date_filed']
    return all(data.get(field) for field in required_fields)