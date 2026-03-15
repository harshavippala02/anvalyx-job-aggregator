from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean
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

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    url = Column(String)
    source = Column(String, index=True)
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
        for job in jobs or []:
            if not isinstance(job, dict):
                skipped += 1
                continue

            external_id = job.get("external_id")
            source = job.get("source")

            if not external_id or not source:
                skipped += 1
                continue

            exists = db.query(Job).filter(
                Job.external_id == external_id,
                Job.source == source
            ).first()

            if exists:
                skipped += 1
                continue

            db.add(Job(**job))
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

        return {
            "all_jobs": total,
            "usajobs": usajobs,
            "adzuna": adzuna,
            "greenhouse": greenhouse,
            "lever": lever
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