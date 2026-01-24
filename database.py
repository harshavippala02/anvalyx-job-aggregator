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
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# -----------------------------
# Job table
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
# Resume table (NEW)
# -----------------------------
class UserResume(Base):
    __tablename__ = "user_resume"

    id = Column(Integer, primary_key=True, index=True)
    resume_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# -----------------------------
# DB init
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

# -----------------------------
# Resume helpers
# -----------------------------
def save_resume(resume_text: str):
    db = SessionLocal()

    # Deactivate old resumes
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
    db = SessionLocal()
    resume = db.query(UserResume).filter(UserResume.is_active == True).first()
    db.close()
    return resume
