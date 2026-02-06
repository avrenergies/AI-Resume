from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import tempfile
import os
from datetime import date

from app.ocr_engine import file_to_text
from app.extractor import (
    extract_name,
    extract_email,
    extract_phone,
    extract_education,
    detect_pan,
    detect_aadhaar
)
from app.experience_calc import calculate_experience
from app.location_address import extract_current_location, extract_address
from app.job_matcher import match_job


API_KEY = "pk_ai_resume_2026"

app = FastAPI(title="AI Resume Parsing API", version="2.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResumeURLRequest(BaseModel):
    resume: str


# 🔥 UNIVERSAL DOWNLOADER
def download_file(url):
    try:
        response = requests.get(url, timeout=40)
    except Exception:
        raise HTTPException(status_code=400, detail="Resume download failed")

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Resume download failed")

    suffix = os.path.splitext(url.split("?")[0])[1] or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(response.content)
        return tmp.name


# 🔥 CORE PARSER (USED BY BOTH V1 + V2)
def parse_core(path, resume_url=""):

    text = file_to_text(path)

    emails = extract_email(text)
    phones = extract_phone(text)

    return {
        "candidateName": extract_name(text) or "",
        "jobTitle": "",
        "department": "",
        "resume": resume_url,
        "isEmployee": "candidate",
        "certificates": [],

        "address": (extract_address(text) or {}).get("address", ""),
        "state": (extract_address(text) or {}).get("state", ""),
        "country": (extract_address(text) or {}).get("country", "India"),
        "pinCode": (extract_address(text) or {}).get("pincode", ""),

        "yearsOfExperience": calculate_experience(text),
        "educationQualification": extract_education(text) or "",

        "currentWorkLocation": (
            f"{extract_current_location(text)['state']}, India"
            if extract_current_location(text) else ""
        ),

        "emails": [
            {"emailAddress": e, "isPrimary": i == 0}
            for i, e in enumerate(emails)
        ],

        "mobileNumbers": [
            {"mobileNumber": p, "isPrimary": i == 0}
            for i, p in enumerate(phones)
        ],

        "pan": {
            "_id": "",
            "panNumber": "xxxxxxxxx" if detect_pan(text) else ""
        },

        "aadhar": {
            "_id": "",
            "aadharNumber": "************" if detect_aadhaar(text) else ""
        },

        "appliedDate": date.today().isoformat(),
        "_raw_text": text  # used internally for v2
    }


# ================= V1 =================

@app.post("/parse-resume")
def parse_resume(data: ResumeURLRequest, x_api_key: str = Header(None)):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    path = download_file(data.resume)

    try:
        result = parse_core(path, data.resume)
        result.pop("_raw_text", None)
        return result
    finally:
        os.remove(path)


@app.post("/parse-resume-upload")
def parse_upload(file: UploadFile = File(...), x_api_key: str = Header(None)):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    allowed = (".pdf", ".docx", ".jpg", ".jpeg", ".png")

    if not file.filename.lower().endswith(allowed):
        raise HTTPException(status_code=400, detail="Unsupported format")

    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        path = tmp.name

    try:
        result = parse_core(path)
        result.pop("_raw_text", None)
        return result
    finally:
        os.remove(path)


# ================= V2 (AI MATCHING) =================

@app.post("/v2/parse-resume")
def parse_resume_v2(data: ResumeURLRequest, x_api_key: str = Header(None)):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    path = download_file(data.resume)

    try:
        result = parse_core(path, data.resume)

        job_data = match_job(result["_raw_text"])

        result["jobTitle"] = job_data.get("jobTitle", "")
        result["department"] = job_data.get("department", "")
        result["matchScore"] = job_data.get("matchScore", 0)

        result.pop("_raw_text", None)
        return result

    finally:
        os.remove(path)


@app.post("/v2/parse-resume-upload")
def parse_upload_v2(file: UploadFile = File(...), x_api_key: str = Header(None)):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        path = tmp.name

    try:
        result = parse_core(path)

        job_data = match_job(result["_raw_text"])

        result["jobTitle"] = job_data.get("jobTitle", "")
        result["department"] = job_data.get("department", "")
        result["matchScore"] = job_data.get("matchScore", 0)

        result.pop("_raw_text", None)
        return result

    finally:
        os.remove(path)
