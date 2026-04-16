import re

# ─── Master skill library (expanded) ────────────────────────────────────────

SKILL_DB: dict[str, list[str]] = {

    "programming": [
        "python", "java", "c++", "c", "javascript", "typescript",
        "golang", "rust", "matlab", "r", "scala", "kotlin", "swift",
        "php", "ruby", "perl", "bash", "shell",
    ],

    "ai_ml": [
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "opencv", "nlp", "computer vision", "scikit-learn", "keras",
        "yolo", "xgboost", "lightgbm", "hugging face", "langchain",
        "openai", "llm", "rag", "stable diffusion",
    ],

    "data": [
        "pandas", "numpy", "power bi", "tableau", "excel",
        "data analysis", "spark", "hadoop", "dbt", "airflow",
        "kafka", "flink", "snowflake", "bigquery", "looker",
    ],

    "backend": [
        "fastapi", "django", "flask", "node", "spring", "express",
        "rest api", "graphql", "grpc", "nestjs", "rails",
        "asp.net", "laravel", "gin", "fiber", "actix",
    ],

    "cloud": [
        "aws", "azure", "gcp", "docker", "kubernetes",
        "terraform", "ansible", "pulumi", "helm", "serverless",
        "lambda", "ec2", "s3", "cloudfront", "cloud run",
    ],

    "database": [
        "mysql", "postgresql", "mongodb", "oracle",
        "sqlite", "redis", "cassandra", "elasticsearch",
        "dynamodb", "firebase", "supabase", "cockroachdb",
    ],

    "devops": [
        "ci/cd", "jenkins", "github actions", "gitlab ci",
        "nginx", "linux", "bash", "prometheus", "grafana",
        "datadog", "splunk", "elk", "argocd", "fluxcd",
    ],

    "frontend": [
        "react", "angular", "vue", "html", "css",
        "bootstrap", "tailwind", "nextjs", "nuxt",
        "svelte", "gatsby", "webpack", "vite", "babel",
        "jquery", "ant design", "material ui", "chakra ui",
    ],

    "testing": [
        "selenium", "jest", "pytest", "junit", "cypress",
        "playwright", "postman", "jmeter", "testng",
        "mocha", "chai", "robot framework", "k6",
    ],

    "tools": [
        "git", "jira", "confluence", "vs code", "intellij",
        "pycharm", "figma", "notion", "slack", "github",
        "gitlab", "bitbucket", "sonarqube", "artifactory",
    ],
}

# ─── Synonyms ────────────────────────────────────────────────────────────────

SYNONYMS: dict[str, str] = {
    "py":        "python",
    "python3":   "python",
    "nodejs":    "node",
    "node.js":   "node",
    "postgres":  "postgresql",
    "mongo":     "mongodb",
    "k8s":       "kubernetes",
    "tf":        "tensorflow",
    "cv":        "computer vision",
    "js":        "javascript",
    "ts":        "typescript",
    "next.js":   "nextjs",
    "nuxt.js":   "nuxt",
    "vue.js":    "vue",
    "react.js":  "react",
    "gh actions": "github actions",
}

# ─── Normalisation ───────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9+.#/ ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ─── Extraction ──────────────────────────────────────────────────────────────

def extract_skills(text: str) -> list[str]:
    text = normalize_text(text)

    # Expand synonyms
    for short, full in SYNONYMS.items():
        text = re.sub(r"\b" + re.escape(short) + r"\b", full, text)

    detected: set[str] = set()
    for skills in SKILL_DB.values():
        for skill in skills:
            if re.search(r"\b" + re.escape(skill) + r"\b", text):
                detected.add(skill)

    return sorted(detected)


# ─── Clustering ──────────────────────────────────────────────────────────────

def cluster_skills(skills: list[str]) -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = {}
    for category, db_skills in SKILL_DB.items():
        matched = sorted(set(skills) & set(db_skills))
        if matched:
            clusters[category] = matched
    return clusters


# ─── Role expectations ───────────────────────────────────────────────────────

ROLE_KEYWORDS: dict[str, list[str]] = {
    "data":     ["data", "analyst", "scientist", "engineer"],
    "backend":  ["backend", "api", "server", "java", "python"],
    "frontend": ["frontend", "ui", "react", "nextjs", "angular"],
    "ai_ml":    ["ml", "ai", "machine", "vision", "nlp"],
    "devops":   ["devops", "infrastructure", "sre", "platform"],
    "cloud":    ["cloud", "aws", "azure", "gcp"],
    "testing":  ["qa", "test", "automation", "quality"],
}


def infer_expected_skills(job_title: str) -> list[str]:
    jt = job_title.lower()
    expected: set[str] = set()

    for category, keywords in ROLE_KEYWORDS.items():
        if any(k in jt for k in keywords):
            expected.update(SKILL_DB.get(category, []))

    # Fallback: return all skills
    if not expected:
        for skills in SKILL_DB.values():
            expected.update(skills)

    return list(expected)


# ─── Fit score ───────────────────────────────────────────────────────────────

def calculate_skill_fit(
    resume_skills: list[str], job_title: str
) -> tuple[int, list[str]]:
    if not resume_skills:
        return 0, []

    expected = infer_expected_skills(job_title)
    if not expected:
        return 0, []

    matched  = set(resume_skills) & set(expected)
    score    = int((len(matched) / len(expected)) * 100)
    missing  = sorted(set(expected) - set(resume_skills))[:10]

    return score, missing
