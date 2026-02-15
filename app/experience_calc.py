import re
import math
from datetime import datetime

NOW = datetime.now()


# ================= MONTH MAP =================

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

    # Normalize OCR dash variants
    text = text.replace("–", "-").replace("—", "-")

    # Format: Aug 2020
    parts = text.split()
    if len(parts) == 2 and parts[0] in MONTHS:
        try:
            return datetime(int(parts[1]), MONTHS[parts[0]], 1)
        except:
            return None

    # Format: 06/2018 or 6-2018
    mm_yyyy = re.match(r'(\d{1,2})[/-](\d{4})', text)
    if mm_yyyy:
        try:
            return datetime(int(mm_yyyy.group(2)), int(mm_yyyy.group(1)), 1)
        except:
            return None

    # Format: 2018
    if text.isdigit() and len(text) == 4:
        try:
            return datetime(int(text), 1, 1)
        except:
            return None

    return None


# ================= DIRECT EXPERIENCE =================

def extract_direct_experience(text):

    patterns = [
        r'(\d{1,2}\.\d+)\s*\+?\s*(years|yrs)',
        r'(\d{1,2})\s*\+?\s*(years|yrs)',
        r'total experience[:\s]+(\d{1,2}\.?\d*)',
        r'overall experience[:\s]+(\d{1,2}\.?\d*)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                if 0 < value < 50:  # sanity check
                    return value
            except:
                continue

    return None


# ================= DATE RANGE EXTRACTION =================

def calculate_from_dates(text):

    text = text.lower()

    # Normalize dash types
    text = text.replace("–", "-").replace("—", "-")

    # Prevent education years being mistaken
    text = re.sub(r'(b\.tech|b\.e|m\.tech|mba|mca).*?\d{4}', '', text)

    pattern = r'([a-z]+\s\d{4}|\d{1,2}[/-]\d{4}|\d{4})\s*(?:-|to)\s*(present|current|till date|till now|[a-z]+\s\d{4}|\d{1,2}[/-]\d{4}|\d{4})'

    matches = re.findall(pattern, text, re.IGNORECASE)

    if not matches:
        return None

    ranges = []

    for start, end in matches:

        start_date = parse_date_safe(start)

        if end in ["present", "current", "till date", "till now"]:
            end_date = NOW
        else:
            end_date = parse_date_safe(end)

        if not start_date or not end_date:
            continue

        if end_date < start_date:
            continue

        ranges.append((start_date, end_date))

    if not ranges:
        return None

    # ================= MERGE OVERLAPPING RANGES =================

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

    if total_months <= 0:
        return None

    return total_months / 12


# ================= FINAL EXPERIENCE =================

def calculate_experience(text):

    text = text.lower()

    # ⭐ Priority 1 — Direct mention
    direct = extract_direct_experience(text)
    if direct is not None:
        return math.floor(direct)

    # ⭐ Priority 2 — Date calculation
    calculated = calculate_from_dates(text)
    if calculated is not None:
        return math.floor(calculated)

    # ⭐ Fallback: detect multiple years like 2019 2020 2021 pattern
    years = re.findall(r'\b20\d{2}\b', text)
    years = sorted(set(years))

    if len(years) >= 2:
        try:
            diff = int(years[-1]) - int(years[0])
            if 0 < diff < 40:
                return diff
        except:
            pass

    return 0
