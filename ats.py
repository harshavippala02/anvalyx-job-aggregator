from pydantic import BaseModel
from typing import List
import re
from collections import Counter

# --------------------------------------------------
# Request / Response Models
# --------------------------------------------------
class ATSRequest(BaseModel):
    resume_text: str
    job_text: str


class ATSResult(BaseModel):
    score: int
    matched: List[str]
    missing: List[str]
    summary: str


# --------------------------------------------------
# Helpers
# --------------------------------------------------
STOPWORDS = {
    "and","the","with","for","this","that","from","your","you","will",
    "have","are","our","job","role","work","years","experience","ability",
    "skills","responsibilities","requirements","including","etc","using"
}

def extract_keywords(text: str) -> List[str]:
    text = text.lower()
    words = re.findall(r"[a-zA-Z]{3,}", text)
    return [w for w in words if w not in STOPWORDS]


# --------------------------------------------------
# ATS Logic (Improved, weighted)
# --------------------------------------------------
def calculate_ats(resume_text: str, job_text: str) -> ATSResult:
    resume_words = extract_keywords(resume_text)
    job_words = extract_keywords(job_text)

    resume_counts = Counter(resume_words)
    job_counts = Counter(job_words)

    job_keywords = set(job_counts.keys())
    resume_keywords = set(resume_counts.keys())

    matched = sorted(job_keywords & resume_keywords)
    missing = sorted(job_keywords - resume_keywords)

    # -----------------------------
    # Weighted scoring (more realistic)
    # -----------------------------
    total_weight = 0
    matched_weight = 0

    for word, weight in job_counts.items():
        total_weight += weight
        if word in resume_counts:
            matched_weight += min(weight, resume_counts[word])

    raw_score = (matched_weight / max(total_weight, 1)) * 100

    # ATS-style normalization (closer to real systems)
    if raw_score >= 75:
        score = min(95, int(raw_score))
        summary = "Excellent match – very ATS friendly"
    elif raw_score >= 60:
        score = int(raw_score)
        summary = "Strong match – minor gaps"
    elif raw_score >= 40:
        score = int(raw_score)
        summary = "Moderate match – needs optimization"
    else:
        score = max(15, int(raw_score))
        summary = "Weak match – resume needs tailoring"

    return ATSResult(
        score=score,
        matched=matched[:40],   # limit noise
        missing=missing[:40],
        summary=summary
    )
