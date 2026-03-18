import hashlib
from datetime import datetime
from typing import Any

import requests

GREENHOUSE_BOARDS = [
    "airbnb",
    "stripe",
    "coinbase",
    "robinhood",
    "instacart",
    "reddit",
    "discord",
    "notion",
    "doordash",
    "databricks",
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

ALLOWED_LOCATION_KEYWORDS = [
    "united states",
    "usa",
    "us",
    "remote",
    "new york",
    "california",
    "texas",
    "florida",
    "illinois",
    "washington",
    "massachusetts",
    "virginia",
    "georgia",
    "north carolina",
    "michigan",
    "new jersey",
    "pennsylvania",
    "ohio",
    "arizona",
    "colorado",
]

BLOCKED_LOCATION_KEYWORDS = [
    "india",
    "mexico",
    "canada",
    "brazil",
    "argentina",
    "germany",
    "france",
    "spain",
    "italy",
    "poland",
    "netherlands",
    "singapore",
    "philippines",
    "australia",
    "japan",
    "ireland",
    "united kingdom",
    "uk",
]

REQUEST_TIMEOUT_SECONDS = 20


def make_external_id(job: dict[str, Any], board: str) -> str:
    raw = (
        str(job.get("id") or "").strip()
        or str(job.get("absolute_url") or "").strip()
        or f"{board}_{job.get('title', '')}"
    )
    return "greenhouse_" + hashlib.md5(raw.encode("utf-8")).hexdigest()


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


def is_allowed_location(location: str) -> bool:
    if not location:
        return False

    loc = location.strip().lower()

    if any(bad in loc for bad in BLOCKED_LOCATION_KEYWORDS):
        return False

    if any(good in loc for good in ALLOWED_LOCATION_KEYWORDS):
        return True

    return False


def build_location(job: dict[str, Any]) -> str:
    location = (job.get("location", {}) or {}).get("name", "")
    location = str(location).strip()

    if not location:
        location = "Unknown"

    return location


def normalize_greenhouse_job(job: dict[str, Any], board: str) -> dict[str, Any] | None:
    title = (job.get("title") or "").strip()
    if not is_allowed_title(title):
        return None

    url = (job.get("absolute_url") or "").strip()
    if not url:
        return None

    location = build_location(job)
    if not is_allowed_location(location):
        return None

    metadata = job.get("metadata") or []
    metadata_text = " | ".join(
        f"{m.get('name', '')}: {m.get('value', '')}"
        for m in metadata
        if isinstance(m, dict)
    ).strip()

    content = (job.get("content") or "").strip()
    description = content if content else metadata_text

    posted_at = (
        parse_posted_at(job.get("updated_at"))
        or parse_posted_at(job.get("created_at"))
    )

    company = board.replace("-", " ").title()

    return {
        "external_id": make_external_id(job, board),
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "source": "greenhouse",
        "description": description[:4000],
        "posted_at": posted_at,
    }


def fetch_greenhouse_jobs() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for board in GREENHOUSE_BOARDS:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()

            payload = response.json()
            jobs = payload.get("jobs", [])

            print(f"Greenhouse fetched {len(jobs)} raw jobs for {board}", flush=True)

            for raw_job in jobs:
                normalized = normalize_greenhouse_job(raw_job, board)
                if not normalized:
                    continue

                key = (normalized["external_id"], normalized["source"])
                if key in seen_keys:
                    continue

                seen_keys.add(key)
                results.append(normalized)

        except Exception as e:
            print(f"⚠️ Greenhouse failed for {board}: {e}", flush=True)

    print(f"✅ Greenhouse normalized jobs count = {len(results)}", flush=True)
    return results