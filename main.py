from dotenv import load_dotenv
import os
from fastapi import FastAPI, Query
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
    ACTIVE_SOURCES,
    ensure_jobs_schema,
    normalize_source_value,
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
            f"| inserted={result['inserted']} | updated={result['updated']} | skipped={result['skipped']}"
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
            f"| inserted={result['inserted']} | updated={result['updated']} | skipped={result['skipped']}"
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
    ensure_jobs_schema()
    refresh_all_sources()

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

    if not scheduler.running:
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


def apply_days_bucket_filter(query, days: int):
    now = datetime.utcnow()

    if days == 1:
        cutoff = now - timedelta(days=1)
        query = query.filter(Job.posted_at.isnot(None), Job.posted_at >= cutoff)

    elif days == 3:
        upper = now - timedelta(days=1)
        lower = now - timedelta(days=3)
        query = query.filter(
            Job.posted_at.isnot(None),
            Job.posted_at < upper,
            Job.posted_at >= lower
        )

    elif days == 5:
        upper = now - timedelta(days=3)
        lower = now - timedelta(days=5)
        query = query.filter(
            Job.posted_at.isnot(None),
            Job.posted_at < upper,
            Job.posted_at >= lower
        )

    elif days == 7:
        upper = now - timedelta(days=5)
        lower = now - timedelta(days=7)
        query = query.filter(
            Job.posted_at.isnot(None),
            Job.posted_at < upper,
            Job.posted_at >= lower
        )

    elif days == 10:
        upper = now - timedelta(days=7)
        lower = now - timedelta(days=10)
        query = query.filter(
            Job.posted_at.isnot(None),
            Job.posted_at < upper,
            Job.posted_at >= lower
        )

    elif days == 30:
        upper = now - timedelta(days=10)
        lower = now - timedelta(days=30)
        query = query.filter(
            Job.posted_at.isnot(None),
            Job.posted_at < upper,
            Job.posted_at >= lower
        )

    else:
        cutoff = now - timedelta(days=days)
        query = query.filter(Job.posted_at.isnot(None), Job.posted_at >= cutoff)

    return query


# --------------------------------------------------
# Jobs API
# --------------------------------------------------
@app.get("/jobs")
def get_jobs(
    search: str | None = None,
    source: str | None = None,
    location: str | None = None,
    company: str | None = None,
    title: str | None = None,
    fresh_only: bool = False,
    days: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    db: Session = SessionLocal()
    try:
        query = db.query(Job).filter(Job.source.in_(ACTIVE_SOURCES))

        if fresh_only:
            cutoff = datetime.utcnow() - timedelta(days=7)
            query = query.filter(Job.posted_at.isnot(None), Job.posted_at >= cutoff)

        if days is not None:
            query = apply_days_bucket_filter(query, days)

        if source:
            normalized_source = normalize_source_value(source)
            query = query.filter(Job.source == normalized_source)

        if location:
            query = query.filter(Job.location.ilike(f"%{location.strip()}%"))

        if company:
            query = query.filter(Job.company.ilike(f"%{company.strip()}%"))

        if title:
            query = query.filter(Job.title.ilike(f"%{title.strip()}%"))

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Job.title.ilike(term),
                    Job.company.ilike(term),
                    Job.location.ilike(term),
                    Job.description.ilike(term)
                )
            )

        jobs = (
            query
            .order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [serialize_job(j) for j in jobs]
    finally:
        db.close()


@app.get("/jobs/fresh")
def get_fresh_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    db: Session = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=7)

    try:
        jobs = (
            db.query(Job)
            .filter(Job.posted_at.isnot(None))
            .filter(Job.posted_at >= cutoff)
            .filter(Job.source.in_(ACTIVE_SOURCES))
            .order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [serialize_job(j) for j in jobs]
    finally:
        db.close()


@app.get("/jobs/older")
def get_older_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
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
            .order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [serialize_job(j) for j in jobs]
    finally:
        db.close()


@app.get("/jobs/filters")
def get_job_filters():
    db: Session = SessionLocal()
    try:
        sources = [
            row[0] for row in
            db.query(Job.source)
            .filter(Job.source.in_(ACTIVE_SOURCES))
            .distinct()
            .order_by(Job.source.asc())
            .all()
            if row[0]
        ]

        locations = [
            row[0] for row in
            db.query(Job.location)
            .filter(Job.location.isnot(None))
            .filter(Job.source.in_(ACTIVE_SOURCES))
            .distinct()
            .order_by(Job.location.asc())
            .limit(200)
            .all()
            if row[0]
        ]

        companies = [
            row[0] for row in
            db.query(Job.company)
            .filter(Job.company.isnot(None))
            .filter(Job.source.in_(ACTIVE_SOURCES))
            .distinct()
            .order_by(Job.company.asc())
            .limit(200)
            .all()
            if row[0]
        ]

        return {
            "sources": sources,
            "locations": locations,
            "companies": companies
        }
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

        missing_descriptions = (
            db.query(Job)
            .filter(
                or_(
                    Job.description.is_(None),
                    Job.description == ""
                )
            )
            .count()
        )

        with_descriptions = (
            db.query(Job)
            .filter(Job.description.isnot(None))
            .filter(Job.description != "")
            .count()
        )

        counts = get_job_counts()
        counts["fresh_jobs_active_sources"] = fresh_jobs
        counts["active_sources"] = ACTIVE_SOURCES
        counts["jobs_with_description"] = with_descriptions
        counts["jobs_missing_description"] = missing_descriptions
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
# TEMP ADMIN: Reset jobs table
# --------------------------------------------------
@app.get("/admin/reset-jobs-table")
def reset_jobs_table():
    from database import engine, Job

    try:
        Job.__table__.drop(bind=engine, checkfirst=True)
        Job.__table__.create(bind=engine, checkfirst=True)
        ensure_jobs_schema()
        return {"message": "jobs table reset successfully"}
    except Exception as e:
        return {"error": str(e)}