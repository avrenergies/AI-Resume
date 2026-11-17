"""
Job-title + division dropdown source.

AVR hierarchy:  Division → Department → Job Title
    GET {DIVISION_API}   → [{"id": 1, "name": "O&M"}, ...]
    GET {JOB_TITLE_API}  → [{"id", "name", "divisionId", "jobTitles": [{"id", "name"}]}, ...]

get_job_titles()      → flat list of every job title (live, cached JOB_TITLE_TTL seconds),
                        merged with the built-in fallback list so the dropdown is never empty.
get_departments()     → departments with divisionId / divisionName and their job titles.
get_divisions()       → [{"id", "name", "jobTitles": [...], "departments": [...]}]
match_job_title()     → fuzzy-map a raw phrase ("Instrumental Technician") to the
                        closest dropdown entry ("Instrumentation Technician").
divisions_for_title() → which division(s) a job title belongs to.
resolve_division()    → canonical division {"id", "name"} for a name typed/selected by the UI.
"""
from __future__ import annotations

import logging
import re
import threading
import time

from app_v2 import constants as C
from app_v2.config import DIVISION_API, JOB_TITLE_API, JOB_TITLE_TTL

log = logging.getLogger("resume_v2.job_titles")

_RETRY_AFTER_FAIL = 60  # seconds before re-trying the AVR API after a failure

_lock = threading.Lock()
_cache: dict = {"titles": [], "departments": [], "divisions": [], "fetched": 0.0, "live": False}

_SYNONYMS = [
    (r"\binstrumental\b", "instrumentation"),
    (r"\binstrument\b", "instrumentation"),
    (r"\be\s*&\s*i\b|\belectrical\s*(and|&)\s*instrumentation\b", "e&i"),
    (r"\bin[\s\-]?charge\b", "incharge"),
    (r"\bsr\.?\b|\bsenior\b", ""),
    (r"\bjr\.?\b|\bjunior\b", ""),
    (r"\btrainee\b|\bapprentice\b", ""),
    (r"\bmaintenance\s+engineer\b", "mechanical engineer"),
]


def _key(s: str) -> str:
    """Case/whitespace-insensitive key ("E&I  Engineer" == "e&i engineer")."""
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


# ── fetching ─────────────────────────────────────────────────────────────────

def _fetch_departments() -> list[dict]:
    import requests
    r = requests.get(JOB_TITLE_API, timeout=6)
    r.raise_for_status()
    data = r.json()
    departments: list[dict] = []
    for dept in data.get("data", []) or []:
        titles = [j["name"].strip() for j in dept.get("jobTitles", []) or [] if j.get("name") and j["name"].strip()]
        departments.append({"id": dept.get("id"), "name": (dept.get("name") or "").strip(),
                            "divisionId": dept.get("divisionId"), "jobTitles": titles})
    return departments


def _fetch_divisions() -> list[dict]:
    import requests
    r = requests.get(DIVISION_API, timeout=6)
    r.raise_for_status()
    data = r.json()
    return [{"id": d.get("id"), "name": (d.get("name") or "").strip()}
            for d in data.get("data", []) or [] if d.get("id") is not None and (d.get("name") or "").strip()]


def _build(departments: list[dict], divisions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Attach divisionName to departments; build division → departments/jobTitles tree."""
    names = {d["id"]: d["name"] for d in C.DIVISIONS_FALLBACK}
    names.update({d["id"]: d["name"] for d in divisions})
    order = [d["id"] for d in divisions] or [d["id"] for d in C.DIVISIONS_FALLBACK]
    for dep in departments:
        if dep.get("divisionId") is not None and dep["divisionId"] not in order:
            order.append(dep["divisionId"])

    tree: dict = {}
    for div_id in order:
        tree[div_id] = {"id": div_id, "name": names.get(div_id, f"Division {div_id}"),
                        "jobTitles": [], "departments": []}
    out_deps = []
    for dep in departments:
        div_id = dep.get("divisionId")
        dep = dict(dep, divisionName=names.get(div_id, f"Division {div_id}") if div_id is not None else "")
        out_deps.append(dep)
        if div_id is None:
            continue
        node = tree[div_id]
        node["departments"].append({"id": dep.get("id"), "name": dep["name"], "jobTitles": list(dep["jobTitles"])})
        seen = {_key(t) for t in node["jobTitles"]}
        for t in dep["jobTitles"]:
            if _key(t) not in seen:
                node["jobTitles"].append(t)
                seen.add(_key(t))
    return out_deps, [tree[i] for i in order]


def _refresh(force: bool = False) -> None:
    """Fill the cache (called under _lock)."""
    fresh = (time.time() - _cache["fetched"]) < JOB_TITLE_TTL
    if _cache["titles"] and fresh and not force:
        return
    live_ok = True
    try:
        departments = _fetch_departments()
        if not departments:
            raise ValueError("empty department list")
    except Exception as exc:
        log.warning("job-title API unavailable (%s) — using built-in division snapshot", exc)
        departments = [dict(d) for d in C.DEPARTMENTS_FALLBACK]
        live_ok = False
    try:
        divisions = _fetch_divisions()
    except Exception as exc:
        log.warning("division API unavailable (%s) — using built-in division names", exc)
        divisions = []  # department titles may still be live; names come from the snapshot
    departments, tree = _build(departments, divisions)

    merged: list[str] = []
    seen: set[str] = set()
    for t in [t for d in departments for t in d["jobTitles"]] + C.JOB_TITLE_FALLBACK:
        if t and _key(t) not in seen:
            merged.append(t)
            seen.add(_key(t))
    fetched = time.time() if live_ok else time.time() - JOB_TITLE_TTL + _RETRY_AFTER_FAIL
    _cache.update(titles=merged, departments=departments, divisions=tree, live=live_ok, fetched=fetched)


# ── public API ───────────────────────────────────────────────────────────────

def get_job_titles(force: bool = False) -> list[str]:
    with _lock:
        _refresh(force)
        return _cache["titles"]


def get_departments() -> list[dict]:
    with _lock:
        _refresh()
        return _cache["departments"]


def get_divisions() -> list[dict]:
    with _lock:
        _refresh()
        return _cache["divisions"]


def job_titles_live() -> bool:
    return bool(_cache["live"])


def divisions_for_title(title: str) -> list[dict]:
    """Divisions ({"id","name"}) whose job-title list contains `title` (case/space-insensitive)."""
    k = _key(title)
    if not k:
        return []
    return [{"id": d["id"], "name": d["name"]} for d in get_divisions()
            if any(_key(t) == k for t in d["jobTitles"])]


def resolve_division(name: str) -> dict | None:
    """Canonical {"id","name"} for a division name (case/space-insensitive), else None."""
    k = _key(name)
    if not k:
        return None
    for d in get_divisions():
        if _key(d["name"]) == k:
            return {"id": d["id"], "name": d["name"]}
    return None


def department_for(division_id, title: str) -> dict | None:
    """The department of `title` inside a division, when exactly one matches."""
    k = _key(title)
    hits = [dep for dep in get_departments()
            if dep.get("divisionId") == division_id and any(_key(t) == k for t in dep["jobTitles"])]
    if len(hits) == 1:
        return {"id": hits[0].get("id"), "name": hits[0]["name"]}
    return None


# ── fuzzy matching ───────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    s = s.lower()
    for pat, rep in _SYNONYMS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"[^a-z&\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def match_job_title(raw: str, options: list[str], threshold: int = 78) -> tuple[str, int]:
    """Return (best_option, score 0-100). ('', 0) when nothing is close enough."""
    if not raw or not options:
        return "", 0
    q = _norm(raw)
    if not q:
        return "", 0
    try:
        from rapidfuzz import fuzz
    except ImportError:  # pragma: no cover
        fuzz = None
    best, best_score = "", 0
    for opt in options:
        o = _norm(opt)
        if not o:
            continue
        if o == q:
            return opt, 100
        if fuzz:
            score = int(max(fuzz.token_set_ratio(q, o), fuzz.WRatio(q, o) * 0.9))
            # penalise matches that only share generic words like "engineer"
            q_toks, o_toks = set(q.split()), set(o.split())
            shared = q_toks & o_toks
            if shared and shared <= {"engineer", "technician", "operator", "manager", "executive", "officer"}:
                score = min(score, 60)
        else:
            score = 100 if o in q or q in o else 0
        if score > best_score:
            best, best_score = opt, score
    if best_score >= threshold:
        return best, best_score
    return "", best_score
