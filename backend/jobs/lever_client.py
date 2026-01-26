import requests
from datetime import datetime
from typing import List

from database import Job, get_db

# ---------------- CONFIG ---------------- #

LEVER_COMPANIES = [
    "stripe",
    "airbnb",
    "coinbase",
    "netflix",
    "robinhood",
    "affirm",
    "asana",
    "canva",
    "dropbox",
    "figma",
    "github",
    "instacart",
    "lyft",
    "pinterest",
    "reddit",
    "snap",
    "spotify",
    "square",
    "uber",
    "yelp",
]

INCLUDE_KEYWORDS = [
    "data analyst",
    "business analyst",
    "analytics",
    "bi analyst",
    "product analyst",
    "decision scientist",
]

EXCLUDE_KEYWORDS = [
    "manager",
    "director",
    "head",
    "vp",
    "principal",
    "staff",
    "lead",
    "intern",
]

US_LOCATION_KEYWORDS = [
    "united states",
    "usa",
    "us",
    "remote - us",
    "remote, us",
    "remote (us)",
]

# ---------------- HELPERS ---------------- #

def is_valid_title(title: str) -> bool:
    t = title.lower()

    if not any(k in t for k in INCLUDE_KEYWORDS):
        return False

    if any(k in t for k in EXCLUDE_KEYWORDS):
        return False

    return True


def is_us_location(location: str) -> bool:
    if not location:
        return False

    loc = location.lower()
    return any(k in loc for k in US_LOCATION_KEYWORDS)


# ---------------- MAIN INGESTION ---------------- #

def fetch_lever_jobs():
    db = next(get_db())

    total = 0
    skipped_role = 0
    skipped_location = 0
    inserted = 0

    for company in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"

        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            jobs = resp.json()
        except Exception as e:
            print(f"❌ Lever fetch failed for {company}: {e}")
            continue

        for job in jobs:
            total += 1

            title = job.get("text", "").strip()
            location = job.get("categories", {}).get("location", "")
            team = job.get("categories", {}).get("team", "")
            apply_url = job.get("hostedUrl")
            description = job.get("descriptionPlain", "")

            if not is_valid_title(title):
                skipped_role += 1
                continue

            if not is_us_location(location):
                skipped_location += 1
                continue

            # Dedup check
            exists = (
                db.query(Job)
                .filter(
                    Job.title == title,
                    Job.company == company,
                    Job.source == "lever",
                )
                .first()
            )

            if exists:
                continue

            job_row = Job(
                title=title,
                company=company,
                location=location,
                description=description,
                apply_url=apply_url,
                source="lever",
                posted_date=datetime.utcnow(),
                is_active=True,
            )

            db.add(job_row)
            inserted += 1

        db.commit()

    print(
        f"✅ Lever summary | total={total}, "
        f"skipped_role={skipped_role}, "
        f"skipped_location={skipped_location}, "
        f"inserted={inserted}"
    )
