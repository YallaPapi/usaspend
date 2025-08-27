from __future__ import annotations

from typing import Any, Dict

from ..schema import canonical_event, normalize_text, normalize_date


def infer_funding_type(record: Dict[str, Any]) -> str:
    """
    Heuristic mapping of USAspending award type codes to a coarse funding_type.
    Contracts (A/B/C/D) -> US_CONTRACT, Assistance (02/03/04/05) -> US_GRANT, else US_AWARD.
    Accepts both snake_case and title-cased keys that may appear in API responses.
    """
    code = (
        record.get("type")
        or record.get("award_type")
        or record.get("prime_award_type")
        or record.get("Award Type")
    )
    code = normalize_text(code)
    if not code:
        return "US_AWARD"
    code = code.strip()
    contracts = {"A", "B", "C", "D"}
    assistance = {"02", "03", "04", "05"}
    if code in contracts:
        return "US_CONTRACT"
    if code in assistance:
        return "US_GRANT"
    return "US_AWARD"


def map_record_to_canonical(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a USAspending search/spending_by_award result to our canonical event dict.
    Handles multiple possible key variants defensively.
    """
    name = (
        rec.get("recipient_name")
        or rec.get("Recipient Name")
        or rec.get("recipient", {}).get("recipient_name")
        or rec.get("recipient", {}).get("recipient_name_raw")
    )
    amount = (
        rec.get("award_amount")
        or rec.get("Award Amount")
        or rec.get("total_obligation")
        or rec.get("obligation")
    )
    action_date = rec.get("action_date") or rec.get("Action Date")
    country = (
        rec.get("recipient_country")
        or rec.get("Recipient Country")
        or rec.get("recipient", {}).get("location_country_code")
        or rec.get("recipient", {}).get("location_country_name")
    )
    naics = rec.get("naics_code") or rec.get("NAICS Code")
    raw_id = (
        rec.get("piid")
        or rec.get("fain")
        or rec.get("uri")
        or rec.get("Award ID")
        or rec.get("generated_unique_award_id")
    )
    uei = rec.get("recipient_uei") or rec.get("Recipient UEI")
    duns = rec.get("recipient_duns") or rec.get("Recipient DUNS")

    identifiers: Dict[str, Any] = {}
    if normalize_text(uei):
        identifiers["UEI"] = uei
    if normalize_text(duns):
        identifiers["DUNS"] = duns

    return canonical_event(
        company_name=name or "",
        funding_type=infer_funding_type(rec),
        funding_amount=amount,
        funding_date=normalize_date(action_date),
        source="usaspending",
        country=country,
        industry=naics,
        identifier=identifiers,
        raw_id=raw_id,
    )


__all__ = ["map_record_to_canonical", "infer_funding_type"]

