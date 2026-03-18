import hashlib
import requests


ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


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


def is_us_or_remote(location: str, description: str = "", remote_flag=None):
    combined = f"{normalize_spaces(location)} {normalize_spaces(description)}".lower()

    if remote_flag is True:
        return True

    if "remote" in combined:
        return True

    us_tokens = [
        "united states",
        "u.s.",
        "usa",
        "us only",
        "u.s. only",
        "america",
    ]

    return any(token in combined for token in us_tokens)


def under_six_years(title: str, description: str):
    combined = f"{normalize_spaces(title)} {normalize_spaces(description)}".lower()
    return not any(token in combined for token in SENIOR_BLOCK_KEYWORDS)


def make_external_id(url: str):
    return "arbeitnow_" + hashlib.md5(url.encode("utf-8")).hexdigest()


def fetch_arbeitnow_jobs():
    try:
        res = requests.get(ARBEITNOW_URL, timeout=60)
        res.raise_for_status()
        payload = res.json()
    except Exception as e:
        print(f"❌ Arbeitnow fetch failed: {e}", flush=True)
        return []

    raw_jobs = payload.get("data", []) or []
    jobs = []

    for job in raw_jobs:
        title = normalize_spaces(job.get("title"))
        company = normalize_spaces(job.get("company_name")) or "Unknown"
        location = normalize_spaces(job.get("location")) or "Unknown"
        url = normalize_spaces(job.get("url"))
        description = job.get("description") or ""
        posted_at = job.get("created_at")
        remote_flag = job.get("remote")

        if not url or not title:
            continue

        if not looks_like_analyst_role(title):
            continue

        if not is_us_or_remote(location, description, remote_flag):
            continue

        if not under_six_years(title, description):
            continue

        jobs.append({
            "external_id": make_external_id(url),
            "title": title,
            "company": company,
            "location": location if location else "Remote",
            "url": url,
            "source": "arbeitnow",
            "description": description,
            "posted_at": posted_at,
        })

    print(f"✅ Arbeitnow fetched {len(jobs)} filtered jobs", flush=True)
    return jobs