from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, save_jobs, SessionLocal, Job
from adzuna_client import fetch_adzuna_jobs
from usajobs_client import fetch_usajobs
from sqlalchemy.orm import Session

app = FastAPI()

# -----------------------------
# Scheduler setup
# -----------------------------
scheduler = BackgroundScheduler()

def refresh_jobs():
    print("🔄 Refreshing jobs from Adzuna...")
    adzuna_jobs = fetch_adzuna_jobs()
    save_jobs(adzuna_jobs)
    print(f"✅ Saved {len(adzuna_jobs)} Adzuna jobs")

    print("🔄 Refreshing jobs from USAJobs...")
    usajobs = fetch_usajobs()
    save_jobs(usajobs)
    print(f"✅ Saved {len(usajobs)} USAJobs jobs")


# Run every 10 minutes
scheduler.add_job(refresh_jobs, "interval", minutes=10)


# -----------------------------
# Startup event
# -----------------------------
@app.on_event("startup")
def startup_event():
    init_db()
    refresh_jobs()   # run once on startup
    scheduler.start()
    print("⏱️ Scheduler started (10-minute interval)")


# -----------------------------
# API Routes
# -----------------------------
@app.get("/")
def health_check():
    return {"status": "Anvalyx backend running"}


@app.get("/jobs")
def get_jobs():
    db: Session = SessionLocal()
    jobs = db.query(Job).order_by(Job.posted_at.desc()).all()

    return [
        {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "posted_at": job.posted_at
        }
        for job in jobs
    ]
