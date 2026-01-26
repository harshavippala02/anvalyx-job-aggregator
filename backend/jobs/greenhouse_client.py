import requests
from datetime import datetime
from typing import List, Dict

# -----------------------------
# CONFIG
# -----------------------------

GREENHOUSE_COMPANIES = [
    "stripe",
    "snowflakecomputing",
    "databricks",
    "coinbase",
    "airbnb",
]

GREENHOUSE_API_TEMPLATE = (
    "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
)

# Data / Analytics keywords
DATA_KEYWORDS = [
    "data",
    "analyst",
    "analytics",
    "business intelligence",
    "bi",
    "machine learning",
    "ml",
    "ai",
    "insights",
]

HEADERS = {
    "User-Agent": "Anvalyx-Job-Aggregator"
}

# -----------------------------
# HELPERS
# -----------------------------

def is_data_role(title: str) -> bool:
    title = title.lower()
    return any(keyword in title for keyword in DATA_KEYWORDS)


def normalize_job(job: Dict, company: str) -> Dict:
    """
    Convert Greenhouse job JSON into your internal Job format
    """
    return {
        "external_id": f"greenhouse-{company}-{job.get('id')}",
        "title": job.get("title"),
        "company": company.title(),
        "location": job.get("location", {}).get("name"),
        "raw_description": job.get("content"),
        "url": job.get("absolute_url"),
        "source": "greenhouse",
        "posted_at": parse_datetime(job.get("updated_at")),
    }


def parse_datetime(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

# -----------------------------
# MAIN INGESTION
# -----------------------------

def fetch_greenhouse_jobs() -> List[Dict]:
    """
    Fetch and normalize data-focused jobs from Greenhouse boards
    """
    all_jobs: List[Dict] = []

    for company in GREENHOUSE_COMPANIES:
        url = GREENHOUSE_API_TEMPLATE.format(company=company)

        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            payload = response.json()

            jobs = payload.get("jobs", [])

            for job in jobs:
                title = job.get("title", "")
                if not title or not is_data_role(title):
                    continue

                normalized = normalize_job(job, company)
                all_jobs.append(normalized)

        except Exception as e:
            print(f"❌ Greenhouse fetch failed for {company}: {e}")

    print(f"✅ Greenhouse fetched {len(all_jobs)} data jobs")
    return all_jobs
