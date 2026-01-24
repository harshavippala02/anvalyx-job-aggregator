import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


CORE_SKILLS = [
    "sql", "python", "power bi", "tableau", "excel",
    "snowflake", "azure", "aws", "etl", "data modeling",
    "analytics", "dashboards", "statistics", "machine learning"
]


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return text


def skill_match_score(resume: str, jd: str):
    matched = [s for s in CORE_SKILLS if s in resume and s in jd]
    score = (len(matched) / len(CORE_SKILLS)) * 100
    return score, matched


def title_match_score(resume: str, jd: str):
    titles = [
        "data analyst",
        "business analyst",
        "bi analyst",
        "analytics engineer"
    ]

    for t in titles:
        if t in resume and t in jd:
            return 100
    return 0


def semantic_similarity(resume: str, jd: str):
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([resume, jd])
    return cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100


def calculate_ats(resume: str, jd: str):
    resume = clean_text(resume)
    jd = clean_text(jd)

    skill_score, matched_skills = skill_match_score(resume, jd)
    title_score = title_match_score(resume, jd)
    semantic_score = semantic_similarity(resume, jd)

    final_score = (
        0.45 * skill_score +
        0.20 * title_score +
        0.35 * semantic_score
    )

    return {
        "ats_score": round(final_score, 2),
        "matched_skills": matched_skills,
        "missing_skills": [s for s in CORE_SKILLS if s not in matched_skills]
    }
