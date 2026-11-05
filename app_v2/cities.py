"""
City dropdown data for v2  (country → state → [cities]).

Source: GeoNames "cities1000" (https://www.geonames.org, licence CC BY 4.0),
state names mapped to the exact names in constants.STATES, plus every city the
extractor already knows (constants.CITY_LOOKUP) with the same spelling it returns.
Rebuild: build_cities.py (kept outside the app).

Used by
  GET /options            → "cities": {country: {state: [city, ...]}}
  GET /cities?country=&state=
  extractor               → normalize_city(): clean the extracted city and map it
                            to the dropdown spelling so the City select is pre-filled
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache

_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cities_data.json")

# old / short names that resumes use → name in the dropdown list
CITY_ALIASES = {
    "madras": "Chennai", "bombay": "Mumbai", "calcutta": "Kolkata", "trichy": "Tiruchirappalli",
    "tiruchirapalli": "Tiruchirappalli", "vizag": "Visakhapatnam", "trivandrum": "Thiruvananthapuram",
    "calicut": "Kozhikode", "cochin": "Kochi", "bangalore": "Bengaluru", "mysore": "Mysuru",
    "mangalore": "Mangaluru", "gurgaon": "Gurugram", "pondicherry": "Puducherry", "allahabad": "Prayagraj",
    "bhubaneshwar": "Bhubaneswar", "belgaum": "Belagavi", "gulbarga": "Kalaburagi", "bellary": "Ballari",
    "shimoga": "Shivamogga", "tumkur": "Tumakuru", "baroda": "Vadodara", "poona": "Pune",
    "benares": "Varanasi", "banaras": "Varanasi", "kanchipuram": "Kanchipuram", "kancheepuram": "Kanchipuram",
    "tuticorin": "Thoothukudi", "ph": "Port Harcourt", "portharcourt": "Port Harcourt",
}


@lru_cache(maxsize=1)
def all_cities() -> dict:
    """{country: {state: [cities]}} — empty dict if the data file is missing (never raises)."""
    try:
        with open(_DATA_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # pragma: no cover
        return {}


def cities_for(country: str, state: str | None = None):
    """List of cities for one state, or {state: [cities]} for a whole country."""
    data = all_cities().get(country or "", {})
    if state:
        return list(data.get(state, []))
    return {k: list(v) for k, v in data.items()}


@lru_cache(maxsize=1)
def _index() -> dict:
    """lower-case city → [(canonical city, state, country), ...]"""
    idx: dict[str, list[tuple[str, str, str]]] = {}
    for country, states in all_cities().items():
        for state, cities in states.items():
            for c in cities:
                idx.setdefault(c.lower(), []).append((c, state, country))
    return idx


# words that are also tiny town names but in resumes are almost always part of an address
_GENERIC = {"nagar", "rani", "west", "east", "north", "south", "main", "new", "old", "road", "colony"}


def _clean_piece(s: str) -> str:
    s = re.sub(r"[^A-Za-z .'\-]", " ", s or "")
    s = re.sub(r"\b(dist(rict)?|taluk|tehsil|mandal|city|town|village|post|po|ps|at)\b\.?", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" .-'")


def _lookup(name: str, country: str, state: str) -> tuple[str, str] | None:
    """Exact (case-insensitive) match, alias-aware. Returns (city, state) or None."""
    hits: list = []
    for key in (name.lower(), CITY_ALIASES.get(name.lower(), "").lower()):  # exact first, alias second
        if key:
            hits = _index().get(key, [])
            if country:
                hits = [h for h in hits if h[2] == country]
            if hits:
                break
    if not hits:
        return None
    if state:
        same = [h for h in hits if h[1] == state]
        if same:
            return same[0][0], same[0][1]
        # known city but in another state → keep the city, do not touch the state
        return hits[0][0], ""
    if len({h[1] for h in hits}) == 1:  # unique → we can also infer the state
        return hits[0][0], hits[0][1]
    return hits[0][0], ""


def _fuzzy(name: str, country: str, state: str) -> str:
    """Spelling variants inside the known state only (e.g. 'Tiruchirapalli')."""
    if not (country and state) or len(name) < 5:
        return ""
    try:
        from rapidfuzz import fuzz, process
    except ImportError:  # pragma: no cover
        return ""
    choices = cities_for(country, state)
    if not choices:
        return ""
    best = process.extractOne(name, choices, scorer=fuzz.ratio, processor=str.lower)
    return best[0] if best and best[1] >= 92 else ""


def normalize_city(raw: str, country: str = "", state: str = "") -> tuple[str, str]:
    """
    Clean an extracted city and map it to the dropdown spelling.
    Returns (city, inferred_state). inferred_state is "" unless the city is unique
    in the country and no state was known.

      'Angawan \\nJaithari Anuppur', India, ''  → ('Anuppur', 'Madhya Pradesh')
      'Bangalore', India, 'Karnataka'          → ('Bengaluru', '')
      'Chennai', India, ''                     → ('Chennai', 'Tamil Nadu')
    """
    if not raw or not str(raw).strip():
        return "", ""
    raw = str(raw)
    pieces = [p for p in (_clean_piece(x) for x in re.split(r"[\n\r,;|/()]+", raw)) if p]
    if not pieces:
        return "", ""
    # 1. a whole piece is a known city
    for p in pieces:
        hit = _lookup(p, country, state)
        if hit:
            return hit[0], (hit[1] if not state else "")
    # 2. a word / two-word run inside a piece is a known city.
    #    Addresses run specific → general, so the LAST hit wins ("Anna Nagar West Chennai" → Chennai).
    last = None
    for p in pieces:
        toks = p.split()
        i = 0
        while i < len(toks):
            for n in (2, 1):
                cand = " ".join(toks[i:i + n])
                if len(toks[i:i + n]) < n or len(cand) < 4 or cand.lower() in _GENERIC:
                    continue
                hit = _lookup(cand, country, state)
                if hit:
                    last = hit
                    i += n - 1
                    break
            i += 1
    if last:
        return last[0], (last[1] if not state else "")
    # 3. close spelling inside the known state
    for p in pieces:
        f = _fuzzy(p, country, state)
        if f:
            return f, ""
    # 4. unknown place: keep the first piece if it looks like a place name
    first = pieces[0]
    if 2 <= len(first) <= 40 and len(first.split()) <= 4:
        return first.title(), ""
    return "", ""


def normalize_location_fields(fields, default_country: str = "") -> None:
    """In-place: clean the city inside currentWorkLocation / permanentAddress descriptors.
    Only touches 'city' (and fills 'state' when it was empty and the city is unique)."""
    for f in fields:
        v = f.get("value") if isinstance(f, dict) else None
        if not isinstance(v, dict) or not v.get("city"):
            continue
        city, st = normalize_city(v["city"], v.get("country") or default_country or "", v.get("state") or "")
        v["city"] = city
        if st and not v.get("state"):
            v["state"] = st
        if not any(v.values()):
            f.update(status="not_extracted", confidence=0.0)
