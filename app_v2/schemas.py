"""
Pydantic models for the review form (POST /review) + the extracted-vs-reviewed diff.
Field names are camelCase to match the AVR frontend / v1 API contract.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app_v2.constants import FIELD_KEYS


class EmailItem(BaseModel):
    emailAddress: str = Field(..., max_length=120)
    isPrimary: bool = False

    @field_validator("emailAddress")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", v):
            raise ValueError(f"invalid email: {v}")
        return v


class PhoneItem(BaseModel):
    countryCode: str = Field("+91", max_length=6)
    mobileNumber: str = Field(..., max_length=20)
    isPrimary: bool = False

    @field_validator("countryCode")
    @classmethod
    def _cc(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("+"):
            v = "+" + v
        if not re.fullmatch(r"\+\d{1,4}", v):
            raise ValueError(f"invalid country code: {v}")
        return v

    @field_validator("mobileNumber")
    @classmethod
    def _num(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if not 6 <= len(digits) <= 15:
            raise ValueError(f"invalid mobile number: {v}")
        return digits


class CertificateItem(BaseModel):
    name: str = Field("", max_length=200)
    fileId: Optional[str] = None
    fileName: Optional[str] = None


class LocationItem(BaseModel):
    country: str = Field("", max_length=80)
    state: str = Field("", max_length=80)
    city: str = Field("", max_length=80)


class AddressItem(BaseModel):
    address: str = Field("", max_length=400)
    city: str = Field("", max_length=80)
    state: str = Field("", max_length=80)
    country: str = Field("", max_length=80)
    pinCode: str = Field("", max_length=12)


class ReviewedFields(BaseModel):
    """Exactly what the Review & Edit column holds when the reviewer presses submit."""
    fullName: str = Field(..., min_length=1, max_length=120)
    surname: str = Field("", max_length=80)
    # Date of birth: stored as DD/MM/YYYY. Also accepts YYYY-MM-DD (HTML date input),
    # DD-MM-YYYY, DD.MM.YYYY and "12 Mar 1990".
    dateOfBirth: str = Field("", max_length=40)
    # Marital Status: one of /options -> maritalStatuses (Single, Married, Divorced, Widowed, Separated)
    maritalStatus: str = Field("", max_length=40)
    emails: list[EmailItem] = Field(..., min_length=1)
    mobileNumbers: list[PhoneItem] = Field(default_factory=list)
    # Division (O&M / Ferro Alloy / Cokeoven ...). The UI makes it required; the API
    # accepts it empty and fills it from the job title when that is unambiguous.
    division: str = Field("", max_length=80)
    divisionId: Optional[int] = None
    jobTitle: str = Field(..., min_length=1, max_length=120)
    yearsOfExperience: str = Field("", max_length=30)
    educationQualification: str = Field("", max_length=80)
    certificates: list[CertificateItem] = Field(default_factory=list)
    currentWorkLocation: LocationItem = Field(default_factory=LocationItem)
    permanentAddress: AddressItem = Field(default_factory=AddressItem)
    pan: str = Field("", max_length=12)
    aadhar: str = Field("", max_length=14)

    @field_validator("fullName", "surname", "division", "jobTitle", "yearsOfExperience", "educationQualification")
    @classmethod
    def _strip(cls, v: str) -> str:
        return re.sub(r"\s+", " ", v or "").strip()

    @field_validator("dateOfBirth")
    @classmethod
    def _dob(cls, v: str) -> str:
        from datetime import date
        from app_v2.personal import find_date, fmt
        v = (v or "").strip()
        if not v:
            return ""
        v = v.split("T")[0]  # "1990-03-12T00:00:00.000Z" from JS date pickers
        dt, _ = find_date(v, user_input=True)
        if not dt:
            raise ValueError("Date of birth must be a real date in DD/MM/YYYY format")
        if dt > date.today() or dt.year < 1900:
            raise ValueError("Date of birth cannot be in the future or before 1900")
        return fmt(dt)

    @field_validator("maritalStatus")
    @classmethod
    def _marital(cls, v: str) -> str:
        from app_v2.personal import normalize_marital
        v = re.sub(r"\s+", " ", v or "").strip()
        if not v:
            return ""
        # known wording -> canonical option; anything else is kept as sent (never rejected)
        return normalize_marital(v) or v[:1].upper() + v[1:]

    @field_validator("pan")
    @classmethod
    def _pan(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if v and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", v):
            raise ValueError("PAN must look like ABCDE1234F")
        return v

    @field_validator("aadhar")
    @classmethod
    def _aadhar(cls, v: str) -> str:
        v = re.sub(r"\D", "", v or "")
        if v and len(v) != 12:
            raise ValueError("Aadhaar must be 12 digits")
        return v

    @model_validator(mode="after")
    def _primary_flags(self):
        if self.emails and not any(e.isPrimary for e in self.emails):
            self.emails[0].isPrimary = True
        if self.mobileNumbers and not any(p.isPrimary for p in self.mobileNumbers):
            self.mobileNumbers[0].isPrimary = True
        self._resolve_division()
        if not self.permanentAddress.country:
            self.permanentAddress.country = self.currentWorkLocation.country or "India"
        return self


    def _resolve_division(self) -> None:
        """Canonical division name + id from the live AVR list.
        - known name (any case/spacing) → canonical name + id
        - empty division → filled from the job title when it belongs to exactly one division
        - divisionId only → name filled from the id
        - unknown name + valid divisionId → name taken from the id
        - unknown name, no valid id → kept as sent (divisionId None) so a brand-new division is never rejected
        """
        from app_v2.job_titles import divisions_for_title, get_divisions, resolve_division
        if self.division:
            hit = resolve_division(self.division)
            if hit:
                self.division, self.divisionId = hit["name"], hit["id"]
            else:
                by_id = next((d for d in get_divisions() if d["id"] == self.divisionId), None) \
                    if self.divisionId is not None else None
                if by_id:
                    self.division = by_id["name"]
                else:
                    self.divisionId = None
            return
        if self.divisionId is not None:
            by_id = next((d for d in get_divisions() if d["id"] == self.divisionId), None)
            if by_id:
                self.division = by_id["name"]
                return
            self.divisionId = None
        hits = divisions_for_title(self.jobTitle)
        if len(hits) == 1:
            self.division, self.divisionId = hits[0]["name"], hits[0]["id"]


class ReviewSubmit(BaseModel):
    uid: str = Field(..., min_length=8, max_length=40)
    fields: ReviewedFields
    reviewer: Optional[str] = Field(None, max_length=120)
    notes: Optional[str] = Field(None, max_length=1000)


# ── diff helpers ─────────────────────────────────────────────────────────────

def _norm(v: Any) -> Any:
    """Normalise a value so cosmetic differences don't count as a correction."""
    if isinstance(v, str):
        return re.sub(r"\s+", " ", v).strip().lower()
    if isinstance(v, list):
        out = []
        for item in v:
            if isinstance(item, dict):
                d = {k: _norm(x) for k, x in item.items() if k not in ("isPrimary", "fileId", "fileName")}
                out.append(tuple(sorted(d.items())))
            else:
                out.append(_norm(item))
        return sorted(out, key=str)
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    return v


def build_corrections(extracted: dict, reviewed: dict) -> tuple[dict, int, int]:
    """
    extracted: {key: descriptor}   reviewed: {key: plain value}
    Returns (corrections, total, changed) where corrections[key] =
      {"extracted": ..., "reviewed": ..., "changed": bool, "extractedStatus": ..., "action": ...}
    action ∈ confirmed | corrected | filled | cleared
    """
    corrections: dict = {}
    changed = 0
    for key in FIELD_KEYS:
        desc = extracted.get(key) or {}
        ext_val = desc.get("value", "")
        rev_val = reviewed.get(key, "")
        same = _norm(ext_val) == _norm(rev_val)
        ext_empty = _norm(ext_val) in ("", [], {}, None) or (isinstance(ext_val, dict) and not any(_norm(ext_val).values()))
        rev_empty = _norm(rev_val) in ("", [], {}, None) or (isinstance(rev_val, dict) and not any(_norm(rev_val).values()))
        if same:
            action = "confirmed"
        elif ext_empty and not rev_empty:
            action = "filled"
        elif rev_empty and not ext_empty:
            action = "cleared"
        else:
            action = "corrected"
        if not same:
            changed += 1
        corrections[key] = {
            "extracted": ext_val, "reviewed": rev_val, "changed": not same,
            "extractedStatus": desc.get("status", "not_extracted"),
            "extractedConfidence": desc.get("confidence", 0), "action": action,
        }
    return corrections, len(FIELD_KEYS), changed
