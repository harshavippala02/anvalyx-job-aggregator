import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# ATS Configuration
# -----------------------------
CORE_SKILLS = {
    "sql", "python", "power bi", "tableau", "excel",
    "snowflake", "aws", "azure", "etl", "data modeling",
    "analytics", "statistics", "machine learning"
}

ROLE_TITLES = {
    "data analyst",
    "business analyst",
    "bi analyst",
    "analytics engineer",
    "reporting analyst"
}

STOPWORDS = {
    "and","the","with","for","this","that","from","your","you",
    "will","have","are","our","job","role","work","years",
    "experience","skills","responsibilities","requirements"
}

# -----------------------------
# Text helpers
# -----------------------------
def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_keywords(text: str):
    words = re.findall(r"[a-zA-Z]{3,}", text)
    return {w for w in words if w not in STOPWORDS}

# -----------------------------
# ATS Components
# -----------------------------
def core_skill_score(resume: str, jd: str):
    matched = [s for s in CORE_SKILLS if s in resume and s in jd]
    score = (len(matched) / len(CORE_SKILLS)) * 100
    return score, matched

def tool_similarity_score(resume: str, jd: str):
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([resume, jd])
    similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
    return similarity * 100

def title_relevance_score(resume: str, jd: str):
    for title in ROLE_TITLES:
        if title in resume and title in jd:
            return 100
    return 0

def keyword_coverage_score(resume: str, jd: str):
    resume_kw = extract_keywords(resume)
    jd_kw = extract_keywords(jd)
    if not jd_kw:
        return 0
    return (len(resume_kw & jd_kw) / len(jd_kw)) * 100

# -----------------------------
# FINAL ATS SCORE
# -----------------------------
def calculate_ats(resume_text: str, job_text: str):
    resume = clean_text(resume_text)
    jd = clean_text(job_text)

    core_score, matched_skills = core_skill_score(resume, jd)
    tool_score = tool_similarity_score(resume, jd)
    title_score = title_relevance_score(resume, jd)
    keyword_score = keyword_coverage_score(resume, jd)

    final_score = (
        0.40 * core_score +
        0.25 * tool_score +
        0.20 * title_score +
        0.15 * keyword_score
    )

    return {
        "ats_score": round(final_score, 2),
        "breakdown": {
            "core_skills": round(core_score, 2),
            "tools_similarity": round(tool_score, 2),
            "title_relevance": round(title_score, 2),
            "keyword_coverage": round(keyword_score, 2)
        },
        "matched_core_skills": matched_skills,
        "missing_core_skills": sorted(list(CORE_SKILLS - set(matched_skills)))
    }
