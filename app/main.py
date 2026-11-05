from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
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
    detect_aadhaar,
    extract_job_title
)
from app.experience_calc import calculate_experience
from app.address_extractor import extract_current_location, extract_address
from app.job_title_cache import load_job_titles


#CONFIG 

API_KEY = os.getenv("RESUME_API_KEY", "pk_ai_resume_2026")
MAX_FILE_SIZE_MB = 10
MAX_TEXT_LENGTH = 20000

# Read allowed CORS origins from env (set in .env via deploy.sh).
# "*" => any origin. A real domain list is recommended in production.
_origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()
ALLOWED_ORIGINS = ["*"] if _origins_env in ("", "*") else [
    o.strip() for o in _origins_env.split(",") if o.strip()
]
# allow_credentials cannot be True together with a wildcard origin.
ALLOW_CREDENTIALS = ALLOWED_ORIGINS != ["*"]

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


#APP INIT 

app = FastAPI(
    title="AI Resume Parsing API",
    version="5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


#  GLOBAL ERROR HANDLER 

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error"}
    )


#  HEALTH 

@app.get("/health")
def health():
    return {"status": "running"}

@app.on_event("startup")
def startup_event():
    try:
        
        print("Loading job titles into memory...")
        load_job_titles()
    except Exception as e:
        print(" Job title preload failed:", e)


def validate_api_key(api_key: str):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


class ResumeURLRequest(BaseModel):
    resume: str


def download_file(url: str):

    try:
        response = requests.get(url, timeout=20)
    except Exception:
        raise HTTPException(status_code=400, detail="Resume download failed")

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Resume download failed")

    size_mb = len(response.content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large")

    suffix = os.path.splitext(url.split("?")[0])[1] or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(response.content)
        return tmp.name


def parse_core(path, resume_url=""):

    text = file_to_text(path)

    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Could not extract text")

    safe_text = text[:MAX_TEXT_LENGTH]

    contact_text = safe_text[:3000]

    emails = extract_email(contact_text)
    phones = extract_phone(contact_text)

    addr = extract_address(safe_text) or {}
    location = extract_current_location(safe_text) or {}

    result = {

        "candidateName": extract_name(safe_text) or "",
        "jobTitle": extract_job_title(safe_text) or "",
        "department": "",
        "resume": resume_url,
        "isEmployee": "candidate",
        "certificates": [],

        "address": addr.get("address", ""),
        "city": addr.get("city", ""),
        "state": addr.get("state", ""),
        "country": addr.get("country", "India"),
        "pinCode": addr.get("pincode", ""),

        "yearsOfExperience": calculate_experience(safe_text),
        "educationQualification": extract_education(safe_text) or "",

        "currentWorkLocation": (
            f"{location.get('city','')}, {location.get('state','')}"
            if location else ""
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
            "panNumber": detect_pan(safe_text) or ""
        },

        "aadhar": {
            "_id": "",
            "aadharNumber": detect_aadhaar(safe_text) or ""
        },

        "appliedDate": date.today().isoformat(),
        "_raw_text": safe_text
    }

    return result


@app.post("/parse-resume")
def parse_resume(data: ResumeURLRequest, api_key: str = Security(api_key_header)):

    validate_api_key(api_key)

    path = download_file(data.resume)

    try:
        result = parse_core(path, data.resume)
        result.pop("_raw_text", None)
        return result
    finally:
        os.remove(path)


@app.post("/parse-resume-upload")
def parse_upload(file: UploadFile = File(...), api_key: str = Security(api_key_header)):

    validate_api_key(api_key)

    allowed = (".pdf", ".docx", ".jpg", ".jpeg", ".png")

    if not file.filename.lower().endswith(allowed):
        raise HTTPException(status_code=400, detail="Unsupported format")

    content = file.file.read()

    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large")

    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        path = tmp.name

    try:
        result = parse_core(path)
        result.pop("_raw_text", None)
        return result
    finally:
        os.remove(path)


