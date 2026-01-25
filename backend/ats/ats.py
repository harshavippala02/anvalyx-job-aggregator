from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import get_db, Job, UserResume
from backend.ats.scoring import calculate_ats_score

load_dotenv()

router = APIRouter(prefix="/ats", tags=["ATS"])

# ---------------- REQUEST MODEL ----------------
class ATSRequest(BaseModel):
    job_description: str

# ---------------- HELPERS ----------------
def get_latest_resume_text(db: Session) -> Optional[str]:
    resume = (
        db.query(UserResume)
        .filter(UserResume.is_active == True)
        .order_by(UserResume.created_at.desc())
        .first()
    )
    return resume.resume_text if resume else None

# ---------------- ROUTES ----------------

@router.post("/score")
def score_manual_job(payload: ATSRequest):
    db = next(get_db())
    try:
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
    finally:
        db.close()


@router.get("/score/job/{job_id}")
def score_job(job_id: int):
    db = next(get_db())
    try:
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
    finally:
        db.close()
