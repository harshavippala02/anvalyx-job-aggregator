import hashlib
import requests


JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"


ANALYST_KEYWORDS = [
    "analyst",
    "data analyst",
    "business analyst",
    "reporting analyst",
    "bi analyst",
    "business intelligence analyst",
    "analytics analyst",
    "operations analyst",
    "marketing analyst",
    "product analyst",
    "financial analyst",
    "data analytics",
]


SENIOR_BLOCK_KEYWORDS = [
    "6+ years",
    "6 years",
    "7+ years",
    "7 years",
    "8+ years",
    "8 years",
    "9+ years",
    "9 years",
    "10+ years",
    "10 years",
    "senior",
    "staff",
    "principal",
    "director",
    "manager",
    "lead",
]


def normalize_spaces(value):
    return " ".join(str(value or "").split()).strip()


def looks_like_analyst_role(title: str):
    title_text = normalize_spaces(title).lower()
    return any(keyword in title_text for keyword in ANALYST_KEYWORDS)


def is_us_or_remote(location: str, description: str = "", job_geo: str = ""):
    combined = f"{normalize_spaces(location)} {normalize_spaces(description)} {normalize_spaces(job_geo)}".lower()

    if "remote" in combined:
        return True

    us_tokens = [
        "united states",
        "u.s.",
        "usa",
        "us only",
        "u.s. only",
        "america",
        "north america",
    ]

    return any(token in combined for token in us_tokens)


def under_six_years(title: str, description: str):
    combined = f"{normalize_spaces(title)} {normalize_spaces(description)}".lower()
    return not any(token in combined for token in SENIOR_BLOCK_KEYWORDS)


def make_external_id(url: str):
    return "jobicy_" + hashlib.md5(url.encode("utf-8")).hexdigest()


def fetch_jobicy_jobs():
    try:
        res = requests.get(JOBICY_URL, timeout=60)
        res.raise_for_status()
        payload = res.json()
    except Exception as e:
        print(f"❌ Jobicy fetch failed: {e}", flush=True)
        return []

    raw_jobs = []

    if isinstance(payload, dict):
        if isinstance(payload.get("jobs"), list):
            raw_jobs = payload.get("jobs") or []
        elif isinstance(payload.get("data"), list):
            raw_jobs = payload.get("data") or []
    elif isinstance(payload, list):
        raw_jobs = payload

    jobs = []

    for job in raw_jobs:
        title = normalize_spaces(job.get("jobTitle") or job.get("title"))
        company = normalize_spaces(job.get("companyName") or job.get("company")) or "Unknown"
        url = normalize_spaces(job.get("url") or job.get("jobUrl"))
        description = job.get("jobDescription") or job.get("description") or ""

        location_parts = []
        if job.get("jobGeo"):
            location_parts.append(str(job.get("jobGeo")))
        if job.get("jobCountry"):
            location_parts.append(str(job.get("jobCountry")))

        location = normalize_spaces(" • ".join(location_parts)) or "Remote"
        posted_at = job.get("pubDate") or job.get("posted_at")

        if not url or not title:
            continue

        if not looks_like_analyst_role(title):
            continue

        if not is_us_or_remote(location, description, job.get("jobGeo")):
            continue

        if not under_six_years(title, description):
            continue

        jobs.append({
            "external_id": make_external_id(url),
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "source": "jobicy",
            "description": description,
            "posted_at": posted_at,
        })

    print(f"✅ Jobicy fetched {len(jobs)} filtered jobs", flush=True)
    return jobs