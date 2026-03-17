import os
import time
import hashlib
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "").strip()
JSEARCH_COUNTRY = os.getenv("JSEARCH_COUNTRY", "us").strip().lower()

JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HOST = "jsearch.p.rapidapi.com"

HEADERS = {
    "X-RapidAPI-Key": JSEARCH_API_KEY,
    "X-RapidAPI-Host": JSEARCH_HOST,
}

KEYWORDS = [
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
]

LOCATIONS = [
    "United States",
    "Remote",
]

ALLOWED_TITLE_KEYWORDS = [
    "analyst",
    "analytics engineer",
    "business intelligence",
    "decision scientist",
]

BLOCKED_TITLE_KEYWORDS = [
    "data engineer",
    "machine learning engineer",
    "ml engineer",
    "software engineer",
    "ai engineer",
    "architect",
    "recruiter",
]

PAGES_PER_QUERY = 1
EMPLOYMENT_TYPES = "FULLTIME"
DATE_POSTED = "3days"
REMOTE_ONLY_FOR_REMOTE_LOCATION = True

REQUEST_SLEEP_SECONDS = 3
REQUEST_TIMEOUT_SECONDS = 20


def make_external_id(job: dict[str, Any]) -> str:
    raw = (
        str(job.get("job_id") or "").strip()
        or str(job.get("job_apply_link") or "").strip()
        or str(job.get("job_google_link") or "").strip()
        or str(job.get("job_title") or "").strip()
    )
    return "jsearch_" + hashlib.md5(raw.encode("utf-8")).hexdigest()


def parse_posted_at(value: Any):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value

    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        return None


def build_location(job: dict[str, Any]) -> str:
    city = (job.get("job_city") or "").strip()
    state = (job.get("job_state") or "").strip()
    country = (job.get("job_country") or "").strip()

    parts = [p for p in [city, state, country] if p]
    location = ", ".join(parts)

    if not location:
        location = (job.get("job_location") or "").strip()

    if not location:
        location = "Unknown"

    is_remote = job.get("job_is_remote")
    if is_remote is True and "remote" not in location.lower():
        location = f"Remote, {location}" if location != "Unknown" else "Remote"

    return location


def is_allowed_title(title: str) -> bool:
    if not title:
        return False

    t = title.strip().lower()

    if any(bad in t for bad in BLOCKED_TITLE_KEYWORDS):
        return False

    return any(good in t for good in ALLOWED_TITLE_KEYWORDS)


def normalize_jsearch_job(job: dict[str, Any]) -> dict[str, Any] | None:
    title = (job.get("job_title") or "").strip()
    if not is_allowed_title(title):
        return None

    apply_url = (
        (job.get("job_apply_link") or "").strip()
        or (job.get("job_google_link") or "").strip()
        or (job.get("job_offer_expiration_datetime_utc") or "").strip()
    )

    if not apply_url:
        return None

    description = (
        (job.get("job_description") or "").strip()
        or (job.get("job_highlights") and str(job.get("job_highlights")))
        or ""
    )

    company = (
        (job.get("employer_name") or "").strip()
        or "Unknown"
    )

    posted_at = (
        parse_posted_at(job.get("job_posted_at_datetime_utc"))
        or parse_posted_at(job.get("job_offer_expiration_datetime_utc"))
    )

    return {
        "external_id": make_external_id(job),
        "title": title,
        "company": company,
        "location": build_location(job),
        "url": apply_url,
        "source": "jsearch",
        "description": description[:2000],
        "posted_at": posted_at,
    }


def fetch_jsearch_page(keyword: str, location: str) -> list[dict[str, Any]]:
    if not JSEARCH_API_KEY:
        print("⚠️ JSEARCH_API_KEY missing, skipping JSearch", flush=True)
        return []

    params = {
        "query": f"{keyword} in {location}",
        "page": "1",
        "num_pages": str(PAGES_PER_QUERY),
        "country": JSEARCH_COUNTRY,
        "date_posted": DATE_POSTED,
        "employment_types": EMPLOYMENT_TYPES,
    }

    if REMOTE_ONLY_FOR_REMOTE_LOCATION and location.lower() == "remote":
        params["remote_jobs_only"] = "true"

    response = requests.get(
        JSEARCH_URL,
        headers=HEADERS,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", [])

    if not isinstance(data, list):
        return []

    return data


def fetch_jsearch_jobs() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for keyword in KEYWORDS:
        for location in LOCATIONS:
            try:
                raw_jobs = fetch_jsearch_page(keyword, location)
                print(
                    f"JSearch fetched {len(raw_jobs)} raw jobs for {keyword} | {location}",
                    flush=True
                )

                for raw_job in raw_jobs:
                    normalized = normalize_jsearch_job(raw_job)
                    if not normalized:
                        continue

                    key = (normalized["external_id"], normalized["source"])
                    if key in seen_keys:
                        continue

                    seen_keys.add(key)
                    results.append(normalized)

            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)

                if status == 429:
                    print("⚠️ JSearch rate limited, stopping this run", flush=True)
                    print(f"✅ JSearch normalized jobs count = {len(results)}", flush=True)
                    return results

                print(f"⚠️ JSearch failed for {keyword} | {location}: {e}", flush=True)

            except Exception as e:
                print(f"⚠️ JSearch failed for {keyword} | {location}: {e}", flush=True)

            time.sleep(REQUEST_SLEEP_SECONDS)

    print(f"✅ JSearch normalized jobs count = {len(results)}", flush=True)
    return results