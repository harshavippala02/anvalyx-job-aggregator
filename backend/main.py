from fastapi import FastAPI
from dotenv import load_dotenv

from database import init_db, get_all_jobs

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="Anvalyx API")

# Health check
@app.get("/")
def health():
    return {"status": "ok"}

# Get jobs API
@app.get("/jobs")
def get_jobs():
    return get_all_jobs()

# Startup event
@app.on_event("startup")
def startup():
    init_db()
