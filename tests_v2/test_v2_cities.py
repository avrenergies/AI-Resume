"""
Tests for the City dropdown fix (v2).  Run: pytest tests_v2 -q
Runs after test_v2.py and reuses its temp DB settings; also runs on its own.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp(prefix="resume_v2_city_test_")
os.environ.setdefault("V2_BASE_DIR", _TMP)
os.environ.setdefault("V2_UPLOAD_DIR", os.path.join(_TMP, "uploads"))
os.environ.setdefault("V2_CERT_DIR", os.path.join(_TMP, "certs"))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(_TMP, "test.db"))
os.environ.setdefault("RESUME_V2_KEY", "test_key_123")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app_v2 import constants as C  # noqa: E402
from app_v2.cities import all_cities, cities_for, normalize_city  # noqa: E402
from app_v2.config import API_PREFIX  # noqa: E402
from app_v2.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── data ─────────────────────────────────────────────────────────────────────

def test_every_india_and_nigeria_state_has_cities():
    data = all_cities()
    for country in ("India", "Nigeria"):
        missing = [s for s in C.STATES[country] if not data.get(country, {}).get(s)]
        assert not missing, f"{country} states without cities: {missing}"


def test_city_state_names_match_dropdown():
    for country, states in all_cities().items():
        assert country in C.STATES
        for st in states:
            assert st in C.STATES[country], f"{country}/{st} not in the State dropdown"


def test_known_extractor_cities_are_in_dropdown():
    for city, (st, country) in C.CITY_LOOKUP.items():
        if city in ("madras", "bombay", "calcutta", "trichy", "vizag", "trivandrum", "calicut"):
            continue
        assert city.title() in cities_for(country, st), f"{city} missing in {st}"


# ── normalisation ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,country,state,expect", [
    ("Angawan \nJaithari Anuppur", "India", "", ("Anuppur", "Madhya Pradesh")),  # real DB row #472
    ("Aurangabad", "India", "Maharashtra", ("Aurangabad", "")),
    ("Aurangabad", "India", "", ("Aurangabad", "")),            # 2 states → do not guess
    ("Surat", "India", "Gujarat", ("Surat", "")),
    ("Chennai", "India", "", ("Chennai", "Tamil Nadu")),
    ("Bangalore", "India", "Karnataka", ("Bangalore", "")),     # existing spelling kept
    ("Madras", "India", "", ("Chennai", "Tamil Nadu")),
    ("Trichy", "India", "Tamil Nadu", ("Tiruchirappalli", "")),
    ("Tiruchirapalli", "India", "Tamil Nadu", ("Tiruchirappalli", "")),
    ("Anna Nagar West Chennai", "India", "Tamil Nadu", ("Chennai", "")),
    ("Chennai", "India", "Bihar", ("Chennai", "")),             # never overwrites a state
    ("Port Harcourt", "Nigeria", "Rivers", ("Port Harcourt", "")),
    ("12/4 ### @@", "India", "", ("", "")),
    ("", "India", "", ("", "")),
])
def test_normalize_city(raw, country, state, expect):
    assert normalize_city(raw, country, state) == expect


# ── API ──────────────────────────────────────────────────────────────────────

def test_options_has_cities_and_old_keys(client):
    d = client.get(f"{API_PREFIX}/options").json()
    for k in ("jobTitles", "experience", "education", "certificates", "countries", "states",
              "countryCodes", "dialCodes"):
        assert k in d, f"existing key {k} disappeared"
    assert "Chennai" in d["cities"]["India"]["Tamil Nadu"]
    assert "Anuppur" in d["cities"]["India"]["Madhya Pradesh"]
    assert "Umuahia" in d["cities"]["Nigeria"]["Abia"]


def test_cities_endpoint(client):
    r = client.get(f"{API_PREFIX}/cities", params={"country": "India", "state": "Tamil Nadu"})
    assert r.status_code == 200 and "Coimbatore" in r.json()["cities"]
    r = client.get(f"{API_PREFIX}/cities", params={"country": "Nigeria"})
    assert "Rivers" in r.json()["states"]
    r = client.get(f"{API_PREFIX}/cities", params={"country": "India", "state": "Nowhere"})
    assert r.status_code == 200 and r.json()["cities"] == []


def test_extract_city_cleaned_and_review_saves_city(client):
    txt = ("RAKESH SINGH\nrakesh.singh@example.com\n9876501234\n"
           "Current location: Village Angawan\nJaithari Anuppur\n"
           "EXPERIENCE\nFitter, ABC Power, 2019 - Present\n")
    r = client.post(f"{API_PREFIX}/extract", files={"file": ("r.txt", io.BytesIO(txt.encode()), "text/plain")})
    assert r.status_code == 200, r.text
    d = r.json()
    for loc in (d["fields"]["currentWorkLocation"]["value"], d["fields"]["permanentAddress"]["value"]):
        assert "\n" not in (loc.get("city") or "")
    body = {"uid": d["uid"], "fields": {
        "fullName": "Rakesh Singh", "emails": [{"emailAddress": "rakesh.singh@example.com"}], "jobTitle": "Fitter",
        "currentWorkLocation": {"country": "India", "state": "Madhya Pradesh", "city": "Anuppur"},
        "permanentAddress": {"country": "India", "state": "Madhya Pradesh", "city": "Anuppur"}}}
    r = client.post(f"{API_PREFIX}/review", json=body)
    assert r.status_code == 200, r.text
    rec = client.get(f"{API_PREFIX}/records/{d['uid']}", headers={"x-api-key": os.environ["RESUME_V2_KEY"]}).json()
    saved = rec["reviews"][0]["reviewed"]
    assert saved["currentWorkLocation"] == {"country": "India", "state": "Madhya Pradesh", "city": "Anuppur"}
    assert saved["permanentAddress"]["city"] == "Anuppur" and saved["permanentAddress"]["state"] == "Madhya Pradesh"
