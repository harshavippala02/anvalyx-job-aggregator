from fastapi import FastAPI, HTTPException
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
from ats import calculate_ai_ats, ATSRequest

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI()

# --------------------------------------------------
# Scheduler
# --------------------------------------------------
scheduler = BackgroundScheduler()

def refresh_jobs():
    adzuna_jobs = fetch_adzuna_jobs()
    save_jobs(adzuna_jobs)

    usajobs = fetch_usajobs()
    save_jobs(usajobs)

scheduler.add_job(refresh_jobs, "interval", minutes=10)

# --------------------------------------------------
# Startup
# --------------------------------------------------
@app.on_event("startup")
def startup_event():
    init_db()
    refresh_jobs()
    scheduler.start()

# --------------------------------------------------
# Health
# --------------------------------------------------
@app.get("/")
def health():
    return {"status": "Anvalyx backend running"}

# --------------------------------------------------
# Jobs API
# --------------------------------------------------
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
            "posted_at": j.posted_at.isoformat()
        }
        for j in jobs
    ]

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
# AI ATS APIs (ONE SOURCE OF TRUTH)
# --------------------------------------------------
@app.post("/ats/score")
def ats_manual(payload: ATSRequest):
    resume = get_active_resume()
    if not resume:
        raise HTTPException(status_code=400, detail="No resume stored")

    result = calculate_ai_ats(
        resume.resume_text,
        payload.job_description
    )

    return result


@app.get("/ats/score/job/{job_id}")
def ats_for_job(job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    db.close()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume = get_active_resume()
    if not resume:
        raise HTTPException(status_code=400, detail="No resume stored")

    job_text = f"""
    {job.title}
    {job.company}
    {job.location}
    """

    result = calculate_ai_ats(
        resume.resume_text,
        job_text
    )

    return result
