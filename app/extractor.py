import re
from typing import Optional, List

import spacy
import phonenumbers


# ================= SAFE SPACY LOAD (LOW RAM) =================
try:
    nlp = spacy.load(
        "en_core_web_sm",
        disable=["parser", "tagger", "lemmatizer"]
    )
except Exception:
    nlp = None


# ─── Text normalisation ───────────────────────────────────────

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\byrs?\b", "years", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d)\+?\s*years", r"\1 years", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text(text: str) -> str:
    text = text.replace("|", " ")
    return re.sub(r"\s+", " ", text).strip()


# ================= EMAIL =================

def _normalize_email_text(text: str) -> str:
    text = re.sub(r"(\.com|\.in|\.org|\.net)([A-Z])", r"\1 \2", text)
    text = text.replace(" @ ", "@").replace(" . ", ".")
    for fake, real in [("(at)", "@"), ("[at]", "@"), ("(dot)", "."), ("[dot]", ".")]:
        text = text.replace(fake, real)
    return text


def extract_email(text: str) -> List[str]:
    text = _normalize_email_text(text)
    matches = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b", text)
    seen, result = set(), []
    for m in matches:
        m = m.lower()
        if m not in seen and len(m) < 50:
            seen.add(m)
            result.append(m)
    return result


# ================= PHONE =================

def _to_e164(raw: str) -> Optional[str]:
    """Normalise any phone string to E164 (+91XXXXXXXXXX), or None if invalid."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        digits = "91" + digits
    elif len(digits) == 11 and digits.startswith("0"):
        digits = "91" + digits[1:]
    if not (11 <= len(digits) <= 13):
        return None
    return "+" + digits


def extract_phone(text: str) -> List[str]:
    seen = set()
    result = []

    # Pass 1: phonenumbers library (most accurate)
    try:
        for match in phonenumbers.PhoneNumberMatcher(text, "IN"):
            e164 = phonenumbers.format_number(
                match.number, phonenumbers.PhoneNumberFormat.E164
            )
            if e164 not in seen:
                seen.add(e164)
                result.append(e164)
    except Exception:
        pass

    # Pass 2: regex fallback — deduplicate against Pass 1
    for raw in re.findall(r"\+?\d[\d\s\-]{8,15}\d", text):
        e164 = _to_e164(raw)
        if e164 and e164 not in seen:
            seen.add(e164)
            result.append(e164)

    return result


# ================= EDUCATION =================

DEGREE_PATTERNS = {
    # Postgraduate
    "PhD":    ["phd", "ph.d", "doctor of philosophy"],
    "MBA":    ["mba", "master of business administration"],
    "M.Tech": ["m.tech", "mtech", "master of technology"],
    "MCA":    ["mca", "master of computer applications"],
    "M.Sc":   ["m.sc", "msc", "master of science"],
    "M.E":    ["master of engineering"],
    "M.A":    ["m.a", "master of arts"],

    # Undergraduate
    "B.Tech": ["b.tech", "btech", "B-tech", "bachelor of technology","b-tech","b tech"],
    "BCA":    ["bca", "bachelor of computer applications"],
    "B.Sc":   ["b.sc", "b.s.c", "bsc", "bachelor of science"],
    "B.E":    ["bachelor of engineering","b.e", "b e", "b.e.", "b-e", "bachelorofengineering"],
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
    "ITI": ["iti (electrician)", "iti(electrician)", "iti electrician",
            "iti (fitter)",      "iti(fitter)",      "iti fitter",
            "iti (welder)",      "iti(welder)",      "iti welder",
            "iti (mechanic)",    "iti(mechanic)",
            "i.t.i","ITI", "I T I",             # catches "I.T.I Fitter", "I.T.I. Electrician"
            ],
  

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
    "B.Tech Electronics & Instrumentation_stream":  "B.Tech",
    "B.E Mechanical Engineering_stream": "B.E"
}

BOUNDARY_ONLY = {
    r"m\.tech": "M.Tech",
    r"b[\s.]?\s*tech": "B.Tech",
    r"m\.e":    "M.E",
    r"b\.e\.?": "B.E",
    r"m\.a":    "M.A",
    r"b\.a":    "B.A",
    r"m\.sc":   "M.Sc",
    r"b\.sc":   "B.Sc",
}

PRIORITY = [
    "PhD", "MBA", "M.Tech", "MCA", "M.Sc", "M.E", "M.A",
    "B.Tech", "BCA", "B.Sc", "B.A",
    "Diploma (Electrical & Electronics)",
    "Diploma (ECE)",
    "Diploma (Mechanical)",
    "Diploma (Civil)",
    "Diploma (Computer Science)",
    "Diploma (Textile Technology)",
    "Diploma",
    "B.E","B.Tech",
    "ITI",
    "Intermediate / 12th",
    "10th / SSC",
]

EDUCATION_HEADINGS = [
    "academic profile", "educational qualification", "educational qualifications",
    "academic qualifications",
    "education", "qualification", "qualifications", "qualification personal details",
    "academic background", "academic details", "basic academic credentials",
    "educational details", "academics",
]

PROFILE_HEADINGS = [
    "professional profile", "career objective", "objective",
    "summary", "profile", "about me", "professional summary",
]

NOSPACE_PATTERNS = [
    ("diplomainmechanicalengineering",                "Diploma (Mechanical)"),
    ("diplomainmechanical",                           "Diploma (Mechanical)"),
    ("mechanicaldiploma",                             "Diploma (Mechanical)"),
    ("d.m.e",                                         "Diploma (Mechanical)"),
    ("dme",                                           "Diploma (Mechanical)"),
    ("diplomainelectricalandelectronicsengineering",  "Diploma (Electrical & Electronics)"),
    ("diplomainelectricalelectronicsengineering",     "Diploma (Electrical & Electronics)"),
    ("diplomainelectricalengineering",                "Diploma (Electrical & Electronics)"),
    ("diplomainelectrical",                           "Diploma (Electrical & Electronics)"),
    ("diplomaineee",                                  "Diploma (Electrical & Electronics)"),
    ("diplomaelectrical",                             "Diploma (Electrical & Electronics)"),
    ("eeediploma",                                    "Diploma (Electrical & Electronics)"),
    ("diplomainelectronicsandcommunication",          "Diploma (ECE)"),
    ("diplomainelectronicsengineering",               "Diploma (ECE)"),
    ("diplomainece",                                  "Diploma (ECE)"),
    ("diplomaelectronics",                            "Diploma (ECE)"),
    ("ecediploma",                                    "Diploma (ECE)"),
    ("diplomaincivilengineering",                     "Diploma (Civil)"),
    ("diplomaincivil",                                "Diploma (Civil)"),
    ("civildiploma",                                  "Diploma (Civil)"),
    ("diplomaincomputerscience",                      "Diploma (Computer Science)"),
    ("btech",                                         "B.Tech"),
    ("bsc",                                           "B.Sc"),
    ("bca",                                           "BCA"),
    ("mtech",                                         "M.Tech"),
    ("diploma",                                       "Diploma"),
    ("b.e(mechanicalengineering)",   "B.E"),
    ("b.e(mechanical)",              "B.E"),
    ("b.e(electrical)",              "B.E"),
    ("b.e(civil)",                   "B.E"),
    ("b.e(ece)",                     "B.E"),
    ("bachelorofengineering", "B.E"),
    ("bacheloroftechnology", "B.Tech"),
    ("masteroftechnology", "M.Tech"),
    ("masterofengineering", "M.E"),
    ("bacheloroftechnology", "B.Tech"),
    ("btech", "B.Tech"),
]


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _dejunk(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def _join_lines(text: str) -> str:
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
    if "diploma" in t_norm or "diploma" in t_joined or "diploma" in t_nospace:
        return True
    if re.search(r"(?<![a-z0-9])d\.m\.e(?![a-z0-9])", t_norm):
        return True
    if re.search(r"(?<![a-z0-9])d\.m\.e(?![a-z0-9])", t_joined):
        return True
    if "dme" in t_nospace:
        return True
    return False


def _scan(text: str, stream_ok: bool = False, global_diploma: bool = False) -> Optional[str]:
    t_norm    = _normalize(text)
    t_joined  = _normalize(_join_lines(text))
    t_nospace = _dejunk(text)

    found = set()

    diploma_present = global_diploma or _has_diploma_evidence(t_norm, t_joined, t_nospace)

    if _has_bsc_variant(t_norm, t_joined, t_nospace):
        found.add("B.Sc")

    for degree, patterns in DEGREE_PATTERNS.items():

        if "diploma in mechanical engineering" in t_norm:
            return "Diploma (Mechanical)"
    
        if degree in STREAM_ALIAS and not stream_ok:
            continue
        for p in patterns:
            if p in t_norm or p in t_joined:
                found.add(degree)
                break

    best_nospace = None
    for pat, degree in NOSPACE_PATTERNS:
        if pat in t_nospace:
            if best_nospace is None:
                best_nospace = degree
            if degree != "Diploma":
                break
    if best_nospace:
        found.add(best_nospace)
    
    if re.search(r'b[\.\-]e\s*\(', t_nospace.replace(" ", "")):
        found.add("B.E")
    
    diploma_present = diploma_present or any(d.startswith("Diploma") for d in found)

    dme_present = (
        bool(re.search(r"(?<![a-z0-9])d\.m\.e(?![a-z0-9])", t_norm))
        or bool(re.search(r"(?<![a-z0-9])d\.m\.e(?![a-z0-9])", t_joined))
        or "dme" in t_nospace
    )

    # Strip university/institute names to avoid false matches
    text_for_scan = re.sub(
                  r'\b(?:university|institute|college|board|deemed|from)\b.*',
               '', t_norm
    )

    for pattern, degree in BOUNDARY_ONLY.items():
        if diploma_present and degree in {"M.E", "B.E", "M.A"}:
            continue
        if dme_present and degree == "M.E":
            continue
        if re.search(r"(?<![a-z0-9.])" + pattern + r"(?![a-z0-9.])", text_for_scan):
            found.add(degree)

    if stream_ok and not diploma_present:
        if re.search(r"\b(mechanical|civil|electrical|electronics)\s+engineering\b", t_norm):
            found.add("B.E")
        elif re.search(r"\b(ece|eee)\b", t_norm):
            found.add("B.E")

    resolved = {STREAM_ALIAS.get(d, d) for d in found}

    has_non_iti = any(d != "ITI" for d in resolved)
    if not has_non_iti:
        if re.search(
            r"\bi\.?t\.?i\.?\b(?!\s*(college|polytechnic|school|university|institute))",
        t_norm   # ← catches I.T.I with dots
    ):
            resolved.add("ITI")
        
        elif any(x in t_norm or x in t_joined for x in DEGREE_PATTERNS.get("ITI", [])):
            resolved.add("ITI")       
    
    if not resolved:
        if "bachelor of engineering" in t_norm:
            return "B.E"
        
        if "bachelorofengineering" in t_nospace:
            return "B.E"

        if "bachelor of technology" in t_norm:
            return "B.Tech"

        if "bacheloroftechnology" in t_nospace:
            return "B.Tech"
        return None
          
    for degree in PRIORITY:
        if degree in resolved:
            return degree
    return next(iter(resolved))


def _get_section(lines: List[str], headings: List[str], window: int = 25) -> List[str]:
    stripped_headings = [re.sub(r"\s+", "", h) for h in headings]
    for i, line in enumerate(lines):
        line_s = re.sub(r"[:\-_*]+$", "", line.strip()).strip()
        line_ns = re.sub(r"\s+", "", line_s)
        if (any(h in line_s for h in headings) or
                any(h in line_ns for h in stripped_headings)):
            section = []
            for line in lines[i + 1:]:
                l = line.lower().strip()

            if l in ["experience","languages","skills","projects",
                     "personal details","job profile","declaration"]:
                break
                 
            section.append(line)

            if len(section) >= window:
                  break
            
            return section
    return []

def extract_education(text: str) -> str:
    t_norm    = _normalize(text)
    t_joined  = _normalize(_join_lines(text))
    t_nospace = _dejunk(text)
    lines     = t_norm.splitlines()

    global_diploma = _has_diploma_evidence(t_norm, t_joined, t_nospace)

    # 1) Education / qualification section
    edu_lines = _get_section(lines, EDUCATION_HEADINGS, window=10)
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


# ================= NAME =================

BLACKLIST = [
    "engineering", "college", "university", "institute",
    "technologies", "technology", "solutions", "systems",
    "pvt", "ltd", "limited", "company", "resume",
    "curriculum", "vitae", "profile", "career", "objective",
    "summary", "mail", "email", "address", "contact", "experience",
    "safety", "officer", "ehs", "professional", "iso", "location",
    "phone", "willing", "relocate", "india",
    "diploma", "degree", "bachelor", "master", "b.tech", "m.tech",
    "maintenance", "operation", "production", "management", "services",
    "well", "also", "dist", "village", "mandal", "nagar", "road",
    "post", "taluk", "taluka", "district", "state", "country",
    "near", "behind", "opposite", "beside", "educational", "qualification",
    "d.m.e", "dme",
    "hazard", "identification", "class", "sscxth", "std", "standard",
    "b.o.e", "b.e", "m.e", "mba", "mca", "bca", "bsc", "msc",
    "board", "school", "intermediate", "hsc", "ssc", "tenth", "tenth class",
    "strong", "resolver", "word", "document", "header", "box",
    "certificate", "certified", "course", "program", "programme", "training",
    "institute", "institution", "centre", "center",
    "education", "educational", "qualification", "qualified",
    "phd","Emechanicalengineering", "B Emechanicalengineering",
]

PHRASE_BLACKLIST = [
    "as well as", "such as", "along with", "responsible for",
    "knowledge of", "experience in", "worked as", "working as",
    "s/o", "d/o", "w/o", "son of", "daughter of", "wife of",
]

address_keywords = [
    "post", "pincode", "pin", "mobile", "tq", "dist",
    "at ", "no ", "road", "nagar", "street", "village",
    "mandal", "district", "taluk", "taluka",
]

non_name_words = {
    "dist", "village", "mandal", "nagar", "road", "post", "pin",
    "taluk", "district", "state", "near", "the", "and", "for",
    "with", "from", "well", "also", "maintenance", "operation",
    "diploma", "degree", "sir", "shri", "mr", "mrs", "ms", "dr",
    "class", "std", "hazard", "identification", "sscxth",
}


def looks_like_name(text: str) -> bool:
    text_clean = text.lower().strip()
    text_clean = re.sub(r'(?<=[a-z])\.(?=[a-z])', ' ', text_clean, flags=re.IGNORECASE)
    text_clean_nodot = text_clean.replace(".", " ").strip()
    words = text_clean_nodot.split()

    if len(words) == 1:
        word = words[0]
        if (len(word) >= 6 and word.isalpha()
                and word not in BLACKLIST
                and word not in non_name_words):
            return True
        
    if not (2 <= len(words) <= 5):
        return False
    if re.search(r"\d|[@_:/]", text):
        return False
    text_words_set = set(text_clean_nodot.split())
    if any(bad in text_words_set for bad in BLACKLIST):
        return False
    if ":" in text:
        return False
    if any(phrase in text_clean for phrase in PHRASE_BLACKLIST):
        return False

    alpha_words = [w for w in words if w.isalpha()]
    if len(alpha_words) < 2:
        return False
    if any(w in non_name_words for w in words):
        return False

    if re.search(r'\([A-Za-z.]+\)', text):
        stripped = re.sub(r'\s*\([^)]*\)', '', text).strip()
        stripped_lower = stripped.lower()
        stripped_words = re.sub(
            r'(?<=[a-z])\.(?=[a-z])', ' ', stripped_lower, flags=re.IGNORECASE
        ).replace(".", " ").split()
        if not (2 <= len(stripped_words) <= 5):
            return False
        if any(w in non_name_words for w in stripped_words):
            return False

    return True


def extract_so_name(line: str) -> Optional[str]:
    pattern_before = r'^([A-Za-z][A-Za-z\s.]{1,35}?),?\s+[SsDdWw][/\.][Oo][\s.]'
    match = re.search(pattern_before, line)
    if match:
        candidate = match.group(1).strip().rstrip(",").strip()
        words = candidate.replace(".", " ").split()
        if 1 <= len(words) <= 4:
            candidate_norm = re.sub(r'(?<=[a-zA-Z])\.(?=[a-zA-Z])', ' ', candidate)
            candidate_norm = re.sub(r'[^\w\s.]', '', candidate_norm).replace(".", " ").strip()
            if not any(bad in candidate_norm.lower() for bad in BLACKLIST):
                return candidate.title()
    return None


def clean_inline_name(line: str) -> str:
    line = re.sub(r'\s*[Ee][-\s]?[Mm]ail\s*[–:\-]?\s*\S+@\S+', '', line)
    line = re.sub(
        r'\s*(Ph|Phone|Mobile|Tel|Mo|Cell)\s*[-–:\.]*\s*[\d\s/+\-]+', '',
        line, flags=re.IGNORECASE
    )
    line = re.sub(r'\s*\S+@\S+', '', line)
    line = line.split('|')[0]
    line = re.split(r'\s+[SsDdWw][/\.][Oo][\s.]', line)[0]
    line = re.sub(r'\s*\([^)]*\)', '', line)
    line = line.strip().rstrip(",-").strip()
    return line


def email_cross_check_should_skip(candidate_name_flat: str, full_text: str) -> bool:
    email_match = re.search(r'([a-zA-Z0-9._%+-]+)@', full_text)
    if not email_match:
        return False
    email_user = re.sub(r'\d+', '', email_match.group(1)).lower()
    combined_name = candidate_name_flat.lower()
    if len(combined_name) >= 8:
        return False
    if combined_name in email_user:
        return True
    return False


def looks_like_doc_header_artifact(line: str) -> bool:
    lower = line.lower().strip()
    if re.search(r'\b(class|std|grade|xth|vth|ixth|xith|xiith|sscxth|hscxth)\b', lower):
        return True
    if re.match(r'^[A-Z\s]{2,20}$', line.strip()) and len(line.strip().split()) == 1:
        return True
    return False


def extract_name(text: str, nlp=None) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    cv_header_keywords = ["curriculum", "resume", "vitae", "curriculam"]
    cv_header_index = None
    education_keywords = [
        "education", "academic", "qualification", "qualification personal details",
        "educational qualification", "educational details", "academic profile",
        "basic academic credentials", "intermediate", "board", "school"
    ]
    # Priority 1 - Top Resume Name Detection
    for line in lines[:5]:
        candidate = re.sub(r'[^A-Za-z .]', '', line).strip()

        candidate_lower = candidate.lower()
        # Skip CV headers
        if any(word in candidate_lower for word in cv_header_keywords):
            continue

        # Reuse existing blacklist
        if any(word in candidate_lower for word in BLACKLIST):
            continue

        if (
        candidate.isupper()
        and len(candidate.split()) <= 3
        and len(candidate) >= 5
        ):
            return candidate.title()

    # Priority 2: Check top 5 lines
    for i, line in enumerate(lines[:5]):
        raw_lower = line.lower()

        # Skip education lines
        if re.search(
        r'\b(engineering|b\.?e|b\.?tech|m\.?tech|diploma|iti)\b',
        raw_lower
       ):
            continue

        if any(word in raw_lower for word in cv_header_keywords):
            if cv_header_index is None:
                cv_header_index = i
            continue
        if any(word in raw_lower for word in education_keywords):
            continue
        if looks_like_doc_header_artifact(line):
            continue

        if re.search(r'[A-Za-z]\.[A-Za-z]', line, re.IGNORECASE):
            normalized = re.sub(r'(?<=[A-Za-z])\.(?=[A-Za-z])', ' ', line)
            normalized = re.sub(r'[^\w\s.]', '', normalized).replace(".", " ").strip()
            if looks_like_name(normalized):
                if not email_cross_check_should_skip(normalized.replace(" ", "").lower(), text):
                    return normalized.title()

        cleaned = clean_inline_name(line)
        cleaned_norm = re.sub(r'(?<=[A-Za-z])\.(?=[A-Za-z])', ' ', cleaned)
        cleaned_norm = re.sub(r'[^\w\s.]', '', cleaned_norm).replace(".", " ").strip()
        if looks_like_name(cleaned_norm):
            if not email_cross_check_should_skip(cleaned_norm.replace(" ", "").lower(), text):
                return cleaned_norm.title()

    # Priority 3: Lines after CV header
    if cv_header_index is not None:
        for line in lines[cv_header_index + 1: cv_header_index + 6]:
            raw_lower = line.lower()
            if any(word in raw_lower for word in education_keywords):
                continue

            so_name = extract_so_name(line)
            if so_name:
                return so_name

            if re.search(r'[A-Za-z]\.[A-Za-z]', line, re.IGNORECASE):
                normalized = re.sub(r'(?<=[A-Za-z])\.(?=[A-Za-z])', ' ', line)
                normalized = re.sub(r'[^\w\s.]', '', normalized).replace(".", " ").strip()
                if looks_like_name(normalized):
                    return normalized.title()

            cleaned = clean_inline_name(line)
            cleaned_norm = re.sub(r'(?<=[A-Za-z])\.(?=[A-Za-z])', ' ', cleaned)
            cleaned_norm = re.sub(r'[^\w\s.]', '', cleaned_norm).replace(".", " ").strip()
            if looks_like_name(cleaned_norm):
                return cleaned_norm.title()

    # Priority 4: General scan first 15 lines
    for i, line in enumerate(lines[:15]):
        raw_lower = line.lower()

        if any(word in raw_lower for word in cv_header_keywords):
            continue
        if any(word in raw_lower for word in education_keywords):
            continue
        if looks_like_doc_header_artifact(line):
            continue

        so_name = extract_so_name(line)
        if so_name:
            return so_name

        if any(kw in raw_lower for kw in address_keywords):
            continue

        if re.search(r'[A-Za-z]\.[A-Za-z]', line, re.IGNORECASE):
            normalized = re.sub(r'(?<=[A-Za-z])\.(?=[A-Za-z])', ' ', line)
            normalized = re.sub(r'[^\w\s.]', '', normalized).replace(".", " ").strip()
            if looks_like_name(normalized):
                if not email_cross_check_should_skip(normalized.replace(" ", "").lower(), text):
                    return normalized.title()

        cleaned = clean_inline_name(line)
        cleaned_norm = re.sub(r'(?<=[A-Za-z])\.(?=[A-Za-z])', ' ', cleaned)
        cleaned_norm = re.sub(r'[^\w\s.]', '', cleaned_norm).replace(".", " ").strip()
        if looks_like_name(cleaned_norm):
            if not email_cross_check_should_skip(cleaned_norm.replace(" ", "").lower(), text):
                return cleaned_norm.title()

    # Priority 5: Extended scan lines 5–25
    for line in lines[5:25]:
        raw_lower = line.lower()
        if any(kw in raw_lower for kw in address_keywords):
            continue
        if any(kw in raw_lower for kw in BLACKLIST):
            continue
        if any(word in raw_lower for word in education_keywords):
            continue
        if re.search(r'\d', line):
            continue
        if ":" in line or "@" in line:
            continue
        if looks_like_doc_header_artifact(line):
            continue
        if len(line.split()) > 5:
            continue

        if re.search(r'[A-Za-z]\.[A-Za-z]', line, re.IGNORECASE):
            normalized = re.sub(r'(?<=[A-Za-z])\.(?=[A-Za-z])', ' ', line)
            normalized = re.sub(r'[^\w\s.]', '', normalized).replace(".", " ").strip()
            if looks_like_name(normalized):
                return normalized.title()

        so_name = extract_so_name(line)
        if so_name:
            return so_name

        plain = re.sub(r'(?<=[A-Za-z])\.(?=[A-Za-z])', ' ', line)
        plain = re.sub(r'[^\w\s.]', '', plain).replace(".", " ").strip()
        if looks_like_name(plain):
            return plain.title()

    # Email fallback
    email_match = re.search(r'([a-zA-Z0-9._%+-]+)@', text)
    if email_match:
        user = re.sub(r'\d+', '', email_match.group(1))
        user = user.replace(".", " ").replace("_", " ")
        parts = [p for p in user.split() if p.isalpha()]
        if 1 <= len(parts) <= 3:
            return " ".join(p.capitalize() for p in parts)

    # NLP fallback
    if nlp:
        try:
            doc = nlp(text[:1000])
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    if looks_like_name(ent.text):
                        return ent.text.title()
        except Exception:
            pass

    return ""


# ================= PAN =================

def detect_pan(text: str) -> Optional[str]:
    match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text.upper())
    if not match:
        return None
    pan = match.group()
    if pan[0:5].isalpha() and pan[5:9].isdigit():
        return pan
    return None


# ================= AADHAAR =================

def detect_aadhaar(text: str) -> Optional[str]:
    match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
    if not match:
        return None
    number = re.sub(r"\s", "", match.group())
    if len(number) == 12:
        return number
    return None