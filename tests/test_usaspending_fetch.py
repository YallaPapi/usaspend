import types
from datetime import datetime, timedelta

import builtins

import src.connectors.usaspending as usa


class DummyResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"status {self.status_code}")

    def json(self):
        return self._json


def test_fetch_paginates_and_maps(monkeypatch):
    # Build two pages of fake results
    page1 = {
        "results": [
            {
                "Recipient Name": "Nova Bio Labs",
                "Award Amount": 150000,
                "Action Date": "2024-01-15",
                "Award Type": "02",
                "Recipient UEI": "UEI-ABC",
                "Award ID": "GRANT-1",
            }
        ],
        "page_metadata": {"hasNext": True},
    }
    page2 = {
        "results": [
            {
                "Recipient Name": "Acme Robotics",
                "Award Amount": 250000,
                "Action Date": "2024-02-01",
                "Award Type": "A",
                "Recipient DUNS": "987654321",
                "Award ID": "CONT-2",
            }
        ],
        "page_metadata": {"hasNext": False},
    }

    calls = {"count": 0}

    def fake_post(url, json=None, headers=None, timeout=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return DummyResp(page1)
        return DummyResp(page2)

    # Patch requests.post used in the connector
    monkeypatch.setattr(usa.requests, "post", fake_post)

    start = datetime.utcnow() - timedelta(days=365)
    end = datetime.utcnow()
    events = usa.fetch(start, end)

    assert len(events) == 2
    # First is grant
    assert events[0]["company_name"] == "Nova Bio Labs"
    assert events[0]["funding_type"] == "US_GRANT"
    # Second is contract
    assert events[1]["company_name"] == "Acme Robotics"
    assert events[1]["funding_type"] == "US_CONTRACT"

