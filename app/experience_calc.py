import re
import math
from datetime import datetime

NOW = datetime.now()

MONTHS: dict[str, int] = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3,  "apr": 4, "april": 4,
    "may": 5, "jun": 6,    "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9,
    "oct": 10,"october": 10,"nov": 11,"november": 11,
    "dec": 12,"december": 12,
}


def parse_date_safe(text: str) -> datetime | None:
    if not text:
        return None
    try:
        text = text.lower().strip()

        # DD-MM-YYYY or DD/MM/YYYY
        m = re.match(r"(\d{2})[/-](\d{2})[/-](\d{4})", text)
        if m:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))

        # MM/YYYY or MM-YYYY
        m = re.match(r"(\d{1,2})[/-](\d{4})", text)
        if m:
            return datetime(int(m.group(2)), int(m.group(1)), 1)

        # Month YYYY (e.g. "August 2019")
        m = re.match(r"([a-z]+)\s+(\d{4})", text)
        if m:
            month = MONTHS.get(m.group(1))
            if month:
                return datetime(int(m.group(2)), month, 1)

    except Exception:
        pass
    return None


def extract_direct_experience(text: str) -> float | None:
    patterns = [
        r"(\d{1,2}\.\d+)\s*\+?\s*(?:years|yrs|year|yr)\b",
        r"(\d{1,2})\s*\+?\s*(?:years|yrs|year|yr)\b",
        r"total\s+experience[:\s]+(\d{1,2})\s*(?:years|yrs|year|yr)\b",
        r"experience[:\s]+(\d{1,2})\s*(?:years|yrs|year|yr)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def calculate_from_dates(text: str) -> float | None:
    if not text:
        return None
    try:
        # Isolate experience section
        m = re.search(
            r"(experience.*?)(education|skills|projects|certifications|personal|$)",
            text, re.IGNORECASE | re.DOTALL,
        )
        section = m.group(1) if m else text

        date_pattern = (
            r"(\d{2}[/-]\d{2}[/-]\d{4}|\d{1,2}[/-]\d{4}|[A-Za-z]+\s\d{4})"
            r"\s*(?:-|–|to)\s*"
            r"(present|current|till|working|\d{2}[/-]\d{2}[/-]\d{4}|\d{1,2}[/-]\d{4}|[A-Za-z]+\s\d{4})"
        )
        matches = re.findall(date_pattern, section, re.IGNORECASE)
        if not matches:
            return None

        ranges = []
        for start_raw, end_raw in matches:
            start = parse_date_safe(start_raw)
            end   = NOW if end_raw.lower() in ("present", "current", "till", "working") \
                       else parse_date_safe(end_raw)

            if not start or not end:
                continue
            if start.year < 1990 or end < start:
                continue
            ranges.append((start, end))

        if not ranges:
            return None

        # Merge overlapping ranges
        ranges.sort()
        merged = [ranges[0]]
        for cur in ranges[1:]:
            prev = merged[-1]
            if cur[0] <= prev[1]:
                merged[-1] = (prev[0], max(prev[1], cur[1]))
            else:
                merged.append(cur)

        total_months = sum(
            max(0, (e.year - s.year) * 12 + (e.month - s.month))
            for s, e in merged
        )
        return total_months / 12

    except Exception:
        return None


def calculate_experience(text: str) -> int:
    if not text:
        return 0
    try:
        tl = text.lower()
        direct     = extract_direct_experience(tl)
        calculated = calculate_from_dates(tl)

        d = math.floor(direct)     if direct     else 0
        c = math.floor(calculated) if calculated else 0
        return max(d, c)
    except Exception:
        return 0
