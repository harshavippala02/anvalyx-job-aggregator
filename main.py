from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, save_jobs, get_all_jobs
from adzuna_client import fetch_adzuna_jobs

app = FastAPI()

# ----------------------------
# Scheduler setup
# ----------------------------
scheduler = BackgroundScheduler()

def refresh_jobs():
    print("🔄 Refreshing jobs from Adzuna...")
    jobs = fetch_adzuna_jobs()
    save_jobs(jobs)
    print(f"✅ Saved {len(jobs)} jobs")

# Run every 10 minutes
scheduler.add_job(refresh_jobs, "interval", minutes=10)

@app.on_event("startup")
def startup_event():
    init_db()

    # Run once immediately on startup
    refresh_jobs()

    # Start scheduler
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

# ----------------------------
# API routes
# ----------------------------
@app.get("/")
def health():
    return {"status": "Anvalyx backend is running"}

@app.get("/jobs")
def get_jobs():
    return get_all_jobs()
