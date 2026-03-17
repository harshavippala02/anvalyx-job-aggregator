import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

BASE_URL = "https://www.linkedin.com/jobs/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Broad enough to find volume, filtered later by title rules.
KEYWORDS = [
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
    "Reporting Analyst",
    "Business Intelligence Analyst",
    "Analytics Engineer",
    "Product Analyst",
    "Marketing Analyst",
    "Operations Analyst",
    "Insights Analyst",
    "Decision Scientist",
]

# You can add/remove locations depending on your needs.
LOCATIONS = [
    "United States",
    "Remote",
    "New York, United States",
    "California, United States",
    "Texas, United States",
    "Illinois, United States",
    "Washington, United States",
    "Massachusetts, United States",
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
]

BLOCKED_TITLES = [
    "data engineer",
    "machine learning engineer",
    "ml engineer",
    "software engineer",
    "ai engineer",
    "scientist",
    "staff",
    "principal",
    "director",
    "manager",
    "architect",
    "recruiter",
]

# Shallow pagination is usually enough for daily runs.
START_OFFSETS = [0, 25, 50]

# r259200 = 3 days in seconds
TIME_FILTER = "r259200"

# Keep this modest. You're using many queries already.
REQUEST_SLEEP_SECONDS = 1.5


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


def parse_jobs(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    cards = soup.select("div.base-card, li div.base-card, ul.jobs-search__results-list li")

    for card in cards:
        try:
            title_el = (
                card.select_one("h3.base-search-card__title")
                or card.select_one("h3")
            )
            company_el = (
                card.select_one("h4.base-search-card__subtitle")
                or card.select_one("h4")
            )
            location_el = (
                card.select_one(".job-search-card__location")
                or card.select_one("span.job-search-card__location")
            )
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

            if not url:
                continue

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "posted": posted,
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

    # Special case: keep analytics engineer
    if "analytics engineer" in t:
        return True

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

    return dedupe_jobs(results)