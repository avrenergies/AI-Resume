import re
<<<<<<< HEAD
import spacy
import phonenumbers
from app.education_extractor import extract_education
from app.address_extractor import extract_address, extract_current_location
from app.job_title_cache import get_job_titles
from rapidfuzz import fuzz
from app.experience_calc import calculate_experience


NAME_LABEL_PATTERNS = [
    r'name\s*[:\-]\s*([A-Za-z\.\s]{3,50})',
    r'full name\s*[:\-]\s*([A-Za-z\.\s]{3,50})'
]

def is_valid_final_name(name):

    if not name:
        return False

    name_lower = name.lower()

    if any(x in name_lower for x in [
        "father", "passport", "dob",
        "resume", "curriculum",
        "address", "place"
    ]):
        return False

    if len(name.split()) > 4:
        return False

    return True
ROLE_MAP = {
    "shift": "Shift Incharge",
    "incharge": "Incharge",
    "operator": "Operator",
    "boiler": "Boiler Operator",
    "dcs": "DCS Engineer",
    "instrument": "Instrumentation Engineer",
    "electrical": "Electrical Engineer",
    "chemist": "Chemist",
    "fitter": "Fitter",
    "safety": "Safety Officer",
    "manager": "Manager"
}

#SAFE SPACY LOAD 

=======
from typing import Optional, List

import spacy
import phonenumbers


# ================= SAFE SPACY LOAD (LOW RAM) =================
>>>>>>> 9d2d7face242eebb6a4a3d878a35ead4285cf42d
try:
    nlp = spacy.load(
        "en_core_web_sm",
        disable=["parser", "tagger", "lemmatizer"]
    )
<<<<<<< HEAD
except:
    nlp = None


# TEXT NORMALIZATION 

def normalize_text(text):

    if not text:
        return ""

    # Normalize experience variants
    text = re.sub(r'yrs?', 'years', text, flags=re.IGNORECASE)
    text = re.sub(r'year[s]?', 'years', text, flags=re.IGNORECASE)

    # Fix OCR glued words
    text = re.sub(r'(\d)\+?\s*years', r'\1 years', text, flags=re.IGNORECASE)

    # Fix glued patterns like 7+Years
    text = re.sub(r'(\d)\+years', r'\1 years', text, flags=re.IGNORECASE)

    # Clean extra spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


#COMMON CLEANERS 

def clean_text(text):

    text = text.replace("|", " ")
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


#  EMAIL 

def normalize_text_for_email(text):

    text = re.sub(r'(\.com|\.in|\.org|\.net)([A-Z])', r'\1 \2', text)

    text = text.replace(" @ ", "@")
    text = text.replace(" . ", ".")
    text = text.replace("(at)", "@")
    text = text.replace("[at]", "@")
    text = text.replace("(dot)", ".")
    text = text.replace("[dot]", ".")

    return text


def extract_email(text):

    text = normalize_text_for_email(text)

    pattern = r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b'

    matches = re.findall(pattern, text, re.IGNORECASE)

    emails = {
        m.lower()
        for m in matches
        if len(m) < 50
    }

    return list(emails)


# PHONE 

def extract_phone(text):

    phones = set()

    try:
        for match in phonenumbers.PhoneNumberMatcher(text, "IN"):
            number = phonenumbers.format_number(
                match.number,
                phonenumbers.PhoneNumberFormat.E164
            )
            phones.add(number)
    except:
        pass

    fallback = re.findall(r'\+?\d[\d\s\-]{8,15}\d', text)

    for f in fallback:

        digits = re.sub(r'\D', '', f)

        if 10 <= len(digits) <= 13:

            phones.add(
                "+" + digits if not digits.startswith("+")
                else digits
            )

    return list(phones)


# EDUCATION 

DEGREE_PATTERNS = {
    "PhD": ["phd", "doctor of philosophy"],
    "MBA": ["mba", "master of business administration"],
    "M.Tech": ["m.tech", "mtech"],
    "M.E": ["m.e"],
    "MCA": ["mca"],
    "M.Sc": ["m.sc", "msc"],
    "B.Tech": ["b.tech", "btech"],
    "B.E": ["b.e", "be "],
    "B.Sc": ["b.sc", "bsc"],
    "BCA": ["bca"]
}


# JOB_TITLE 

JOB_ROLE_KEYWORDS = {

"HR Executive": ["hr executive","human resource executive"],
"HR Manager": ["hr manager","human resource manager"],

"Finance Executive": ["finance executive","accounts executive"],
"Finance Team": ["finance team"],

"Operations Manager": ["operations manager"],
"Plant Manager": ["plant manager"],

"Safety Officer": ["safety officer"],

"Admin / Store Keeper": ["store keeper","admin","store manager"],

"Mechanical Engineer": ["mechanical engineer"],
"Mechanical Technician": ["mechanical technician"],
"Mechanical Helper": ["mechanical helper"],
"Mechanical Welder": ["mechanical welder"],
"Mechanical Fitter": ["mechanical fitter"],
"Mechanical Incharge": ["mechanical incharge"],

"Electrical Engineer": ["electrical engineer"],
"Electrical Technician": ["electrical technician"],

"E&I Engineer": ["e&i engineer","ei engineer"],

"Instrumentation Engineer": ["instrumentation engineer"],
"Instrumentation Technician": ["instrumentation technician"],
"Instrumentation Incharge": ["instrumentation incharge"],

"O&M Engineer": ["o&m engineer","operation and maintenance engineer"],

"Power Plant Operations": ["power plant operation","power plant operations"],
"Power Plant Maintenance": ["power plant maintenance"],

"Turbine DCS Operator": ["turbine dcs operator"],
"Turbine Field Operator": ["turbine field operator"],

"Boiler DCS Operator": ["boiler dcs operator"],
"Boiler Field Operator": ["boiler field operator"],

"Control Room Operator": ["control room operator"],

"CHP Operator": ["chp operator"],
"AHP Operator": ["ahp operator"],
"FHS Operator": ["fhs operator"],

"WTP Incharge": ["wtp incharge"],
"WTP Chemist": ["wtp chemist"],
"DM Chemist": ["dm chemist"],
"DM Operator": ["dm operator"],

"RO Plant Chemist": ["ro plant chemist"],
"RO Plant Operator": ["ro plant operator"],

"Senior Chemist": ["senior chemist"],

"Cooling Tower Operator": ["cooling tower operator"],

"Bagasse Operator": ["bagasse operator"],

"Commissioning Engineer - Turbine": ["commissioning engineer turbine"],

"IT Admin": ["it admin","system administrator"],

"Computer Science and Engineering": ["computer science engineer"],

"Bull Driver": ["bull driver"],

"Fresher": ["fresher"],
"Boiler Field Operator": [
    "boiler field operator",
    "boiler field operator",
    "boiler field  operator"],

"Instrumentation Engineer": [
    "instrumentation engineer",
    "instrument engineer"
],

"Shift Incharge": [
    "shift incharge",
    "shift in charge",
    "shift incharge",
    "shift in charge",
    "shift duty",
    "shift supervisor",
    "plant operator shift",
    "plant incharge",
    "power plant",
    "plant operation",
    "plant operator"
],

"Boiler Operator": [
    "boiler",
    "fbc boiler",
    "afbc boiler"
],

"DM Operator": [
    "dm plant",
    "dm operator"
],
}
import re

def normalize_line(line):
    line = line.lower()
    line = re.sub(r'[^a-z\s]', ' ', line)
    return re.sub(r'\s+', ' ', line).strip()
def clean_job_title(role):

    if not role:
        return None
    if role.strip() == "plant":
        return None
    role = role.lower()

    # REMOVE DATE PART
    role = re.sub(r'from.*', '', role)

    # REMOVE COMPANY / LOCATION
    role = re.sub(r'in .*', '', role)

    # REMOVE NUMBERS
    role = re.sub(r'\d+', '', role)

    role = role.strip()

    # ===============================
    # NORMALIZATION RULES (CRITICAL)
    # ===============================
    if "oper" in role:
        if "boiler" in role:
            return "Boiler Operator"
        if "field" in role:
            return "Field Operator"
        return "Operator"
    if "instrument" in role:
        return "Instrumentation Engineer"

    if "electrical" in role:
        return "Electrical Engineer"

    if "chemist" in role:
        return "Chemist"

    if "fitter" in role:
        return "Fitter"
    if "shift" in role:
        return "Shift Incharge"
    if "boiler" in role and "operator" in role:
        return "Boiler Operator"
    if "operator" in role and len(role.split()) <= 2:
        return role.title()

    if "dcs" in role:
        return "DCS Engineer"

    if "safety" in role:
        return "Safety Officer"

    if "manager" in role:
        if any(k in role for k in ["plant", "operation", "project", "maintenance"]):
            return role.title()
        return "Manager"

    # fallback
    if len(role.split()) > 5:
        return None

    return role.title()

def extract_job_title(text):

    import re
    from rapidfuzz import fuzz

    if not text:
        return None

    text_lower = text.lower()

    # ===============================
    # 1. DIRECT ROLE EXTRACTION
    # ===============================
    patterns = [
        r'working as (?:a|an)?\s*(.*?)\s*(?:in|at)',
        r'working as (.*?)\n',
        r'designation\s*[:\-]\s*(.*)',
        r'position\s*[:\-]\s*(.*)',
        r'role\s*[:\-]\s*(.*)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            role = match.group(1).strip()

            if role and len(role) > 3:
                return clean_job_title(role)

    # ===============================
    # 2. GET JOB TITLES FROM API
    # ===============================
    job_titles = get_job_titles()
    if not job_titles:
        return None

    # ===============================
    # 3. EXTRACT EXPERIENCE SECTION ONLY
    # ===============================
    exp_match = re.search(
        r'(experience.*?)(education|skills|projects|personal|declaration|$)',
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not exp_match:
        return None

    exp_text = exp_match.group(1)

    lines = [l.strip() for l in exp_text.split("\n") if l.strip()]

    best_title = None
    best_score = 0

    # ===============================
    # 4. SCAN EXPERIENCE LINES
    # ===============================
    for i, line in enumerate(lines[:25]):

        clean = normalize_line(line)
        for job, keywords in JOB_ROLE_KEYWORDS.items():
            for kw in keywords:
                if kw in clean:
                    return job
        if not clean or len(clean) < 5:
            continue

        # ❌ SKIP NOISE
        if any(x in clean for x in [
            "b.tech", "diploma", "ssc", "inter",
            "degree", "email", "phone", "address", "objective"
        ]):
            continue

        # 🔥 KEEP ONLY ROLE LINES
        if not any(k in clean for k in [
            "engineer", "technician", "operator",
            "manager", "chemist", "fitter", "incharge"
        ]):
            continue
        keywords = clean.split()
        filtered_titles = [
            t for t in job_titles
            if any(k in t.lower() or t.lower() in clean for k in keywords)
        ]
        if not filtered_titles:
            filtered_titles = job_titles[:50] 
        # ===============================
        # 5. FUZZY MATCHING
        # ===============================
        for title in filtered_titles:

            if any(x in title.lower() for x in ["computer science", "degree"]):
                continue
            score = fuzz.partial_ratio(clean, title.lower())
            if title.lower() in clean:
                score += 50
            # BOOST ROLE WORDS
            if any(k in clean for k in [
                "engineer", "technician", "operator",
                "manager", "executive", "incharge"
            ]):
                score += 20

            # BOOST RECENT LINES
            score += max(0, 60 - i * 2)

            # BOOST CURRENT JOB
            if any(k in clean for k in ["present", "current", "till"]):
                score += 50

            if score > best_score and score > 55:
                best_score = score
                best_title = title

    # ===============================
    # 6. FINAL OUTPUT
    # ===============================
    if best_title:
        cleaned = clean_job_title(best_title)
        if cleaned:
            return cleaned
    return best_title if best_title else "Fresher"

def looks_like_name(text):

    BLACKLIST = [
        "resume", "curriculum", "vitae",
        "objective", "career", "summary",
        "skills", "education", "academic",
        "experience", "work experience",
        "profile", "professional",
        "declaration", "personal details",
        "contact", "email", "phone",
        "address", "language",
        "working knowledge", "company",
        "responsibilities", "project",
        "manager", "engineer", "operator"
    ]
    words = text.split()

    if not (1 <= len(words) <= 4):
        return False

    if re.search(r"\d|[@_]", text):
        return False

    for bad in BLACKLIST:
        if bad in text.lower():
            return False

    return True
def is_address_line(line):
    return any(x in line.lower() for x in [
        "nagar", "district", "road", "street", "colony",
        "mandal", "pin", "village", "post"
    ])
def extract_name(text):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # ===============================
    # STEP 1: STRICT NAME FIELD (SAFE)
    # ===============================
    for line in lines:
        if re.match(r'^\s*name\s*[:\-]', line.lower()):
            match = re.search(r'name\s*[:\-]\s*([A-Za-z\s\.]{3,50})', line, re.I)
            if match:
                name = match.group(1).strip().title()
                if is_valid_name(name):
                    return name

    # ===============================
    # STEP 2: MR / MS BASED (NEW)
    # ===============================
    match = re.search(r'\b(mr|ms|mrs)\.?\s+([A-Za-z\s\.]{3,50})', text, re.I)
    if match:
        name = match.group(2).strip().title()
        if is_valid_name(name):
            return name

    # ===============================
    # STEP 3: HEADER DETECTION (FIXED)
    # ===============================
    for line in lines[:15]:

        clean = line.strip()
        lower = clean.lower()

        if not clean:
            continue

        # ❌ HARD REJECTION (CRITICAL FIX)
        if any(x in lower for x in [
            "father", "s/o", "d/o",
            "passport", "dob", "birth",
            "address", "po:", "place",
            "email", "phone", "mobile",
            "resume", "curriculum", "vitae",
            "objective", "skills", "experience",
            "academic", "qualification",
            "core competencies",
            "declaration",
            "web skype", "passport no"
        ]):
            continue

        # ❌ reject junk chars
        if re.search(r'\d|[@:/\-]', clean):
            continue

        # ❌ reject long lines
        if len(clean.split()) > 4:
            continue

        # ✅ STRONG SIGNAL: UPPERCASE NAME
        if clean.isupper() and 1 <= len(clean.split()) <= 4:
            name = clean.title()
            if is_valid_name(name):
                return name

        # ✅ NORMAL NAME
        if re.match(r'^[A-Za-z.\s]{3,40}$', clean):
            name = clean.title()
            if is_valid_name(name):
                return name

    # ===============================
    # STEP 4: EMAIL FALLBACK
    # ===============================
    match = re.search(r'([a-zA-Z]+)[._]?([a-zA-Z]+)?@', text)

    if match:
        parts = [p for p in match.groups() if p]
        name = " ".join(p.capitalize() for p in parts)
        if is_valid_name(name):
            return name

    return None
def is_valid_name(line):

    BAD_WORDS = [
        "curriculum", "vitae", "competencies",
        "passport", "birth", "mechanical", "with",
        "core", "date", "objective",
        "father", "address", "place","instrument technician",
        "department","government","india"
    ]

    line = line.strip()

    if len(line) < 3 or len(line) > 40:
        return False

    if any(char.isdigit() for char in line):
        return False

    if len(line.split()) > 4:
        return False

    # allow single word names (IMPORTANT FIX)
    if len(line.split()) == 1:
        if not line.isupper():
            return False

    for word in BAD_WORDS:
        if word in line.lower():
            return False

    return True
# ================= PAN =================

def detect_pan(text):

    match = re.search(
        r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
        text.upper()
    )

    return match.group() if match else None
=======
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
>>>>>>> 9d2d7face242eebb6a4a3d878a35ead4285cf42d


# ================= AADHAAR =================

<<<<<<< HEAD
def detect_aadhaar(text):

    match = re.search(
        r'\b\d{4}\s?\d{4}\s?\d{4}\b',
        text
    )

    if not match:
        return None

    return re.sub(r"\s", "", match.group())

def extract_all_fields(text):

    # BASIC
    name = extract_name(text)
    email = extract_email(text)
    phone = extract_phone(text)

    # JOB + EXPERIENCE
    job_title = extract_job_title(text)
    experience = calculate_experience(text)

    # NEW MODULES (YOU IMPORTED ALREADY)
    education = extract_education(text)
    address_data = extract_address(text)

    # OPTIONAL LOCATION
    location = extract_current_location(text)

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "job_title": job_title,
        "experience": experience,
        "education": education,

        # ADDRESS
        "address": address_data.get("address"),
        "city": address_data.get("city"),
        "state": address_data.get("state"),
        "country": address_data.get("country"),
        "pincode": address_data.get("pincode"),

        # CURRENT LOCATION (OPTIONAL)
        "current_city": location.get("city") if location else "",
        "current_state": location.get("state") if location else "",
    }
=======
def detect_aadhaar(text: str) -> Optional[str]:
    match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
    if not match:
        return None
    number = re.sub(r"\s", "", match.group())
    if len(number) == 12:
        return number
    return None
>>>>>>> 9d2d7face242eebb6a4a3d878a35ead4285cf42d
