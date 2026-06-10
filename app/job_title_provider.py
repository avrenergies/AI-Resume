<<<<<<< HEAD
import requests

API_URL = "https://api.avrenergies.com/job-posting/departments/with-job-titles"

def fetch_job_titles_from_api():
    try:
        res = requests.get(API_URL, timeout=5)

        if res.status_code != 200:
            return []

        data = res.json()

        titles = []
        for dept in data.get("data", []):
            for job in dept.get("jobTitles", []):
                if job.get("name"):
                    titles.append(job["name"].strip())

        return titles

    except Exception:
=======
import requests

API_URL = "https://api.avrenergies.com/job-posting/departments/with-job-titles"

def fetch_job_titles_from_api():
    try:
        res = requests.get(API_URL, timeout=5)

        if res.status_code != 200:
            return []

        data = res.json()

        titles = []
        for dept in data.get("data", []):
            for job in dept.get("jobTitles", []):
                if job.get("name"):
                    titles.append(job["name"].strip())

        return titles

    except Exception:
>>>>>>> 9d2d7face242eebb6a4a3d878a35ead4285cf42d
        return []