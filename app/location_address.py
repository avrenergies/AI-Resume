import re
import spacy

nlp = spacy.load("en_core_web_sm")

INDIAN_STATES = [
    "tamil nadu","karnataka","kerala","andhra pradesh",
    "telangana","maharashtra","delhi","west bengal",
    "uttar pradesh","rajasthan","gujarat","madhya pradesh",
    "haryana","punjab","bihar","odisha","assam",
    "jharkhand","chhattisgarh","uttarakhand","goa"
]

ADDRESS_HINT_WORDS = [
    "street","st","road","rd","nagar","colony","layout",
    "lane","ln","block","sector","phase","building",
    "apartment","flat","floor","tower","near","opposite"
]

NOISE_WORDS = [
    "resume","curriculum","email","phone",
    "objective","profile","education","experience"
]


# ================= PINCODE =================

def extract_pincode(text):
    match = re.search(r'\b\d{6}\b', text)
    return match.group() if match else ""


# ================= STATE =================

def extract_state(text):

    text_lower = text.lower()

    for state in INDIAN_STATES:
        if state in text_lower:
            return state.title()

    return ""


# ================= CITY via NER =================

def extract_city(text):

    doc = nlp(text)

    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            city = ent.text.strip()

            # avoid country mistaken as city
            if city.lower() != "india":
                return city

    return ""


# ================= ADDRESS BLOCK DETECTOR =================

def find_address_block(text):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    candidates = []

    for i, line in enumerate(lines):

        lower = line.lower()

        # Skip obvious noise
        if any(word in lower for word in NOISE_WORDS):
            continue

        score = 0

        if any(hint in lower for hint in ADDRESS_HINT_WORDS):
            score += 2

        if re.search(r'\b\d{6}\b', line):
            score += 3

        if any(state in lower for state in INDIAN_STATES):
            score += 2

        if re.search(r'\d+', line):
            score += 1

        if score >= 3:
            candidates.append((score, i, line))

    if not candidates:
        return ""

    # pick highest score
    best = sorted(candidates, reverse=True)[0]

    idx = best[1]

    # grab neighboring lines (addresses span multiple lines)
    block = lines[max(0, idx-1): idx+2]

    return ", ".join(block)


# ================= FINAL EXTRACTOR =================

def extract_address(text):

    address_block = find_address_block(text)

    if not address_block:
        return None

    pincode = extract_pincode(address_block) or extract_pincode(text)
    state = extract_state(address_block) or extract_state(text)
    city = extract_city(address_block)

    return {
        "address": address_block,
        "city": city,
        "state": state,
        "country": "India",
        "pincode": pincode
    }


# ================= CURRENT LOCATION =================

def extract_current_location(text):

    city = extract_city(text)
    state = extract_state(text)

    if not city and not state:
        return None

    return {
        "city": city,
        "state": state,
        "country": "India"
    }
