import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

BASE_URL = "https://www.linkedin.com/jobs/search"
DETAIL_URL_TEMPLATE = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.linkedin.com/jobs/",
}

KEYWORDS = [
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
    "Reporting Analyst",
    "Business Intelligence Analyst",
    "Analytics Engineer",
]

LOCATIONS = [
    "United States",
    "Remote",
    "New York, United States",
    "California, United States",
]

ALLOWED_TITLES = [
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
    "financial reporting analyst",
    "data reporting analyst",
    "sales operations analyst",
]

BLOCKED_TITLES = [
    "data engineer",
    "machine learning engineer",
    "ml engineer",
    "software engineer",
    "ai engineer",
    "architect",
    "recruiter",
]

START_OFFSETS = [0, 25]
TIME_FILTER = "r259200"
REQUEST_SLEEP_SECONDS = 2.0
DETAIL_REQUEST_SLEEP_SECONDS = 1.0
DETAIL_FETCH_LIMIT = 20


def build_url(keyword: str, location: str, start: int = 0) -> str:
    params = {
        "keywords": keyword,
        "location": location,
        "f_TPR": TIME_FILTER,
        "sortBy": "R",
        "start": start,
    }
    return f"{BASE_URL}?{urlencode(params)}"


def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def extract_job_id_from_url(url: str) -> str | None:
    if not url:
        return None
    match = re.search(r"/jobs/view/(?:[^/]+-)?(\d+)", url)
    if match:
        return match.group(1)
    return None


def clean_description_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def fetch_job_description(job_id: str) -> str:
    if not job_id:
        return ""

    detail_url = DETAIL_URL_TEMPLATE.format(job_id=job_id)

    try:
        response = requests.get(detail_url, headers=HEADERS, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        description_el = (
            soup.select_one(".show-more-less-html__markup")
            or soup.select_one(".description__text")
            or soup.select_one("div.show-more-less-html__markup")
        )

        if not description_el:
            return ""

        return clean_description_text(description_el.get_text("\n", strip=True))
    except Exception as e:
        print(f"LinkedIn detail fetch failed for {job_id}: {e}")
        return ""


def parse_jobs(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    cards = soup.select("div.base-card, li div.base-card, ul.jobs-search__results-list li")

    for card in cards:
        try:
            title_el = card.select_one("h3.base-search-card__title") or card.select_one("h3")
            company_el = card.select_one("h4.base-search-card__subtitle") or card.select_one("h4")
            location_el = card.select_one(".job-search-card__location") or card.select_one("span.job-search-card__location")
            link_el = (
                card.select_one("a.base-card__full-link")
                or card.select_one("a[href*='/jobs/view/']")
                or card.select_one("a")
            )
            time_el = card.select_one("time")

            if not title_el or not company_el or not link_el:
                continue

            title = title_el.get_text(" ", strip=True)
            company = company_el.get_text(" ", strip=True)
            location = location_el.get_text(" ", strip=True) if location_el else ""
            url = link_el.get("href", "").split("?")[0].strip()
            posted = time_el.get_text(" ", strip=True) if time_el else ""
            job_id = extract_job_id_from_url(url)

            if not url:
                continue

            jobs.append({
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "posted": posted,
                "description": "",
            })
        except Exception:
            continue

    return jobs


def is_recent(posted_text: str) -> bool:
    if not posted_text:
        return False

    t = posted_text.lower().strip()

    if "just now" in t or "today" in t:
        return True

    if "hour" in t:
        return True

    if "day" in t:
        try:
            days = int(t.split()[0])
            return days <= 3
        except Exception:
            return False

    return False


def is_allowed_title(title: str) -> bool:
    if not title:
        return False

    t = title.lower().strip()

    if "analytics engineer" in t:
        return True

    senior_blockers = [
        "staff",
        "principal",
        "director",
        "manager",
        "head of",
        "vice president",
        "vp ",
    ]
    if any(bad in t for bad in senior_blockers):
        return False

    if any(bad in t for bad in BLOCKED_TITLES):
        return False

    return any(good in t for good in ALLOWED_TITLES)


def dedupe_jobs(jobs: list[dict]) -> list[dict]:
    seen = set()
    output = []

    for job in jobs:
        key = (
            job.get("title", "").strip().lower(),
            job.get("company", "").strip().lower(),
            job.get("location", "").strip().lower(),
            job.get("url", "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(job)

    return output


def pull_linkedin_jobs() -> list[dict]:
    results = []

    for keyword in KEYWORDS:
        for location in LOCATIONS:
            for start in START_OFFSETS:
                url = build_url(keyword, location, start)

                try:
                    html = fetch_page(url)
                    jobs = parse_jobs(html)

                    if not jobs:
                        break

                    for job in jobs:
                        if not is_recent(job.get("posted", "")):
                            continue
                        if not is_allowed_title(job.get("title", "")):
                            continue
                        results.append(job)

                except Exception as e:
                    print(f"LinkedIn fetch failed for {keyword} | {location} | start={start}: {e}")

                time.sleep(REQUEST_SLEEP_SECONDS)

    results = dedupe_jobs(results)

    # only enrich a small batch first for stability
    for job in results[:DETAIL_FETCH_LIMIT]:
        job_id = job.get("job_id")
        if job_id:
            job["description"] = fetch_job_description(job_id)
            time.sleep(DETAIL_REQUEST_SLEEP_SECONDS)

    return [
        {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "posted": job.get("posted", ""),
            "description": job.get("description", ""),
        }
        for job in results
    ]