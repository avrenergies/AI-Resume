"""
Tests for the careers-page autofill endpoint (v2.4.0).  Run: pytest tests_v2 -q
"""
from __future__ import annotations

import glob
import io
import os
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp(prefix="resume_v2_public_test_")
os.environ.setdefault("V2_BASE_DIR", _TMP)
os.environ.setdefault("V2_UPLOAD_DIR", os.path.join(_TMP, "uploads"))
os.environ.setdefault("V2_CERT_DIR", os.path.join(_TMP, "certs"))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(_TMP, "test.db"))
os.environ.setdefault("RESUME_V2_KEY", "test_key_123")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app_v2 import public  # noqa: E402
from app_v2.config import API_PREFIX, UPLOAD_DIR  # noqa: E402
from app_v2.main import app  # noqa: E402

URL = f"{API_PREFIX}/public/autofill"
RESUME = ("RAVI KUMAR\nravi.kumar@example.com\n+91 98765 01234\n"
          "Date of Birth : 15/08/1992\nMarital Status : Married\n"
          "Aadhaar No: 2345 6789 0123\n"
          "SUMMARY\n6 years of experience as Boiler Operator in thermal power plant.\n"
          "EXPERIENCE\nBoiler Operator, ABC Power Plant, 2018 - Present\n"
          "CERTIFICATES\nBoiler Operation Engineer (BOE) certificate, First Aid training\n")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_limits(monkeypatch):
    public._hits.clear()
    monkeypatch.setattr(public, "RATE_PER_MIN", 1000)
    monkeypatch.setattr(public, "RATE_PER_HOUR", 1000)
    yield
    public._hits.clear()


def _post(client, text=RESUME, name="resume.txt", raw=None, headers=None):
    data = raw if raw is not None else text.encode()
    return client.post(URL, files={"file": (name, io.BytesIO(data), "application/octet-stream")}, headers=headers or {})


def _db_counts(client):
    r = client.get(f"{API_PREFIX}/stats", headers={"x-api-key": os.environ["RESUME_V2_KEY"]})
    return r.json() if r.status_code == 200 else None


def test_autofill_returns_form_values(client):
    r = _post(client)
    assert r.status_code == 200, r.text
    d = r.json()
    f = d["form"]
    assert d["ok"] is True
    assert f["name"] == "Ravi Kumar"
    assert f["email"] == "ravi.kumar@example.com"
    assert f["phone"] == "9876501234" and f["countryCode"] == "+91"
    assert f["idType"] == "Aadhar" and f["idNumber"] == "234567890123"
    assert f["dateOfBirth"] == "15/08/1992" and f["maritalStatus"] == "Married"
    assert f["experienceYears"] == 6 or f["experienceYears"] == 6.0
    assert f["experience"] in ("5-10 years",)
    # division comes from the live AVR list on the server (may differ from the offline snapshot):
    # it must be present, and whenever a division is returned its id must be returned too
    assert "division" in f and "divisionId" in f
    if f["division"]:
        assert isinstance(f["divisionId"], int)
    assert f["jobTitle"]
    assert isinstance(f["certificates"], list)
    for k in ("name", "email", "phone", "idType", "idNumber", "experience", "division", "jobTitle",
              "certificates", "dateOfBirth", "maritalStatus"):
        assert k in d["status"]
    assert "fullName" in d["fields"] and "emails" in d["fields"]


def test_pan_when_no_aadhaar(client):
    r = _post(client, "SURESH M\nsuresh@example.com\n9876501299\nPAN: ABCPS1234K\nFitter\n")
    f = r.json()["form"]
    assert f["idType"] == "PAN" and f["idNumber"] == "ABCPS1234K"


def test_no_id_found(client):
    f = _post(client, "SURESH M\nsuresh@example.com\n9876501299\nFitter\n").json()["form"]
    assert f["idType"] == "" and f["idNumber"] == ""


def test_nothing_is_stored(client):
    before_db = _db_counts(client)
    before_files = set(os.listdir(UPLOAD_DIR)) if os.path.isdir(UPLOAD_DIR) else set()
    before_tmp = set(glob.glob(os.path.join(tempfile.gettempdir(), "pub_*")))
    assert _post(client).status_code == 200
    assert _db_counts(client) == before_db
    after_files = set(os.listdir(UPLOAD_DIR)) if os.path.isdir(UPLOAD_DIR) else set()
    assert after_files == before_files
    assert set(glob.glob(os.path.join(tempfile.gettempdir(), "pub_*"))) == before_tmp


def test_cors_allows_careers_page(client):
    r = client.options(URL, headers={"Origin": "https://avrenergies.com",
                                     "Access-Control-Request-Method": "POST"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://avrenergies.com"


def test_rate_limit_per_minute(client, monkeypatch):
    monkeypatch.setattr(public, "RATE_PER_MIN", 2)
    assert _post(client).status_code == 200
    assert _post(client).status_code == 200
    r = _post(client)
    assert r.status_code == 429 and "Retry-After" in r.headers and "try again" in r.json()["detail"]


def test_rate_limit_is_per_visitor(client, monkeypatch):
    monkeypatch.setattr(public, "RATE_PER_MIN", 1)
    assert _post(client, headers={"x-forwarded-for": "1.1.1.1"}).status_code == 200
    assert _post(client, headers={"x-forwarded-for": "1.1.1.1"}).status_code == 429
    assert _post(client, headers={"x-forwarded-for": "2.2.2.2"}).status_code == 200


def test_rate_limit_per_hour(client, monkeypatch):
    monkeypatch.setattr(public, "RATE_PER_HOUR", 1)
    assert _post(client).status_code == 200
    assert _post(client).status_code == 429


@pytest.mark.parametrize("name,raw,code", [
    ("resume.exe", b"MZ....", 400),
    ("resume", b"hello", 400),
    ("resume.txt", b"", 400),
    ("resume.txt", b"   \n\t  ", 422),
    ("resume.pdf", b"not really a pdf", 422),
])
def test_bad_files(client, name, raw, code):
    r = _post(client, name=name, raw=raw)
    assert r.status_code == code, r.text
    assert "detail" in r.json()


def test_too_big(client, monkeypatch):
    monkeypatch.setattr(public, "MAX_FILE_MB", 1)
    r = _post(client, raw=b"a" * (1024 * 1024 + 10))
    assert r.status_code == 413


def test_too_many_pdf_pages(client, monkeypatch):
    monkeypatch.setattr(public, "MAX_PDF_PAGES", 0)
    pdf = open(os.path.join(ROOT, "data", "sample_resume.pdf"), "rb").read()
    r = _post(client, name="cv.pdf", raw=pdf)
    assert r.status_code == 413 and "pages" in r.json()["detail"]


def test_real_pdf(client):
    pdf = open(os.path.join(ROOT, "data", "sample_resume.pdf"), "rb").read()
    r = _post(client, name="cv.pdf", raw=pdf)
    assert r.status_code == 200, r.text
    f = r.json()["form"]
    assert f["name"] and f["email"] and f["phone"]


def test_busy_returns_503(client, monkeypatch):
    monkeypatch.setattr(public, "_slots", threading.BoundedSemaphore(1))
    monkeypatch.setattr(public, "WAIT_SLOT_SEC", 0.1)
    public._slots.acquire()
    try:
        r = _post(client)
        assert r.status_code == 503 and "busy" in r.json()["detail"]
    finally:
        public._slots.release()


def test_existing_endpoints_unchanged(client):
    assert client.get(f"{API_PREFIX}/health").json()["version"] == "2.4.0"
    o = client.get(f"{API_PREFIX}/options").json()
    for k in ("jobTitles", "divisions", "maritalStatuses", "cities", "experience", "education", "certificates"):
        assert k in o
