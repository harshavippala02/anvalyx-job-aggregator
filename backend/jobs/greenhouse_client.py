import requests
from typing import List, Dict
from datetime import datetime
from dateutil import parser

# ---------------- CONFIG ----------------

GREENHOUSE_COMPANIES = [
    "stripe",
    "databricks",
    "coinbase",
    "airbnb",
]

DATA_KEYWORDS = [
    "data",
    "analyst",
    "analytics",
    "business intelligence",
    "bi",
    "sql",
    "machine learning",
    "ml",
    "scientist",
    "engineer",
]

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


# ---------------- HELPERS ----------------

def parse_datetime(dt_str: str):
    if not dt_str:
        return None
    try:
        return parser.parse(dt_str)
    except Exception:
        return None


def is_data_role(title: str) -> bool:
    if not title:
        return False

    title = title.lower()
    return any(keyword in title for keyword in DATA_KEYWORDS)


def normalize_job(job: Dict, company: str) -> Dict:
    return {
        "external_id": f"greenhouse-{company}-{job.get('id')}",
        "title": job.get("title"),
        "company": company.title(),
        "location": job.get("location", {}).get("name"),
        "url": job.get("absolute_url"),
        "source": "greenhouse",
        "posted_at": parse_datetime(job.get("updated_at")),
    }


# ---------------- MAIN FETCH ----------------

def fetch_greenhouse_jobs() -> List[Dict]:
    all_jobs: List[Dict] = []
    total_kept = 0

    for company in GREENHOUSE_COMPANIES:
        url = f"{BASE_URL}/{company}/jobs?content=true"

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get("jobs", [])

            for job in jobs:
                title = job.get("title", "")
                if not is_data_role(title):
                    continue

                normalized = normalize_job(job, company)
                all_jobs.append(normalized)
                total_kept += 1

        except Exception as e:
            print(f"❌ Greenhouse fetch failed for {company}: {e}")

    print(f"✅ Greenhouse fetched {total_kept} data jobs")
    return all_jobs
