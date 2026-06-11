import re
import spacy


# ================= SAFE SPACY LOAD =================
try:
    nlp = spacy.load(
        "en_core_web_sm",
        disable=["parser", "tagger", "lemmatizer"]
    )
except:
    nlp = None


# ================= CONSTANTS =================

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
    "apartment","flat","floor","tower","near","opposite",
    "village","post","district"
]

NOISE_WORDS = [
    "resume","curriculum","email","phone",
    "objective","profile","education","experience",
    "skills","certifications"
]

TECH_BLACKLIST = [
    "react","java","python","devops",
    "django","flask","aws","azure",
    "node","angular","vue"
]


# ================= PINCODE =================

def extract_pincode(text):
    match = re.search(r"\b\d{6}\b", text)
    return match.group() if match else ""


# ================= STATE =================

def extract_state(text):
    text_lower = text.lower()
    for state in INDIAN_STATES:
        if state in text_lower:
            return state.title()
    return ""


# ================= LABELED ADDRESS DETECTOR =================

def find_labeled_address(text):

    match = re.search(
        r'address\s*[:\-]\s*(.+)',
        text,
        re.IGNORECASE
    )

    if match:
        # capture next 2 lines also
        start = match.start()
        lines = text[start:].split("\n")[:3]
        return " ".join(lines)

    return None


# ================= CITY =================

def extract_city(text):

    # Pattern: Chennai – 600096
    match = re.search(r'([A-Za-z\s]+)[–\-]\s*\d{6}', text)
    if match:
        city = match.group(1).strip()
        if city.lower() not in TECH_BLACKLIST:
            return city.title()

    # NER fallback
    if nlp:
        try:
            doc = nlp(text[:1000])
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC"]:
                    city = ent.text.strip().lower()
                    if (
                        city not in TECH_BLACKLIST
                        and not re.search(r"\d", city)
                        and city != "india"
                    ):
                        return city.title()
        except:
            pass

    return ""


# ================= SMART ADDRESS DETECTOR =================

def find_address_block(text):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if not lines:
        return ""

    # 1️⃣ First check labeled address anywhere
    labeled = find_labeled_address(text)
    if labeled:
        return labeled

    candidates = []

    # 2️⃣ Check entire document (top + bottom)
    for i, line in enumerate(lines):

        lower = line.lower()

        if any(word in lower for word in NOISE_WORDS):
            continue

        score = 0

        if any(hint in lower for hint in ADDRESS_HINT_WORDS):
            score += 3

        if re.search(r"\b\d{6}\b", line):
            score += 5

        if any(state in lower for state in INDIAN_STATES):
            score += 3

        if re.search(r"\d+", line):
            score += 1

        if score >= 4:
            candidates.append((score, i))

    if not candidates:
        return ""

    # pick highest scoring
    candidates.sort(reverse=True)
    _, idx = candidates[0]

    # capture nearby lines
    start = max(0, idx - 1)
    end = min(len(lines), idx + 2)

    block = lines[start:end]
    block_text = ", ".join(block)
    block_text = re.sub(r'\S+@\S+', '', block_text)
    block_text = re.sub(r'\b\d{10,}\b', '', block_text)
    block_text = re.sub(r'[|]', ' ', block_text)
    STOP_WORDS = [
        "declaration","objective","career","email","mobile","phone","skype",
        "skills","linguistic ability","married","responsibilities","career summary","professional summary"
    ]
    
    for stop in STOP_WORDS:
        block_text = re.split(stop, block_text, flags=re.I)[0]
        block_text = re.sub(r'\s+', ' ', block_text)
        return block_text.strip(" ,:-")


# ================= FINAL ADDRESS EXTRACTOR =================

def extract_address(text):

    address_block = find_address_block(text)

    if not address_block:
        return None

    pincode = extract_pincode(address_block) or extract_pincode(text)
    state = extract_state(address_block) or extract_state(text)
    city = extract_city(address_block)

    return {
        "address": address_block.strip(),
        "city": city,
        "state": state,
        "country": "India",
        "pincode": pincode
    }


# ================= CURRENT LOCATION =================

def extract_current_location(text):

    header_text = text[:1200]

    city = extract_city(header_text)
    state = extract_state(header_text)

    BAD_LOCATION_WORDS = [
        "knowledge",
        "worked",
        "field",
        "afbc",
        "operator",
        "plant",
        "project",
        "engineer",
        "maintenance",
        "power",
        "resume",
        "curriculum"
    ]

    if city:

        city_lower = city.lower().strip()

        if city_lower in BAD_LOCATION_WORDS:
            city = ""

        if len(city.split()) > 4:
            city = ""

        if not re.match(r'^[A-Za-z\s]+$', city):
            city = ""

    if not city and not state:
        return None

    return {
        "city": city,
        "state": state,
        "country": "India"
    }