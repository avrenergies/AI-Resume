from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import tempfile
import os
from datetime import date

from app.ocr_engine import pdf_to_text
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


# ================= CONFIG =================
API_KEY = "pk_ai_resume_2026"


# ================= APP INIT =================
app = FastAPI(
    title="AI Resume Parsing API",
    version="1.1"
)

# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= REQUEST MODEL =================
class ResumeURLRequest(BaseModel):
    resume: str   # S3 public / pre-signed URL


# ================= CORE PROCESSOR (LOCKED) =================
def process_resume_file(resume_path: str, resume_url: str = ""):
    text = pdf_to_text(resume_path)

    name = extract_name(text)
    email = extract_email(text)
    phone = extract_phone(text)
    education = extract_education(text)
    experience = calculate_experience(text)

    location = extract_current_location(text)
    address_info = extract_address(text)

    pan_present = detect_pan(text)
    aadhaar_present = detect_aadhaar(text)

    return {
        "candidateName": name or "",
        "jobTitle": "",
        "department": "",
        "resume": resume_url,
        "isEmployee": "candidate",
        "certificates": [],

        "address": address_info.get("address") if address_info else "",
        "state": address_info.get("state") if address_info else "",
        "country": address_info.get("country") if address_info else "india",
        "pinCode": address_info.get("pincode") if address_info else "",

        "yearsOfExperience": experience if experience is not None else 0,
        "educationQualification": education or "",
        "currentWorkLocation": (
            f"{location['state']}, {location['country']}"
            if location else ""
        ),

        "emails": [
            {
                "emailAddress": email,
                "isPrimary": True
            }
        ] if email else [],

        "mobileNumbers": [
            {
                "mobileNumber": phone,
                "isPrimary": True
            }
        ] if phone else [],

        "pan": {
            "_id": "",
            "panNumber": "xxxxxxxxx" if pan_present else ""
        },

        "aadhar": {
            "_id": "",
            "aadharNumber": "************" if aadhaar_present else ""
        },

        "appliedDate": date.today().isoformat()
    }


# ================= ENDPOINT 1 (EXISTING – S3 URL) =================
@app.post("/parse-resume")
def parse_resume_from_url(
    data: ResumeURLRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        response = requests.get(data.resume, timeout=30)
    except Exception:
        raise HTTPException(status_code=400, detail="Resume download failed")

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Resume download failed")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(response.content)
        resume_path = tmp.name

    try:
        return process_resume_file(resume_path, resume_url=data.resume)
    finally:
        os.remove(resume_path)


# ================= ENDPOINT 2 (NEW – DIRECT PDF UPLOAD) =================
@app.post("/parse-resume-upload")
def parse_resume_from_upload(
    file: UploadFile = File(...),
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        resume_path = tmp.name

    try:
        return process_resume_file(resume_path, resume_url="")
    finally:
        os.remove(resume_path)
