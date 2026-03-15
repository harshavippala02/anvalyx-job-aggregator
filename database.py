from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./jobs.db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# Only these sources are active right now
ACTIVE_SOURCES = ["usajobs", "adzuna"]


# -----------------------------
# Jobs table
# -----------------------------
class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_job_external_source"),
    )

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True, nullable=False)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    url = Column(String)
    source = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    posted_at = Column(DateTime, default=datetime.utcnow)


# -----------------------------
# Resume table (single active resume)
# -----------------------------
class UserResume(Base):
    __tablename__ = "user_resume"

    id = Column(Integer, primary_key=True, index=True)
    resume_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# -----------------------------
# DB initialization
# -----------------------------
def init_db():
    Base.metadata.create_all(bind=engine)


# -----------------------------
# Job helpers
# -----------------------------
def save_jobs(jobs):
    db = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        jobs = [j for j in (jobs or []) if isinstance(j, dict)]

        if not jobs:
            print("💾 save_jobs complete | inserted=0, skipped=0")
            return {"inserted": 0, "skipped": 0}

        valid_jobs = []
        for job in jobs:
            external_id = job.get("external_id")
            source = job.get("source")

            if not external_id or not source:
                skipped += 1
                continue

            valid_jobs.append(job)

        if not valid_jobs:
            print(f"💾 save_jobs complete | inserted=0, skipped={skipped}")
            return {"inserted": 0, "skipped": skipped}

        sources = list({j["source"] for j in valid_jobs})
        external_ids = list({j["external_id"] for j in valid_jobs})

        existing_rows = db.query(Job.external_id, Job.source).filter(
            Job.source.in_(sources),
            Job.external_id.in_(external_ids)
        ).all()

        existing_keys = {(row.external_id, row.source) for row in existing_rows}

        for job in valid_jobs:
            key = (job["external_id"], job["source"])

            if key in existing_keys:
                skipped += 1
                continue

            db.add(Job(**job))
            existing_keys.add(key)
            inserted += 1

        db.commit()
        print(f"💾 save_jobs complete | inserted={inserted}, skipped={skipped}")
        return {"inserted": inserted, "skipped": skipped}

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_all_jobs():
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.posted_at.desc()).all()
        return jobs
    finally:
        db.close()


def clear_all_jobs():
    db = SessionLocal()
    try:
        deleted = db.query(Job).delete()
        db.commit()
        return deleted
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_job_counts():
    db = SessionLocal()
    try:
        total = db.query(Job).count()
        usajobs = db.query(Job).filter(Job.source == "usajobs").count()
        adzuna = db.query(Job).filter(Job.source == "adzuna").count()
        greenhouse = db.query(Job).filter(Job.source == "greenhouse").count()
        lever = db.query(Job).filter(Job.source == "lever").count()
        apify = db.query(Job).filter(Job.source == "apify").count()

        return {
            "all_jobs": total,
            "usajobs": usajobs,
            "adzuna": adzuna,
            "greenhouse": greenhouse,
            "lever": lever,
            "apify": apify
        }
    finally:
        db.close()


# -----------------------------
# Resume helpers
# -----------------------------
def save_resume(resume_text: str):
    """
    Saves a new resume and deactivates old ones.
    Only ONE resume is active at any time.
    """
    db = SessionLocal()

    try:
        db.query(UserResume).update({UserResume.is_active: False})

        resume = UserResume(
            resume_text=resume_text,
            is_active=True
        )

        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_active_resume():
    """
    Returns the currently active resume.
    """
    db = SessionLocal()
    try:
        resume = (
            db.query(UserResume)
            .filter(UserResume.is_active == True)
            .first()
        )
        return resume
    finally:
        db.close()


# -----------------------------
# FastAPI DB dependency
# -----------------------------
def get_db():
    """
    Yields a database session for FastAPI routes
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()