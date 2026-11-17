"""
Date of birth + Marital Status for v2 — shared by the extractor (/extract) and the
review form validation (/review), so both use exactly the same rules.

Date of birth is always returned / stored as DD/MM/YYYY (the review form format).
Marital Status is always one of constants.MARITAL_STATUS_OPTIONS.
"""
from __future__ import annotations

import re
from datetime import date

from app_v2 import constants as C

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_ORD = r"(?:st|nd|rd|th)?"

_PAT_ISO = re.compile(r"(?<!\d)(\d{4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})(?!\d)")
_PAT_NUM = re.compile(r"(?<!\d)(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{4}|\d{2})(?!\d)")
_PAT_DMY = re.compile(r"(?<!\d)(\d{1,2})" + _ORD + r"[\s\-/.,]*(?:of\s+)?" + _MON + r"\b[\s\-/.,']*(\d{4}|\d{2})(?!\d)", re.I)
_PAT_MDY = re.compile(r"\b" + _MON + r"\b[\s\-/.]*(\d{1,2})" + _ORD + r"[\s,\-/.]*(\d{4}|\d{2})(?!\d)", re.I)

# "Date of Birth", "DOB", "D.O.B", "Birth Date", "Born on" ...
_DOB_LABEL = re.compile(r"(?:date\s*of\s*birth|birth\s*date|\bd\s*\.?\s*o\s*\.?\s*b\b\.?|\bborn(?:\s+on)?\b)", re.I)
# "Marital Status" (incl. the common misspelling "Martial Status"), "Civil Status"
_MS_LABEL = re.compile(r"(?:mar(?:it|ti)al\s*status|\bmar(?:it|ti)al\b|civil\s*status)", re.I)
_MS_STATUS_LABEL = re.compile(r"\bstatus\s*[:\-–=]\s*", re.I)
_MS_WORDS = re.compile(
    r"\b(" + "|".join(sorted((re.escape(k).replace(r"\ ", r"\s*") for k in C.MARITAL_STATUS_ALIASES),
                             key=len, reverse=True)) + r")\b", re.I)


def _year(y: str, today: date) -> int:
    n = int(y)
    if len(y) == 4:
        return n
    full = 2000 + n
    return full if full <= today.year - 14 else 1900 + n  # "05" -> 2005, "95" -> 1995


def _mk(d: int, m: int, y: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _age_ok(dt: date, today: date) -> bool:
    age = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
    return 14 <= age <= 80


def find_date(s: str, today: date | None = None, user_input: bool = False) -> tuple[date | None, float]:
    """First real date in s -> (date, certainty 0-1). Day-first (DD/MM) like India / Nigeria.
    user_input=True: strict (no US month/day guessing) for what the reviewer typed."""
    today = today or date.today()
    found: list[tuple[int, date, float]] = []
    for m in _PAT_ISO.finditer(s):
        dt = _mk(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if dt:
            found.append((m.start(), dt, 1.0))
    for m in _PAT_NUM.finditer(s):
        a, b, y = int(m.group(1)), int(m.group(2)), _year(m.group(3), today)
        if a > 12 and b <= 12:
            dt, cert = _mk(a, b, y), 1.0
        elif b > 12 and a <= 12:
            if user_input:
                continue  # MM/DD is not accepted from the form
            dt, cert = _mk(b, a, y), 0.75  # resume written US-style (month first)
        else:
            dt, cert = _mk(a, b, y), (1.0 if a == b else 0.85)  # both <= 12: day-first
        if dt:
            found.append((m.start(), dt, cert))
    for m in _PAT_DMY.finditer(s):
        mon = m.group(2).lower()
        dt = _mk(int(m.group(1)), _MONTHS["sep" if mon.startswith("sep") else mon[:3]], _year(m.group(3), today))
        if dt:
            found.append((m.start(), dt, 1.0))
    for m in _PAT_MDY.finditer(s):
        mon = m.group(1).lower()
        dt = _mk(int(m.group(2)), _MONTHS["sep" if mon.startswith("sep") else mon[:3]], _year(m.group(3), today))
        if dt:
            found.append((m.start(), dt, 1.0))
    if not found:
        return None, 0.0
    found.sort(key=lambda x: x[0])
    _, dt, cert = found[0]
    return dt, cert


_OTHER_LABEL = re.compile(r"^\s*[A-Za-z][A-Za-z .&/()]{2,40}\s*[:=]")
_INLINE_LABEL = re.compile(r"(?:\s{2,}|\t|\s\|\s)[A-Za-z][A-Za-z .&/()]{2,40}\s*[:=]")


def _value_windows(text: str, end: int) -> list[str]:
    """Where the value of a label can be: the rest of the label's line (cut at the next
    'Other Label:' on the same line), then up to 2 short lines below (table layouts).
    Stops at the next 'Other Label:' line so a blank DOB never takes a joining date."""
    rest = text[end:end + 300]
    lines = rest.split("\n")
    first = _INLINE_LABEL.split(lines[0])[0][:70]
    out = [first]
    for ln in lines[1:3]:
        s = ln.strip()
        if not s:
            continue
        if _OTHER_LABEL.match(s) or len(s) > 40:
            break
        out.append(s)
    return [re.sub(r"\s+", " ", w) for w in out if w.strip()]


def fmt(dt: date) -> str:
    return dt.strftime("%d/%m/%Y")


def extract_dob(text: str, today: date | None = None) -> tuple[str, float, str, str]:
    """-> (DD/MM/YYYY, confidence, source, iso). Only dates next to a DOB label are used,
    so job/education dates are never taken as a birth date."""
    today = today or date.today()
    for m in _DOB_LABEL.finditer(text or ""):
        for window in _value_windows(text, m.end()):
            dt, cert = find_date(window, today)
            if dt:
                if _age_ok(dt, today):
                    conf = round(0.92 * cert, 2)
                    return fmt(dt), conf, f"label '{m.group(0).strip()}'", dt.isoformat()
                break
    return "", 0.0, "none", ""


def normalize_marital(value: str) -> str:
    """Any wording -> one of MARITAL_STATUS_OPTIONS, or '' if not recognised."""
    v = re.sub(r"[\s\-]+", " ", (value or "").strip().lower())
    if not v:
        return ""
    if v in C.MARITAL_STATUS_ALIASES:
        return C.MARITAL_STATUS_ALIASES[v]
    m = _MS_WORDS.search(v)
    if m:
        return C.MARITAL_STATUS_ALIASES.get(re.sub(r"[\s\-]+", " ", m.group(1).lower()), "")
    return ""


def extract_marital(text: str) -> tuple[str, float, str]:
    """-> (option, confidence, source). Uses the 'Marital Status' label; a bare 'Status: Married'
    line is accepted with lower confidence."""
    text = text or ""
    for m in _MS_LABEL.finditer(text):
        for window in _value_windows(text, m.end()):
            w = _MS_WORDS.search(window[:45])
            if w:
                val = normalize_marital(w.group(1))
                if val:
                    return val, 0.92, f"label '{m.group(0).strip()}'"
                break
    for m in _MS_STATUS_LABEL.finditer(text):
        w = _MS_WORDS.match(text, m.end())
        if w:
            val = normalize_marital(w.group(1))
            if val:
                return val, 0.75, "label 'Status'"
    return "", 0.0, "none"
