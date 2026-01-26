import requests
from typing import List
from datetime import datetime
from database import Job, get_db

# ---------------- CONFIG ----------------

GREENHOUSE_COMPANIES = [
    "airbnb",
    "stripe",
    "coinbase",
    "databricks",
    "snowflake",
    "mongodb",
    "asana",
    "notion",
    "figma",
    "openai",
    "plaid",
    "robinhood",
    "shopify",
    "twilio",
    "zoom"
]

DATA_ROLE_KEYWORDS = [
    "data analyst",
    "business analyst",
    "analytics",
    "bi analyst",
    "reporting",
    "insights",
    "data scientist",
    "machine learning",
    "ml engineer",
    "analytics engineer"
]

EXCLUDED_SENIORITY_KEYWORDS = [
    "director",
    "head",
    "vp",
    "vice president",
    "principal",
    "staff",
    "lead",
    "manager"
]

# ---------------- FILTER HELPERS ----------------

def is_data_role(title: str) -> bool:
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in DATA_ROLE_KEYWORDS)

def is_us_job(location: str | None) -> bool:
    if not location:
        return False

    loc = location.lower()
    return (
        "united states" in loc
        or ("remote" in loc and ("us" in loc or "united states" in loc))
    )

def is_allowed_seniority(title: str) -> bool:
    t = title.lower()
    return not any(word in t for word in EXCLUDED_SENIORITY_KEYWORDS)

# ---------------- MAIN FETCH FUNCTION ----------------

def fetch_greenhouse_jobs():
    db = next(get_db())

    total = 0
    skipped_role = 0
    skipped_location = 0
    skipped_seniority = 0
    inserted = 0

    for company in GREENHOUSE_COMPANIES:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            jobs = response.json().get("jobs", [])

            for job in jobs:
                total += 1

                title = job.get("title", "")
                location = job.get("location", {}).get("name", "")
                job_url = job.get("absolute_url", "")
                description = job.get("content", "")

                # 1️⃣ Role filter
                if not is_data_role(title):
                    skipped_role += 1
                    continue

                # 2️⃣ USA-only filter
                if not is_us_job(location):
                    skipped_location += 1
                    continue

                # 3️⃣ Seniority filter
                if not is_allowed_seniority(title):
                    skipped_seniority += 1
                    continue

                # 4️⃣ Deduplication
                exists = (
                    db.query(Job)
                    .filter(Job.source == "greenhouse", Job.url == job_url)
                    .first()
                )
                if exists:
                    continue

                new_job = Job(
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    url=job_url,
                    source="greenhouse",
                    created_at=datetime.utcnow(),
                )

                db.add(new_job)
                inserted += 1

            db.commit()

        except Exception as e:
            print(f"❌ Greenhouse fetch failed for {company}: {e}")

    print(
        f"✅ Greenhouse summary | "
        f"total={total}, "
        f"skipped_role={skipped_role}, "
        f"skipped_location={skipped_location}, "
        f"skipped_seniority={skipped_seniority}, "
        f"inserted={inserted}"
    )
