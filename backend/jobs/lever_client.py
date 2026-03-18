import hashlib
from datetime import datetime
from typing import Any

import requests

LEVER_COMPANIES = [
    "netflix",
    "shopify",
    "affirm",
    "figma",
    "palantir",
    "asana",
    "yelp",
    "square",
    "scaleai",
]

ALLOWED_TITLE_KEYWORDS = [
    "data analyst",
    "business analyst",
    "bi analyst",
    "reporting analyst",
    "business intelligence analyst",
    "analytics engineer",
    "product analyst",
    "marketing analyst",
    "operations analyst",
    "insights analyst",
    "decision scientist",
    "data analytics analyst",
    "commercial analyst",
    "financial analyst",
    "pricing analyst",
    "risk analyst",
    "strategy analyst",
]

BLOCKED_TITLE_KEYWORDS = [
    "data engineer",
    "machine learning engineer",
    "ml engineer",
    "software engineer",
    "ai engineer",
    "architect",
    "recruiter",
    "talent",
    "designer",
    "frontend",
    "backend",
    "full stack",
    "devops",
    "site reliability",
    "sre",
]

SENIOR_BLOCKERS = [
    "staff",
    "principal",
    "director",
    "manager",
    "head of",
    "vice president",
    "vp ",
]

REQUEST_TIMEOUT_SECONDS = 20


def make_external_id(job: dict[str, Any], company_slug: str) -> str:
    raw = (
        str(job.get("id") or "").strip()
        or str(job.get("hostedUrl") or "").strip()
        or f"{company_slug}_{job.get('text', '')}"
    )
    return "lever_" + hashlib.md5(raw.encode("utf-8")).hexdigest()


def parse_posted_at(value: Any):
    if not value:
        return None

    try:
        # Lever often returns milliseconds timestamp
        if isinstance(value, (int, float)):
            if value > 10_000_000_000:
                return datetime.utcfromtimestamp(value / 1000)
            return datetime.utcfromtimestamp(value)

        text = str(value).strip()
        if text.isdigit():
            num = int(text)
            if num > 10_000_000_000:
                return datetime.utcfromtimestamp(num / 1000)
            return datetime.utcfromtimestamp(num)

        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        return None


def is_allowed_title(title: str) -> bool:
    if not title:
        return False

    t = title.strip().lower()

    if any(bad in t for bad in BLOCKED_TITLE_KEYWORDS):
        return False

    if any(bad in t for bad in SENIOR_BLOCKERS):
        return False

    if "analytics engineer" in t:
        return True

    return any(good in t for good in ALLOWED_TITLE_KEYWORDS)


def build_location(job: dict[str, Any]) -> str:
    categories = job.get("categories") or {}
    location = (categories.get("location") or "").strip()

    if not location:
        location = "Unknown"

    return location


def normalize_lever_job(job: dict[str, Any], company_slug: str) -> dict[str, Any] | None:
    title = (job.get("text") or "").strip()
    if not is_allowed_title(title):
        return None

    url = (job.get("hostedUrl") or "").strip()
    if not url:
        return None

    description = (
        (job.get("descriptionPlain") or "").strip()
        or (job.get("description") or "").strip()
        or ""
    )

    location = build_location(job)
    posted_at = (
        parse_posted_at(job.get("createdAt"))
        or parse_posted_at(job.get("updatedAt"))
    )

    company = company_slug.replace("-", " ").title()

    return {
        "external_id": make_external_id(job, company_slug),
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "source": "lever",
        "description": description[:4000],
        "posted_at": posted_at,
    }


def fetch_lever_jobs() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for company_slug in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"

        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()

            jobs = response.json()
            if not isinstance(jobs, list):
                jobs = []

            print(f"Lever fetched {len(jobs)} raw jobs for {company_slug}", flush=True)

            for raw_job in jobs:
                normalized = normalize_lever_job(raw_job, company_slug)
                if not normalized:
                    continue

                key = (normalized["external_id"], normalized["source"])
                if key in seen_keys:
                    continue

                seen_keys.add(key)
                results.append(normalized)

        except Exception as e:
            print(f"⚠️ Lever failed for {company_slug}: {e}", flush=True)

    print(f"✅ Lever normalized jobs count = {len(results)}", flush=True)
    return results