import requests
from sentence_transformers import SentenceTransformer, util
from functools import lru_cache

model = SentenceTransformer('all-MiniLM-L6-v2')

JOB_API = "https://api.avrenergies.com/job-posting/departments/with-job-titles"


@lru_cache(maxsize=1)
def fetch_jobs():
    try:
        res = requests.get(JOB_API, timeout=10)
        data = res.json()

        jobs = []

        for dept in data["data"]:
            department = dept["name"]

            for job in dept["jobTitles"]:
                jobs.append({
                    "title": job["name"],
                    "department": department
                })

        return jobs

    except Exception as e:
        print("JOB API ERROR:", e)
        return []


def match_job(resume_text):

    jobs = fetch_jobs()

    if not jobs:
        return {}

    resume_embedding = model.encode(resume_text)

    best_score = 0
    best_job = None

    for job in jobs:
        job_embedding = model.encode(job["title"])
        score = util.cos_sim(resume_embedding, job_embedding).item()

        if score > best_score:
            best_score = score
            best_job = job

    if not best_job:
        return {}

    return {
        "jobTitle": best_job["title"],
        "department": best_job["department"],
        "matchScore": round(best_score, 2)
    }
