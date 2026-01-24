from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

# -------------------------------------------------------------------
# Database URL
# -------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

# If running locally and DATABASE_URL is not set,
# fall back to SQLite
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./jobs.db"

# Fix for Render Postgres URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

# -------------------------------------------------------------------
# Job Model
# -------------------------------------------------------------------
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    url = Column(String)
    source = Column(String)
    posted_at = Column(DateTime, default=datetime.utcnow)

# -------------------------------------------------------------------
# TEMPORARY: Recreate tables (safe for now)
# -------------------------------------------------------------------
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# -------------------------------------------------------------------
# DB Helpers
# -------------------------------------------------------------------
def save_jobs(jobs):
    db = SessionLocal()
    try:
        for job in jobs:
            existing = (
                db.query(Job)
                .filter(
                    Job.external_id == job["external_id"],
                    Job.source == job["source"],
                )
                .first()
            )

            if not existing:
                db_job = Job(
                    external_id=job["external_id"],
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    url=job["url"],
                    source=job["source"],
                    posted_at=job["posted_at"],
                )
                db.add(db_job)

        db.commit()
    finally:
        db.close()


def get_all_jobs():
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.posted_at.desc()).all()
        return [
            {
                "id": j.id,
                "external_id": j.external_id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "url": j.url,
                "source": j.source,
                "posted_at": j.posted_at,
            }
            for j in jobs
        ]
    finally:
        db.close()
