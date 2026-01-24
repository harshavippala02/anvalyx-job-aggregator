from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from sqlalchemy.orm import Session

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

from ats_engine import calculate_ats

app = FastAPI()

# -----------------------------
# Scheduler
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

scheduler.add_job(refresh_jobs, "interval", minutes=10)

# -----------------------------
# Startup
# -----------------------------
@app.on_event("startup")
def startup_event():
    init_db()
    refresh_jobs()
    scheduler.start()
    print("⏱️ Scheduler started (10-minute interval)")

# -----------------------------
# Health
# -----------------------------
@app.get("/")
def health():
    return {"status": "Anvalyx backend running"}

# -----------------------------
# Jobs API
# -----------------------------
@app.get("/jobs")
def get_jobs():
    db: Session = SessionLocal()
    jobs = db.query(Job).order_by(Job.posted_at.desc()).all()
    db.close()

    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "url": j.url,
            "source": j.source,
            "posted_at": j.posted_at
        }
        for j in jobs
    ]

# -----------------------------
# Resume API
# -----------------------------
class ResumeRequest(BaseModel):
    resume_text: str

@app.post("/resume")
def upload_resume(payload: ResumeRequest):
    resume = save_resume(payload.resume_text)
    return {
        "message": "Resume saved successfully",
        "resume_id": resume.id
    }

@app.get("/resume")
def fetch_resume():
    resume = get_active_resume()
    if not resume:
        return {"message": "No resume found"}

    return {
        "resume_text": resume.resume_text,
        "updated_at": resume.updated_at
    }

# -----------------------------
# ATS APIs
# -----------------------------
class ATSRequest(BaseModel):
    job_description: str

@app.post("/ats/score")
def ats_score_manual(payload: ATSRequest):
    """
    ATS score for pasted job descriptions
    (manual ATS checker tab)
    """
    resume = get_active_resume()
    if not resume:
        return {"error": "No resume found. Upload resume first."}

    return calculate_ats(
        resume.resume_text,
        payload.job_description
    )

@app.get("/ats/score/job/{job_id}")
def ats_score_for_job(job_id: int):
    """
    ATS score for a job inside Anvalyx
    (per-job ATS)
    """
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    db.close()

    if not job:
        return {"error": "Job not found"}

    resume = get_active_resume()
    if not resume:
        return {"error": "No resume found. Upload resume first."}

    # Build job text (can be expanded later)
    job_text = f"""
    {job.title}
    {job.company}
    {job.location}
    {job.source}
    """

    return calculate_ats(
        resume.resume_text,
        job_text
    )
