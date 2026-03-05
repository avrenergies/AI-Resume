import re
import spacy

# ================= SAFE SPACY LOAD =================
try:
    nlp = spacy.load(
        "en_core_web_sm",
        disable=["parser", "tagger", "lemmatizer"]
    )
except Exception:
    nlp = None


# ================= CONSTANTS =================

INDIAN_STATES = [
    "tamil nadu","tn","tamilnadu","karnataka","ka","kerala","kl","andhra pradesh","ap",
    "telangana","ts","maharashtra","mh","delhi","dl","west bengal","wb",
    "uttar pradesh","up","rajasthan","rj","gujarat","gj","madhya pradesh","mp",
    "haryana","hr","punjab","pb","bihar","odisha","assam"
]

ADDRESS_HINT_WORDS = [
    "street","st","road","rd","nagar","colony","layout",
    "lane","ln","block","sector","phase","building",
    "apartment","flat","floor","tower","near","opposite",
    "village","post","district","native","address","location"
]

NOISE_WORDS = [
    "resume","curriculum","email","phone",
    "objective","profile","education","experience",
    "skills","certifications"
]

STOP_WORDS = [
    "declaration","education","academic","experience",
    "skills","objective","summary"
]

TECH_BLACKLIST = [
    "react","java","python","devops",
    "django","flask","aws","azure",
    "node","angular","vue"
]

PINCODE_REGEX = re.compile(r"\b\d{6}\b")


# ================= PINCODE =================

def extract_pincode(text):
    match = PINCODE_REGEX.search(text)
    return match.group() if match else ""


# ================= STATE =================

def extract_state(text):
    text_lower = text.lower()

    for state in INDIAN_STATES:
        if re.search(r"\b" + re.escape(state) + r"\b", text_lower):
            if len(state) <= 3:
                return state.upper()
            return state.title()

    return ""


# ================= CITY =================

def extract_city(text):

    # Example: Chennai - 600096
    match = re.search(r"([A-Za-z\s]+)[–\-]\s*\d{6}", text)

    if match:
        city = match.group(1).strip().split(",")[-1].strip()

        if city.lower() not in TECH_BLACKLIST:
            return city.title()

    # spaCy NER fallback
    if nlp:
        try:
            doc = nlp(text[:1000])

            for ent in doc.ents:

                if ent.label_ in ["GPE","LOC"]:

                    city = ent.text.strip().lower()

                    if (
                        city not in TECH_BLACKLIST
                        and not re.search(r"\d", city)
                        and city != "india"
                    ):
                        return city.title()

        except Exception:
            pass

    return ""


# ================= SMART ADDRESS DETECTOR =================

def find_address_near_contact_info(text):

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    lines = lines[:25]

    for i, line in enumerate(lines):

        lower_line = line.lower()

        if any(stop in lower_line for stop in STOP_WORDS):
            break

        if (
            PINCODE_REGEX.search(line)
            or any(state in lower_line for state in INDIAN_STATES)
            or any(word in lower_line for word in ADDRESS_HINT_WORDS)
        ):

            if any(noise in lower_line for noise in NOISE_WORDS):
                continue

            address_parts = []

            for part in lines[i:i+4]:

                if any(stop in part.lower() for stop in STOP_WORDS):
                    break

                address_parts.append(part)

            if address_parts:
                return ", ".join(address_parts)

    return ""


# ================= FINAL EXTRACTORS =================

def extract_address(text):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    address_parts = []

    for line in lines[:15]:

        lower = line.lower()

        if any(stop in lower for stop in STOP_WORDS):
            break

        if "@" in line or re.search(r"\d{10}", line):
            continue

        if (
            PINCODE_REGEX.search(line)
            or "india" in lower
            or any(state in lower for state in INDIAN_STATES)
            or any(word in lower for word in ADDRESS_HINT_WORDS)
        ):

            if re.fullmatch(r"[A-Z\. ]{3,}", line):
                continue

            clean_line = re.sub(
                r"(?i)^(permanent\s+address|current\s+address|address)\s*[:\-]?\s*",
                "",
                line
            )

            address_parts.append(clean_line)

    full_address = ", ".join(address_parts)

    city = extract_city(full_address)
    state = extract_state(full_address)

    return {
        "address": full_address,
        "city": city,
        "state": state,
        "country": "India",
        "pincode": extract_pincode(full_address)
    }


# ================= CURRENT LOCATION =================

def extract_current_location(text):

    header_text = text[:1200]

    city = extract_city(header_text)
    state = extract_state(header_text)

    if not city and not state:
        return None

    return {
        "city": city,
        "state": state,
        "country": "India"
    }
