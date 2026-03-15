from dotenv import load_dotenv
import os
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

# --------------------------------------------------
# ENV
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --------------------------------------------------
# Internal imports
# --------------------------------------------------
from database import (
    init_db,
    save_jobs,
    save_resume,
    get_active_resume,
    SessionLocal,
    Job
)

from adzuna_client import fetch_adzuna_jobs
from usajobs_client import fetch_usajobs

from backend.ats.ats import router as ats_router

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI(title="Anvalyx Backend")
app.include_router(ats_router)

# --------------------------------------------------
# Scheduler
# --------------------------------------------------
scheduler = BackgroundScheduler()

# --------------------------------------------------
# Refresh functions
# --------------------------------------------------
def refresh_usajobs():
    print("🔄 USAJobs refresh started")
    try:
        jobs = fetch_usajobs() or []
        save_jobs(jobs)
        print(f"✅ USAJobs refreshed | fetched={len(jobs)}")
    except Exception as e:
        print(f"❌ USAJobs failed: {e}")


def refresh_adzuna():
    print("🔄 Adzuna refresh started")
    try:
        jobs = fetch_adzuna_jobs() or []
        save_jobs(jobs)
        print(f"✅ Adzuna refreshed | fetched={len(jobs)}")
    except Exception as e:
        print(f"⚠️ Adzuna skipped: {e}")


def refresh_all_sources():
    print("🚀 Full refresh cycle started")
    refresh_usajobs()
    refresh_adzuna()
    print("✅ Full refresh cycle finished")

# --------------------------------------------------
# Startup / Shutdown
# --------------------------------------------------
@app.on_event("startup")
def startup_event():
    init_db()

    # Run once immediately when the app starts
    refresh_all_sources()

    # Schedule each source separately
    scheduler.add_job(
        refresh_usajobs,
        "interval",
        hours=6,
        id="refresh_usajobs",
        replace_existing=True
    )

    scheduler.add_job(
        refresh_adzuna,
        "interval",
        hours=2,
        id="refresh_adzuna",
        replace_existing=True
    )

    scheduler.start()
    print("✅ Scheduler started")


@app.on_event("shutdown")
def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
        print("🛑 Scheduler stopped")

# --------------------------------------------------
# Health
# --------------------------------------------------
@app.get("/")
def health():
    return {"status": "Anvalyx backend running"}

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def serialize_job(j: Job):
    return {
        "id": j.id,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "apply_url": j.url,
        "source": j.source,
        "posted": j.posted_at.isoformat() if j.posted_at else None
    }

# --------------------------------------------------
# Jobs API
# --------------------------------------------------
@app.get("/jobs")
def get_jobs():
    db: Session = SessionLocal()
    try:
        jobs = (
            db.query(Job)
            .filter(Job.posted_at.isnot(None))
            .order_by(Job.posted_at.desc())
            .all()
        )
        return [serialize_job(j) for j in jobs]
    finally:
        db.close()


@app.get("/jobs/fresh")
def get_fresh_jobs():
    db: Session = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=7)

    try:
        jobs = (
            db.query(Job)
            .filter(Job.posted_at.isnot(None))
            .filter(Job.posted_at >= cutoff)
            .order_by(Job.posted_at.desc())
            .all()
        )
        return [serialize_job(j) for j in jobs]
    finally:
        db.close()


@app.get("/jobs/older")
def get_older_jobs():
    db: Session = SessionLocal()
    start = datetime.utcnow() - timedelta(days=30)
    end = datetime.utcnow() - timedelta(days=7)

    try:
        jobs = (
            db.query(Job)
            .filter(Job.posted_at.isnot(None))
            .filter(Job.posted_at < end)
            .filter(Job.posted_at >= start)
            .order_by(Job.posted_at.desc())
            .all()
        )
        return [serialize_job(j) for j in jobs]
    finally:
        db.close()

# --------------------------------------------------
# Resume API
# --------------------------------------------------
class ResumeRequest(BaseModel):
    resume_text: str


@app.post("/resume")
def upload_resume(payload: ResumeRequest):
    resume = save_resume(payload.resume_text)
    return {"message": "Resume saved", "resume_id": resume.id}


@app.get("/resume")
def fetch_resume():
    resume = get_active_resume()

    if not resume:
        return {"message": "No resume found"}

    return {
        "resume_text": resume.resume_text,
        "updated_at": resume.updated_at
    }