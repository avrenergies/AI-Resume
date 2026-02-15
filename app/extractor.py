import re
import spacy
import phonenumbers


# ================= SAFE SPACY LOAD (LOW RAM) =================
try:
    nlp = spacy.load(
        "en_core_web_sm",
        disable=["parser", "tagger", "lemmatizer"]
    )
except:
    nlp = None


# ================= COMMON CLEANERS =================

def clean_text(text):
    text = text.replace("|", " ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ================= EMAIL =================

def normalize_text_for_email(text):

    # Fix OCR glued domains
    text = re.sub(r'(\.com|\.in|\.org|\.net)([A-Z])', r'\1 \2', text)

    # Replace OCR mistakes
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

    # Remove duplicates + unrealistic long strings
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

    # Fallback regex (OCR sometimes breaks spacing)
    fallback = re.findall(r'\+?\d[\d\s\-]{8,15}\d', text)

    for f in fallback:
        digits = re.sub(r'\D', '', f)
        if 10 <= len(digits) <= 13:
            phones.add("+" + digits if not digits.startswith("+") else digits)

    return list(phones)


# ================= EDUCATION =================

DEGREE_PATTERNS = {
    "PhD": ["phd", "doctor of philosophy"],
    "MBA": ["mba", "master of business administration"],
    "M.Tech": ["m.tech", "mtech", "master of technology"],
    "M.E": ["m.e", "master of engineering"],
    "MCA": ["mca", "master of computer applications"],
    "M.Sc": ["m.sc", "msc", "master of science"],
    "B.Tech": ["b.tech", "btech", "bachelor of technology"],
    "B.E": ["b.e", "be ", "bachelor of engineering"],
    "B.Sc": ["b.sc", "bsc", "bachelor of science"],
    "BCA": ["bca", "bachelor of computer applications"]
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

    # Return highest qualification
    priority = list(DEGREE_PATTERNS.keys())
    for degree in priority:
        if degree in found:
            return degree

    return found[0]


# ================= NAME =================

BLACKLIST = [
    "engineering", "college", "university", "institute",
    "technologies", "technology", "solutions", "systems",
    "pvt", "ltd", "limited", "company", "resume",
    "curriculum", "vitae", "profile"
]


def looks_like_name(text):

    words = text.split()

    if not (2 <= len(words) <= 4):
        return False

    if re.search(r"\d|[@_]", text):
        return False

    for bad in BLACKLIST:
        if bad in text.lower():
            return False

    return True


def extract_name(text):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 🔥 Strong Header Priority (first 6 lines)
    for line in lines[:6]:
        if looks_like_name(line):
            return line.title()

    # 🔥 Email username fallback
    email_match = re.search(r'([a-zA-Z0-9._%+-]+)@', text)
    if email_match:
        user = email_match.group(1).replace(".", " ").replace("_", " ")
        parts = user.split()
        if 1 <= len(parts) <= 3:
            return " ".join(p.capitalize() for p in parts)

    # 🔥 NLP fallback
    if nlp:
        try:
            doc = nlp(text[:1000])
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    if looks_like_name(ent.text):
                        return ent.text.title()
        except:
            pass

    return None


# ================= PAN =================

def detect_pan(text):

    match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text.upper())

    if not match:
        return None

    pan = match.group()

    # Optional strict format validation
    if pan[0:5].isalpha() and pan[5:9].isdigit():
        return pan

    return None


# ================= AADHAAR =================

def detect_aadhaar(text):

    match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)

    if not match:
        return None

    number = re.sub(r"\s", "", match.group())

    # Basic validation
    if len(number) == 12:
        return number

    return None
