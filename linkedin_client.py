import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE_URL = "https://www.linkedin.com/jobs/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

KEYWORDS = [
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
    "Reporting Analyst",
    "Business Intelligence Analyst",
    "Analytics Engineer"
]


def build_url(keyword, start=0):
    params = {
        "keywords": keyword,
        "location": "United States",
        "f_TPR": "r604800",
        "sortBy": "R",
        "start": start
    }

    return BASE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())


def fetch_page(url):
    r = requests.get(url, headers=HEADERS)
    return r.text


def parse_jobs(html):

    soup = BeautifulSoup(html, "html.parser")

    jobs = []

    cards = soup.select("div.base-card")

    for card in cards:

        title = card.select_one("h3")
        company = card.select_one("h4")
        link = card.select_one("a")
        location = card.select_one(".job-search-card__location")
        time = card.select_one("time")

        if not title or not company or not link:
            continue

        jobs.append({
            "title": title.text.strip(),
            "company": company.text.strip(),
            "location": location.text.strip() if location else "",
            "url": link["href"].split("?")[0],
            "posted": time.text.strip() if time else ""
        })

    return jobs


def is_recent(posted_text):

    posted_text = posted_text.lower()

    if "hour" in posted_text:
        return True

    if "day" in posted_text:
        days = int(posted_text.split()[0])
        return days <= 3

    return False


def pull_linkedin_jobs():

    results = []

    for keyword in KEYWORDS:

        for start in [0, 25]:

            url = build_url(keyword, start)

            html = fetch_page(url)

            jobs = parse_jobs(html)

            for job in jobs:

                if not is_recent(job["posted"]):
                    continue

                results.append(job)

    return results