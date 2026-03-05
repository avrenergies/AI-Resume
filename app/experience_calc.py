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



def extract_direct_experience(text):

    if not text:
        return None

    patterns = [

        # contain year/years
        r'(\d{1,2}\.\d+)\s*\+?\s*(years|yrs|year|yr)\b',
        r'(\d{1,2})\s*\+?\s*(years|yrs|year|yr)\b',

        # total experience: x years
        r'total\s+experience[:\s]+(\d{1,2})\s*(years|yrs|year|yr)\b',

        # experience: x years
        r'experience[:\s]+(\d{1,2})\s*(years|yrs|year|yr)\b'
    ]

    for pattern in patterns:

        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            try:
                return float(match.group(1))
            except:
                continue

    return None



def calculate_from_dates(text):

    if not text:
        return None

    try:

        # isolate experience section
        match = re.search(
            r'(experience.*?)(education|skills|projects|certifications|personal|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )

        exp_section = match.group(1) if match else text

        pattern = r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{1,2}[/-]\d{4}|[A-Za-z]+\s\d{4})\s*(?:-|–|to)\s*(present|current|till|working|\d{2}[/-]\d{2}[/-]\d{4}|\d{1,2}[/-]\d{4}|[A-Za-z]+\s\d{4})'

        matches = re.findall(pattern, exp_section, re.IGNORECASE)

        if not matches:
            return None

        ranges = []

        for start, end in matches:

            start_date = parse_date_safe(start)

            if end.lower() in ["present", "current", "till", "working"]:
                end_date = NOW
            else:
                end_date = parse_date_safe(end)

            # Skip invalid dates
            if not start_date or not end_date:
                continue

            # Skip unrealistic years
            if start_date.year < 1990:
                continue

            if end_date < start_date:
                continue

            ranges.append((start_date, end_date))

        if not ranges:
            return None

        # Merge overlapping ranges
        ranges.sort()
        merged = [ranges[0]]

        for current in ranges[1:]:
            prev = merged[-1]

            if current[0] <= prev[1]:
                merged[-1] = (
                    prev[0],
                    max(prev[1], current[1])
                )
            else:
                merged.append(current)

        # Calculate total months
        total_months = 0

        for start, end in merged:
            months = (
                (end.year - start.year) * 12 +
                (end.month - start.month)
            )

            if months > 0:
                total_months += months

        return total_months / 12

    except Exception:
        return None



def calculate_experience(text):

    if not text:
        return 0

    try:

        text = text.lower()

        direct = extract_direct_experience(text)
        calculated = calculate_from_dates(text)

        direct_val = math.floor(direct) if direct else 0
        calculated_val = math.floor(calculated) if calculated else 0

        # return maximum valid value
        return max(direct_val, calculated_val)

    except Exception:
        return 0

