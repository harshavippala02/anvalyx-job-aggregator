import requests
import os
from datetime import datetime

USAJOBS_API_URL = "https://data.usajobs.gov/api/search"


def fetch_usajobs():
    headers = {
        "User-Agent": os.getenv("USAJOBS_USER_AGENT"),
        "Authorization-Key": os.getenv("USAJOBS_API_KEY"),
        "Host": "data.usajobs.gov"
    }

    params = {
        "Keyword": "Data Analyst",
        "LocationName": "United States",
        "ResultsPerPage": 25
    }

    response = requests.get(
        USAJOBS_API_URL,
        headers=headers,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    items = data.get("SearchResult", {}).get("SearchResultItems", [])

    jobs = []

    for item in items:

        job = item.get("MatchedObjectDescriptor", {})

        if not job:
            continue

        location = "Unknown"
        locations = job.get("PositionLocation", [])
        if locations:
            location = locations[0].get("LocationName", "Unknown")

        posted = job.get("PublicationStartDate")

        posted_dt = None
        if posted:
            try:
                posted_dt = datetime.fromisoformat(posted.replace("Z", ""))
            except Exception:
                posted_dt = None

        jobs.append({
            "external_id": f"usajobs_{job.get('PositionID')}",
            "title": job.get("PositionTitle"),
            "company": job.get("OrganizationName"),
            "location": location,
            "url": job.get("PositionURI"),
            "source": "usajobs",
            "description": job.get("UserArea", {}).get("Details", {}).get("JobSummary", ""),
            "posted_at": posted_dt
        })

    return jobs