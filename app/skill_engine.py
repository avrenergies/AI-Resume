import re

# ⭐ MASTER SKILL LIBRARY
# Expand anytime safely.

SKILL_DB = {

    "programming": [
        "python","java","c++","c","javascript","typescript",
        "golang","rust","matlab","r"
    ],

    "ai_ml":[
        "machine learning","deep learning","tensorflow",
        "pytorch","opencv","nlp","computer vision",
        "scikit-learn","keras","yolo","xgboost"
    ],

    "data":[
        "pandas","numpy","power bi","tableau",
        "excel","data analysis","spark","hadoop"
    ],

    "backend":[
        "fastapi","django","flask","node","spring",
        "express","rest api","graphql"
    ],

    "cloud":[
        "aws","azure","gcp","docker","kubernetes",
        "terraform"
    ],

    "database":[
        "mysql","postgresql","mongodb","oracle",
        "sqlite","redis"
    ],

    "devops":[
        "ci/cd","jenkins","github actions",
        "nginx","linux","bash"
    ],

    "frontend":[
        "react","angular","vue","html","css",
        "bootstrap","tailwind"
    ]
}


# ================= NORMALIZER =================

def normalize_skill(skill):
    return skill.lower().strip()


# ================= SKILL EXTRACTION =================

def extract_skills(text):

    text = text.lower()

    detected = set()

    for category, skills in SKILL_DB.items():

        for skill in skills:

            # exact word match
            pattern = r'\b' + re.escape(skill) + r'\b'

            if re.search(pattern, text):
                detected.add(skill)

    return sorted(list(detected))


# ================= CLUSTERING =================

def cluster_skills(skills):

    clusters = {}

    for category, db_skills in SKILL_DB.items():

        matched = list(set(skills) & set(db_skills))

        if matched:
            clusters[category] = matched

    return clusters


# ================= FIT SCORE =================

def calculate_skill_fit(resume_skills, job_title):

    """
    Basic intelligence:
    Match job keywords inside title
    against candidate skills.
    """

    if not resume_skills:
        return 0, []

    job_title = job_title.lower()

    expected = []

    # naive mapping (can become AI later)
    for category, skills in SKILL_DB.items():

        if any(word in job_title for word in category.split("_")):
            expected.extend(skills)

    if not expected:
        # fallback: assume tech job
        expected = sum(SKILL_DB.values(), [])

    matched = list(set(resume_skills) & set(expected))

    score = int((len(matched) / max(len(expected),1)) * 100)

    missing = list(set(expected) - set(resume_skills))[:10]

    return score, missing
