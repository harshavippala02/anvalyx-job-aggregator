from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, save_jobs
from adzuna_client import fetch_adzuna_jobs
from usajobs_client import fetch_usajobs

app = FastAPI()

# ----------------------------
# Scheduler setup
# ----------------------------
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

# ----------------------------
# Startup event
# ----------------------------
@app.on_event("startup")
def startup_event():
    init_db()

    # Run once immediately
    refresh_jobs()

    # Start scheduler
    scheduler.start()
    print("⏱️ Scheduler started (10-minute interval)")
