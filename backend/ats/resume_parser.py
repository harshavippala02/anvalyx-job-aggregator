import re
from datetime import datetime

# --------------------------------------------------
# ATS Skill Dictionary (v1)
# --------------------------------------------------

SKILL_KEYWORDS = {
    "sql": ["sql", "tsql", "pl/sql"],
    "python": ["python", "pandas", "numpy"],
    "power bi": ["power bi", "dax", "power query"],
    "tableau": ["tableau"],
    "excel": ["excel", "vlookup", "pivot"],
    "snowflake": ["snowflake"],
    "dbt": ["dbt"],
    "airflow": ["airflow"],
    "aws": ["aws", "s3", "lambda"],
    "azure": ["azure", "adls", "synapse"],
    "gcp": ["gcp", "bigquery"],
}

DOMAIN_KEYWORDS = {
    "finance": ["finance", "bank", "banking", "trading", "investment"],
    "healthcare": ["healthcare", "clinical", "patient"],
    "retail": ["retail", "ecommerce"],
    "manufacturing": ["manufacturing", "supply chain"],
    "insurance": ["insurance", "claims", "underwriting"],
}

# --------------------------------------------------
# Skill Extraction
# --------------------------------------------------

def extract_skills(resume_text: str) -> list[str]:
    if not resume_text:
        return []

    resume_lower = resume_text.lower()
    found_skills = set()

    for skill, aliases in SKILL_KEYWORDS.items():
        for alias in aliases:
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, resume_lower):
                found_skills.add(skill)
                break

    return sorted(found_skills)

# --------------------------------------------------
# Years of Experience Extraction
# --------------------------------------------------

def extract_years_of_experience(resume_text: str) -> int:
    if not resume_text:
        return 0

    text = resume_text.lower()
    years_found = []

    date_ranges = re.findall(
        r"(20\d{2})\s*(?:-|–|to)\s*(20\d{2}|present)",
        text
    )

    current_year = datetime.utcnow().year

    for start, end in date_ranges:
        start_year = int(start)
        end_year = current_year if end == "present" else int(end)

        if end_year >= start_year:
            years_found.append(end_year - start_year)

    return max(years_found) if years_found else 0

# --------------------------------------------------
# Domain Extraction
# --------------------------------------------------

def extract_domains(resume_text: str) -> list[str]:
    if not resume_text:
        return []

    text = resume_text.lower()
    domains = []

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(k in text for k in keywords):
            domains.append(domain)

    return domains

# --------------------------------------------------
# Master Resume Parser
# --------------------------------------------------

def parse_resume(resume_text: str) -> dict:
    """
    ATS-style resume parsing.
    This is the single source of truth for downstream ATS logic.
    """
    return {
        "skills": extract_skills(resume_text),
        "years_experience": extract_years_of_experience(resume_text),
        "domains": extract_domains(resume_text),
    }
