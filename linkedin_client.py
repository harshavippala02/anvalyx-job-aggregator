import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    "Product Analyst",
    "Marketing Analyst",
    "Operations Analyst",
    "Insights Analyst",
    "Decision Scientist",
]

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
    "sales operations analyst",
    "operations analytics analyst",
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

START_OFFSETS = [0, 25, 50]
TIME_FILTER = "r259200"  # last 3 days
REQUEST_SLEEP_SECONDS = 1.0
DETAIL_REQUEST_SLEEP_SECONDS = 0.15
DETAIL_MAX_WORKERS = 8


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

    # Typical LinkedIn URL:
    # https://www.linkedin.com/jobs/view/job-title-4386531478
    match = re.search(r"/jobs/view/(?:[^/]+-)?(\d+)", url)
    if match:
        return match.group(1)

    parsed = urlparse(url)
    path_match = re.search(r"(\d+)", parsed.path or "")
    if path_match:
        return path_match.group(1)

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
        response = requests.get(detail_url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        description_el = (
            soup.select_one(".show-more-less-html__markup")
            or soup.select_one(".description__text")
            or soup.select_one(".job-search__description")
            or soup.select_one("section.show-more-less-html")
            or soup.select_one("div.show-more-less-html__markup")
        )

        if not description_el:
            return ""

        description = description_el.get_text("\n", strip=True)
        return clean_description_text(description)

    except Exception as e:
        print(f"LinkedIn detail fetch failed for job_id={job_id}: {e}")
        return ""


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
            job_id = extract_job_id_from_url(url)

            if not url or not job_id:
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

    # Keep analytics engineer specifically
    if "analytics engineer" in t:
        return True

    # Seniority blocking
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


def enrich_jobs_with_descriptions(jobs: list[dict]) -> list[dict]:
    if not jobs:
        return jobs

    enriched = []

    with ThreadPoolExecutor(max_workers=DETAIL_MAX_WORKERS) as executor:
        future_to_job = {
            executor.submit(fetch_job_description, job["job_id"]): job
            for job in jobs
            if job.get("job_id")
        }

        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                description = future.result() or ""
            except Exception:
                description = ""

            job["description"] = description
            enriched.append(job)

            time.sleep(DETAIL_REQUEST_SLEEP_SECONDS)

    # Preserve jobs that may not have been scheduled for any reason
    enriched_by_url = {job["url"]: job for job in enriched}
    final_jobs = []

    for job in jobs:
        final_jobs.append(enriched_by_url.get(job["url"], job))

    return final_jobs


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

                    filtered_jobs = []
                    for job in jobs:
                        if not is_recent(job.get("posted", "")):
                            continue

                        if not is_allowed_title(job.get("title", "")):
                            continue

                        filtered_jobs.append(job)

                    if filtered_jobs:
                        filtered_jobs = enrich_jobs_with_descriptions(filtered_jobs)
                        results.extend(filtered_jobs)

                except Exception as e:
                    print(f"LinkedIn fetch failed for {keyword} | {location} | start={start}: {e}")

                time.sleep(REQUEST_SLEEP_SECONDS)

    final_jobs = dedupe_jobs(results)

    # Keep only fields your backend expects
    return [
        {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "posted": job.get("posted", ""),
            "description": job.get("description", ""),
        }
        for job in final_jobs
    ]