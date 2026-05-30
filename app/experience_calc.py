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

def extract_total_experience_priority(text):
    text = text.lower()

    # 1. X+ years (highest priority)
    match = re.search(r'(\d+)\+?\s*years? of experience', text)
    if match:
        return int(match.group(1))

    # 2. Total experience
    match = re.search(r'(total|overall)\s*(\d+)\s*years?', text)
    if match:
        return int(match.group(2))

    # 3. Standalone "X years experience"
    match = re.search(r'(\d+)\s*years?\s*(experience)?', text)
    if match:
        return int(match.group(1))

    return None
# DATE PARSER 

def parse_date_safe(text):

    if not text:
        return None

    try:
        text = text.lower().strip()

        # DD-MM-YYYY or DD/MM/YYYY
        match = re.match(r'(\d{2})[/-](\d{2})[/-](\d{4})', text)
        if match:
            return datetime(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1))
            )

        # MM/YYYY or MM-YYYY
        match = re.match(r'(\d{1,2})[/-](\d{4})', text)
        if match:
            return datetime(
                int(match.group(2)),
                int(match.group(1)),
                1
            )

        # Month YYYY
        match = re.match(r'([a-zA-Z]+)\s+(\d{4})', text)
        if match:
            month = MONTHS.get(match.group(1))
            if month:
                return datetime(
                    int(match.group(2)),
                    month,
                    1
                )

    except Exception:
        return None

    return None


#  DIRECT EXPERIENCE

def extract_direct_experience(text):

    if not text:
        return 0

    matches = []

    patterns = [
        r'(\d{1,2})\+?\s*(years|yrs|year)',
        r'over\s*(\d{1,2})\s*years',
        r'more than\s*(\d{1,2})\s*years',
        r'total\s*experience\s*(?:is|:)?\s*(\d{1,2})',
        r'experience\s*[:\-]?\s*(\d{1,2})'
    ]

    for pattern in patterns:
        found = re.findall(pattern, text)

        for m in found:
            val = m[0] if isinstance(m, tuple) else m

            if str(val).isdigit():
                v = int(val)

                if 0 < v <= 40:
                    matches.append(v)
                if v > 40:
                    continue

    # 🔥 CRITICAL FIX
    if len(matches) == 0:
        return 0

    return max(matches)
import re
from datetime import datetime


def calculate_from_dates(text):

    if not text:
        return 0

    text = text.lower()
    text = text.replace("–", "-").replace("—", "-")

    try:
        # =====================================
        # 1. FRESHER CHECK
        # =====================================
        if "fresher" in text or "no experience" in text:
            return 0

        # =====================================
        # 2. DIRECT EXPERIENCE (HIGHEST PRIORITY)
        # =====================================
        direct_patterns = [
            r'(\d+)\+?\s*years? of experience',
            r'(total|overall)\s*(\d+)\s*years?',
            r'(\d+)\s*years?\s*experience'
        ]

        for pattern in direct_patterns:
            match = re.search(pattern, text)
            if match:
                for g in match.groups():
                    if g and g.isdigit():
                        return int(g)

        # =====================================
        # 3. DATE RANGE EXTRACTION
        # =====================================
        pattern = r'(\d{4}|[a-zA-Z]{3,9}\s?\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})\s*(?:-|to)\s*(\d{4}|present|current|till|working|[a-zA-Z]{3,9}\s?\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})'

        matches = re.findall(pattern, text)

        if not matches:
            return 0

        ranges = []

        for start, end in matches:

            # -------------------------------
            # START YEAR
            # -------------------------------
            start_year = None
            year_match = re.search(r'(\d{4})', start)
            if year_match:
                start_year = int(year_match.group(1))

            if not start_year or start_year < 1990:
                continue

            # -------------------------------
            # END YEAR
            # -------------------------------
            if end in ["present", "current", "till", "working"]:
                end_year = datetime.now().year
            else:
                year_match = re.search(r'(\d{4})', end)
                end_year = int(year_match.group(1)) if year_match else None

            if not end_year or end_year < start_year:
                continue

            ranges.append((start_year, end_year))

        if not ranges:
            return 0

        # =====================================
        # 4. MERGE OVERLAPPING RANGES
        # =====================================
        ranges = sorted(ranges)

        merged = [ranges[0]]

        for current in ranges[1:]:
            prev_start, prev_end = merged[-1]
            curr_start, curr_end = current

            if curr_start <= prev_end:  # overlap
                merged[-1] = (prev_start, max(prev_end, curr_end))
            else:
                merged.append(current)

        # =====================================
        # 5. TOTAL EXPERIENCE (ALL JOBS)
        # =====================================
        total_years = sum(end - start for start, end in merged)

        return total_years

    except Exception:
        return 0
def calculate_experience(text):

    text_lower = text.lower()

    # ✅ STEP 1: FRESHER CHECK
    if "fresher" in text_lower:
        return 0

    # ✅ STEP 2: DIRECT EXPERIENCE (NEW ADD)
    direct_exp = extract_total_experience_priority(text)
    if direct_exp is not None:
        return direct_exp

    values = []

    # ===============================
    # 2. STRONG DIRECT (MOST IMPORTANT)
    # ===============================
    direct_patterns = [
        r'(\d{1,2})\+?\s*(years|yrs)',
        r'(\d{1,2})\s*year',
        r'over\s*(\d{1,2})\s*years',
        r'more than\s*(\d{1,2})\s*years',
        r'(\d{1,2})\s*years experience',
        r'experience\s*[:\-]?\s*(\d{1,2})'
    ]

    for pattern in direct_patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            val = m[0] if isinstance(m, tuple) else m
            if val.isdigit():
                v = int(val)
                if 0 < v <= 30:
                    values.append(v)

    # ===============================
    # 3. CONTEXT BASED (CRITICAL)
    # ===============================
    context_patterns = [
        r'worked.*?(\d{1,2})\s*years',
        r'experience of (\d{1,2})',
        r'(\d{1,2})\s*years worked',
    ]

    for pattern in context_patterns:
        matches = re.findall(pattern, text)
        for val in matches:
            if val.isdigit():
                v = int(val)
                if 0 < v <= 30:
                    values.append(v)

    # ===============================
    # 4. DATE BASED (SECONDARY)
    # ===============================
    date_years = calculate_from_dates(text)

    # ===============================
    # 5. FINAL DECISION
    # ===============================

    if values:
        if date_years:
            best = min(values)   # prevents inflated values like 31
        else:
            best = max(values)

        # validate with date if available
        if date_years and abs(best - date_years) <= 5:
            return int(date_years)
        if best > 40:
            return date_years if date_years else 0
        return best

    if date_years:
        return int(date_years)

    return 0
