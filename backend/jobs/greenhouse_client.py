import requests
import re
from datetime import datetime
from sqlalchemy.orm import Session

from database import SessionLocal, Job

# ---------------- CONFIG ----------------

GREENHOUSE_COMPANIES = [
    "snowflakecomputing",
    "databricks",
    "stripe",
    "airbnb",
    "linkedin",
    "dropbox",
    "asana",
    "coinbase",
    "roblox",
    "atlassian",
]

ALLOWED_ROLES = [
    "data analyst",
    "business analyst",
    "analytics engineer",
    "bi analyst",
    "product analyst",
]

EXCLUDED_KEYWORDS = [
    "intern",
    "internship",
    "student",
    "phd",
    "research",
]

US_KEYWORDS = [
    "united states",
    "usa",
    "us",
    "remote - us",
    "remote (us)",
    "remote, us",
]

# ---------------- HELPERS ----------------

def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"\b(level|lvl)\b", "", title)
    title = re.sub(r"\b(i|ii|iii|iv|v|\d+)\b", "", title)
    return title.strip()


def is_allowed_role(title: str) -> bool:
    title = normalize_title(title)
    return any(role in title for role in ALLOWED_ROLES)


def is_excluded(title: str) -> bool:
    title = title.lower()
    return any(word in title for word in EXCLUDED_KEYWORDS)


def is_us_location(location: str) -> bool:
    location = location.lower()
    return any(key in location for key in US_KEYWORDS)


def extract_location(job: dict) -> str:
    if job.get("location") and job["location"].get("name"):
        return job["location"]["name"]
    return ""


def parse_posted_date(job: dict):
    try:
        return datetime.strptime(job["updated_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception:
        return datetime.utcnow()


# ---------------- MAIN INGESTION ----------------

def fetch_greenhouse_jobs():
    db: Session = SessionLocal()

    total = skipped_role = skipped_location = skipped_excluded = inserted = 0

    for company in GREENHOUSE_COMPANIES:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
            resp = requests.get(url, timeout=15)

            if resp.status_code != 200:
                print(f"❌ Greenhouse fetch failed for {company}: {resp.status_code}")
                continue

            jobs = resp.json().get("jobs", [])
            if not jobs:
                continue

            for job in jobs:
                total += 1

                title = job.get("title", "").strip()
                if not title:
                    skipped_role += 1
                    continue

                if is_excluded(title):
                    skipped_excluded += 1
                    continue

                if not is_allowed_role(title):
                    skipped_role += 1
                    continue

                location = extract_location(job)
                if not is_us_location(location):
                    skipped_location += 1
                    continue

                job_url = job.get("absolute_url")
                if not job_url:
                    continue

                # Dedup by URL
                if db.query(Job).filter(Job.url == job_url).first():
                    continue

                new_job = Job(
                    title=title,
                    company=company.replace("-", " ").title(),
                    location=location,
                    url=job_url,
                    source="greenhouse",
                    posted_at=parse_posted_date(job),
                )

                db.add(new_job)
                inserted += 1

        except Exception as e:
            print(f"❌ Greenhouse error for {company}: {e}")

    db.commit()
    db.close()

    print(
        f"✅ Greenhouse summary | "
        f"total={total}, "
        f"skipped_role={skipped_role}, "
        f"skipped_location={skipped_location}, "
        f"skipped_excluded={skipped_excluded}, "
        f"inserted={inserted}"
    )
