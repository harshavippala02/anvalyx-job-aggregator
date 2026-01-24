import requests
import os

APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

def fetch_adzuna_jobs():
    if not APP_ID or not APP_KEY:
        raise RuntimeError("ADZUNA_APP_ID or ADZUNA_APP_KEY is missing")

    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"

    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": "data analyst",
        "where": "USA",
        "results_per_page": 20,
        "content-type": "application/json",
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    jobs = []
    for j in data.get("results", []):
        jobs.append({
            "external_id": j["id"],
            "title": j["title"],
            "company": j["company"]["display_name"],
            "location": j["location"]["display_name"],
            "url": j["redirect_url"],
            "source": "adzuna",
            "posted_at": j.get("created"),
        })

    return jobs
