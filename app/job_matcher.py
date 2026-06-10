import logging
from functools import lru_cache

import requests
import torch
from sentence_transformers import SentenceTransformer, util

from app.skill_engine import extract_skills, cluster_skills, calculate_skill_fit

logger = logging.getLogger("resume_api.job_matcher")

JOB_API = "https://api.avrenergies.com/job-posting/departments/with-job-titles"

# ─── Model ───────────────────────────────────────────────────────────────────

try:
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("SentenceTransformer loaded")
except Exception as exc:
    logger.error("SentenceTransformer load failed: %s", exc)
    _model = None


# ─── Job fetch ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def fetch_jobs() -> list[dict]:
    try:
        resp = requests.get(JOB_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        jobs = [
            {"title": job["name"], "department": dept.get("name", "")}
            for dept in data.get("data", [])
            for job in dept.get("jobTitles", [])
            if job.get("name")
        ]
        logger.info("Loaded %d jobs from API", len(jobs))
        return jobs
    except Exception as exc:
        logger.error("Job API error: %s", exc)
        return []


@lru_cache(maxsize=1)
def get_job_embeddings():
    jobs = fetch_jobs()
    if not jobs or _model is None:
        return [], None
    titles = [j["title"] for j in jobs]
    embeddings = _model.encode(titles, convert_to_tensor=True, show_progress_bar=False)
    return jobs, embeddings


# ─── Match ───────────────────────────────────────────────────────────────────

def match_job(resume_text: str) -> dict:
    if _model is None:
        return _fallback()

    jobs, job_embeddings = get_job_embeddings()
    if not jobs or job_embeddings is None:
        return _fallback()

    skills = extract_skills(resume_text)
    query  = " ".join(skills) if skills else resume_text[:1500]

    resume_emb = _model.encode(query, convert_to_tensor=True)
    scores     = util.cos_sim(resume_emb, job_embeddings)[0]
    best_idx   = int(torch.argmax(scores))
    best_score = float(scores[best_idx])
    best_job   = jobs[best_idx]

    clusters             = cluster_skills(skills)
    fit_score, missing   = calculate_skill_fit(skills, best_job["title"])

    return {
        "jobTitle":     best_job["title"],
        "department":   best_job["department"],
        "matchScore":   round(best_score, 2),
        "skills":       skills,
        "skillClusters": clusters,
        "fitScore":     fit_score,
        "missingSkills": missing,
    }


def _fallback() -> dict:
    return {
        "jobTitle":     "Software Engineer",
        "department":   "Engineering",
        "matchScore":   0,
        "skills":       [],
        "skillClusters": {},
        "fitScore":     0,
        "missingSkills": [],
    }
