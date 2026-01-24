from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    external_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String)
    location = Column(String)
    url = Column(Text)
    source = Column(String, nullable=False)
    posted_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uix_external_source"),
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def save_jobs(jobs: list[dict]):
    db = SessionLocal()

    for job in jobs:
        exists = (
            db.query(Job)
            .filter(
                Job.external_id == str(job["external_id"]),
                Job.source == job["source"],
            )
            .first()
        )

        if exists:
            continue

        db.add(
            Job(
                external_id=str(job["external_id"]),
                title=job["title"],
                company=job.get("company"),
                location=job.get("location"),
                url=job.get("url"),
                source=job["source"],
                posted_at=job.get("posted_at"),
            )
        )

    db.commit()
    db.close()


def get_all_jobs():
    db = SessionLocal()
    jobs = db.query(Job).order_by(Job.posted_at.desc()).all()
    db.close()

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
