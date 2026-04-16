import os
import tempfile
import logging
from datetime import date

import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.ocr_engine import file_to_text, SUPPORTED_EXTENSIONS
from app.extractor import (
    extract_name, extract_email, extract_phone,
    extract_education, detect_pan, detect_aadhaar,
)
from app.experience_calc import calculate_experience
from app.location_address import extract_current_location, extract_address
from app.job_matcher import match_job

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("resume_api")

# ─── Config ─────────────────────────────────────────────────────────────────
API_KEY          = os.environ["RESUME_API_KEY"]
MAX_FILE_SIZE_MB = 10
MAX_TEXT_LENGTH  = 20_000
ALLOWED_ORIGINS  = os.getenv(
    "ALLOWED_ORIGINS",
    "https://avrenergies.com,https://www.avrenergies.com"
).split(",")

# ─── Rate limiter ────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ─── Auth ────────────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def require_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Resume Parsing API", version="7.0", docs_url=None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["x-api-key", "Content-Type"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"error": "Internal Server Error"})

# ─── Health ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "running",
        "version": "7.0",
        "supported_formats": sorted(SUPPORTED_EXTENSIONS),
    }

# ─── Helpers ─────────────────────────────────────────────────────────────────
class ResumeURLRequest(BaseModel):
    resume: str

def _get_ext(filename: str) -> str:
    return os.path.splitext(filename)[-1].lower()

def _validate_ext(ext: str):
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Accepted: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

def download_file(url: str) -> str:
    try:
        resp = requests.get(url, timeout=20)
    except Exception as exc:
        logger.warning("Download failed: %s", exc)
        raise HTTPException(status_code=400, detail="Resume download failed")

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Resume download failed")

    content = resp.content
    if len(content) / (1024 * 1024) > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    ext = _get_ext(url.split("?")[0]) or ".pdf"
    _validate_ext(ext)

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        return tmp.name

def parse_core(path: str, resume_url: str = "") -> dict:
    text = file_to_text(path)

    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    safe_text = text[:MAX_TEXT_LENGTH]
    emails    = extract_email(safe_text)
    phones    = extract_phone(safe_text)
    addr      = extract_address(safe_text) or {}
    location  = extract_current_location(safe_text) or {}

    loc_city  = location.get("city", "")
    loc_state = location.get("state", "")
    current_work_location = ", ".join(filter(None, [loc_city, loc_state]))

    result = {
        "candidateName":          extract_name(safe_text) or "",
        "jobTitle":               "",
        "department":             "",
        "resume":                 resume_url,
        "isEmployee":             "candidate",
        "certificates":           [],
        "address":                addr.get("address", ""),
        "city":                   addr.get("city", ""),
        "state":                  addr.get("state", ""),
        "country":                addr.get("country", "India"),
        "pinCode":                addr.get("pincode", ""),
        "yearsOfExperience":      calculate_experience(safe_text),
        "educationQualification": extract_education(safe_text) or "",
        "currentWorkLocation":    current_work_location,
        "emails": [
            {"emailAddress": e, "isPrimary": i == 0}
            for i, e in enumerate(emails)
        ],
        "mobileNumbers": [
            {"mobileNumber": p, "isPrimary": i == 0}
            for i, p in enumerate(phones)
        ],
        "pan":    {"_id": "", "panNumber":    detect_pan(safe_text) or ""},
        "aadhar": {"_id": "", "aadharNumber": detect_aadhaar(safe_text) or ""},
        "appliedDate": date.today().isoformat(),
        "_raw_text":   safe_text,
    }

    logger.info(
        "Parsed: name=%r exp=%s edu=%r city=%r phones=%d emails=%d",
        result["candidateName"], result["yearsOfExperience"],
        result["educationQualification"], result["city"],
        len(phones), len(emails),
    )
    return result

def _clean(result: dict) -> dict:
    result.pop("_raw_text", None)
    return result

def _apply_job_match(result: dict) -> dict:
    job_data = match_job(result["_raw_text"]) or {}
    result.update({
        "jobTitle":      job_data.get("jobTitle", ""),
        "department":    job_data.get("department", ""),
        "matchScore":    job_data.get("matchScore", 0),
        "skills":        job_data.get("skills", []),
        "skillClusters": job_data.get("skillClusters", {}),
        "fitScore":      job_data.get("fitScore", 0),
        "missingSkills": job_data.get("missingSkills", []),
    })
    return result

# ─── V1: URL ─────────────────────────────────────────────────────────────────
@app.post("/parse-resume", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def parse_resume(request: Request, data: ResumeURLRequest):
    path = download_file(data.resume)
    try:
        return _clean(parse_core(path, data.resume))
    finally:
        os.remove(path)

# ─── V1: Upload ───────────────────────────────────────────────────────────────
@app.post("/parse-resume-upload", dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
def parse_upload(request: Request, file: UploadFile = File(...)):
    ext = _get_ext(file.filename or "")
    _validate_ext(ext)
    content = file.file.read()
    if len(content) / (1024 * 1024) > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        path = tmp.name
    try:
        return _clean(parse_core(path))
    finally:
        os.remove(path)

# ─── V2: URL + AI job match ───────────────────────────────────────────────────
@app.post("/v2/parse-resume", dependencies=[Depends(require_api_key)])
@limiter.limit("20/minute")
def parse_resume_v2(request: Request, data: ResumeURLRequest):
    path = download_file(data.resume)
    try:
        return _clean(_apply_job_match(parse_core(path, data.resume)))
    finally:
        os.remove(path)

# ─── V2: Upload + AI job match ────────────────────────────────────────────────
@app.post("/v2/parse-resume-upload", dependencies=[Depends(require_api_key)])
@limiter.limit("20/minute")
def parse_upload_v2(request: Request, file: UploadFile = File(...)):
    ext = _get_ext(file.filename or "")
    _validate_ext(ext)
    content = file.file.read()
    if len(content) / (1024 * 1024) > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        path = tmp.name
    try:
        return _clean(_apply_job_match(parse_core(path)))
    finally:
        os.remove(path)
