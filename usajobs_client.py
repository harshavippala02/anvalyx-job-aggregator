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

    response = requests.get(USAJOBS_API_URL, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    results = data["SearchResult"]["SearchResultItems"]

    jobs = []

    for item in results:
        job = item["MatchedObjectDescriptor"]

        jobs.append({
            "external_id": job["PositionID"],
            "title": job["PositionTitle"],
            "company": job["OrganizationName"],
            "location": job["PositionLocation"][0]["LocationName"],
            "url": job["PositionURI"],
            "source": "usajobs",
            "posted_at": datetime.fromisoformat(job["PublicationStartDate"].replace("Z", ""))
        })

    return jobs
