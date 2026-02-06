import re
from datetime import datetime
import math

NOW = datetime.now()

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

# ================= DATE PARSER =================

def parse_date_safe(text):
    text = text.lower().strip()

    # Aug 2020
    parts = text.split()
    if len(parts) == 2 and parts[0] in MONTHS:
        return datetime(int(parts[1]), MONTHS[parts[0]], 1)

    # 06/2018
    mm_yyyy = re.match(r'(\d{1,2})[/-](\d{4})', text)
    if mm_yyyy:
        return datetime(int(mm_yyyy.group(2)), int(mm_yyyy.group(1)), 1)

    # 2018
    if text.isdigit() and len(text) == 4:
        return datetime(int(text), 1, 1)

    return None


# ================= DIRECT EXPERIENCE =================

def extract_direct_experience(text):

    patterns = [
        r'(\d{1,2}\.\d+)\s*\+?\s*(years|yrs)',
        r'(\d{1,2})\s*\+?\s*(years|yrs)',
        r'total experience[:\s]+(\d{1,2}\.?\d*)',
        r'experience[:\s]+(\d{1,2}\.?\d*)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None


# ================= DATE RANGE =================

def calculate_from_dates(text):

    pattern = r'([A-Za-z]+\s\d{4}|\d{1,2}[/-]\d{4}|\d{4})\s*(?:-|–|to)\s*(present|current|till date|[A-Za-z]+\s\d{4}|\d{1,2}[/-]\d{4}|\d{4})'

    matches = re.findall(pattern, text, re.IGNORECASE)

    if not matches:
        return None

    ranges = []

    for start, end in matches:

        start_date = parse_date_safe(start)
        end_date = NOW if end.lower() in ["present", "current", "till date"] else parse_date_safe(end)

        if not start_date or not end_date:
            continue

        if end_date < start_date:
            continue

        ranges.append((start_date, end_date))

    if not ranges:
        return None

    # 🔥 Merge overlapping ranges (VERY IMPORTANT)
    ranges.sort()

    merged = [ranges[0]]

    for current in ranges[1:]:
        prev = merged[-1]

        if current[0] <= prev[1]:
            merged[-1] = (prev[0], max(prev[1], current[1]))
        else:
            merged.append(current)

    total_months = 0

    for start, end in merged:
        months = (end.year - start.year) * 12 + (end.month - start.month)
        total_months += months

    return total_months / 12


# ================= FINAL EXPERIENCE =================

def calculate_experience(text):

    text = text.lower()

    # ⭐ Priority 1 — Direct mention
    direct = extract_direct_experience(text)
    if direct:
        return math.floor(direct)

    # ⭐ Priority 2 — Date calculation
    calculated = calculate_from_dates(text)
    if calculated:
        return math.floor(calculated)

    # ⭐ Safe fallback
    return 0
