import os
from dotenv import load_dotenv
from typing import List, Dict
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

from backend.ats.scoring import calculate_ats_score
from backend.ats.resume_parser import parse_resume

# --------------------------------------------------
# Environment
# --------------------------------------------------
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBED_MODEL = "text-embedding-3-small"

# --------------------------------------------------
# Request Models
# --------------------------------------------------
class ATSRequest(BaseModel):
    job_description: str

# --------------------------------------------------
# Helpers (AI Embeddings)
# --------------------------------------------------
def embed_text(text: str) -> List[float]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return response.data[0].embedding

# --------------------------------------------------
# OPTIONAL: AI-BASED ATS (SECONDARY)
# --------------------------------------------------
def calculate_ai_ats(resume_text: str, job_text: str) -> Dict:
    """
    AI-based similarity score (kept for optional comparison).
    Not the primary ATS score anymore.
    """
    resume_embedding = embed_text(resume_text)
    job_embedding = embed_text(job_text)

    similarity = cosine_similarity(
        [resume_embedding],
        [job_embedding]
    )[0][0]

    score = int(similarity * 100)

    strengths = []
    gaps = []

    if score >= 70:
        strengths.append("Strong semantic alignment with job requirements")
    elif score >= 50:
        strengths.append("Moderate semantic alignment")
        gaps.append("Some key skills or role context may be missing")
    else:
        gaps.append("Low semantic match with job description")

    return {
        "ai_score": score,
        "strengths": strengths,
        "gaps": gaps
    }

# --------------------------------------------------
# PRIMARY ATS SCORING (RULE-BASED, TRUSTED)
# --------------------------------------------------
def calculate_ats_for_job(
    resume_text: str,
    job_description: str,
    job_title: str = "",
    required_years: int = 0
) -> Dict:
    """
    Main ATS scoring function used by the app.
    """

    # 1️⃣ Parse resume
    parsed_resume = parse_resume(resume_text)

    structured_resume = {
        "skills": parsed_resume.get("skills", []),
        "titles": parsed_resume.get("titles", []),
        "years_experience": parsed_resume.get("years_experience", 0)
    }

    # 2️⃣ Extract job-side data (simple version for now)
    job_skills = parse_resume(job_description).get("skills", [])

    structured_job = {
        "skills": job_skills,
        "title": job_title,
        "required_years": required_years,
        "tools": job_skills
    }

    # 3️⃣ Rule-based ATS score (PRIMARY)
    ats_result = calculate_ats_score(
        resume=structured_resume,
        job=structured_job
    )

    # 4️⃣ Optional AI score (SECONDARY, informational)
    ai_result = calculate_ai_ats(
        resume_text=resume_text,
        job_text=job_description
    )

    # 5️⃣ Combined response
    return {
        "ats_score": ats_result["ats_score"],
        "interpretation": ats_result["interpretation"],
        "breakdown": ats_result["breakdown"],
        "missing_skills": ats_result["missing_skills"],
        "ai_similarity_score": ai_result["ai_score"]
    }
