import requests
from sentence_transformers import SentenceTransformer, util
from functools import lru_cache
import torch

from app.skill_engine import (
    extract_skills,
    cluster_skills,
    calculate_skill_fit
)

# ================= MODEL LOAD =================

try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    print("❌ MODEL LOAD FAILED:", e)
    model = None


JOB_API = "https://api.avrenergies.com/job-posting/departments/with-job-titles"


# ================= FETCH JOBS =================

@lru_cache(maxsize=1)
def fetch_jobs():
    try:
        res = requests.get(JOB_API, timeout=10)
        data = res.json()

        jobs = []

        for dept in data.get("data", []):
            department = dept.get("name", "")

            for job in dept.get("jobTitles", []):
                title = job.get("name", "")
                if title:
                    jobs.append({
                        "title": title,
                        "department": department
                    })

        print(f"✅ Loaded {len(jobs)} jobs from API")

        return jobs

    except Exception as e:
        print("❌ JOB API ERROR:", e)
        return []


# ================= PRE-ENCODE JOB TITLES =================

@lru_cache(maxsize=1)
def get_job_embeddings():

    jobs = fetch_jobs()

    if not jobs or not model:
        return [], None

    titles = [job["title"] for job in jobs]

    embeddings = model.encode(
        titles,
        convert_to_tensor=True,
        show_progress_bar=False
    )

    return jobs, embeddings


# ================= MATCH ENGINE =================

def match_job(resume_text):

    if not model:
        return fallback_response()

    jobs, job_embeddings = get_job_embeddings()

    if not jobs or job_embeddings is None:
        return fallback_response()

    # ⭐ Extract skills first (SMART MATCHING)
    skills = extract_skills(resume_text)

    summary_text = " ".join(skills)

    # If no skills detected → fallback to resume head section
    if not summary_text:
        summary_text = resume_text[:1500]

    # ⭐ Encode summary only (IMPORTANT FIX)
    resume_embedding = model.encode(
        summary_text,
        convert_to_tensor=True
    )

    # ⭐ Fast vector similarity
    scores = util.cos_sim(resume_embedding, job_embeddings)[0]

    best_idx = torch.argmax(scores).item()
    best_score = scores[best_idx].item()
    best_job = jobs[best_idx]

    # ================= SKILL INTELLIGENCE =================

    clusters = cluster_skills(skills)

    fit_score, missing = calculate_skill_fit(
        skills,
        best_job["title"]
    )

    return {
        "jobTitle": best_job["title"],
        "department": best_job["department"],
        "matchScore": round(float(best_score), 2),

        "skills": skills,
        "skillClusters": clusters,
        "fitScore": fit_score,
        "missingSkills": missing
    }


# ================= FALLBACK =================

def fallback_response():
    return {
        "jobTitle": "Software Engineer",
        "department": "Engineering",
        "matchScore": 0,
        "skills": [],
        "skillClusters": {},
        "fitScore": 0,
        "missingSkills": []
    }
