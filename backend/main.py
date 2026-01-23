import os
import requests
from fastapi import FastAPI
from dotenv import load_dotenv
from backend.database import init_db, save_jobs, get_all_jobs

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
    raise RuntimeError("Adzuna credentials missing")

app = FastAPI(title="Anvalyx API")


def fetch_adzuna_jobs():
    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": 50,
        "what": "data analyst",
        "where": "United States",
        "content-type": "application/json",
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()
    jobs = []

    for j in data.get("results", []):
        jobs.append({
            "title": j.get("title"),
            "company": j.get("company", {}).get("display_name"),
            "location": j.get("location", {}).get("display_name"),
            "url": j.get("redirect_url"),
            "source": "adzuna",
        })

    return jobs


@app.on_event("startup")
def startup():
    init_db()
    jobs = fetch_adzuna_jobs()
    save_jobs(jobs)


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/jobs")
def jobs():
    return get_all_jobs()
