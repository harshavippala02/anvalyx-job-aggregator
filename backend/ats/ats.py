import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.database import get_db
from backend.models import Job, Resume
from backend.ats.scoring import calculate_ats_score

# ---------------- ENV ----------------
load_dotenv()

router = APIRouter(prefix="/ats", tags=["ATS"])

# ---------------- REQUEST MODELS ----------------
class ATSRequest(BaseModel):
    job_description: str

# ---------------- HELPERS ----------------
def get_latest_resume_text(db) -> Optional[str]:
    resume = (
        db.query(Resume)
        .order_by(Resume.created_at.desc())
        .first()
    )
    return resume.text if resume else None

# ---------------- ROUTES ----------------

@router.post("/score")
def score_manual_job(payload: ATSRequest):
    """
    Manual ATS check (resume vs pasted job description)
    """
    db = next(get_db())
    resume_text = get_latest_resume_text(db)

    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="No resume found. Please upload a resume first."
        )

    result = calculate_ats_score(
        resume_text=resume_text,
        job_text=payload.job_description
    )

    return {
        "score": result["ats_score"],
        "confidence": result["confidence"],
        "strengths": result["strengths"],
        "missing_skills": result["missing_skills"],
        "interpretation": result["interpretation"],
        "breakdown": result["breakdown"]
    }


@router.get("/score/job/{job_id}")
def score_job(job_id: int):
    """
    ATS check for a job already stored in DB
    """
    db = next(get_db())

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume_text = get_latest_resume_text(db)
    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="No resume found. Please upload a resume first."
        )

    result = calculate_ats_score(
        resume_text=resume_text,
        job_text=job.description
    )

    return {
        "score": result["ats_score"],
        "confidence": result["confidence"],
        "strengths": result["strengths"],
        "missing_skills": result["missing_skills"],
        "interpretation": result["interpretation"],
        "breakdown": result["breakdown"]
    }
