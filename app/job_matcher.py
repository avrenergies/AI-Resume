import logging 
from functools import lru_cache

import requests
import torch
from sentence_transformers import SentenceTransformer, util

from app.skill_engine import extract_skills, cluster_skills, calculate_skill_fit

logger = logging.getLogger("resume_api.job_matcher")

JOB_API = "https://api.avrenergies.com/job-posting/departments/with-job-titles"

# ─── Inline JSON  ─────────────────────────────────────────────────────────────
# Primary source when API is down.
# Keep this in sync with department_response.json.

_JSON_DATA = {
    "success": True,
    "data": [
        {
            "_id": "691f2a874d5c21325b70914e",
            "name": "HR Team",
            "jobTitles": [
                {"_id": "691f2a874d5c21325b709150", "name": "HR Executive",  "certificates": []},
                {"_id": "691f2b3c4d5c21325b709167", "name": "HR Manager",    "certificates": []},
            ],
        },
        {
            "_id": "691f36114d5c21325b7092c1",
            "name": "Finance Team",
            "jobTitles": [
                {"_id": "691f36114d5c21325b7092c3", "name": "Finance Executive", "certificates": []},
            ],
        },
        {
            "_id": "691ffcdd4d5c21325b70966f",
            "name": "Power Plant O&M",
            "jobTitles": [
                {"_id": "692008644d5c21325b70978a", "name": "Safety Officer",
                 "certificates": [{"_id": "68e4b9f492b57cb2253c69c9", "name": "Safety Certificate"}]},
                {"_id": "692015624d5c21325b709a0d", "name": "Admin / Store Keeper", "certificates": []},
                {"_id": "692181694d5c21325b70b537", "name": "Operations Manager",   "certificates": []},
                {"_id": "692a9d45828ee8fad4050760", "name": "Plant Manager",
                 "certificates": [{"_id": "68e4a78692b57cb2253c6995", "name": "BOE"}]},
            ],
        },
        {
            "_id": "692155f54d5c21325b70ae8c",
            "name": "Power Plant Maintenance",
            "jobTitles": [
                {"_id": "692155f54d5c21325b70ae8e", "name": "Instrumentation Incharge",   "certificates": []},
                {"_id": "6923f6e7d0ae9825536c4671", "name": "Mill wright Fitter",         "certificates": []},
                {"_id": "6926a291db47e4b9df77d588", "name": "Mechanical Helper",          "certificates": []},
                {"_id": "6927f71cdb47e4b9df77e7df", "name": "Mechanical Incharge",        "certificates": []},
                {"_id": "69281019db47e4b9df77ee11", "name": "Mechanical Technician",      "certificates": []},
                {"_id": "69296be8828ee8fad404de35", "name": "Electrical Technician",      "certificates": []},
                {"_id": "692972fd828ee8fad404e54f", "name": "E&I  Engineer",              "certificates": []},
                {"_id": "69297dc1828ee8fad404e9e2", "name": "Instrumentation Engineer",   "certificates": []},
                {"_id": "69298362828ee8fad404ee5e", "name": "Instrumentation Technician", "certificates": []},
                {"_id": "692d250f828ee8fad4051a37", "name": "Electrical Engineer",        "certificates": []},
                {"_id": "692d2ccb828ee8fad40527e7", "name": "Mechanical Welder",          "certificates": []},
                {"_id": "693d2ca4092cef3d99fd3e2c", "name": "Mechanical Engineer",        "certificates": []},
                {"_id": "694e699f77df131fd48f1f86", "name": "Mechanical Fitter",          "certificates": []},
                {"_id": "694e6ac177df131fd48f1fef", "name": "IBR Welder",                "certificates": []},
            ],
        },
        {
            "_id": "692179564d5c21325b70b1bf",
            "name": "Water Treatment Plant",
            "jobTitles": [
                {"_id": "692179564d5c21325b70b1c1", "name": "RO Plant Chemist",  "certificates": []},
                {"_id": "6924016fd0ae9825536c4d33", "name": "RO plant Operators","certificates": []},
                {"_id": "69240870d0ae9825536c51c9", "name": "WTP Incharge",      "certificates": []},
                {"_id": "692438a3a4e47cd0a5a914d4", "name": "DM Operator",       "certificates": []},
                {"_id": "692557daa4e47cd0a5a91dee", "name": "DM Chemist",        "certificates": []},
                {"_id": "692586d5a4e47cd0a5a91fd9", "name": "WTP Chemist",       "certificates": []},
                {"_id": "6927f083db47e4b9df77e589", "name": "Senior Chemist",    "certificates": []},
            ],
        },
        {
            "_id": "69268d4ddb47e4b9df77d3a4",
            "name": "Power Plant Operations",
            "jobTitles": [
                {"_id": "69268d4ddb47e4b9df77d3a6", "name": "CHP Operator",          "certificates": []},
                {"_id": "69268ff0db47e4b9df77d496", "name": "FHS Operator",          "certificates": []},
                {"_id": "6926d492db47e4b9df77d85c", "name": "Turbine DCS Operator",  "certificates": []},
                {"_id": "6926e12bdb47e4b9df77dd77", "name": "Turbine Field Operator","certificates": []},
                {"_id": "69294134828ee8fad403b6bd", "name": "Shift Incharge",
                 "certificates": [{"_id": "68e4a78692b57cb2253c6995", "name": "BOE"}]},
                {"_id": "6929484e828ee8fad403bec5", "name": "Boiler DCS Operator",
                 "certificates": [
                     {"_id": "68e4b91392b57cb2253c69b3", "name": "First Class"},
                     {"_id": "68e4b91c92b57cb2253c69b7", "name": "Second Class"},
                 ]},
                {"_id": "692a9099828ee8fad404fd0e", "name": "Boiler Field Operator",
                 "certificates": [
                     {"_id": "68e4b91392b57cb2253c69b3", "name": "First Class"},
                     {"_id": "68e4b91c92b57cb2253c69b7", "name": "Second Class"},
                 ]},
                {"_id": "692a9523828ee8fad40503f4", "name": "AHP Operator", "certificates": []},
            ],
        },
        {
            "_id": "69298758828ee8fad404f1c4",
            "name": "Others",
            "jobTitles": [
                {"_id": "69298758828ee8fad404f1c6", "name": "Control Instrumentation",          "certificates": []},
                {"_id": "692988b1828ee8fad404f2f9", "name": "Computer Science and Engineering", "certificates": []},
                {"_id": "69298952828ee8fad404f3b0", "name": "Control Room Operator",            "certificates": []},
                {"_id": "692989b6828ee8fad404f404", "name": "Bull Driver",                      "certificates": []},
                {"_id": "69298a1b828ee8fad404f48c", "name": "O&M Engineer",                     "certificates": []},
                {"_id": "692a9680828ee8fad405054b", "name": "Bagasse Operator",                 "certificates": []},
                {"_id": "692a97ee828ee8fad4050697", "name": "Cooling Tower Operator",           "certificates": []},
                {"_id": "692d765b828ee8fad40538d2", "name": "Commissioning Engineer - Turbine", "certificates": []},
                {"_id": "69301188e3df32cc1333214e", "name": "IT Admin",                         "certificates": []},
                {"_id": "696ba97ea84e92ba896f78fe", "name": "Fresher",                          "certificates": []},
            ],
        },
    ],
}

# ─── Model ────────────────────────────────────────────────────────────────────

try:
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("SentenceTransformer loaded")
except Exception as exc:
    logger.error("SentenceTransformer load failed: %s", exc)
    _model = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_departments(data):
    roles = []
    for dept in data.get("data", []):
        for jt in dept.get("jobTitles", []):
            if jt.get("name"):
                roles.append({
                    "id":           jt["_id"],
                    "title":        jt["name"],
                    "department":   dept["name"],
                    "dept_id":      dept["_id"],
                    "certificates": jt.get("certificates", []),
                })
    return roles


def _norm(text):
    return text.strip().lower()


def _title_set(roles):
    return {r["title"].strip().lower() for r in roles}


def _is_valid_title(raw):
    if not raw:
        return False
    BAD_STARTS = {"in", "at", "for", "of", "to", "a", "an", "the",
                  "and", "or", "with", "by", "on", "from"}
    words = raw.strip().split()
    if not words:
        return False
    if words[0].lower() in BAD_STARTS:
        return False
    return len(raw.strip()) >= 4


# ─── Source 1: Live API (optional, with fallback) ─────────────────────────────

@lru_cache(maxsize=1)
def fetch_jobs_from_api():
    try:
        resp = requests.get(JOB_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise ValueError("API returned success=false")
        roles = _parse_departments(data)
        if not roles:
            raise ValueError("API returned empty role list")
        logger.info("API source OK — %d roles loaded", len(roles))
        return roles
    except Exception as exc:
        logger.warning("API source FAILED: %s", exc)
        return None


# ─── Source 2: Inline JSON (always available) ─────────────────────────────────

@lru_cache(maxsize=1)
def fetch_jobs_from_json():
    try:
        roles = _parse_departments(_JSON_DATA)
        if not roles:
            raise ValueError("JSON returned empty role list")
        logger.info("JSON source OK — %d roles loaded", len(roles))
        return roles
    except Exception as exc:
        logger.warning("JSON source FAILED: %s", exc)
        return None


# ─── Dual-source loader ───────────────────────────────────────────────────────
#
# Outcome A  Both alive & roles MATCH   → "API + JSON in sync"
# Outcome B  Both alive & roles DIFFER  → "Mismatch — verify manually"
# Outcome C  API down  / JSON alive     → "JSON only (API down)"
# Outcome D  API alive / JSON down      → "API only (JSON down)"
# Outcome E  Both down                  → raises RuntimeError

def load_sources():
    api_roles  = fetch_jobs_from_api()
    json_roles = fetch_jobs_from_json()

    api_ok  = api_roles  is not None
    json_ok = json_roles is not None

    if not api_ok and not json_ok:
        raise RuntimeError("Both sources unavailable.")

    if not api_ok and json_ok:
        logger.warning("OUTCOME C — API down, using JSON fallback")
        return json_roles, {
            "state": "C", "label": "JSON only (API down)",
            "detail": "Live API unavailable. Using local JSON source.",
            "in_sync": None,
            "warning": "API is down — results may not reflect the latest roles.",
            "mismatch_detail": None,
        }

    if api_ok and not json_ok:
        logger.warning("OUTCOME D — JSON down, using API only")
        return api_roles, {
            "state": "D", "label": "API only (JSON down)",
            "detail": "Local JSON failed. Using live API.",
            "in_sync": None,
            "warning": "JSON source failed.",
            "mismatch_detail": None,
        }

    only_api  = _title_set(api_roles)  - _title_set(json_roles)
    only_json = _title_set(json_roles) - _title_set(api_roles)

    if not only_api and not only_json:
        logger.info("OUTCOME A — both sources in sync (%d roles)", len(api_roles))
        return api_roles, {
            "state": "A", "label": "API + JSON in sync",
            "detail": "Both sources live and agree on %d roles." % len(api_roles),
            "in_sync": True, "warning": None, "mismatch_detail": None,
        }

    parts = []
    if only_api:  parts.append("Only in API: "  + ", ".join(sorted(only_api)))
    if only_json: parts.append("Only in JSON: " + ", ".join(sorted(only_json)))
    mismatch = " | ".join(parts)
    logger.warning("OUTCOME B — mismatch: %s", mismatch)
    return api_roles, {
        "state": "B", "label": "Mismatch — verify manually",
        "detail": "Both sources live but role lists differ. Using API as primary.",
        "in_sync": False,
        "warning": "Role lists are out of sync between API and JSON.",
        "mismatch_detail": mismatch,
    }


# ─── Embeddings cache ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_job_embeddings(titles_key):
    titles = titles_key.split("|")
    if not titles or _model is None:
        return [], None
    embeddings = _model.encode(titles, convert_to_tensor=True, show_progress_bar=False)
    logger.info("Title embeddings computed for %d roles", len(titles))
    return titles, embeddings


# ─── Priority 1: Subject / Post Applied For ──────────────────────────────────

_P1_PATTERNS = [
    "subject",
    "post applied for",
    "application for the post of",
    "applying for the post of",
    "applying for the position of",
    "applying for the role of",
    "applied for",
]

def _priority1_subject(text):
    for line in text.splitlines():
        ll = line.strip().lower()
        for pat in _P1_PATTERNS:
            if ll.startswith(pat):
                raw = line.strip()[len(pat):].strip(" :-")
                for prefix in ["application for the post of", "for the post of"]:
                    if raw.lower().startswith(prefix):
                        raw = raw[len(prefix):].strip()
                if raw:
                    logger.debug("[P1] matched: %r", raw)
                    return raw
    return None


# ─── Priority 2: Current / Present Employment ────────────────────────────────

_PRESENT_MARKERS = [
    "till date", "present", "current", "ongoing",
    "to date", "till now", "still date",
]

# Longest-first so specific patterns match before short ones
_DESIGNATION_KEYS = [
    "currently working as",
    "presently working as",
    "nature of work",
    "working as",
    "employed as",
    "current designation",
    "work designation",
    "designation",
    "position",
    "post",
]

_TYPO_MAP = {
    "curent":       "current",
    "oragnisation": "organisation",
    "organisaton":  "organisation",
    "designaton":   "designation",
    "stilldate":    "till date",
    "tilldate":     "till date",
}

def _fix_typos(text):
    t = text.lower()
    for wrong, right in _TYPO_MAP.items():
        t = t.replace(wrong, right)
    return t


def _collapse_spaces(text):
    result = ""
    prev_space = False
    for ch in text:
        if ch == " ":
            if not prev_space:
                result += ch
            prev_space = True
        else:
            result += ch
            prev_space = False
    return result


def _extract_raw_from_line(line, key):
    ll = line.strip().lower()
    idx_key = ll.find(key)
    if idx_key == -1:
        return ""
    after = line[idx_key + len(key):].strip()
    while after and after[0] in ": -.|=":
        after = after[1:].strip()
    raw = after.strip()
    for noise in [" from ", " since ", " at ", " in "]:
        if noise in raw.lower():
            raw = raw[:raw.lower().find(noise)].strip()
    for i, ch in enumerate(raw):
        if ch.isdigit() and raw[i: i + 4].isdigit():
            raw = raw[:i].strip(" ,.-")
            break
    for article in ["a ", "an "]:
        if raw.lower().startswith(article):
            raw = raw[len(article):]

    # 1. lowercase domain parens
    for domain in ["(o&m)", "(mechanical)", "(electrical)", "(civil)", "(operation)", "(operations)"]:
        idx = raw.lower().find(domain)
        if idx != -1:
            raw = raw[:idx] + domain + raw[idx + len(domain):]

    # 2. strip "from <date>" suffix
    for noise in [" from ", " since "]:
        pos = raw.lower().find(noise)
        if pos != -1:
            raw = raw[:pos]
    
    # 3. strip trailing bare year like "15 January 2023"
    words = raw.split()
    for i, w in enumerate(words):
        if len(w) == 4 and w.isdigit() and int(w) > 1900 and i >= 2:
            raw = " ".join(words[:i - 2])
            break
    return raw.strip()

def _priority2_current(text):
    """
    P2 — Handles all bio-data formats:
      "Work Designation : Boiler Field Operator"
      "Designation    :    Shift Incharge"   (extra spaces)
      "Designation - Electrical Technician"  (dash separator)
      "Nature of Work: Instrumentation Technician"
      "Post: WTP Chemist"
      "Designation:\\n    WTP Incharge"      (title on next line)
      "CURENT ORGANIZATION ... till date"   (typo + window search)
    Falls back to scanning ALL lines when no present-marker found.
    """
    text_fixed = _collapse_spaces(_fix_typos(text))
    lines      = text_fixed.splitlines()

    present_idx = [
        i for i, line in enumerate(lines)
        if any(marker in line.lower() for marker in _PRESENT_MARKERS)
    ]

    window_lines, seen = [], set()
    for idx in present_idx:
        for offset in range(-3, 4):
            pos = idx + offset
            if 0 <= pos < len(lines) and pos not in seen:
                seen.add(pos)
                window_lines.append((pos, lines[pos]))

    # No present marker → scan ALL lines (bio data without dates)
    if window_lines:     # Sort descending by line position — latest job in resume = highest index
         candidate_pairs = sorted(window_lines, key=lambda x: x[0], reverse=True)
    else:
        candidate_pairs = list(enumerate(lines))
    
    for pos, line in candidate_pairs:
        ll = _collapse_spaces(line.strip().lower())
        for key in _DESIGNATION_KEYS:
            if key not in ll:
                continue
            raw = _extract_raw_from_line(line, key)
            # Title on next line
            if not raw and pos + 1 < len(lines):
                next_line = lines[pos + 1].strip()
                if next_line and not any(k in next_line.lower() for k in _DESIGNATION_KEYS):
                    raw = next_line
            if _is_valid_title(raw):
                logger.debug("[P2] key=%r matched: %r", key, raw)
                return raw
    return None


# ─── Priority 3: Responsibility-Based Extraction ─────────────────────────────

_RESP_MAP = [
    (["turbine instrument", "cabel wir", "cable wir", "cable wiring"], "Instrumentation Technician"),
    (["boiler dcs", "dcs boiler"],                                      "Boiler DCS Operator"),
    (["boiler field", "field boiler", "boiler operat"],                 "Boiler Field Operator"),
    (["turbine dcs", "dcs turbine"],                                    "Turbine DCS Operator"),
    (["turbine field", "field turbine"],                                "Turbine Field Operator"),
    (["coal handl", "ash handl", "chp operator"],                       "CHP Operator"),
    (["fuel handl", "fhs operator"],                                    "FHS Operator"),
    (["shift supervis", "shift incharge"],                              "Shift Incharge"),
    (["ro plant", "reverse osmosis"],                                   "RO plant Operators"),
    (["water treat", "wtp incharge", "dm plant"],                       "WTP Incharge"),
    (["chemist", "chemical analys", "water quality"],                   "WTP Chemist"),
    (["plc ", "scada", "dcs control", "control system"],                "Control Instrumentation"),
    (["electrical maint", "panel wiring", "switchgear"],                "Electrical Technician"),
    (["welding", " weld "],                                             "Mechanical Welder"),
    (["fitter", "pipe fitting", "piping"],                              "Mechanical Fitter"),
    (["mechanical maint", "rotating equip"],                            "Mechanical Technician"),
    (["safety ", "hse ", "permit to work"],                             "Safety Officer"),
    (["human resource", "recruitment"],                                 "HR Executive"),
    (["finance", "accounting", "payroll"],                              "Finance Executive"),
    (["store keeper", "inventory", "warehouse"],                        "Admin / Store Keeper"),
    (["it admin", "information tech"],                                  "IT Admin"),
    (["bagasse"],                                                        "Bagasse Operator"),
    (["cooling tower"],                                                  "Cooling Tower Operator"),
    (["ash handling plant", "ahp operator"],                            "AHP Operator"),
]

def _priority3_responsibilities(text):

    text_lower = text.lower()
     # ← Find MOST RECENT job block only (between first heading and next heading)
    # Look for present/current markers to anchor current role
    present_markers = ["till date", "present", "current", "ongoing", "to date"]
    anchor = -1
    for marker in present_markers:
        pos = text_lower.rfind(marker)  # rfind = last occurrence = most recent
        if pos != -1:
            anchor = max(anchor, pos)
    
    if anchor != -1:
        # Take 300 chars around the present marker as current role block
        block = text_lower[max(0, anchor - 300): anchor + 100]
    else:
        start = -1
        for heading in ["experience", "employment", "career", "project"]:
            pos = text_lower.find(heading)
            if pos != -1:
                start = pos
                break
        block = text_lower[start:start+500] if start != -1 else text_lower[:500]
    
    for keywords, role in _RESP_MAP:
        if any(kw in block for kw in keywords):
            logger.debug("[P3] keyword → %r", role)
            return role
    return None


# ─── Priority 4: Objective / Summary Fallback ────────────────────────────────

_P4_ROLES = [
    "boiler field operator", "boiler dcs operator",
    "turbine dcs operator", "turbine field operator",
    "shift incharge", "chp operator", "fhs operator", "ahp operator",
    "wtp chemist", "wtp incharge", "ro plant chemist", "dm chemist",
    "instrumentation technician", "instrumentation engineer",
    "electrical technician", "electrical engineer",
    "mechanical engineer", "mechanical technician", "mechanical fitter",
    "safety officer", "instrumentation incharge",
    "hr executive", "finance executive",
    "it admin", "control room operator",
    "cooling tower operator", "bagasse operator", "o&m engineer",
]

def _priority4_objective(text):
    text_lower = text.lower()
    block = text_lower
    for heading in ["objective", "summary", "career goal", "profile", "about me"]:
        pos = text_lower.find(heading)
        if pos != -1:
            block = text_lower[pos: pos + 600]
            break
    best_role, best_score = None, 0
    for role in _P4_ROLES:
        score = sum(1 for kw in role.split() if len(kw) > 2 and kw in block)
        if score > best_score:
            best_score, best_role = score, role
    if best_role and best_score >= 1:
        logger.debug("[P4] matched: %r (score=%d)", best_role, best_score)
        return best_role.title()
    return None


# ─── Role mapper ──────────────────────────────────────────────────────────────

_ALIAS_MAP = [
    (["technician instrument", "instrument technician", "instrument tech",
      "instrumentation tech", "instrumentation dept technician",
      "e&i technician", "e and i technician", "e&i tech",
      "electrical instrument technician", "elec instrument tech"],
     "Instrumentation Technician"),
    (["instrument engineer", "instrumentation dept engineer",
      "e&i engineer", "e and i engineer", "electrical instrument engineer"],
     "Instrumentation Engineer"),
    (["instrument incharge", "instrument supervisor", "e&i incharge"],
     "Instrumentation Incharge"),
    (["boiler operator dcs", "dcs operator boiler", "boiler panel operator","boiler dcs engineer", "boiler dcs engg"],
     "Boiler DCS Operator"),
    (["boiler operator field", "field operator boiler", "boiler floor operator"],
     "Boiler Field Operator"),
    (["turbine operator dcs", "dcs operator turbine", "turbine panel operator"],
     "Turbine DCS Operator"),
    (["turbine operator field", "field operator turbine", "turbine floor operator"],
     "Turbine Field Operator"),
    (["wtp operator", "water treatment operator", "water treatment incharge",
      "wtp in-charge", "wtp in charge"],
     "WTP Incharge"),
    (["ro operator", "ro plant operator", "reverse osmosis operator"],
     "RO plant Operators"),
    (["dm operator", "demineralisation operator", "demineralization operator"],
     "DM Operator"),
    (["mech engineer", "mechanical dept engineer"], "Mechanical Engineer"),
    (["mech technician", "mechanical dept technician"], "Mechanical Technician"),
    (["mech fitter", "mechanical dept fitter"], "Mechanical Fitter"),
    (["mech welder", "mechanical dept welder"], "Mechanical Welder"),
    (["mech helper", "mechanical dept helper"], "Mechanical Helper"),
    (["elec engineer", "electrical dept engineer"], "Electrical Engineer"),
    (["elec technician", "electrical dept technician"], "Electrical Technician"),
    (["chp operator", "coal handling operator", "coal plant operator"], "CHP Operator"),
    (["fhs operator", "fuel handling operator", "fuel plant operator"], "FHS Operator"),
    (["ahp operator", "ash handling operator", "ash plant operator"], "AHP Operator"),
    (["shift supervisor", "shift officer", "shift in-charge", "shift in charge","Shift In-charge"], "Shift Incharge"),
    (["hr officer", "hr admin", "human resource officer", "human resource executive"], "HR Executive"),
    (["finance officer", "accounts officer", "accounts executive"], "Finance Executive"),
    (["store keeper", "storekeeper", "store incharge", "store in charge",
      "admin store", "store admin"], "Admin / Store Keeper"),
    (["o&m engineer", "o and m engineer", "om engineer", "operation maintenance engineer"], "O&M Engineer"),
    (["commissioning engineer turbine", "turbine commissioning"], "Commissioning Engineer - Turbine"),
    (["deputy manager mechanical", "deputy manager (mechanical)", "manager mechanical", "mechanical manager",
      "deputy manager maintenance", "maintenance manager","project manager o&m", "project manager (o&m)",
      "o&m manager", "operations manager", "operation manager","plant manager", "general manager plant",
      "deputy manager", "assistant manager plant"],"Plant Manager"),
    (["manager electrical", "electrical manager","deputy manager electrical"],"Plant Manager"), 
    (["hr manager", "human resource manager", "manager hr"],"HR Manager"),
]

_NOISE_WORDS = {
    "dept", "department", "section", "division", "unit",
    "the", "and", "or", "of", "in", "at", "for",
}


def _map_to_approved(raw, roles):
    """
    Pass 0 — alias map      (word-order variants, abbreviations, dept suffixes)
    Pass 1 — substring      (exact / contains)
    Pass 2 — token overlap  (noise-word stripped)
    Pass 3 — SentenceTransformer semantic similarity
    """
    norm_raw = _norm(raw)
    norm_raw_spaced = norm_raw  # alias map + substring already handles variations

    for aliases, role_name in _ALIAS_MAP:
        if any(alias in norm_raw_spaced for alias in aliases):
            for role in roles:
                if _norm(role["title"]) == _norm(role_name):
                    logger.debug("[MAP] alias: %r → %r", raw, role["title"])
                    return role

    for role in roles:
        norm_title = _norm(role["title"])
        if norm_title in norm_raw or norm_raw in norm_title:
            return role

    raw_tokens = set(norm_raw.split()) - _NOISE_WORDS
    best_role, best_score = None, 0
    for role in roles:
        role_tokens = set(_norm(role["title"]).split()) - _NOISE_WORDS
        overlap = len(raw_tokens & role_tokens)
        if overlap > best_score:
            best_score, best_role = overlap, role
    # ← Raise threshold: single token overlap only valid if title is also 1 token
    title_word_count = len(norm_raw.split())
    min_overlap = 1 if title_word_count <= 2 else 2   # need 2+ overlap for longer titles
    if best_role and best_score >= min_overlap:
        return best_role

    if _model is not None and roles:
        titles   = [r["title"] for r in roles]
        raw_emb  = _model.encode(raw,    convert_to_tensor=True)
        t_embs   = _model.encode(titles, convert_to_tensor=True, show_progress_bar=False)
        scores   = util.cos_sim(raw_emb, t_embs)[0]
        best_idx = int(torch.argmax(scores))
        logger.debug("[MAP] semantic: %r → %r (%.3f)",
                     raw, roles[best_idx]["title"], float(scores[best_idx]))
        return roles[best_idx]

    return None


# ─── Title extractor (P1 → P5) ───────────────────────────────────────────────

def _extract_job_title(resume_text, roles):
    checks = [
        (1, "Direct Subject/Post Mention",   _priority1_subject,          "high"),
        (2, "Current/Present Employment",    _priority2_current,          "high"),
        (3, "Responsibility-Based Mapping",  _priority3_responsibilities, "medium"),
        (4, "Objective/Summary Fallback",    _priority4_objective,        "low"),
    ]

    for priority, label, fn, confidence in checks:
        raw = fn(resume_text)
        if not raw:
            continue
        role_obj = _map_to_approved(raw, roles)
        return {
            "priority":       priority,
            "priority_label": label,
            "extracted_raw":  raw,
            "mapped_role":    role_obj["title"]        if role_obj else raw,
            "department":     role_obj["department"]   if role_obj else "Unknown",
            "dept_id":        role_obj["dept_id"]      if role_obj else None,
            "role_id":        role_obj["id"]           if role_obj else None,
            "certificates":   role_obj["certificates"] if role_obj else [],
            "confidence":     confidence,
        }

    # P5 — SentenceTransformer skill-based semantic search
    logger.info("[P5] No keyword match — falling back to semantic search")
    skills = extract_skills(resume_text)
    query  = " ".join(skills) if skills else resume_text[:1500]

    if _model is not None and roles:
        titles_key         = "|".join(r["title"] for r in roles)
        titles, embeddings = _get_job_embeddings(titles_key)
        if embeddings is not None:
            query_emb = _model.encode(query, convert_to_tensor=True)
            scores    = util.cos_sim(query_emb, embeddings)[0]
            best_idx  = int(torch.argmax(scores))
            role_obj  = roles[best_idx]
            return {
                "priority":       5,
                "priority_label": "Semantic Skill Search (SentenceTransformer)",
                "extracted_raw":  query[:120],
                "mapped_role":    role_obj["title"],
                "department":     role_obj["department"],
                "dept_id":        role_obj["dept_id"],
                "role_id":        role_obj["id"],
                "certificates":   role_obj["certificates"],
                "confidence":     "low",
            }

    return {
        "priority":       0,
        "priority_label": "No match found",
        "extracted_raw":  "",
        "mapped_role":    "Others",
        "department":     "Others",
        "dept_id":        None,
        "role_id":        None,
        "certificates":   [],
        "confidence":     "low",
    }


# ─── Public entry point ───────────────────────────────────────────────────────

def match_job(resume_text: str) -> dict:
    """
    Called by main.py for every resume.
    Returns a dict with jobTitle, department, certificates, matchScore,
    skills, skillClusters, fitScore, missingSkills, role_id, dept_id, source.
    """
    if _model is None:
        return _fallback()

    roles, source_meta = load_sources()
    title_info         = _extract_job_title(resume_text, roles)

    skills             = extract_skills(resume_text)
    clusters           = cluster_skills(skills)
    fit_score, missing = calculate_skill_fit(skills, title_info["mapped_role"])

    match_score        = 0.0
    titles_key         = "|".join(r["title"] for r in roles)
    titles, embeddings = _get_job_embeddings(titles_key)
    if embeddings is not None:
        query     = " ".join(skills) if skills else resume_text[:1500]
        query_emb = _model.encode(query, convert_to_tensor=True)
        scores    = util.cos_sim(query_emb, embeddings)[0]
        match_score = round(float(torch.max(scores)), 4)

    return {
        "jobTitle":      title_info["mapped_role"],
        "department":    title_info["department"],
        "role_id":       title_info["role_id"],
        "dept_id":       title_info["dept_id"],
        "matchScore":    match_score,
        "skills":        skills,
        "skillClusters": clusters,
        "fitScore":      fit_score,
        "missingSkills": missing,
        "certificates":  title_info["certificates"],
        "source":        source_meta,
        "extraction": {
            "priority":       title_info["priority"],
            "priority_label": title_info["priority_label"],
            "extracted_raw":  title_info["extracted_raw"],
            "confidence":     title_info["confidence"],
        },
    }


def _fallback() -> dict:
    return {
        "jobTitle": "", "department": "", "role_id": None, "dept_id": None,
        "matchScore": 0, "skills": [], "skillClusters": {}, "fitScore": 0,
        "missingSkills": [], "certificates": [], "source": {}, "extraction": {},
    }