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
    clear_all_jobs,
    get_job_counts,
    SessionLocal,
    Job,
    ACTIVE_SOURCES
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
        result = save_jobs(jobs)
        print(
            f"✅ USAJobs refreshed | fetched={len(jobs)} "
            f"| inserted={result['inserted']} | skipped={result['skipped']}"
        )
    except Exception as e:
        print(f"❌ USAJobs failed: {e}")


def refresh_adzuna():
    print("🔄 Adzuna refresh started")
    try:
        jobs = fetch_adzuna_jobs() or []
        result = save_jobs(jobs)
        print(
            f"✅ Adzuna refreshed | fetched={len(jobs)} "
            f"| inserted={result['inserted']} | skipped={result['skipped']}"
        )
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
    return {
        "status": "Anvalyx backend running",
        "active_sources": ACTIVE_SOURCES
    }


@app.head("/")
def health_head():
    return


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def serialize_job(j: Job):
    return {
        "id": j.id,
        "external_id": j.external_id,
        "title": j.title,
        "company": j.company,
        "location": j.location,
        "apply_url": j.url,
        "source": j.source,
        "description": j.description,
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
            .filter(Job.source.in_(ACTIVE_SOURCES))
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
            .filter(Job.source.in_(ACTIVE_SOURCES))
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
            .filter(Job.source.in_(ACTIVE_SOURCES))
            .order_by(Job.posted_at.desc())
            .all()
        )
        return [serialize_job(j) for j in jobs]
    finally:
        db.close()


@app.get("/jobs/debug-counts")
def debug_counts():
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)

        fresh_jobs = (
            db.query(Job)
            .filter(Job.posted_at.isnot(None))
            .filter(Job.posted_at >= cutoff)
            .filter(Job.source.in_(ACTIVE_SOURCES))
            .count()
        )

        counts = get_job_counts()
        counts["fresh_jobs_active_sources"] = fresh_jobs
        counts["active_sources"] = ACTIVE_SOURCES
        return counts
    finally:
        db.close()


# --------------------------------------------------
# Admin API
# --------------------------------------------------
@app.delete("/admin/clear-jobs")
def clear_jobs():
    deleted = clear_all_jobs()
    return {
        "message": "All jobs cleared successfully",
        "deleted_jobs": deleted
    }


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
# --------------------------------------------------
# TEMP ADMIN: Reset jobs table (for schema updates)
# --------------------------------------------------
@app.get("/admin/reset-jobs-table")
def reset_jobs_table():
    from database import engine, Job

    try:
        Job.__table__.drop(bind=engine, checkfirst=True)
        Job.__table__.create(bind=engine, checkfirst=True)
        return {"message": "jobs table reset successfully"}
    except Exception as e:
        return {"error": str(e)}