from datetime import datetime

from src.mappings.usaspending import map_record_to_canonical, infer_funding_type


def test_infer_funding_type_contracts():
    assert infer_funding_type({"type": "A"}) == "US_CONTRACT"
    assert infer_funding_type({"award_type": "B"}) == "US_CONTRACT"


def test_infer_funding_type_grants():
    assert infer_funding_type({"prime_award_type": "02"}) == "US_GRANT"
    assert infer_funding_type({"Award Type": "05"}) == "US_GRANT"


def test_map_record_minimal_fields():
    rec = {
        "Recipient Name": "Acme Robotics, Inc.",
        "Award Amount": 12345.67,
        "Action Date": "2024-06-30",
        "Award Type": "A",
        "Recipient UEI": "UEI-XYZ",
        "Recipient DUNS": "123456789",
        "Award ID": "CONT-0001",
        "NAICS Code": "334111",
    }
    out = map_record_to_canonical(rec)
    assert out["company_name"] == "Acme Robotics, Inc."
    assert out["funding_type"] == "US_CONTRACT"
    assert out["funding_amount"] == 12345.67
    assert out["funding_date"] == "2024-06-30"
    assert out["source"] == "usaspending"
    assert out["identifier"]["UEI"] == "UEI-XYZ"
    assert out["identifier"]["DUNS"] == "123456789"
    assert out["raw_id"] == "CONT-0001"
    assert out["industry"] == "334111"

