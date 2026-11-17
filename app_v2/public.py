"""
Public resume autofill for the careers page (avrenergies.com/careers → "Apply Job").

    POST /resume-extractor-v2/public/autofill   (multipart, field "file")

Made for anonymous visitors, so unlike /extract it:
  * stores NOTHING - no file on disk, no database row, no training data (privacy + disk safe)
  * is rate limited per visitor IP and limits how many extractions run at once
  * rejects very long PDFs (OCR on 100s of pages would block the server)
  * returns the values flat, ready to drop into the Apply Job form fields
The careers form still submits the application to the AVR backend exactly as before.
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app_v2.config import ALLOWED_EXT, API_PREFIX, MAX_FILE_MB

log = logging.getLogger("resume_v2.public")

RATE_PER_MIN = int(os.getenv("PUBLIC_RATE_PER_MIN", "6"))
RATE_PER_HOUR = int(os.getenv("PUBLIC_RATE_PER_HOUR", "30"))
MAX_PDF_PAGES = int(os.getenv("PUBLIC_MAX_PDF_PAGES", "10"))
MAX_PARALLEL = int(os.getenv("PUBLIC_MAX_PARALLEL", "2"))   # per worker
WAIT_SLOT_SEC = 45

router = APIRouter(prefix=f"{API_PREFIX}/public", tags=["Public (careers page)"])

_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = threading.Lock()
_slots = threading.BoundedSemaphore(MAX_PARALLEL)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def _rate_check(ip: str) -> None:
    now = time.time()
    with _hits_lock:
        q = _hits[ip]
        while q and now - q[0] > 3600:
            q.popleft()
        last_min = sum(1 for t in q if now - t < 60)
        if last_min >= RATE_PER_MIN or len(q) >= RATE_PER_HOUR:
            wait = 60 if last_min >= RATE_PER_MIN else int(3600 - (now - q[0])) + 1
            raise HTTPException(429, f"Too many resume uploads. Please try again in {max(wait, 1)} seconds.",
                                headers={"Retry-After": str(max(wait, 1))})
        q.append(now)
        if len(_hits) > 20000:  # keep memory bounded
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > 3600]:
                _hits.pop(k, None)


def _pdf_pages(path: str) -> int:
    try:
        from pdfminer.pdfpage import PDFPage
        with open(path, "rb") as fh:
            return sum(1 for _ in PDFPage.get_pages(fh))
    except Exception:
        return 0  # unreadable here -> let the normal reader decide


def _val(fields: dict, key: str):
    d = fields.get(key) or {}
    return d.get("value", "")


def _status(fields: dict, key: str) -> str:
    return (fields.get(key) or {}).get("status", "not_extracted")


def _to_form(fields: dict, years: float | None) -> tuple[dict, dict]:
    emails = _val(fields, "emails") or []
    phones = _val(fields, "mobileNumbers") or []
    p_email = next((e for e in emails if e.get("isPrimary")), emails[0] if emails else {})
    p_phone = next((p for p in phones if p.get("isPrimary")), phones[0] if phones else {})
    certs = [c.get("name", "") for c in (_val(fields, "certificates") or []) if c.get("name")]

    pan, aad = _val(fields, "pan"), _val(fields, "aadhar")
    pan_c = float((fields.get("pan") or {}).get("confidence") or 0)
    aad_c = float((fields.get("aadhar") or {}).get("confidence") or 0)
    if aad and (not pan or aad_c >= pan_c):
        id_type, id_number, id_key = "Aadhar", aad, "aadhar"
    elif pan:
        id_type, id_number, id_key = "PAN", pan, "pan"
    else:
        id_type, id_number, id_key = "", "", "aadhar"

    div = fields.get("division") or {}
    form = {
        "idType": id_type,                       # "Aadhar" | "PAN" | ""
        "idNumber": id_number,
        "pan": pan,
        "aadhar": aad,
        "name": _val(fields, "fullName"),
        "surname": _val(fields, "surname"),
        "email": p_email.get("emailAddress", ""),
        "phone": p_phone.get("mobileNumber", ""),
        "countryCode": p_phone.get("countryCode", ""),
        "experience": _val(fields, "yearsOfExperience"),   # bucket, e.g. "3-5 years"
        "experienceYears": years,                          # number, e.g. 4.5 (null if unknown)
        "division": div.get("value", ""),
        "divisionId": div.get("divisionId"),
        "jobTitle": _val(fields, "jobTitle"),
        "certificates": certs,
        "educationQualification": _val(fields, "educationQualification"),
        "dateOfBirth": _val(fields, "dateOfBirth"),
        "maritalStatus": _val(fields, "maritalStatus"),
        "currentLocation": _val(fields, "currentWorkLocation") or {},
        "permanentAddress": _val(fields, "permanentAddress") or {},
    }
    status = {
        "idType": _status(fields, id_key), "idNumber": _status(fields, id_key),
        "name": _status(fields, "fullName"), "email": _status(fields, "emails"),
        "phone": _status(fields, "mobileNumbers"), "experience": _status(fields, "yearsOfExperience"),
        "division": _status(fields, "division"), "jobTitle": _status(fields, "jobTitle"),
        "certificates": _status(fields, "certificates"),
        "dateOfBirth": _status(fields, "dateOfBirth"), "maritalStatus": _status(fields, "maritalStatus"),
    }
    return form, status


def _work(path: str, filename: str) -> dict:
    from app_v2.extractor import extract, extract_experience
    from app_v2.textract import file_to_text
    if not _slots.acquire(timeout=WAIT_SLOT_SEC):
        raise HTTPException(503, "The resume reader is busy. Please try again in a minute.")
    try:
        t0 = time.perf_counter()
        try:
            text, method = file_to_text(path, filename)
        except Exception as exc:
            log.warning("public autofill: could not read file (%s)", type(exc).__name__)
            raise HTTPException(422, "Could not read this file. Please upload a PDF, DOC, DOCX or a clear image.")
        if not (text or "").strip():
            raise HTTPException(422, "No text found in this resume. If it is a photo or scan, please upload a clearer copy.")
        fields, meta = extract(text)
        try:
            years, _ = extract_experience(text)
        except Exception:
            years = None
        form, status = _to_form(fields, years)
        return {"ok": True, "form": form, "status": status, "fields": fields,
                "meta": {"textMethod": method, "durationMs": int((time.perf_counter() - t0) * 1000),
                         "detectedCountry": meta.get("detectedCountry"),
                         "extractionStatus": meta.get("extractionStatus")}}
    finally:
        _slots.release()


@router.post("/autofill", summary="Careers page: upload a resume -> values to pre-fill the Apply Job form (nothing is stored)")
async def public_autofill(
    request: Request,
    file: Annotated[UploadFile, File(description="Resume: PDF, DOC, DOCX, RTF, TXT or image")],
):
    """
    Returns `form` (flat values for the Apply Job form), `status` (per field:
    `extracted` / `low_confidence` / `not_extracted`) and `fields` (full descriptors, same as /extract).

    Nothing is saved: the file is deleted right after reading. Limits per visitor IP:
    PUBLIC_RATE_PER_MIN per minute and PUBLIC_RATE_PER_HOUR per hour (HTTP 429 with Retry-After).
    """
    _rate_check(_client_ip(request))
    name = os.path.basename(file.filename or "")
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported file type '{ext or 'none'}'. Allowed: {', '.join(sorted(ALLOWED_EXT))}")
    content = await file.read(MAX_FILE_MB * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(400, "Empty file uploaded")
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {MAX_FILE_MB} MB")
    fd, path = tempfile.mkstemp(suffix=ext, prefix="pub_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        if ext == ".pdf" and _pdf_pages(path) > MAX_PDF_PAGES:
            raise HTTPException(413, f"Resume has more than {MAX_PDF_PAGES} pages. Please upload a shorter resume.")
        result = await run_in_threadpool(_work, path, name)
        log.info("public autofill ok: status=%s %sms", result["meta"]["extractionStatus"], result["meta"]["durationMs"])
        return result
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
