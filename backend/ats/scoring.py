import re
import os
from typing import Dict, List
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBED_MODEL = "text-embedding-3-small"

# ---------------- FEATURE FLAGS ----------------
ENABLE_NORMALIZATION = True
ENABLE_KEYWORD_BOOST = True
ENABLE_MISSING_SKILLS = True

# ---------------- CONFIG ----------------
MIN_SCORE = 35
MAX_SCORE = 95
KEYWORD_BOOST_MAX = 15

COMMON_SKILLS = [
    "sql", "python", "r", "power bi", "tableau", "excel",
    "snowflake", "aws", "azure", "gcp", "airflow", "dbt",
    "etl", "data analysis", "machine learning", "statistics"
]

# ---------------- HELPERS ----------------
def embed_text(text: str) -> List[float]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text[:3000]
    )
    return response.data[0].embedding


def normalize_score(raw_similarity: float) -> int:
    score = int(raw_similarity * 100)
    return max(MIN_SCORE, min(MAX_SCORE, score))


def extract_keywords(text: str) -> List[str]:
    text = text.lower()
    found = []
    for skill in COMMON_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text):
            found.append(skill)
    return list(set(found))


def keyword_boost(resume_text: str, job_text: str) -> Dict:
    resume_skills = extract_keywords(resume_text)
    job_skills = extract_keywords(job_text)

    matched = list(set(resume_skills) & set(job_skills))
    missing = list(set(job_skills) - set(resume_skills))

    boost = min(len(matched) * 3, KEYWORD_BOOST_MAX)

    return {
        "boost": boost,
        "matched": matched,
        "missing": missing
    }


def confidence_label(score: int) -> str:
    if score >= 80:
        return "High"
    elif score >= 60:
        return "Medium–High"
    elif score >= 45:
        return "Medium"
    return "Low"

# ---------------- MAIN ATS ENGINE ----------------
def calculate_ats_score(resume_text: str, job_text: str) -> Dict:

    resume_embedding = embed_text(resume_text)
    job_embedding = embed_text(job_text)

    similarity = cosine_similarity(
        [resume_embedding],
        [job_embedding]
    )[0][0]

    semantic_score = int(similarity * 100)

    base_score = (
        normalize_score(similarity)
        if ENABLE_NORMALIZATION
        else semantic_score
    )

    final_score = base_score
    breakdown = {"semantic_match": semantic_score}
    missing_skills = []
    strengths = []

    if ENABLE_KEYWORD_BOOST:
        kb = keyword_boost(resume_text, job_text)
        final_score = min(final_score + kb["boost"], MAX_SCORE)
        breakdown["keyword_boost"] = kb["boost"]

        if ENABLE_MISSING_SKILLS:
            missing_skills = kb["missing"][:5]

        if kb["boost"] > 0:
            strengths.append("Relevant technical skills detected")

    if semantic_score >= 60:
        strengths.append("Strong role and experience alignment")

    if final_score >= 80:
        interpretation = "Strong ATS match. Resume aligns well with job requirements."
    elif final_score >= 60:
        interpretation = "Good ATS match. Minor optimizations could improve ranking."
    elif final_score >= 45:
        interpretation = "Moderate ATS match. Resume lacks some key skills."
    else:
        interpretation = "Low ATS match. Resume is missing several core requirements."

    return {
        "ats_score": final_score,
        "confidence": confidence_label(final_score),
        "breakdown": breakdown,
        "missing_skills": missing_skills,
        "strengths": strengths,
        "interpretation": interpretation
    }
