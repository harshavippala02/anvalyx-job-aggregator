import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables (.env locally, Render env in prod)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Fix Render postgres URL if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Real external job id (Adzuna / ATS)
    external_id = Column(String(100), nullable=False)

    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)

    # REAL apply URL
    url = Column(Text, nullable=False)

    # Source: adzuna / greenhouse / lever / etc
    source = Column(String(50), nullable=False)

    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_job_external_source"),
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def save_jobs(jobs: list[dict]):
    db = SessionLocal()
    try:
        for job in jobs:
            exists = (
                db.query(Job)
                .filter(
                    Job.external_id == job["external_id"],
                    Job.source == job["source"],
                )
                .first()
            )

            if exists:
                continue

            db.add(
                Job(
                    external_id=job["external_id"],
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    url=job["url"],
                    source=job["source"],
                    posted_at=job.get("posted_at"),
                )
            )

        db.commit()
    finally:
        db.close()


def get_all_jobs():
    db = SessionLocal()
    try:
        rows = (
            db.query(Job)
            .order_by(Job.created_at.desc())
            .limit(200)
            .all()
        )

        return [
            {
                "id": r.id,
                "external_id": r.external_id,
                "title": r.title,
                "company": r.company,
                "location": r.location,
                "url": r.url,
                "source": r.source,
                "posted_at": r.posted_at.isoformat() if r.posted_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()
