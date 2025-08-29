"""
Mapping utilities for SBIR/STTR awards to canonical funding event schema.
"""

from typing import Dict, Any, Optional
from datetime import datetime


def map_sbir_award_to_canonical(award_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map SBIR/STTR award data to canonical funding event schema.

    Args:
        award_data: Raw SBIR award data from API

    Returns:
        Normalized funding event dictionary
    """
    # Extract company/recipient name
    company_name = (
        award_data.get('company_name') or
        award_data.get('firm_name') or
        award_data.get('recipient_name') or
        award_data.get('awardee_name') or
        ''
    ).strip()

    # Determine funding type and phase
    award_type = award_data.get('award_type', '')
    program = award_data.get('program', '').upper()
    phase = str(award_data.get('phase', '1'))

    # Categorize funding type
    funding_type = classify_sbir_funding_type(program, phase, award_type)

    # Extract amount
    amount = extract_award_amount(award_data)

    # Award date - try multiple possible date fields
    funding_date = extract_award_date(award_data)

    # Industry classification from NAICS or other codes
    industry = extract_industry_from_codes(award_data)

    # Identifiers
    identifiers = extract_identifiers(award_data)

    return {
        "company_name": company_name,
        "funding_type": funding_type,
        "funding_amount": amount,
        "funding_date": funding_date,
        "source": "sbir",
        "country": "US",  # SBIR awards are US-based by default
        "industry": industry,
        "identifier": identifiers,
        "raw_id": generate_raw_id(award_data, company_name),
        "additional_data": {
            "agency": award_data.get('agency') or award_data.get('funding_agency'),
            "topic": award_data.get('topic') or award_data.get('solicitation_topic'),
            "phase": phase,
            "program": program,
            "sbir_table": extract_sbir_table_info(award_data)
        }
    }


def classify_sbir_funding_type(program: str, phase: str, award_type: str) -> str:
    """
    Classify the SBIR funding type based on program and phase information.
    """
    program_upper = program.upper()

    # Determine if STTR or SBIR
    if 'STTR' in program_upper:
        base_type = 'STTR'
    else:
        base_type = 'SBIR'

    # Map phase to suffix
    phase_suffixes = {
        '1': '_PHASE_1',
        '2': '_PHASE_2',
        '3': '_PHASE_3',
        'I': '_PHASE_1',   # Alternative phase notations
        'II': '_PHASE_2',
        'III': '_PHASE_3'
    }

    suffix = phase_suffixes.get(phase, '_PHASE_1')

    return f"{base_type}{suffix}"


def extract_award_amount(award_data: Dict[str, Any]) -> Optional[float]:
    """
    Extract and normalize the award amount.
    """
    amount_fields = [
        'award_amount', 'amount', 'total_award_amount',
        'funding_amount', 'obligation_amount', 'awarded_amount'
    ]

    for field in amount_fields:
        amount = award_data.get(field)
        if amount is not None:
            if isinstance(amount, str):
                # Clean up currency strings
                amount = amount.replace('$', '').replace(',', '').replace(' ', '')
                try:
                    return float(amount)
                except ValueError:
                    continue
            elif isinstance(amount, (int, float)):
                return float(amount)

    return None


def extract_award_date(award_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract the award announcement or start date.
    """
    date_fields = [
        'award_date', 'start_date', 'funding_date', 'announced_date',
        'effective_date', 'date_awarded', 'award_announcement_date'
    ]

    for field in date_fields:
        date_value = award_data.get(field)
        if date_value:
            if isinstance(date_value, str):
                try:
                    # Try to normalize date format
                    if 'T' in date_value:
                        parsed = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                    else:
                        parsed = datetime.strptime(date_value, '%Y-%m-%d')
                    return parsed.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    continue
            elif isinstance(date_value, datetime):
                return date_value.strftime('%Y-%m-%d')

    return None


def extract_industry_from_codes(award_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract industry information from NAICS codes or other classification systems.
    """
    # Try NAICS code first
    naics_code = award_data.get('naics_code') or award_data.get('naics')
    if naics_code:
        return map_naics_to_industry(str(naics_code))

    # Try other industry fields
    industry_fields = ['industry', 'sector', 'industry_description', 'naics_description']
    for field in industry_fields:
        industry = award_data.get(field)
        if industry and isinstance(industry, str):
            return industry.strip()

    return None


def extract_identifiers(award_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract company identifiers (UEI, DUNS, etc.).
    """
    identifiers = {}

    # UEI (Unique Entity Identifier)
    uei = award_data.get('uei') or award_data.get('uei_number')
    if uei:
        identifiers['uei'] = str(uei)

    # DUNS number
    duns = award_data.get('duns') or award_data.get('duns_number')
    if duns:
        identifiers['duns'] = str(duns)

    # Other potential identifiers
    other_id_fields = [
        ('cage_code', 'cage'),
        ('tax_id', 'tax_id_number'),
        ('ein', 'employer_identification_number')
    ]

    for key, field_name in other_id_fields:
        value = award_data.get(field_name) or award_data.get(key)
        if value:
            identifiers[key] = str(value)

    # If no identifiers found, try to extract from raw_id or other fields
    if not identifiers:
        raw_id = award_data.get('contract_number') or award_data.get('award_number')
        if raw_id:
            identifiers['award_number'] = str(raw_id)

    return identifiers


def extract_sbir_table_info(award_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract SBIR table-specific information for additional metadata.
    """
    table_info = {}

    # Federal agency information
    agency_info = award_data.get('solicitation_agency') or award_data.get('agency')
    if agency_info:
        table_info['solicitation_agency'] = str(agency_info)

    # Research topic
    topic = award_data.get('solicitation_topic') or award_data.get('topic_code')
    if topic:
        table_info['topic'] = str(topic)

    # Business type
    business_type = award_data.get('business_type') or award_data.get('firm_type')
    if business_type:
        table_info['business_type'] = str(business_type)

    return table_info


def generate_raw_id(award_data: Dict[str, Any], company_name: str) -> str:
    """
    Generate a unique raw ID for the SBIR award.
    """
    # Try to use official award/contract numbers first
    id_fields = ['award_id', 'contract_number', 'award_number', 'proposal_number']
    for field in id_fields:
        award_id = award_data.get(field)
        if award_id:
            return f"SBIR-{str(award_id)}"

    # Fallback to generating from available data
    agency = award_data.get('agency', 'UNK')
    phase = award_data.get('phase', '1')
    date_str = extract_award_date(award_data) or 'UKN'

    # Use first part of company name to keep it readable
    company_part = company_name.replace(' ', '')[:15] if company_name else 'UNKNOWN'

    return f"SBIR-{agency}-{phase}-{date_str}-{company_part}"


def map_naics_to_industry(naics_code: str) -> str:
    """
    Map NAICS codes to industry categories.
    """
    if not naics_code or not naics_code.isdigit():
        return "Unknown"

    # First 2 digits of NAICS determine the sector
    sector = int(naics_code[:2])

    naics_sectors = {
        11: "Agriculture",
        21: "Mining",
        22: "Utilities",
        23: "Construction",
        31: "Manufacturing",
        32: "Manufacturing",
        33: "Manufacturing",
        42: "Wholesale Trade",
        44: "Retail Trade",
        45: "Retail Trade",
        48: "Transportation",
        49: "Transportation",
        51: "Information",
        52: "Finance",
        53: "Real Estate",
        54: "Professional Services",
        55: "Management",
        56: "Administrative Services",
        61: "Educational Services",
        62: "Healthcare",
        71: "Arts and Entertainment",
        72: "Accommodation and Food",
        81: "Other Services",
        92: "Public Administration"
    }

    return naics_sectors.get(sector, "Manufacturing")


def validate_sbir_data(data: Dict[str, Any]) -> bool:
    """
    Validate that required SBIR data fields are present.
    """
    required_fields = ['company_name', 'funding_date']

    for field in required_fields:
        if not data.get(field):
            return False

    return True