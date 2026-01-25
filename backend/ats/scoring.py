from typing import List, Dict
import re
from difflib import SequenceMatcher


# -------------------------------
# Helpers
# -------------------------------

def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


# -------------------------------
# Core ATS Scoring
# -------------------------------

def calculate_ats_score(
    resume: Dict,
    job: Dict
) -> Dict:
    """
    resume: {
        "skills": [],
        "titles": [],
        "years_experience": int
    }

    job: {
        "skills": [],
        "title": str,
        "required_years": int,
        "tools": []
    }
    """

    score = 0
    breakdown = {}

    # -------------------------------
    # 1. Skill Match (40)
    # -------------------------------
    resume_skills = set(map(normalize, resume.get("skills", [])))
    job_skills = set(map(normalize, job.get("skills", [])))

    matched_skills = resume_skills.intersection(job_skills)
    missing_skills = sorted(job_skills - resume_skills)

    skill_score = int((len(matched_skills) / max(len(job_skills), 1)) * 40)
    breakdown["skill_match"] = skill_score
    score += skill_score

    # -------------------------------
    # 2. Role Alignment (20)
    # -------------------------------
    title_scores = [
        similarity(resume_title, job.get("title", ""))
        for resume_title in resume.get("titles", [])
    ]

    best_title_match = max(title_scores, default=0)
    role_score = int(best_title_match * 20)

    breakdown["role_alignment"] = role_score
    score += role_score

    # -------------------------------
    # 3. Experience Relevance (15)
    # -------------------------------
    resume_years = resume.get("years_experience", 0)
    required_years = job.get("required_years", resume_years)

    experience_score = int(
        min(resume_years / max(required_years, 1), 1.0) * 15
    )

    breakdown["experience_relevance"] = experience_score
    score += experience_score

    # -------------------------------
    # 4. Tools & Tech Stack (15)
    # -------------------------------
    resume_tools = set(map(normalize, resume.get("skills", [])))
    job_tools = set(map(normalize, job.get("tools", [])))

    matched_tools = resume_tools.intersection(job_tools)

    tools_score = int((len(matched_tools) / max(len(job_tools), 1)) * 15)
    breakdown["tools_tech_match"] = tools_score
    score += tools_score

    # -------------------------------
    # 5. Resume Quality (10)
    # -------------------------------
    quality_score = 6  # baseline
    if resume_years >= 3:
        quality_score += 2
    if len(resume.get("skills", [])) >= 8:
        quality_score += 2

    quality_score = min(quality_score, 10)
    breakdown["resume_quality"] = quality_score
    score += quality_score

    # -------------------------------
    # Final Output
    # -------------------------------
    return {
        "ats_score": min(score, 100),
        "breakdown": breakdown,
        "missing_skills": list(missing_skills),
        "interpretation": interpret_score(score)
    }


# -------------------------------
# Score Meaning
# -------------------------------

def interpret_score(score: int) -> str:
    if score >= 85:
        return "Very strong – recruiter-safe"
    elif score >= 70:
        return "Good – apply with minor tweaks"
    elif score >= 55:
        return "Risky – optimize resume"
    else:
        return "Likely auto-reject"
