from fastapi import FastAPI
from database import init_db, save_jobs, get_all_jobs

app = FastAPI(title="Anvalyx Job Aggregator")


@app.on_event("startup")
def startup():
    init_db()

    # TEMP seed (safe)
    jobs = [
        {
            "title": "Financial Data Analyst",
            "company": "Veolia Water Technologies & Solutions",
            "location": "USA",
            "url": "https://jobs.example.com/1",
        },
        {
            "title": "Data Analyst",
            "company": "Amazon",
            "location": "USA",
            "url": "https://jobs.example.com/2",
        },
    ]

    save_jobs(jobs)


@app.get("/")
def root():
    return {"status": "Anvalyx backend running"}


@app.get("/jobs")
def jobs():
    return get_all_jobs()
