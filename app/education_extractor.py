import re
import spacy   
import json    
...
# ================= EDUCATION =================

DEGREE_PATTERNS = {
    # Postgraduate
    "PhD":    ["phd", "ph.d", "doctor of philosophy"],
    "MBA":    ["mba", "master of business administration"],
    "M.Tech": ["m.tech", "mtech", "master of technology"],
    "MCA":    ["mca", "master of computer applications"],
    "M.Sc":   ["m.sc", "msc", "master of science"],
    "M.E":    ["master of engineering"],  # "m.e" removed — caught by BOUNDARY_ONLY with lookbehind
    "M.A":    ["m.a", "master of arts"],
 
    # Undergraduate
    "B.Tech": ["b.tech", "btech", "bachelor of technology"],
    "BCA":    ["bca", "bachelor of computer applications"],
    "B.Sc":   ["b.sc", "b.s.c", "bsc", "bachelor of science"],
    "B.E":    ["bachelor of engineering"],  # "b.e" removed — caught by BOUNDARY_ONLY with lookbehind
    "B.A":    ["bachelor of arts"],
 
    # Diploma specific (order matters — specific before generic)
    "Diploma (Electrical & Electronics)": [
        "diploma in electrical & electronics engineering",
        "diploma in electrical and electronics engineering",
        "diploma in electrical engineering",
        "diploma in eee",
        "diploma (eee)",
        "diploma(eee)",
        "diploma electrical & electronics",
        "diploma electrical and electronics",
        "diploma electrical",
        "eee diploma",
        "diploma eee",
    ],
    "Diploma (Textile Technology)": [
        "diploma in textile technology",
    ],
    "Diploma (ECE)": [
        "diploma in ece",
        "diploma in electronics and communication",
        "diploma in electronics & communication",
        "diploma in electronics engineering",
        "diploma(ece)",
        "diploma (ece)",
        "diploma ece",
        "ece diploma",
        "diploma electronics",
        "diploma in electronics",
    ],
    "Diploma (Mechanical)": [
        "diploma in mechanical engineering",
        "diploma in mechanical",
        "diploma (mechanical)",
        "diploma mechanical",
        "mechanical diploma",
        "d.m.e",
        "dme",
    ],
    "Diploma (Civil)": [
        "diploma in civil engineering",
        "diploma in civil",
        "diploma (civil)",
        "diploma civil",
        "civil diploma",
    ],
    "Diploma (Computer Science)": [
        "diploma in computer science",
        "diploma in cs",
        "diploma (cs)",
        "diploma cs",
    ],
    # Generic diploma LAST — only catches bare "diploma" with no stream
    "Diploma": ["diploma"],
 
    # ITI specific only
    "ITI": ["iti (electrician)", "iti(electrician)", "iti electrician"],
 
    # Standalone engineering streams -> B.E (only when no diploma keyword)
    "BE (Mechanical)_stream": [
        "mechanical engineering",
        "mechanical engg",
    ],
    "BE (Electrical & Electronics)_stream": [
        "electrical engineering",
        "electrical and electronics engineering",
        "electrical & electronics engineering",
        "electrical and electronics",
        "electrical & electronics",
        "eee",
    ],
    "BE (ECE)_stream": [
        "electronics and communication engineering",
        "electronics & communication engineering",
        "electronics engineering",
        "electronics and communication",
        "electronics & communication",
        "ece",
    ],
    "BE (Civil)_stream": [
        "civil engineering",
        "civil engg",
    ],
 
    # School
    "Intermediate / 12th": [
        "intermediate", "12th", "hsc", "higher secondary",
        "plus two", "+2", "10+2", "pre-university", "junior college",
    ],
}
 
STREAM_ALIAS = {
    "BE (Mechanical)_stream": "B.E",
    "BE (Electrical & Electronics)_stream": "B.E",
    "BE (ECE)_stream": "B.E",
    "BE (Civil)_stream": "B.E",
}
 
BOUNDARY_ONLY = {
    r"m\.tech": "M.Tech",
    r"b\.tech": "B.Tech",
    r"m\.e":    "M.E",
    r"b\.e":    "B.E",
    r"m\.a":    "M.A",
    r"b\.a":    "B.A",
    r"m\.sc":   "M.Sc",
    r"b\.sc":   "B.Sc",
}
 
PRIORITY = [
    "PhD", "MBA", "M.Tech", "MCA", "M.Sc", "M.E", "M.A",
    "B.Tech", "BCA", "B.Sc", "B.A",
    # Specific Diploma subtypes ranked ABOVE B.E —
    # a "diploma in X engineering" match is more specific than a bare stream keyword.
    # B.E is still caught when NO diploma evidence exists (stream_ok path).
    "Diploma (Electrical & Electronics)",
    "Diploma (ECE)",
    "Diploma (Mechanical)",
    "Diploma (Civil)",
    "Diploma (Computer Science)",
    "Diploma (Textile Technology)",
    "Diploma",
    # B.E falls here — only wins when no specific Diploma subtype matched
    "B.E",
    "ITI",
    "Intermediate / 12th",
    "10th / SSC",
]
 
EDUCATION_HEADINGS = [
    "academic profile", "educational qualification", "educational qualifications",
    "education", "qualification", "qualifications", "qualification personal details",
    "academic background", "academic details", "basic academic credentials",
    "educational details", "academics",
]
 
PROFILE_HEADINGS = [
    "professional profile", "career objective", "objective",
    "summary", "profile", "about me", "professional summary",
]
 
# BUG FIX: Removed the `break` — must scan ALL patterns to find most specific.
# Ordered most-specific first so the best match wins.
NOSPACE_PATTERNS = [
    ("diplomainmechanicalengineering",       "Diploma (Mechanical)"),
    ("diplomainmechanical",                  "Diploma (Mechanical)"),
    ("mechanicaldiploma",                    "Diploma (Mechanical)"),
    ("d.m.e",                                "Diploma (Mechanical)"),
    ("dme",                                  "Diploma (Mechanical)"),
    ("diplomainelectricalandelectronicsengineering", "Diploma (Electrical & Electronics)"),
    ("diplomainelectricalelectronicsengineering",    "Diploma (Electrical & Electronics)"),
    ("diplomainelectricalengineering",       "Diploma (Electrical & Electronics)"),
    ("diplomainelectrical",                  "Diploma (Electrical & Electronics)"),
    ("diplomaineee",                         "Diploma (Electrical & Electronics)"),
    ("diplomaelectrical",                    "Diploma (Electrical & Electronics)"),
    ("eeediploma",                           "Diploma (Electrical & Electronics)"),
    ("diplomainelectronicsandcommunication", "Diploma (ECE)"),
    ("diplomainelectronicsengineering",      "Diploma (ECE)"),
    ("diplomainece",                         "Diploma (ECE)"),
    ("diplomaelectronics",                   "Diploma (ECE)"),
    ("ecediploma",                           "Diploma (ECE)"),
    ("diplomaincivilengineering",            "Diploma (Civil)"),
    ("diplomaincivil",                       "Diploma (Civil)"),
    ("civildiploma",                         "Diploma (Civil)"),
    ("diplomaincomputerscience",             "Diploma (Computer Science)"),
    ("btech",                                "B.Tech"),
    ("bsc",                                  "B.Sc"),
    ("bca",                                  "BCA"),
    ("mtech",                                "M.Tech"),
    ("mca",                                  "MCA"),
    ("diploma",                              "Diploma"),
]
 
 
def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[ \t]+", " ", text)
    return text
 
 
def _dejunk(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())
 
 
def _join_lines(text: str) -> str:
    """Replace newlines with spaces so multi-line phrases become matchable."""
    return re.sub(r"\n+", " ", text)
 
 
def _has_bsc_variant(t_norm: str, t_joined: str, t_nospace: str) -> bool:
    pat = r"(?<![a-z0-9])b[\s.]*s[\s.]*c(?![a-z0-9])"
    return (
        re.search(pat, t_norm) is not None
        or re.search(pat, t_joined) is not None
        or "degree(bsc)" in t_nospace
        or "bsc" in t_nospace
    )
 
 
def _has_diploma_evidence(t_norm: str, t_joined: str, t_nospace: str) -> bool:
    """
    Returns True if ANY diploma indicator is present, including
    abbreviations like D.M.E / DME and split across lines.
    """
    if "diploma" in t_norm or "diploma" in t_joined or "diploma" in t_nospace:
        return True
    if re.search(r"(?<![a-z0-9])d\.m\.e(?![a-z0-9])", t_norm):
        return True
    if re.search(r"(?<![a-z0-9])d\.m\.e(?![a-z0-9])", t_joined):
        return True
    if "dme" in t_nospace:
        return True
    return False
 
 
def _scan(text: str, stream_ok: bool = False, global_diploma: bool = False) -> str | None:
    t_norm    = _normalize(text)
    # BUG FIX: t_joined joins lines so "DIPLOMA\n(ECE)" becomes "diploma (ece)"
    t_joined  = _normalize(_join_lines(text))
    t_nospace = _dejunk(text)
 
    found: set[str] = set()
 
    # Compute diploma evidence upfront (local + global)
    diploma_present = global_diploma or _has_diploma_evidence(t_norm, t_joined, t_nospace)
 
    # Strong B.Sc recovery
    if _has_bsc_variant(t_norm, t_joined, t_nospace):
        found.add("B.Sc")
 
    # Pass 1: exact phrases — check BOTH t_norm and t_joined
    # t_joined catches patterns split across lines e.g. "DIPLOMA\n(ECE)"
    for degree, patterns in DEGREE_PATTERNS.items():
        if degree in STREAM_ALIAS and not stream_ok:
            continue
        for p in patterns:
            if p in t_norm or p in t_joined:
                found.add(degree)
                break
 
    # Pass 2: de-spaced scan — BUG FIX: NO break, scan ALL patterns
    # so specific subtypes aren't shadowed by the generic "diploma" entry
    best_nospace: str | None = None
    for pat, degree in NOSPACE_PATTERNS:
        if pat in t_nospace:
            # Keep going — last specific match in priority order wins
            # But since list is ordered specific-first, take the FIRST match
            if best_nospace is None:
                best_nospace = degree
            # Stop only when we've found a specific (non-generic) match
            if degree != "Diploma":
                break
    if best_nospace:
        found.add(best_nospace)
 
    # Recompute after Pass 1 & 2 — specific Diploma subtype may now be in found
    diploma_present = diploma_present or any(d.startswith("Diploma") for d in found)
 
    # Pass 3: boundary tokens — block M.E / B.E / M.A when diploma is present.
    # Also block m.e when it appears as part of d.m.e (Diploma Mechanical Engg abbrev).
    dme_present = bool(re.search(r"(?<![a-z0-9])d\.m\.e(?![a-z0-9])", t_norm)) or \
                  bool(re.search(r"(?<![a-z0-9])d\.m\.e(?![a-z0-9])", t_joined)) or \
                  "dme" in t_nospace
    for pattern, degree in BOUNDARY_ONLY.items():
        if diploma_present and degree in {"M.E", "B.E", "M.A"}:
            continue
        # Extra guard: don't let m.e fire when it's part of d.m.e
        if dme_present and degree == "M.E":
            continue
        if re.search(r"(?<![a-z0-9.])" + pattern + r"(?![a-z0-9.])", t_norm):
            found.add(degree)
 
    # Stream promotion: only when absolutely no diploma evidence anywhere
    if stream_ok and not diploma_present:
        if re.search(
            r"\b(mechanical|civil|electrical|electronics)\s+engineering\b", t_norm
        ):
            found.add("B.E")
        elif re.search(r"\b(ece|eee)\b", t_norm):
            found.add("B.E")
 
    # Resolve stream aliases
    resolved: set[str] = {STREAM_ALIAS.get(d, d) for d in found}
 
    # ITI: only if nothing stronger found
    has_non_iti = any(d != "ITI" for d in resolved)
    if not has_non_iti:
        if re.search(
            r"\biti\b(?!\s*(college|polytechnic|school|university|institute|centre|center))",
            t_norm
        ):
            resolved.add("ITI")
        elif any(x in t_norm for x in DEGREE_PATTERNS.get("ITI", [])):
            resolved.add("ITI")
 
    if not resolved:
        return None
 
    for degree in PRIORITY:
        if degree in resolved:
            return degree
    return next(iter(resolved))
 
 
def _get_section(lines: list[str], headings: list[str], window: int = 25) -> list[str]:
    stripped_headings = [re.sub(r"\s+", "", h) for h in headings]
    for i, line in enumerate(lines):
        # Strip trailing punctuation so "academic profile:" matches "academic profile"
        line_s = re.sub(r"[:\-_*]+$", "", line.strip()).strip()
        line_ns = re.sub(r"\s+", "", line_s)
        if (any(h in line_s for h in headings) or
                any(h in line_ns for h in stripped_headings)):
            return lines[i + 1: i + 1 + window]
    return []
 
 
def extract_education(text: str) -> str:
    t_norm   = _normalize(text)
    t_joined = _normalize(_join_lines(text))
    t_nospace = _dejunk(text)
    lines    = t_norm.splitlines()
 
    # Check diploma evidence across the FULL document first
    global_diploma = _has_diploma_evidence(t_norm, t_joined, t_nospace)
 
    # 1) Education / qualification section
    edu_lines = _get_section(lines, EDUCATION_HEADINGS, window=35)
    if edu_lines:
        degree = _scan("\n".join(edu_lines), stream_ok=True, global_diploma=global_diploma)
        if degree:
            return degree
 
    # 2) Profile / summary section
    profile_lines = _get_section(lines, PROFILE_HEADINGS, window=12)
    if profile_lines:
        degree = _scan("\n".join(profile_lines), stream_ok=False, global_diploma=global_diploma)
        if degree:
            return degree
 
    # 3) Full text fallback
    degree = _scan(t_norm, stream_ok=True, global_diploma=global_diploma)
    if degree:
        return degree
 
    return "Intermediate / 12th"
 
 
if __name__ == "__main__":
    tests = [
        # Original tests
        ("Qualification Personal Details\nYear of Passing 2012 Mechanical Engineering", "B.E"),
        ("Education\nDiploma in Mechanical Engineering", "Diploma (Mechanical)"),
        ("Education\nDegree (B.S.C)(Chemistry) :-2014 pass out (52%)", "B.Sc"),
        ("Education\nDip lo m a in M e chanical Eng ine ering (p asse d o ut- 2 00 6)", "Diploma (Mechanical)"),
        ("BASICACADEMICCREDENTIALS\nNon-Matric", "Intermediate / 12th"),
        ("Education\nDIPLOMA\n(ECE)", "Diploma (ECE)"),
        ("Education\nM.A in Hindi Language", "M.A"),
        ("QUALIFICATION PERSONAL DETAILS\nYear of Passing 2012 Mechanical Engineering\nInstitution: Govt ITI College", "B.E"),
        ("Education\nElectrical Engineering", "B.E"),
        ("Education\nElectronics Engineering", "B.E"),
        ("Education\nDiploma in Electrical Engineering", "Diploma (Electrical & Electronics)"),
        ("Education\nDiploma in ECE", "Diploma (ECE)"),
        ("Work Experience\n5 years in marketing", "Intermediate / 12th"),
 
        # Your 4 failing cases
        ("Academic Profile\nDiploma in Electrical & Electronics Engineering", "Diploma (Electrical & Electronics)"),
        ("ACADEMIC PROFILE:\nD.M.E", "Diploma (Mechanical)"),
        ("EDUCATIONAL DETAILS:\nDIPLOMA\n(ECE)", "Diploma (ECE)"),
        ("Professional Profile\nHardworking EEE Diploma fresher", "Diploma (Electrical & Electronics)"),
 
        # Extra edge cases
        ("Education\nD.M.E", "Diploma (Mechanical)"),
        ("Education\nDME 2018", "Diploma (Mechanical)"),
        ("Education\nDiploma (Mechanical)", "Diploma (Mechanical)"),
        ("Education\nDiploma ECE", "Diploma (ECE)"),
        ("Education\nDiploma Electrical", "Diploma (Electrical & Electronics)"),
        ("Education\nEEE Diploma", "Diploma (Electrical & Electronics)"),
    ]
 
    pass_count, fail_count = 0, 0
    for text, expected in tests:
        got = extract_education(text)
        if got == expected:
            pass_count += 1
            print(f"✓ got={got!r:40s} input={text[:60]!r}")
        else:
            fail_count += 1
            print(f"✗ expected={expected!r:32s} got={got!r:24s} input={text[:60]!r}")
 
    print(f"\nResults: {pass_count} passed, {fail_count} failed, total={len(tests)}")