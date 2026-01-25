import re
from typing import Dict, List
from sklearn.metrics.pairwise import cosine_similarity

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
def normalize_score(raw_score: float) -> int:
    """
    Converts raw cosine similarity into realistic ATS score
    """
    score = int(raw_score * 100)
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
def calculate_ats_score(
    resume_embedding: List[float],
    job_embedding: List[float],
    resume_text: str,
    job_text: str
) -> Dict:

    # 1️⃣ Semantic similarity
    similarity = cosine_similarity(
        [resume_embedding],
        [job_embedding]
    )[0][0]

    semantic_score = int(similarity * 100)

    # 2️⃣ Normalize
    base_score = (
        normalize_score(similarity)
        if ENABLE_NORMALIZATION
        else semantic_score
    )

    breakdown = {
        "semantic_match": semantic_score
    }

    final_score = base_score
    missing_skills = []

    # 3️⃣ Keyword boost
    if ENABLE_KEYWORD_BOOST:
        kb = keyword_boost(resume_text, job_text)
        final_score += kb["boost"]
        final_score = min(final_score, MAX_SCORE)

        breakdown["keyword_boost"] = kb["boost"]

        if ENABLE_MISSING_SKILLS:
            missing_skills = kb["missing"][:5]

    # 4️⃣ Interpretation
    if final_score >= 80:
        interpretation = "Strong ATS match. Resume aligns well with job requirements."
    elif final_score >= 60:
        interpretation = "Good ATS match. Minor optimizations could improve ranking."
    elif final_score >= 45:
        interpretation = "Moderate ATS match. Resume lacks some key skills."
    else:
        interpretation = "Low ATS match. Resume is missing several core requirements."

    strengths = []
    if semantic_score >= 60:
        strengths.append("Strong role and experience alignment")
    if ENABLE_KEYWORD_BOOST and breakdown.get("keyword_boost", 0) > 0:
        strengths.append("Relevant technical skills detected")

    return {
        "ats_score": final_score,
        "confidence": confidence_label(final_score),
        "breakdown": breakdown,
        "missing_skills": missing_skills,
        "strengths": strengths,
        "interpretation": interpretation
    }
