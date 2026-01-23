from fastapi import FastAPI
from dotenv import load_dotenv

from database import init_db

# Load environment variables
load_dotenv()

# Create the FastAPI app (ONLY ONCE)
app = FastAPI(title="Anvalyx API")

# Health check endpoint (required for Render)
@app.get("/")
def health():
    return {"status": "ok"}

# Run on startup
@app.on_event("startup")
def startup():
    init_db()
