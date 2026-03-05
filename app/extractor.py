import re
import spacy
import phonenumbers


# ================= SAFE SPACY LOAD =================

try:
    nlp = spacy.load(
        "en_core_web_sm",
        disable=["parser", "tagger", "lemmatizer"]
    )
except:
    nlp = None


# ================= TEXT NORMALIZATION =================

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


# ================= COMMON CLEANERS =================

def clean_text(text):

    text = text.replace("|", " ")
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# ================= EMAIL =================

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


# ================= PHONE =================

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


# ================= EDUCATION =================

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


def extract_education(text):

    text_lower = text.lower()

    found = []

    for degree, patterns in DEGREE_PATTERNS.items():

        for p in patterns:

            if p in text_lower:

                found.append(degree)
                break

    if not found:
        return None

    priority = list(DEGREE_PATTERNS.keys())

    for degree in priority:

        if degree in found:
            return degree

    return found[0]


# ================= NAME =================

BLACKLIST = [
    "engineering", "college", "university",
    "institute", "technologies",
    "technology", "solutions", "systems",
    "pvt", "ltd", "limited",
    "company", "resume"
]
SECTION_WORDS = [
    "personal", "summary", "objective",
    "profile", "details", "information"
]

HEADER_WORDS = [
    "curriculum", "vitae", "resume", "cv"
]


def looks_like_name(text):

    words = text.split()

    if not (1 <= len(words) <= 4):
        return False

    if re.search(r"\d|[@_]", text):
        return False

    for bad in BLACKLIST:
        if bad in text.lower():
            return False

    return True

def extract_name(text):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for line in lines[:10]:

        line_lower = line.lower()

        # Skip headers
        if any(h in line_lower for h in HEADER_WORDS):
            continue

        # Skip email lines
        if "mail" in line_lower or "email" in line_lower:
            continue

        # Skip phone/mobile lines
        if "phone" in line_lower or "mobile" in line_lower:
            continue

        # Remove section words
        for word in SECTION_WORDS:
            line = re.sub(rf'\b{word}\b', '', line, flags=re.IGNORECASE)

        line = line.strip()

        # Remove punctuation except dot
        line = re.sub(r'[^\w\s\.]', '', line)

        words = line.split()

        if len(words) == 0 or len(words) > 4:
            continue

        cleaned = []

        for w in words:

            # Handle initials like B.
            if len(w) == 2 and w.endswith("."):
                continue

            cleaned.append(w)

        if not cleaned:
            continue

        name = " ".join(cleaned)

        if re.match(r'^[A-Za-z\s\.]{3,40}$', name):
            if looks_like_name(name):
                return name.title()

    # Email fallback
    email_match = re.search(r'([a-zA-Z0-9._%+-]+)@', text)

    if email_match:

        user = email_match.group(1)

        # Remove numbers from username
        user = re.sub(r'\d+', '', user)

        user = user.replace(".", " ").replace("_", " ")

        parts = user.split()

        if 1 <= len(parts) <= 3:
            return " ".join(p.capitalize() for p in parts)

    return None


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

