import os
from typing import List
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

# --------------------------------------------------
# OpenAI Client
# --------------------------------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBED_MODEL = "text-embedding-3-small"

# --------------------------------------------------
# Request Model
# --------------------------------------------------
class ATSRequest(BaseModel):
    job_description: str

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def embed_text(text: str) -> List[float]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return response.data[0].embedding

# --------------------------------------------------
# AI ATS SCORING (SINGLE SOURCE OF TRUTH)
# --------------------------------------------------
def calculate_ai_ats(resume_text: str, job_text: str):
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
        strengths.append("Strong alignment with job requirements")
    elif score >= 50:
        strengths.append("Moderate alignment with job requirements")
        gaps.append("Some key skills or keywords may be missing")
    else:
        gaps.append("Low keyword and skill match with the job description")

    explanation = (
        "This ATS score is calculated using AI embeddings that compare your resume "
        "against the job description based on skills, role context, and terminology. "
        "Higher scores indicate closer alignment with how modern ATS systems screen resumes."
    )

    return {
        "score": score,
        "strengths": strengths,
        "gaps": gaps,
        "explanation": explanation
    }
