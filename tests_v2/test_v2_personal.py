"""
Tests for Date of birth + Marital Status (v2.3.0).  Run: pytest tests_v2 -q
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp(prefix="resume_v2_personal_test_")
os.environ.setdefault("V2_BASE_DIR", _TMP)
os.environ.setdefault("V2_UPLOAD_DIR", os.path.join(_TMP, "uploads"))
os.environ.setdefault("V2_CERT_DIR", os.path.join(_TMP, "certs"))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(_TMP, "test.db"))
os.environ.setdefault("RESUME_V2_KEY", "test_key_123")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app_v2.config import API_PREFIX  # noqa: E402
from app_v2.main import app  # noqa: E402
from app_v2.personal import extract_dob, extract_marital, normalize_marital  # noqa: E402

T = date(2026, 11, 18)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── extraction rules ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expect", [
    ("Date of Birth : 12/03/1990", "12/03/1990"),
    ("DOB: 05-11-1988", "05/11/1988"),
    ("D.O.B. 1990-07-21", "21/07/1990"),
    ("Date of Birth & Age : 12.03.1990 (34 yrs)", "12/03/1990"),
    ("Date of Birth\n:\n25/12/1995", "25/12/1995"),
    ("DOB : 15th August 1992", "15/08/1992"),
    ("Born on March 5, 1991", "05/03/1991"),
    ("Date of birth- 3 Jan 85", "03/01/1985"),
    ("dob 7-sept-1993", "07/09/1993"),
    ("Date Of Birth :- 02 - 06 - 1994", "02/06/1994"),
    ("Date of Birth | 21-07-1990 | Gender | Male", "21/07/1990"),
    ("DOB: 03/25/1990", "25/03/1990"),                       # month-first resume
    # never guess
    ("Date of Birth :\nDate of Joining : 01/02/2005", ""),   # blank DOB, next label has a date
    ("Date of Birth: NA    Date of Joining: 01/02/2005", ""),
    ("Experience 01/02/2015 - 2020", ""),                    # no DOB label
    ("Born in Chennai", ""),
    ("Date of Birth: 31/02/1990", ""),                       # impossible date
    ("DOB : 12/03/24", ""),                                  # would be a 2-year-old
])
def test_extract_dob(text, expect):
    assert extract_dob(text, T)[0] == expect


@pytest.mark.parametrize("text,expect", [
    ("Marital Status : Unmarried", "Single"),
    ("Martial Status: Married", "Married"),
    ("Sex/Marital Status : Male/Married", "Married"),
    ("Marital status - single", "Single"),
    ("Civil Status: Widow", "Widowed"),
    ("Marital Status : Not Married", "Single"),
    ("Marital Status\n:\nMarried", "Married"),
    ("Status : Married", "Married"),
    ("Status: active employee", ""),
    ("Marital Status :\nNationality : Indian\nSingle hobbies", ""),
    ("No marital info", ""),
])
def test_extract_marital(text, expect):
    assert extract_marital(text)[0] == expect


def test_normalize_marital():
    assert [normalize_marital(x) for x in ["SINGLE", "un-married", "Widower", "Married ", "engaged", ""]] == \
        ["Single", "Single", "Widowed", "Married", "", ""]


# ── API ──────────────────────────────────────────────────────────────────────

RESUME = ("RAVI KUMAR\nravi.kumar@example.com\n9876501234\n"
          "Date of Birth : 15/08/1992\nMarital Status : Married\n"
          "EXPERIENCE\nBoiler Operator, ABC Power Plant, 2018 - Present\n")


def _extract(client, text=RESUME):
    r = client.post(f"{API_PREFIX}/extract", files={"file": ("r.txt", io.BytesIO(text.encode()), "text/plain")})
    assert r.status_code == 200, r.text
    return r.json()


def test_options_has_marital_statuses_and_old_keys(client):
    d = client.get(f"{API_PREFIX}/options").json()
    assert d["maritalStatuses"] == ["Single", "Married", "Divorced", "Widowed", "Separated"]
    assert d["dateOfBirthFormat"] == "DD/MM/YYYY"
    for k in ("jobTitles", "divisions", "divisionNames", "departments", "experience", "education",
              "certificates", "countries", "states", "countryCodes", "dialCodes", "cities"):
        assert k in d, f"existing key {k} disappeared"


def test_extract_returns_both_fields(client):
    f = _extract(client)["fields"]
    assert f["dateOfBirth"]["value"] == "15/08/1992" and f["dateOfBirth"]["status"] == "extracted"
    assert f["dateOfBirth"]["iso"] == "1992-08-15"
    assert f["maritalStatus"]["value"] == "Married" and f["maritalStatus"]["status"] == "extracted"
    for k in ("fullName", "emails", "mobileNumbers", "division", "jobTitle", "currentWorkLocation"):
        assert k in f


def test_extract_missing_fields_are_red(client):
    f = _extract(client, "SURESH\nsuresh@example.com\n9876501299\nFitter\n")["fields"]
    assert f["dateOfBirth"]["status"] == "not_extracted" and f["dateOfBirth"]["value"] == ""
    assert f["maritalStatus"]["status"] == "not_extracted"


def _review(client, uid, **extra):
    fields = {"fullName": "Ravi Kumar", "emails": [{"emailAddress": "ravi.kumar@example.com"}],
              "jobTitle": "Boiler DCS Operator", "division": "O&M"}
    fields.update(extra)
    return client.post(f"{API_PREFIX}/review", json={"uid": uid, "fields": fields})


def _saved(client, uid):
    rec = client.get(f"{API_PREFIX}/records/{uid}", headers={"x-api-key": os.environ["RESUME_V2_KEY"]}).json()
    return rec["reviews"][0]["reviewed"], rec["reviews"][0]["corrections"]


@pytest.mark.parametrize("sent,stored", [
    ("15/08/1992", "15/08/1992"),
    ("1992-08-15", "15/08/1992"),                 # HTML date input
    ("1992-08-15T00:00:00.000Z", "15/08/1992"),   # JS toISOString()
    ("15-08-1992", "15/08/1992"),
    ("15.08.1992", "15/08/1992"),
    ("15 Aug 1992", "15/08/1992"),
    ("", ""),
])
def test_review_stores_dob_as_dd_mm_yyyy(client, sent, stored):
    uid = _extract(client)["uid"]
    r = _review(client, uid, dateOfBirth=sent, maritalStatus="Married")
    assert r.status_code == 200, r.text
    reviewed, _ = _saved(client, uid)
    assert reviewed["dateOfBirth"] == stored


@pytest.mark.parametrize("bad", ["31/02/1990", "08/25/1992", "abc", "15/08/2099"])
def test_review_rejects_bad_dob_with_clear_message(client, bad):
    uid = _extract(client)["uid"]
    r = _review(client, uid, dateOfBirth=bad)
    assert r.status_code == 422
    assert "Date of birth" in r.text


@pytest.mark.parametrize("sent,stored", [
    ("Married", "Married"), ("single", "Single"), ("Unmarried", "Single"),
    ("WIDOW", "Widowed"), ("", ""), ("Engaged", "Engaged"),
])
def test_review_stores_marital_status(client, sent, stored):
    uid = _extract(client)["uid"]
    r = _review(client, uid, maritalStatus=sent)
    assert r.status_code == 200, r.text
    reviewed, _ = _saved(client, uid)
    assert reviewed["maritalStatus"] == stored


def test_review_without_new_fields_still_works(client):
    uid = _extract(client)["uid"]
    r = _review(client, uid)
    assert r.status_code == 200, r.text
    reviewed, _ = _saved(client, uid)
    assert reviewed["dateOfBirth"] == "" and reviewed["maritalStatus"] == ""


def test_corrections_track_new_fields(client):
    uid = _extract(client)["uid"]
    r = _review(client, uid, dateOfBirth="16/08/1992", maritalStatus="Married")
    assert r.status_code == 200
    body = r.json()
    assert "dateOfBirth" in body["changedFields"] and "maritalStatus" not in body["changedFields"]
    assert body["candidate"]["dateOfBirth"] == "16/08/1992" and body["candidate"]["maritalStatus"] == "Married"
    _, corr = _saved(client, uid)
    assert corr["dateOfBirth"]["action"] == "corrected" and corr["maritalStatus"]["action"] == "confirmed"
