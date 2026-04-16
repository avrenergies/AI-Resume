import re
import spacy
import phonenumbers

# ─── spaCy safe load ─────────────────────────────────────────────────────────
try:
    nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
except Exception:
    nlp = None

# ─── Text normalisation ──────────────────────────────────────────────────────

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


# ─── Email ───────────────────────────────────────────────────────────────────

def _normalize_email_text(text: str) -> str:
    text = re.sub(r"(\.com|\.in|\.org|\.net)([A-Z])", r"\1 \2", text)
    text = text.replace(" @ ", "@").replace(" . ", ".")
    for fake, real in [("(at)", "@"), ("[at]", "@"), ("(dot)", "."), ("[dot]", ".")]:
        text = text.replace(fake, real)
    return text


def extract_email(text: str) -> list[str]:
    text = _normalize_email_text(text)
    matches = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b", text)
    seen, result = set(), []
    for m in matches:
        m = m.lower()
        if m not in seen and len(m) < 50:
            seen.add(m)
            result.append(m)
    return result


# ─── Phone ───────────────────────────────────────────────────────────────────

def _to_e164(raw: str) -> str | None:
    """Normalise any phone string to E164 (+91XXXXXXXXXX), or None if invalid."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        digits = "91" + digits
    elif len(digits) == 11 and digits.startswith("0"):
        digits = "91" + digits[1:]
    if not (11 <= len(digits) <= 13):
        return None
    return "+" + digits


def extract_phone(text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

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


# ─── Education ───────────────────────────────────────────────────────────────
# FIX: use \b word-boundary regex instead of substring 'in text_lower'
# This prevents "Tech Mahindra" matching "mba", "B.E Hons" mismatching, etc.

DEGREE_PATTERNS: dict[str, list[str]] = {
    "PhD":    [r"\bph\.?d\b", r"\bdoctor of philosophy\b"],
    "MBA":    [r"\bmba\b", r"\bmaster of business administration\b"],
    "M.Tech": [r"\bm\.?tech\b"],
    "M.E":    [r"\bm\.e\b"],
    "MCA":    [r"\bmca\b"],
    "M.Sc":   [r"\bm\.?sc\b"],
    "B.Tech": [r"\bb\.?tech\b"],
    "B.E":    [r"\bb\.e\b", r"\bbachelor of engineering\b"],
    "B.Sc":   [r"\bb\.?sc\b"],
    "BCA":    [r"\bbca\b"],
    "B.Com":  [r"\bb\.?com\b"],
    "B.A":    [r"\bb\.a\b", r"\bbachelor of arts\b"],
}

# Degree priority: highest first
DEGREE_PRIORITY = [
    "PhD", "MBA", "M.Tech", "M.E", "MCA", "M.Sc",
    "B.Tech", "B.E", "B.Sc", "BCA", "B.Com", "B.A",
]


def extract_education(text: str) -> str | None:
    text_lower = text.lower()
    found = set()
    for degree, patterns in DEGREE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                found.add(degree)
                break
    if not found:
        return None
    for degree in DEGREE_PRIORITY:
        if degree in found:
            return degree
    return next(iter(found))


# ─── Name ────────────────────────────────────────────────────────────────────

_BLACKLIST = {
    "engineering", "college", "university", "institute", "technologies",
    "technology", "solutions", "systems", "pvt", "ltd", "limited",
    "company", "resume", "curriculum", "vitae", "cv",
}
_SECTION_WORDS = [
    "personal", "summary", "objective", "profile", "details", "information",
]
_HEADER_WORDS = ["curriculum", "vitae", "resume", "cv"]


def _looks_like_name(text: str) -> bool:
    words = text.split()
    if not (1 <= len(words) <= 4):
        return False
    if re.search(r"[\d@_]", text):
        return False
    return not any(b in text.lower() for b in _BLACKLIST)


def extract_name(text: str) -> str | None:
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for line in lines[:10]:
        lo = line.lower()
        if any(h in lo for h in _HEADER_WORDS):
            continue
        if any(w in lo for w in ("mail", "email", "phone", "mobile", "@")):
            continue

        # Strip section-label words
        cleaned = line
        for word in _SECTION_WORDS:
            cleaned = re.sub(rf"\b{word}\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^\w\s\.]", "", cleaned).strip()

        words = cleaned.split()
        if not words or len(words) > 4:
            continue

        # Drop bare initials like "B."
        words = [w for w in words if not (len(w) == 2 and w.endswith("."))]
        if not words:
            continue

        name = " ".join(words)
        if re.match(r"^[A-Za-z\s\.]{3,40}$", name) and _looks_like_name(name):
            return name.title()

    # spaCy PERSON fallback
    if nlp:
        try:
            doc = nlp(text[:800])
            for ent in doc.ents:
                if ent.label_ == "PERSON" and _looks_like_name(ent.text):
                    return ent.text.title()
        except Exception:
            pass

    # Email username fallback
    m = re.search(r"([a-zA-Z0-9._%+-]+)@", text)
    if m:
        user = re.sub(r"\d+", "", m.group(1)).replace(".", " ").replace("_", " ")
        parts = user.split()
        if 1 <= len(parts) <= 3:
            return " ".join(p.capitalize() for p in parts)

    return None


# ─── PAN ─────────────────────────────────────────────────────────────────────

def detect_pan(text: str) -> str | None:
    m = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text.upper())
    return m.group() if m else None


# ─── Aadhaar ─────────────────────────────────────────────────────────────────

def detect_aadhaar(text: str) -> str | None:
    m = re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text)
    if not m:
        return None
    return re.sub(r"\s", "", m.group())
