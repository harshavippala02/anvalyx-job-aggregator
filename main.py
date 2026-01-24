from fastapi import FastAPI
from database import init_db, save_jobs, get_all_jobs
from adzuna_client import fetch_adzuna_jobs

app = FastAPI()


@app.on_event("startup")
def startup():
    init_db()

    jobs = fetch_adzuna_jobs()

    # 🔒 Normalize jobs (CRITICAL FIX)
    normalized = []
    for j in jobs:
        normalized.append({
            "external_id": j.get("external_id") or j.get("id"),
            "title": j["title"],
            "company": j["company"],
            "location": j["location"],
            "url": j["url"],
            "source": j.get("source", "adzuna"),
            "posted_at": j.get("posted_at"),
        })

    save_jobs(normalized)


@app.get("/")
def root():
    return {"status": "Anvalyx backend is running"}


@app.get("/jobs")
def list_jobs():
    return get_all_jobs()
