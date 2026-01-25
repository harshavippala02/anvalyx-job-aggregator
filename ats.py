import os
import math
from typing import List
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBED_MODEL = "text-embedding-3-small"


# -----------------------------
# Math helpers
# -----------------------------
def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


# -----------------------------
# Embedding helper
# -----------------------------
def embed_text(text: str) -> List[float]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return response.data[0].embedding


# -----------------------------
# MAIN ATS ENGINE
# -----------------------------
def calculate_ats_score(resume_text: str, job_text: str) -> dict:
    """
    Returns:
    {
        score: int (0–100),
        similarity: float,
        explanation: str
    }
    """

    resume_embedding = embed_text(resume_text)
    job_embedding = embed_text(job_text)

    similarity = cosine_similarity(resume_embedding, job_embedding)

    # Scale similarity → ATS-like score
    score = int(min(max(similarity * 100, 0), 100))

    explanation = (
        "Score is based on semantic similarity between resume and job description, "
        "similar to modern ATS systems."
    )

    return {
        "score": score,
        "similarity": round(similarity, 4),
        "explanation": explanation
    }
