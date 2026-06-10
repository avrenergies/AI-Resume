<<<<<<< HEAD
import re


# ================= MASTER SKILL LIBRARY =================

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


# ================= SYNONYMS =================

SYNONYMS = {
    "py": "python",
    "python3": "python",
    "nodejs": "node",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "cv": "computer vision"
}


# ================= NORMALIZER =================

def normalize_text(text):
    text = text.lower()
    text = text.replace("-", " ")
    text = re.sub(r'[^a-z0-9+.#/ ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_skill(skill):
    skill = skill.lower().strip()
    return SYNONYMS.get(skill, skill)


# ================= SKILL EXTRACTION =================

def extract_skills(text):

    text = normalize_text(text)

    detected = set()

    # Apply synonym expansion in text
    for short, full in SYNONYMS.items():
        text = re.sub(r'\b' + re.escape(short) + r'\b', full, text)

    for category, skills in SKILL_DB.items():

        for skill in skills:

            pattern = r'\b' + re.escape(skill) + r'\b'

            if re.search(pattern, text):
                detected.add(skill)

    return sorted(detected)


# ================= CLUSTERING =================

def cluster_skills(skills):

    clusters = {}

    for category, db_skills in SKILL_DB.items():

        matched = list(set(skills) & set(db_skills))

        if matched:
            clusters[category] = sorted(matched)

    return clusters


# ================= JOB ROLE EXPECTATION =================

ROLE_KEYWORDS = {
    "data": ["data", "analyst", "scientist"],
    "backend": ["backend", "api", "server"],
    "frontend": ["frontend", "ui", "react"],
    "ai_ml": ["ml", "ai", "machine", "vision"],
    "devops": ["devops", "infrastructure"],
    "cloud": ["cloud", "aws", "azure"]
}


def infer_expected_skills(job_title):

    job_title = job_title.lower()

    expected = []

    for category, keywords in ROLE_KEYWORDS.items():
        if any(k in job_title for k in keywords):
            expected.extend(SKILL_DB.get(category, []))

    # fallback: general tech expectation
    if not expected:
        expected = sum(SKILL_DB.values(), [])

    return list(set(expected))


# ================= FIT SCORE =================

def calculate_skill_fit(resume_skills, job_title):

    if not resume_skills:
        return 0, []

    expected = infer_expected_skills(job_title)

    matched = list(set(resume_skills) & set(expected))

    score = int((len(matched) / max(len(expected), 1)) * 100)

    missing = list(set(expected) - set(resume_skills))

    # limit missing to top 10
    missing = missing[:10]

    return score, missing
=======
import re


# ================= MASTER SKILL LIBRARY =================

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


# ================= SYNONYMS =================

SYNONYMS = {
    "py": "python",
    "python3": "python",
    "nodejs": "node",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "cv": "computer vision"
}


# ================= NORMALIZER =================

def normalize_text(text):
    text = text.lower()
    text = text.replace("-", " ")
    text = re.sub(r'[^a-z0-9+.#/ ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_skill(skill):
    skill = skill.lower().strip()
    return SYNONYMS.get(skill, skill)


# ================= SKILL EXTRACTION =================

def extract_skills(text):

    text = normalize_text(text)

    detected = set()

    # Apply synonym expansion in text
    for short, full in SYNONYMS.items():
        text = re.sub(r'\b' + re.escape(short) + r'\b', full, text)

    for category, skills in SKILL_DB.items():

        for skill in skills:

            pattern = r'\b' + re.escape(skill) + r'\b'

            if re.search(pattern, text):
                detected.add(skill)

    return sorted(detected)


# ================= CLUSTERING =================

def cluster_skills(skills):

    clusters = {}

    for category, db_skills in SKILL_DB.items():

        matched = list(set(skills) & set(db_skills))

        if matched:
            clusters[category] = sorted(matched)

    return clusters


# ================= JOB ROLE EXPECTATION =================

ROLE_KEYWORDS = {
    "data": ["data", "analyst", "scientist"],
    "backend": ["backend", "api", "server"],
    "frontend": ["frontend", "ui", "react"],
    "ai_ml": ["ml", "ai", "machine", "vision"],
    "devops": ["devops", "infrastructure"],
    "cloud": ["cloud", "aws", "azure"]
}


def infer_expected_skills(job_title):

    job_title = job_title.lower()

    expected = []

    for category, keywords in ROLE_KEYWORDS.items():
        if any(k in job_title for k in keywords):
            expected.extend(SKILL_DB.get(category, []))

    # fallback: general tech expectation
    if not expected:
        expected = sum(SKILL_DB.values(), [])

    return list(set(expected))


# ================= FIT SCORE =================

def calculate_skill_fit(resume_skills, job_title):

    if not resume_skills:
        return 0, []

    expected = infer_expected_skills(job_title)

    matched = list(set(resume_skills) & set(expected))

    score = int((len(matched) / max(len(expected), 1)) * 100)

    missing = list(set(expected) - set(resume_skills))

    # limit missing to top 10
    missing = missing[:10]

    return score, missing
>>>>>>> 9d2d7face242eebb6a4a3d878a35ead4285cf42d
