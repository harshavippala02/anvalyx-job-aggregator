from fastapi import FastAPI
from backend.database import init_db, seed_data, get_all_jobs

app = FastAPI(title="Anvalyx API")


@app.on_event("startup")
def startup():
    init_db()
    seed_data()


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/jobs")
def jobs():
    return get_all_jobs()
