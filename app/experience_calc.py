import re
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
    "dec": 12, "december": 12,
}
 
# ================= PRESENT TOKENS =================
 
PRESENT_TOKENS = {
    "present", "current", "currently", "till date", "till now",
    "to date", "ongoing", "continue", "continuing",
    "date", "now", "still date", "still now", "still",
    "till present", "todate", "tilldate",
}
 
# ================= FRESHER GUARD =================
 
FRESHER_PATTERN = re.compile(
    r'\b(fresher|fresh\s+graduate|freshers|entry[\s-]level\s+fresher)\b',
    re.IGNORECASE
)
 
# ================= SECTION HEADING PATTERNS =================
 
EDU_HEADING = re.compile(
    r'\b(education|academic|qualification|certif)\b',
    re.IGNORECASE
)
 
WORK_HEADING = re.compile(
    r'(?:work\s*experience|employment\s*history|professional\s*experience'
    r'|professionalexperience'            # ← no-space variant
    r'|experience\s*detail|job\s*history|career\s*history)',
    re.IGNORECASE
)
 
SUMMARY_HEADING = re.compile(
    r'\b(career\s*summary|career\s*objective|objective|professional\s*summary'
    r'|profile\s*summary|summary|about\s*me|professional\s*profile)\b',
    re.IGNORECASE
)
 
EMPLOYMENT_CONTEXT = re.compile(
    r'\b(previous\s*employ(?:ee|ment|er)?'
    r'|current\s*employ(?:ee|ment|er)?'
    r'|present\s*employ(?:ee|ment|er)?'
    r'|previous\s*experience'
    r'|current\s*experience'
    r'|present\s*experience'
    r'|currently\s*working'
    r'|presently\s*working)\b',
    re.IGNORECASE
)
 
# ================= EDUCATION SECTION STRIPPER =================
 
def strip_education_block(text: str) -> str:
    """Remove education sections so their years don't pollute date calculations."""
    section_split = re.compile(
        r'(?=\n\s*(?:[A-Z][A-Z\s]{2,}|[A-Z][a-z]+(?:\s+[A-Za-z]+){0,3})\s*[:\n])',
    )
    sections = section_split.split(text)
    kept = []
    for section in sections:
        first_line = section.strip().split('\n')[0]
        if EDU_HEADING.search(first_line):
            continue
        kept.append(section)
    result = '\n'.join(kept)
    return result if result.strip() else text
 
 
# ================= FORMAT OUTPUT =================
 
def format_experience(total_months: float) -> str:
    """
    Convert total months to human-readable experience string.
    Output is YEARS ONLY — months never shown in output.

    Rules:
      < 7 months   -> "0 years"   (too short to count)
      7-11 months  -> "1 year"    (round up to 1 year)
      12+ months:
        rem < 6    -> "X years"   (drop remainder)
        rem >= 6   -> "X+1 years" (round up)
    """
    total_months_int = int(round(total_months))
 
    if total_months_int < 7:
        return "0 years"
 
    if total_months_int < 12:
        return "1 year"
 
    years = total_months_int // 12
    rem = total_months_int % 12
 
    if rem >= 6:
        years += 1
 
    return f"{years} year{'s' if years != 1 else ''}"
 
 
# ================= DATE PARSER =================
 
def parse_date_safe(raw: str):
    """Parse many date formats. Returns datetime or None."""
    text = raw.lower().strip()
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r'(\d{1,2})(st|nd|rd|th)\b', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
 
    # "Sep 2016", "Sep-2016", "Sep/2016", "September 2016"
    # "December2024" — month name directly followed by year (no space/separator)
    text_norm = re.sub(r'([a-z]+)[/\-](\d{4})', r'\1 \2', text)
    parts = text_norm.split()
    if len(parts) == 2 and parts[0] in MONTHS:
        try:
            return datetime(int(parts[1]), MONTHS[parts[0]], 1)
        except Exception:
            return None
        
    m = re.match(r'^([a-z]+)(\d{4})$', text)
    if m and m.group(1) in MONTHS:
        try:
             return datetime(int(m.group(2)), MONTHS[m.group(1)], 1)
        except Exception:
            return None
 
    # "06/2018", "6-2018"
    m = re.match(r'^(\d{1,2})[/-](\d{4})$', text)
    if m:
        try:
            return datetime(int(m.group(2)), int(m.group(1)), 1)
        except Exception:
            return None
 
    # "18.03.2024", "18-03-2024", "18/03/2024"
    m = re.match(r'^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$', text)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except Exception:
            return None
 
    # "20-feb-2014", "20 feb 2014"
    m = re.match(r'^(\d{1,2})[\s/-]([a-z]+)[\s/-](\d{4})$', text)
    if m and m.group(2) in MONTHS:
        try:
            return datetime(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
        except Exception:
            return None
 
    # bare year "2018"
    if re.fullmatch(r'\d{4}', text):
        try:
            return datetime(int(text), 1, 1)
        except Exception:
            return None
 
    return None
 
 
# ================= IS PRESENT =================
 
def is_present(raw: str) -> bool:
    """Return True if string means 'currently working / till today'."""
    text = raw.lower().strip()
    if text in PRESENT_TOKENS:
        return True
    for token in PRESENT_TOKENS:
        if len(token) > 3 and token in text:
            return True
    return False
 
 
# ================= DATE RANGE PATTERNS =================
 
_SEP = r'\s*(?:to|-|to\s*-|-\s*to)\s*'
 
_DATE_TOKEN = (
    r'(?:'
    r'[a-z]+[\s\-/]?\d{4}'                  # Sep 2016 / Sep-2016 / December2024
    r'|\d{1,2}[./-]\d{1,2}[./-]\d{4}'     # 18.03.2024
    r'|\d{1,2}[\s/-][a-z]+[\s/-]\d{4}'    # 20-feb-2014
    r'|\d{1,2}[/-]\d{4}'                   # 06/2018
    r'|\d{4}'                               # 2020
    r')'
)
 
_PRESENT_VARIANT = (
    r'(?:present|current(?:ly)?|till\s*date|till\s*now|till\s*present'
    r'|still\s*date|still\s*now|still'   
    r'|to\s*date|ongoing|continuing?'
    r'|date|now|todate|tilldate|currently\s*working)'
)
 
_RANGE_PATTERN = re.compile(
    rf'({_DATE_TOKEN})\s*{_SEP}\s*({_PRESENT_VARIANT}|{_DATE_TOKEN})',
    re.IGNORECASE
)
 
# "From Sep-2016" / "Since Jan 2018"
_OPEN_START_PATTERN = re.compile(
    rf'\b(?:from|since|w\.?e\.?f\.?)\s+({_DATE_TOKEN})',
    re.IGNORECASE
)
 
# "Sep-2016 onwards" / "Sep-2016 till date"
_OPEN_END_PATTERN = re.compile(
    rf'({_DATE_TOKEN})\s+(?:onwards?|till\s*now|till\s*date|to\s*present|to\s*date)',
    re.IGNORECASE
)
 
 
# ================= RANGE EXTRACTOR =================
 
def _extract_ranges(text: str) -> list:
    """
    Extract all (start, end) datetime pairs from text.
    Handles closed ranges, present ranges, open-start, open-end.
    """
    norm = text.lower()
    norm = norm.replace("\u2013", "-").replace("\u2014", "-")
    ranges = []
    seen_starts = set()
 
    # 1. Closed + present ranges
    for m in _RANGE_PATTERN.finditer(norm):
        start_raw = m.group(1).strip()
        end_raw = m.group(2).strip()
        start = parse_date_safe(start_raw)
        end = NOW if is_present(end_raw) else parse_date_safe(end_raw)
        if start and end and end >= start:
            months = (end.year - start.year) * 12 + (end.month - start.month)
            if 0 < months <= 600:
                ranges.append((start, end))
                seen_starts.add(start)
 
    # 2. Open-start: "From Sep-2016"
    for m in _OPEN_START_PATTERN.finditer(norm):
        start_raw = m.group(1).strip()
        start = parse_date_safe(start_raw)
        if start and start not in seen_starts:
            months = (NOW.year - start.year) * 12 + (NOW.month - start.month)
            if 0 < months <= 600:
                ranges.append((start, NOW))
                seen_starts.add(start)
 
    # 3. Open-end suffix: "Sep-2016 onwards"
    for m in _OPEN_END_PATTERN.finditer(norm):
        start_raw = m.group(1).strip()
        start = parse_date_safe(start_raw)
        if start and start not in seen_starts:
            months = (NOW.year - start.year) * 12 + (NOW.month - start.month)
            if 0 < months <= 600:
                ranges.append((start, NOW))
                seen_starts.add(start)
 
    return ranges
 
 
def _merge_and_sum(ranges: list):
    """Merge overlapping ranges, return total months as float or None."""
    if not ranges:
        return None
    ranges = sorted(set(ranges))
    merged = [list(ranges[0])]
    for cur_start, cur_end in ranges[1:]:
        prev = merged[-1]
        if cur_start <= prev[1]:
            prev[1] = max(prev[1], cur_end)
        else:
            merged.append([cur_start, cur_end])
    total = 0
    for start, end in merged:
        total += (end.year - start.year) * 12 + (end.month - start.month)
    return float(total) if total > 0 else None
 
 
def calculate_from_dates(text: str):
    """Extract all date ranges and return total months (float) or None."""
    return _merge_and_sum(_extract_ranges(text))
 
 
# ================= CAREER SUMMARY SCANNER =================
 
def extract_career_summary_dates(text: str):
    """
    Find career summary/objective section.
    If employment context keywords found, extract date ranges from that block.
    Handles: previous employment, current employment, currently working, etc.
    """
    lines = text.lower().split('\n')
    in_summary = False
    summary_lines = []
 
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if SUMMARY_HEADING.search(stripped):
            in_summary = True
            continue
        if in_summary:
            if WORK_HEADING.search(stripped):
                break
            if EDU_HEADING.search(stripped):
                break
            if re.match(r'^[A-Z\s]{5,}$', stripped.upper()) and len(stripped) > 4:
                break
            summary_lines.append(stripped)
 
    if not summary_lines:
        return None
 
    block = '\n'.join(summary_lines)
    if not EMPLOYMENT_CONTEXT.search(block):
        return None
 
    return calculate_from_dates(block)
 
 
# ================= DIRECT EXPERIENCE EXTRACTOR =================
 
def extract_direct_experience(text: str):
    """
    Extract explicitly stated total experience number.
    Returns years as float or None.
    ONLY used when no date ranges are found.

    Patterns:
      A: "Total experience: 11 years"
      B: "TotalworkingExperience-11 Years"
      C: "14+ YRS OF EXPERIENCE"
      D: "8+ years of experience in..."
      E: "18 years working experience"  (S1 - number BEFORE keyword)
      F: "Total Experience of 19+ years"
      G: "Total Experience of 19+ years" / "Experience of 18 years"
      H: "Total 08 years" / "Total 8 Years" — no "experience" word needed
      I: "Working Experience – 26 Years" / "Experience : 26 Years"
       
    """
    patterns = [

         # G: "Total Experience of 19+ years" / "Experience of 18 years"
        re.compile(
            r'(?:total|overall|aggregate|combined)?\s*'
            r'(?:experience|exp\.?)'
            r'\s+of\s+'
            r'(\d{1,2}(?:\.\d)?)\s*\+?'
            r"\s*(?:yr\s*s?|years?['\u2019]?s?|yrs)",
            re.IGNORECASE
        ),

        # H: "Total 08 years" / "Total 8 Years" — no "experience" word needed
        re.compile(
            r'(?:total|overall|aggregate|combined)\s+'
            r'(\d{1,2}(?:\.\d)?)\s*\+?'
            r"\s*(?:yr\s*s?|years?['\u2019]?s?|yrs)",
            re.IGNORECASE
        ),

        # I: "Working Experience – 26 Years" / "Experience : 26 Years"
        re.compile(
            r'(?:working\s+|work\s+|professional\s+|industry\s+)?'
            r'(?:experience|exp\.?)'
            r'\s*[-–:]\s*'
            r'(\d{1,2}(?:\.\d)?)\s*\+?'
            r"\s*(?:yr\s*s?|years?['\u2019]?s?|yrs)",
            re.IGNORECASE
        ),

        # A+B: "total[working]experience: 11 years"
        re.compile(
            r'(?:total|overall|aggregate|combined)'
            r'(?:[\s\-]*(?:work|working|professional|industry))?\s*'
            r'(?:experience|exp\.?|expr\.?)'
            r'[\s:=\-\.]*'
            r'(\d{1,2}(?:\.\d)?)\s*\+?'
            r"\s*(?:yr\s*s?|years?['\u2019]?s?|yrs)",
            re.IGNORECASE
        ),
        # C: "14+ YRS OF EXPERIENCE"
        re.compile(
            r'(\d{1,2}(?:\.\d)?)\s*\+?'
            r"\s*(?:yr\s*s?|years?['\u2019]?s?|yrs)"
            r'(?:\s+of)?(?:\s+\w+){0,2}\s+(?:experience|exp\.?)',
            re.IGNORECASE
        ),
        # D: "8+ years of experience"
        re.compile(
            r'(\d{1,2}(?:\.\d)?)\s*\+'
            r"\s*(?:yr\s*s?|years?['\u2019]?s?|yrs)"
            r'\s+(?:of\s+)?(?:experience|exp\.?)',
            re.IGNORECASE
        ),
        # E: "18 years working experience"
        re.compile(
            r'(\d{1,2}(?:\.\d)?)\s*\+?'
            r"\s*(?:yr\s*s?|years?['\u2019]?s?|yrs)"
            r'\s+(?:of\s+)?(?:working\s+|work\s+|professional\s+)?(?:experience|exp\.?)',
            re.IGNORECASE
        ),

        # F: Standalone "19+ years" / "19+ yrs" — prominent claim without trailing word
        #    Matches: "19+ Years", "with 19+ years", "having 19+ years", etc.
        re.compile(
            r'(?:^|(?:have|having|with|carrying|brings?|possess(?:ing)?'
            r'|spanning?|across|of|total|overall)\s+)'
            r'(\d{1,2}(?:\.\d)?)\s*\+'
            r"\s*(?:yr\s*s?|years?['\u2019]?s?|yrs)"
            r'(?:\s|$|[,.])',
            re.IGNORECASE | re.MULTILINE
        ),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            try:
                val = float(m.group(1))
                if 0 < val < 60:
                    return val
            except (ValueError, IndexError):
                continue
    return None
 
 
# ================= INLINE DURATION EXTRACTOR =================
 
# Detects numbered list lines: (1), 1), 1., 1:-, etc.
_LIST_LINE_MARKER = re.compile(r'^\s*(?:\(\d+\)|\d+[).:\-])', re.MULTILINE)
 
# Duration tokens on a line
_DUR_TOKEN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(year|yr|month|mon)s?\b',
    re.IGNORECASE
)
 
 
def extract_inline_durations(text: str):
    """
    For list-style entries with inline durations (no date ranges).
    Sums all duration values found on numbered list lines.
    Returns total months (float) or None if < 2 list lines found.

    Handles:
      "(1):- Company – 1 year"        → 12 months
      "(2):- Company – 6 months"      → 6 months
      "(3):- Company Wadi 1 year"     → 12 months  (trailing, no dash)
    """
    total_months = 0.0
    line_count = 0
 
    for line in text.split('\n'):
        if not _LIST_LINE_MARKER.match(line):
            continue
        line_total = 0.0
        found = False
        for m in _DUR_TOKEN.finditer(line):
            val = float(m.group(1))
            unit = m.group(2).lower()
            if unit.startswith('year') or unit.startswith('yr'):
                line_total += val * 12
            else:
                line_total += val
            found = True
        if found:
            total_months += line_total
            line_count += 1
 
    if line_count >= 2 and total_months > 0:
        return total_months
    return None
 
 
# ================= MAIN ENTRY POINT =================
 
def calculate_experience(text: str) -> str:
    """
    Calculate total work experience from resume text.

    Priority:
      0. Fresher guard → "0 years"
      1. Compute date ranges from all non-education sections
      2. Extract directly mentioned experience number
      3. Decision logic:
           - Both exist:
               computed > direct  → use computed  (manual calc is higher, trust it)
               computed <= direct → use direct    (stated number is higher or equal, trust it)
           - Only computed → use computed
           - Only direct   → use direct
      4. Inline list durations fallback
      5. Year-span heuristic fallback
      6. "0 years"
    """

    # 0. Fresher guard
    if FRESHER_PATTERN.search(text):
        return "0 years"

    text_lower = text.lower()
    clean_text = strip_education_block(text_lower)

    # 1. Date range calculation
    date_months = calculate_from_dates(clean_text)
    summary_months = extract_career_summary_dates(text_lower)

    all_date = [m for m in (date_months, summary_months) if m is not None]
    computed = max(all_date) if all_date else None

    # 2. Direct mention
    direct = extract_direct_experience(text_lower)
    direct_months = direct * 12 if direct is not None else None

    # 3. Decision: compare computed vs direct
    if computed is not None and direct_months is not None:
        if computed > direct_months:
            chosen = computed       # manual calc higher → trust computed
        else:
            chosen = direct_months  # stated number higher or equal → trust direct
        return format_experience(chosen)

    if computed is not None:
        return format_experience(computed)

    # 4. Inline list durations
    inline = extract_inline_durations(clean_text)
    if inline is not None:
        return format_experience(inline)

    # 5. Direct mention only (no dates found anywhere)
    if direct_months is not None:
        return format_experience(direct_months)

    # 6. Year-span heuristic (last resort)
    years_found = sorted(set(
        int(y) for y in re.findall(r'\b((?:19[9]\d|20\d{2}))\b', clean_text)
    ))
    if len(years_found) >= 2:
        diff = years_found[-1] - years_found[0]
        if 0 < diff < 45:
            return format_experience(float(diff * 12))

    return "0 years"