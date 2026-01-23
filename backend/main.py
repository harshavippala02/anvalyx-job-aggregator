from fastapi import FastAPI
from dotenv import load_dotenv
import os
import requests
from datetime import datetime

from database import init_db, insert_job, get_jobs

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

app = FastAPI(title="Anvalyx API")

# ---------------- STARTUP ----------------
@app.on_event("startup")
def startup():
    init_db()
    fetch_adzuna_jobs()
    fetch_greenhouse_jobs()
    fetch_lever_jobs()
    print("✅ All job sources loaded")

# ---------------- ADZUNA ----------------
def fetch_adzuna_jobs():
    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": 50,
        "what": "data analyst",
        "content-type": "application/json"
    }

    res = requests.get(url, params=params).json()

    for j in res.get("results", []):
        insert_job({
            "job_id": f"adzuna_{j['id']}",
            "title": j["title"],
            "company": j["company"]["display_name"],
            "location": j["location"]["display_name"],
            "category": j["category"]["label"],
            "salary_min": j.get("salary_min") or 0,
            "salary_max": j.get("salary_max") or 0,
            "url": j["redirect_url"],
            "source": "Adzuna",
            "created": j["created"]
        })

# ---------------- GREENHOUSE ----------------
def fetch_greenhouse_jobs():
    boards = [
        "airbnb", "stripe", "databricks",
        "snowflake", "openai"
    ]

    for company in boards:
        api = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        res = requests.get(api).json()

        # 🚨 SAFETY CHECK
        if not isinstance(res, dict):
            continue

        jobs = res.get("jobs")
        if not isinstance(jobs, list):
            continue

        for j in jobs:
            if not isinstance(j, dict):
                continue

            insert_job({
                "job_id": j.get("id"),
                "title": j.get("title"),
                "company": company,
                "location": j.get("location", {}).get("name"),
                "category": "IT Jobs",
                "salary_min": None,
                "salary_max": None,
                "url": j.get("absolute_url"),
                "created": j.get("updated_at"),
                "source": "greenhouse"
            })


# ---------------- LEVER ----------------
def fetch_lever_jobs():
    companies = [
        "netflix", "spotify", "robinhood",
        "square", "coinbase", "figma"
    ]

    for company in companies:
        api = f"https://api.lever.co/v0/postings/{company}"
        res = requests.get(api).json()

        # Safety check
        if not isinstance(res, list):
            continue

        for j in res:
            # 🚨 Skip if j is not a dict
            if not isinstance(j, dict):
                continue

            text_content = ""

            text = j.get("text")

            # text can be str OR list OR None
            if isinstance(text, str):
                text_content = text.lower()

            elif isinstance(text, list):
                text_content = " ".join(
                    t.get("text", "") for t in text if isinstance(t, dict)
                ).lower()

            # Only keep Data jobs
            if "data" not in text_content:
                continue

            insert_job({
                "job_id": j.get("id"),
                "title": j.get("text"),
                "company": company,
                "location": j.get("categories", {}).get("location"),
                "category": "IT Jobs",
                "salary_min": None,
                "salary_max": None,
                "url": j.get("hostedUrl"),
                "created": j.get("createdAt"),
                "source": "lever"   # ✅ REQUIRED
            })
@app.get("/")
def root():
    return {"message": "Anvalyx backend is running"}

@app.get("/jobs")
def jobs(
    keyword: str = None,
    location: str = None,
    min_salary: int = 0
):
    return get_jobs(keyword, location, min_salary)
