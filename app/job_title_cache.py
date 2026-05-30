import time
from app.job_title_provider import fetch_job_titles_from_api

CACHE_DURATION = 3600  # 1 hour

_job_titles = []
_last_fetch = 0


def load_job_titles():
    global _job_titles, _last_fetch

    titles = fetch_job_titles_from_api()

    if titles:
        _job_titles = titles
        _last_fetch = time.time()

    return _job_titles


def get_job_titles():
    global _job_titles, _last_fetch

    now = time.time()

    # return cache
    if _job_titles and (now - _last_fetch < CACHE_DURATION):
        return _job_titles

    # refresh
    return load_job_titles()