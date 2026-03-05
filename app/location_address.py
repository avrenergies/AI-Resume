location_address.v2.txt
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
    "Tamil nadu","TN","Tamilnadu","karnataka","ka","kerala","kl","andhra pradesh","ap",
    "telangana","ts","maharashtra","mh","delhi","dl","west bengal","wb",
    "uttar pradesh","up","rajasthan","rj","gujarat","gj","madhya pradesh","mp",
    "haryana","hr","punjab","pb","bihar","odisha","assam"
]

ADDRESS_HINT_WORDS = [
    "street","st","road","rd","nagar","colony","layout",
    "lane","ln","block","sector","phase","building",
    "apartment","flat","floor","tower","near","opposite",
    "village","post","district","native place","native","Permanent Address:",
    "current address","Address","location","address for communication","communication address"]

NOISE_WORDS = [
    "resume","curriculum","email","phone",
    "objective","profile","education","experience",
    "skills","certifications","january", "february", "march", 
    "april", "may", "june", "july", "august", "september", 
    "october", "november", "december","challenging","responsible","position","organization","contribute","objective","client","designation"
]

STOP_WORDS = ["declaration", "education", "academic", "experience", "skills", "objective", "strengths","summary"]


TECH_BLACKLIST = [
    "react","java","python","devops",
    "django","flask","aws","azure",
    "node","angular","vue"
]

PINCODE_REGEX = re.compile(r"\b\d{6}\b")

# ================= PINCODE =================
def clean_ocr_line(line):
    """Removes tags and leading symbols common in scanned PDFs."""
    # 1. Remove tags found in scanned PDF text and Use word boundaries \b in your regex
    line = re.sub(r'\ ', '', line)
                  
    # 2. Clean leading symbols (colons, dashes, dots)
    line = re.sub(r'^[:\-\s,•]+', '', line).strip() # Remove leading symbols
    return line

def extract_pincode(text):
    match = re.search(r"\b\d{6}\b", text)
    return match.group() if match else ""

def extract_state(text):
    text_lower = text.lower()
    for state in INDIAN_STATES:
        if re.search(r'\b' + re.escape(state) + r'\b', text_lower):
            return state.upper() if len(state) <= 3 else state.title()
    return ""

# ================= CITY =================

def extract_city(text):

    # Pattern: Chennai – 600096
    match = re.search(r'([A-Za-z\s]+)[–\-]\s*\d{6}', text)
    if match:
        city = match.group(1).strip().split(',')[-1].strip()
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

def find_address_near_contact_info(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    lines = lines[:25]
       
    # --- STEP 1 ---
    for i, line in enumerate(lines):
        lower_line = line.lower()

        if any(stop in lower_line for stop in STOP_WORDS):
            break

        if (
            PINCODE_REGEX.search(line)
            or any(state in lower for state in INDIAN_STATES)
            or any(word in lower for word in ADDRESS_HINT_WORDS)
        ):

         if any(noise in lower for noise in NOISE_WORDS):
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


    for i, line in enumerate(lines[:15]): 
        lower = line.lower()

        # Stop if experience section starts
        if any(stop in lower for stop in STOP_WORDS):
            break

        # Ignore email & phone
        if "@" in line or re.search(r"\d{10}", line):
            continue

        if (
            PINCODE_REGEX.search(line)
            or "india" in lower
            or any(state in lower for state in INDIAN_STATES)
            or any(word in lower for word in ADDRESS_HINT_WORDS)
        ):

    line = re.sub(r'(?i)^address\s*[:\-]?\s*', '', line)

            address_parts.append(line)

    full_address = ", ".join(address_parts)

    return {
        "address": full_address,
        "city": "",
        "state": "",
        "country": "India",
        "pincode": extract_pincode(full_address)
    }

def extract_current_location(text):
    header_text = text[:1200]
    city = extract_city(header_text)
    state = extract_state(header_teximport re
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
    "Tamil nadu","TN","Tamilnadu","karnataka","ka","kerala","kl","andhra pradesh","ap",
    "telangana","ts","maharashtra","mh","delhi","dl","west bengal","wb",
    "uttar pradesh","up","rajasthan","rj","gujarat","gj","madhya pradesh","mp",
    "haryana","hr","punjab","pb","bihar","odisha","assam"
]

ADDRESS_HINT_WORDS = [
    "street","st","road","rd","nagar","colony","layout",
    "lane","ln","block","sector","phase","building",
    "apartment","flat","floor","tower","near","opposite",
    "village","post","district","native place","native",
    "current address","location","address for communication","communication address"]

NOISE_WORDS = [
    "resume","curriculum","email","phone",
    "objective","profile","education","experience",
    "skills","certifications","january", "february", "march", 
    "april", "may", "june", "july", "august", "september", 
    "october", "november", "december","challenging","responsible","position","organization","contribute","objective","client","designation"
]

STOP_WORDS = ["declaration", "education", "academic", "experience", "skills", "objective", "strengths","summary"]


TECH_BLACKLIST = [
    "react","java","python","devops",
    "django","flask","aws","azure",
    "node","angular","vue"
]

PINCODE_REGEX = re.compile(r"\b\d{6}\b")

# ================= PINCODE =================

def extract_pincode(text):
    match = re.search(r"\b\d{6}\b", text)
    return match.group() if match else ""


# ================= STATE =================

def extract_state(text):
    text_lower = text.lower()
    for state in INDIAN_STATES:
        if re.search(r'\b' + re.escape(state) + r'\b', text_lower):
            return state.upper() if len(state) <= 3 else state.title()
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
        city = match.group(1).strip().split(',')[-1].strip()
        if city.lower() not in TECH_BLACKLIST and city.lower() not in ["pin code", "pincode", "pin"]:
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

def find_address_near_contact_info(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    lines = lines[:25]
       
    # --- STEP 1 ---
    for i, line in enumerate(lines):
        lower_line = line.lower()

        if any(stop in lower_line for stop in STOP_WORDS):
            break

        if (
            PINCODE_REGEX.search(line)
            or any(state in lower for state in INDIAN_STATES)
            or any(word in lower for word in ADDRESS_HINT_WORDS)
        ):
            
            if any(noise in lower for noise in NOISE_WORDS):
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

    for i, line in enumerate(lines[:15]): 
        lower = line.lower()

        # Stop if experience section starts
        if any(stop in lower for stop in STOP_WORDS):
            break

        # Ignore email & phone
        if "@" in line or re.search(r"\d{10}", line):
            continue

        if (
            PINCODE_REGEX.search(line)
            or "india" in lower
            or any(state in lower for state in INDIAN_STATES)
            or any(word in lower for word in ADDRESS_HINT_WORDS)
        ):
            
            # skip name-like uppercase lines
            if re.fullmatch(r"[A-Z\. ]{3,}", line):
                continue
            
            line = re.sub(r'(?i)^(permanent\s+address|current\s+address|address)\s*[:\-]?\s*', '', line)

            address_parts.append(line)

    # -------- Second pass (bottom resumes like Personal Details) --------
    
    PERSONAL_FIELDS = ["name", "father", "mother", "dob", "date of birth", "age", "gender"]
    if not address_parts:

        for i, line in enumerate(lines):

            if "address" in line.lower():

                label_clean = re.sub(
                    r'(?i)^(permanent\s+address|current\s+address|address)\s*[:\-]?\s*',
                    '',
                    line
                ).strip()

                if label_clean:
                    address_parts.append(label_clean)

                for part in lines[i+1:i+4]:

                    lower_part = part.lower()

                    # skip personal detail lines
                    if any(p in lower_part for p in PERSONAL_FIELDS):
                        continue

                    address_parts.append(part.strip())

                break


    full_address = ", ".join(address_parts)

    city = extract_city(full_address)
    state = extract_state(full_address)

    return {
        "address": full_address,
        "city": city,
        "state": state,
        "country": "India",
        "pincode": extract_pincode(text)
    }

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
    }t)
    if not city and not state:

     if not city and not state:
        return None
    
    return {

        "city": city,
        "state": state,
        "country": "India"
    }

    



    



    
