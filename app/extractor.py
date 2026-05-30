import re
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

try:
    nlp = spacy.load(
        "en_core_web_sm",
        disable=["parser", "tagger", "lemmatizer"]
    )
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


# ================= AADHAAR =================

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
