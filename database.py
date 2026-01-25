from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
    source = Column(String)
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

    for job in jobs:
        exists = db.query(Job).filter(
            Job.external_id == job["external_id"],
            Job.source == job["source"]
        ).first()

        if not exists:
            db.add(Job(**job))

    db.commit()
    db.close()

def get_all_jobs():
    db = SessionLocal()
    jobs = db.query(Job).order_by(Job.posted_at.desc()).all()
    db.close()
    return jobs

# -----------------------------
# Resume helpers
# -----------------------------
def save_resume(resume_text: str):
    """
    Saves a new resume and deactivates old ones.
    Only ONE resume is active at any time.
    """
    db = SessionLocal()

    # Deactivate previous resumes
    db.query(UserResume).update({UserResume.is_active: False})

    resume = UserResume(
        resume_text=resume_text,
        is_active=True
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)
    db.close()

    return resume

def get_active_resume():
    """
    Returns the currently active resume.
    """
    db = SessionLocal()
    resume = (
        db.query(UserResume)
        .filter(UserResume.is_active == True)
        .first()
    )
    db.close()
    return resume

# -----------------------------
# ✅ FastAPI DB dependency (MISSING PART)
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
