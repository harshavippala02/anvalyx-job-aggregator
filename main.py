from dotenv import load_dotenv
import os
import hashlib
from fastapi import FastAPI, Query, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta
from linkedin_client import pull_linkedin_jobs
from jsearch_client import fetch_jsearch_jobs

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
    update_job_status,
    should_hide_due_to_experience,
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
# LinkedIn helpers
# --------------------------------------------------
def parse_linkedin_posted_text(posted_text: str):
    if not posted_text:
        return None

    text_value = str(posted_text).strip().lower()
    now = datetime.utcnow()

    if "just now" in text_value or "today" in text_value:
        return now

    if "hour" in text_value:
        return now

    if "day" in text_value:
        try:
            num = int(text_value.split()[0])
            return now - timedelta(days=num)
        except Exception:
            return now

    if "week" in text_value:
        try:
            num = int(text_value.split()[0])
            return now - timedelta(days=(num * 7))
        except Exception:
            return None

    return None


def make_linkedin_external_id(url: str):
    return "linkedin_" + hashlib.md5(url.encode("utf-8")).hexdigest()


def normalize_linkedin_jobs(raw_jobs):
    normalized = []

    for job in raw_jobs:
        url = (job.get("url") or "").strip()
        if not url:
            continue

        posted_at = parse_linkedin_posted_text(job.get("posted"))

        normalized.append({
            "external_id": make_linkedin_external_id(url),
            "title": (job.get("title") or "").strip(),
            "company": (job.get("company") or "").strip(),
            "location": (job.get("location") or "").strip() or "Unknown",
            "url": url,
            "source": "linkedin",
            "description": job.get("description") or "",
            "posted_at": posted_at,
        })

    return normalized


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


def refresh_linkedin_source():
    print("🔄 LinkedIn refresh started")
    try:
        raw_jobs = pull_linkedin_jobs() or []
        jobs = normalize_linkedin_jobs(raw_jobs)
        result = save_jobs(jobs)
        print(
            f"✅ LinkedIn refreshed | fetched={len(raw_jobs)} "
            f"| inserted={result['inserted']} | updated={result['updated']} | skipped={result['skipped']}"
        )
    except Exception as e:
        print(f"⚠️ LinkedIn skipped: {e}")

def refresh_jsearch():
    print("🔄 JSearch refresh started")
    try:
        jobs = fetch_jsearch_jobs() or []
        result = save_jobs(jobs)
        print(
            f"✅ JSearch refreshed | fetched={len(jobs)} "
            f"| inserted={result['inserted']} | updated={result['updated']} | skipped={result['skipped']}"
        )
    except Exception as e:
        print(f"⚠️ JSearch skipped: {e}")


def refresh_all_sources():
    print("🚀 Full refresh cycle started")
    refresh_usajobs()
    refresh_adzuna()
    refresh_linkedin_source()
    refresh_jsearch()
    print("✅ Full refresh cycle finished")


# --------------------------------------------------
# Startup / Shutdown
# --------------------------------------------------
@app.on_event("startup")
def startup_event():
    init_db()
    ensure_jobs_schema()

    scheduler.add_job(
        refresh_linkedin_source,
        "interval",
        hours=4,
        id="refresh_linkedin",
        replace_existing=True
    )

    scheduler.add_job(
        refresh_jsearch,
        "interval",
        hours=6,
        id="refresh_jsearch",
        replace_existing=True
    )

    if not scheduler.running:
        scheduler.start()

    print("✅ Scheduler started", flush=True)

    # one-time boot refresh for testing
    try:
        print("🚀 Running one-time boot refresh: JSearch", flush=True)
        refresh_jsearch()
        print("✅ One-time boot refresh finished", flush=True)
    except Exception as e:
        print(f"❌ One-time boot refresh failed: {e}", flush=True)


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
# LinkedIn endpoints
# --------------------------------------------------
@app.get("/pull-linkedin")
def pull_linkedin():
    jobs = pull_linkedin_jobs()
    return {
        "count": len(jobs),
        "jobs": jobs[:20]
    }


@app.post("/refresh-linkedin")
def refresh_linkedin():
    raw_jobs = pull_linkedin_jobs() or []
    jobs = normalize_linkedin_jobs(raw_jobs)
    result = save_jobs(jobs)

    return {
        "status": "ok",
        "fetched": len(raw_jobs),
        "inserted": result["inserted"],
        "updated": result["updated"],
        "skipped": result["skipped"],
    }

@app.post("/refresh-jsearch")
def refresh_jsearch_endpoint():
    jobs = fetch_jsearch_jobs() or []
    result = save_jobs(jobs)

    return {
        "status": "ok",
        "fetched": len(jobs),
        "inserted": result["inserted"],
        "updated": result["updated"],
        "skipped": result["skipped"],
    }

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
        "status": j.status,
        "posted": j.posted_at.isoformat() if j.posted_at else None,
        "min_experience_years": j.min_experience_years,
        "max_experience_years": j.max_experience_years,
        "experience_level": j.experience_level,
        "experience_display": j.experience_display or "Unknown",
        "work_mode": j.work_mode or "Unknown",
        "job_type": j.job_type or "Unknown",
        "auto_skipped_reason": j.auto_skipped_reason,
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


def apply_default_experience_visibility(query, status: str | None):
    # Hide 6+ jobs from main Jobs view only.
    # Saved/Applied/Skipped views are allowed to show whatever was explicitly saved/applied/skipped.
    if status is None or status == "new":
        query = query.filter(
            or_(
                Job.min_experience_years.is_(None),
                Job.min_experience_years < 6
            )
        ).filter(
            or_(
                Job.experience_display.is_(None),
                Job.experience_display != "6+"
            )
        ).filter(
            or_(
                Job.auto_skipped_reason.is_(None),
                Job.auto_skipped_reason != "experience_6_plus"
            )
        )

    return query


@app.get("/jobs/summary")
def jobs_summary(search: str | None = None):
    db: Session = SessionLocal()
    try:
        base_query = db.query(Job).filter(Job.source.in_(ACTIVE_SOURCES))

        if search:
            term = f"%{search.strip()}%"
            base_query = base_query.filter(
                or_(
                    Job.title.ilike(term),
                    Job.company.ilike(term),
                    Job.location.ilike(term),
                    Job.description.ilike(term)
                )
            )

        jobs_base = apply_default_experience_visibility(base_query, "new")

        def count_with_days_and_status(days_value=None, status_value=None):
            q = base_query

            if status_value:
                q = q.filter(Job.status == status_value)
            else:
                q = q.filter(Job.status == "new")
                q = apply_default_experience_visibility(q, "new")

            if days_value is not None:
                q = apply_days_bucket_filter(q, days_value)

            return q.count()

        summary = {
            "status_counts": {
                "jobs": jobs_base.filter(Job.status == "new").count(),
                "saved": base_query.filter(Job.status == "saved").count(),
                "applied": base_query.filter(Job.status == "applied").count(),
                "skipped": base_query.filter(Job.status == "skipped").count(),
            },
            "day_counts": {
                "1": count_with_days_and_status(1, None),
                "3": count_with_days_and_status(3, None),
                "5": count_with_days_and_status(5, None),
                "7": count_with_days_and_status(7, None),
                "10": count_with_days_and_status(10, None),
                "30": count_with_days_and_status(30, None),
            }
        }

        return summary
    finally:
        db.close()


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
    status: str | None = None,
    fresh_only: bool = False,
    days: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    db: Session = SessionLocal()
    try:
        query = db.query(Job).filter(Job.source.in_(ACTIVE_SOURCES))

        if not status:
            query = query.filter(Job.status == "new")

        if status:
            query = query.filter(Job.status == status)

        query = apply_default_experience_visibility(query, status)

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
            .filter(Job.status == "new")
            .filter(
                or_(
                    Job.min_experience_years.is_(None),
                    Job.min_experience_years < 6
                )
            )
            .filter(
                or_(
                    Job.experience_display.is_(None),
                    Job.experience_display != "6+"
                )
            )
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
            .filter(Job.status == "new")
            .filter(
                or_(
                    Job.min_experience_years.is_(None),
                    Job.min_experience_years < 6
                )
            )
            .filter(
                or_(
                    Job.experience_display.is_(None),
                    Job.experience_display != "6+"
                )
            )
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


@app.post("/jobs/{job_id}/status")
def set_job_status(job_id: int, status: str = Query(...)):
    allowed = {"new", "saved", "applied", "skipped"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")

    job = update_job_status(job_id, status)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "message": "Job status updated",
        "job_id": job_id,
        "status": status
    }


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