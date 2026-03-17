import os
from apify_client import ApifyClient


APIFY_TOKEN = os.getenv("APIFY_TOKEN")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID")


def normalize_apify_job(item):
    """
    Convert Apify dataset item -> Anvalyx job format
    Adjust field names depending on the actor output.
    """

    external_id = (
        item.get("id")
        or item.get("jobId")
        or item.get("job_id")
        or item.get("url")
    )

    title = (
        item.get("title")
        or item.get("positionName")
        or item.get("jobTitle")
    )

    company = (
        item.get("company")
        or item.get("companyName")
        or "Unknown"
    )

    location = (
        item.get("location")
        or item.get("jobLocation")
        or "Unknown"
    )

    url = (
        item.get("url")
        or item.get("jobUrl")
        or item.get("applyUrl")
    )

    description = (
        item.get("description")
        or item.get("jobDescription")
    )

    posted = (
        item.get("datePosted")
        or item.get("postedAt")
        or item.get("publicationDate")
        or item.get("createdAt")
    )

    if not external_id or not title or not url:
        return None

    return {
        "external_id": str(external_id),
        "title": str(title),
        "company": str(company),
        "location": str(location),
        "url": str(url),
        "source": "apify",
        "description": description,
        "posted_at": posted,
    }


def fetch_apify_jobs():
    """
    Fetch jobs from Apify actor dataset
    """

    if not APIFY_TOKEN:
        print("⚠️ APIFY_TOKEN not set")
        return []

    if not APIFY_ACTOR_ID:
        print("⚠️ APIFY_ACTOR_ID not set")
        return []

    client = ApifyClient(APIFY_TOKEN)

    try:

        run = client.actor(APIFY_ACTOR_ID).call()

        dataset_id = run.get("defaultDatasetId")

        if not dataset_id:
            print("⚠️ No dataset returned")
            return []

        dataset = client.dataset(dataset_id)

        jobs = []

        for item in dataset.iterate_items():

            job = normalize_apify_job(item)

            if job:
                jobs.append(job)

        return jobs

    except Exception as e:

        print(f"❌ Apify fetch failed: {e}")
        return []