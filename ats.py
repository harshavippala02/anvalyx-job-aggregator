import os
import math
from typing import List
from openai import OpenAI
from pydantic import BaseModel

# --------------------------------------------------
# OpenAI Client
# --------------------------------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBED_MODEL = "text-embedding-3-small"

# --------------------------------------------------
# Request / Response Models
# --------------------------------------------------
class ATSRequest(BaseModel):
    job_description: str

class ATSResponse(BaseModel):
    score: int
    similarity: float
    summary: str


# --------------------------------------------------
# Math
# --------------------------------------------------
def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


# --------------------------------------------------
# Embedding helper
# --------------------------------------------------
def embed_text(text: str) -> List[float]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return response.data[0].embedding


# --------------------------------------------------
# AI ATS ENGINE (CORE)
# --------------------------------------------------
def calculate_ai_ats(resume_text: str, job_text: str) -> ATSResponse:
    resume_embedding = embed_text(resume_text)
    job_embedding = embed_text(job_text)

    similarity = cosine_similarity(resume_embedding, job_embedding)

    # Convert similarity → ATS-style score
    raw_score = similarity * 100

    # Normalize like real ATS systems
    if raw_score >= 85:
        score = min(95, int(raw_score))
        summary = "Excellent match – very ATS friendly"
    elif raw_score >= 70:
        score = int(raw_score)
        summary = "Strong match – minor gaps"
    elif raw_score >= 50:
        score = int(raw_score)
        summary = "Moderate match – resume could be optimized"
    else:
        score = max(25, int(raw_score))
        summary = "Low match – resume needs tailoring"

    return ATSResponse(
        score=score,
        similarity=round(similarity, 4),
        summary=summary
    )
