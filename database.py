from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    UniqueConstraint,
    text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./jobs.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

ACTIVE_SOURCES = ["usajobs", "adzuna", "linkedin"]


# -----------------------------
# Helpers
# -----------------------------
def normalize_source_value(source):
    if not source:
        return None

    s = str(source).strip().lower()

    mapping = {
        "usajobs": "usajobs",
        "usa jobs": "usajobs",
        "adzuna": "adzuna",
        "linkedin": "linkedin",
        "linkedin_public": "linkedin",
    }

    return mapping.get(s, s)


def clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def parse_posted_at(value):
    if not value:
        return None

    if isinstance(value, datetime):
        if value.tzinfo:
            return value.replace(tzinfo=None)
        return value

    try:
        value = str(value).strip()
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")

        dt = datetime.fromisoformat(value)
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


def normalize_job(job: dict):
    return {
        "external_id": clean_text(job.get("external_id")),
        "title": clean_text(job.get("title")) or "Untitled Job",
        "company": clean_text(job.get("company")) or "Unknown",
        "location": clean_text(job.get("location")) or "Unknown",
        "url": clean_text(job.get("url")),
        "source": normalize_source_value(job.get("source")),
        "description": clean_text(job.get("description")),
        "posted_at": parse_posted_at(job.get("posted_at")),
    }


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
    status = Column(String, default="new", nullable=False)
    applied_at = Column(DateTime, nullable=True)


# -----------------------------
# Resume table
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


def ensure_jobs_schema():
    db = SessionLocal()
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                external_id VARCHAR NOT NULL,
                title VARCHAR NULL,
                company VARCHAR NULL,
                location VARCHAR NULL,
                url VARCHAR NULL,
                source VARCHAR NOT NULL,
                description TEXT NULL,
                posted_at TIMESTAMP NULL,
                status VARCHAR NOT NULL DEFAULT 'new',
                applied_at TIMESTAMP NULL
            )
        """))

        db.execute(text("""
            ALTER TABLE jobs
            ADD COLUMN IF NOT EXISTS description TEXT
        """))

        db.execute(text("""
            ALTER TABLE jobs
            ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP
        """))

        db.execute(text("""
            ALTER TABLE jobs
            ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'new'
        """))

        db.execute(text("""
            ALTER TABLE jobs
            ADD COLUMN IF NOT EXISTS applied_at TIMESTAMP
        """))

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_jobs_external_id ON jobs (external_id)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_jobs_source ON jobs (source)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_jobs_title ON jobs (title)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_jobs_company ON jobs (company)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_jobs_location ON jobs (location)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_jobs_posted_at ON jobs (posted_at)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs (status)
        """))

        db.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uq_job_external_source'
                ) THEN
                    ALTER TABLE jobs
                    ADD CONSTRAINT uq_job_external_source UNIQUE (external_id, source);
                END IF;
            END
            $$;
        """))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# -----------------------------
# Job helpers
# -----------------------------
ddef save_jobs(jobs):
    db = SessionLocal()
    inserted = 0
    updated = 0
    skipped = 0

    try:
        jobs = [j for j in (jobs or []) if isinstance(j, dict)]

        if not jobs:
            print("💾 save_jobs complete | inserted=0, updated=0, skipped=0")
            return {"inserted": 0, "updated": 0, "skipped": 0}

        normalized_jobs = []
        seen_keys = set()

        for raw_job in jobs:
            job = normalize_job(raw_job)

            if not job["external_id"] or not job["source"] or not job["url"]:
                skipped += 1
                continue

            key = (job["external_id"], job["source"])

            # remove duplicates inside the same incoming batch
            if key in seen_keys:
                skipped += 1
                continue

            seen_keys.add(key)
            normalized_jobs.append(job)

        if not normalized_jobs:
            print(f"💾 save_jobs complete | inserted=0, updated=0, skipped={skipped}")
            return {"inserted": 0, "updated": 0, "skipped": skipped}

        sources = list({j["source"] for j in normalized_jobs})
        external_ids = list({j["external_id"] for j in normalized_jobs})

        existing_rows = db.query(Job).filter(
            Job.source.in_(sources),
            Job.external_id.in_(external_ids)
        ).all()

        existing_map = {
            (row.external_id, row.source): row
            for row in existing_rows
        }

        for job in normalized_jobs:
            key = (job["external_id"], job["source"])
            existing = existing_map.get(key)

            if existing:
                changed = False

                if existing.title != job["title"]:
                    existing.title = job["title"]
                    changed = True

                if existing.company != job["company"]:
                    existing.company = job["company"]
                    changed = True

                if existing.location != job["location"]:
                    existing.location = job["location"]
                    changed = True

                if existing.url != job["url"]:
                    existing.url = job["url"]
                    changed = True

                if existing.description != job["description"]:
                    existing.description = job["description"]
                    changed = True

                if existing.posted_at != job["posted_at"]:
                    existing.posted_at = job["posted_at"]
                    changed = True

                if changed:
                    updated += 1
                else:
                    skipped += 1
            else:
                new_job = Job(**job)
                db.add(new_job)
                existing_map[key] = new_job
                inserted += 1

        db.commit()
        print(f"💾 save_jobs complete | inserted={inserted}, updated={updated}, skipped={skipped}")
        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_job_status(job_id: int, status: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None

        job.status = status
        if status == "applied":
            job.applied_at = datetime.utcnow()

        db.commit()
        db.refresh(job)
        return job
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_all_jobs():
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.posted_at.desc().nullslast(), Job.id.desc()).all()
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
        linkedin = db.query(Job).filter(Job.source == "linkedin").count()
        greenhouse = db.query(Job).filter(Job.source == "greenhouse").count()
        lever = db.query(Job).filter(Job.source == "lever").count()
        apify = db.query(Job).filter(Job.source == "apify").count()

        applied = db.query(Job).filter(Job.status == "applied").count()
        saved = db.query(Job).filter(Job.status == "saved").count()
        skipped = db.query(Job).filter(Job.status == "skipped").count()
        new_count = db.query(Job).filter(Job.status == "new").count()

        return {
            "all_jobs": total,
            "usajobs": usajobs,
            "adzuna": adzuna,
            "linkedin": linkedin,
            "greenhouse": greenhouse,
            "lever": lever,
            "apify": apify,
            "new": new_count,
            "saved": saved,
            "applied": applied,
            "skipped": skipped,
        }
    finally:
        db.close()


# -----------------------------
# Resume helpers
# -----------------------------
def save_resume(resume_text: str):
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()