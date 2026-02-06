import requests
from sentence_transformers import SentenceTransformer, util
from functools import lru_cache

from app.skill_engine import (
    extract_skills,
    cluster_skills,
    calculate_skill_fit
)

# ✅ Load ONCE (VERY IMPORTANT)
model = SentenceTransformer('all-MiniLM-L6-v2')

JOB_API = "https://api.avrenergies.com/job-posting/departments/with-job-titles"


# ================= FETCH JOBS WITH CACHE =================

@lru_cache(maxsize=1)
def fetch_jobs():
    """
    Cached job fetch.
    Prevents API calls on every resume.
    HUGE performance win.
    """
    try:
        res = requests.get(JOB_API, timeout=15)
        data = res.json()

        jobs = []

        for dept in data.get("data", []):
            department = dept.get("name", "")

            for job in dept.get("jobTitles", []):
                jobs.append({
                    "title": job.get("name", ""),
                    "department": department
                })

        print(f"✅ Loaded {len(jobs)} job titles from AVR API")

        return jobs

    except Exception as e:
        print("❌ JOB API ERROR:", e)
        return []


# ================= MATCH ENGINE =================

def match_job(resume_text):

    jobs = fetch_jobs()

    if not jobs:
        return {}

    # ⭐ Encode resume ONCE
    resume_embedding = model.encode(resume_text)

    best_score = 0
    best_job = None

    for job in jobs:

        job_embedding = model.encode(job["title"])

        score = util.cos_sim(
            resume_embedding,
            job_embedding
        ).item()

        if score > best_score:
            best_score = score
            best_job = job

    if not best_job:
        return {}

    # ================= SKILL INTELLIGENCE =================

    skills = extract_skills(resume_text)
    clusters = cluster_skills(skills)

    fit_score, missing = calculate_skill_fit(
        skills,
        best_job["title"]
    )

    return {
        "jobTitle": best_job["title"],
        "department": best_job["department"],
        "matchScore": round(best_score, 2),

        # ⭐ AI Layer
        "skills": skills,
        "skillClusters": clusters,
        "fitScore": fit_score,
        "missingSkills": missing
    }
