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
import re

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

ACTIVE_SOURCES = [
    "usajobs",
    "adzuna",
    "linkedin",
    "jsearch",
    "greenhouse",
    "lever",
    "remotive",
    "arbeitnow",
    "jobicy",
]


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
        "jsearch": "jsearch",
        "greenhouse": "greenhouse",
        "lever": "lever",
        "remotive": "remotive",
        "arbeitnow": "arbeitnow",
        "arbeit now": "arbeitnow",
        "jobicy": "jobicy",
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


def normalize_spaces(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def extract_experience_info(title: str | None, description: str | None):
    title_text = normalize_spaces(title).lower()
    desc_text = normalize_spaces(description).lower()
    combined = f"{title_text} {desc_text}".strip()

    if not combined:
        return {
            "min_experience_years": None,
            "max_experience_years": None,
            "experience_level": "unknown",
            "experience_display": "Unknown",
        }

    senior_title_keywords = [
        "senior",
        "sr ",
        "sr.",
        "staff",
        "principal",
        "director",
        "manager",
        "lead",
    ]

    junior_keywords = [
        "entry level",
        "entry-level",
        "junior",
        "jr ",
        "jr.",
        "new grad",
        "new graduate",
        "graduate",
        "early career",
        "campus hire",
    ]

    # Explicit entry-level style
    for kw in junior_keywords:
        if kw in combined:
            return {
                "min_experience_years": 0,
                "max_experience_years": 2,
                "experience_level": "entry",
                "experience_display": "0-2",
            }

    # Match ranges like 1-3 years / 2 to 4 years / 5–7 years
    range_patterns = [
        r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s*\+?\s*(?:years|year|yrs|yr)",
        r"(\d{1,2})\s*(?:to)\s*(\d{1,2})\s*\+?\s*(?:years|year|yrs|yr)",
        r"(?:minimum of\s*)?(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:years|year|yrs|yr)",
    ]

    for pattern in range_patterns:
        match = re.search(pattern, combined, flags=re.IGNORECASE)
        if match:
            min_years = int(match.group(1))
            max_years = int(match.group(2))
            if max_years < min_years:
                min_years, max_years = max_years, min_years

            level = "mid"
            if max_years <= 2:
                level = "entry"
            elif min_years >= 6:
                level = "senior"

            return {
                "min_experience_years": min_years,
                "max_experience_years": max_years,
                "experience_level": level,
                "experience_display": f"{min_years}-{max_years}",
            }

    # Match 3+ years / 6+ years
    plus_patterns = [
        r"(\d{1,2})\s*\+\s*(?:years|year|yrs|yr)",
        r"(?:at least|minimum of|min\.?)\s*(\d{1,2})\s*(?:years|year|yrs|yr)",
        r"(\d{1,2})\s*(?:years|year|yrs|yr)\s*(?:of experience)?\s*(?:required|preferred|minimum)?",
    ]

    for pattern in plus_patterns:
        match = re.search(pattern, combined, flags=re.IGNORECASE)
        if match:
            min_years = int(match.group(1))
            level = "mid"
            if min_years <= 2:
                level = "entry"
            elif min_years >= 6:
                level = "senior"

            return {
                "min_experience_years": min_years,
                "max_experience_years": None,
                "experience_level": level,
                "experience_display": f"{min_years}+",
            }

    # Title-based inference fallback
    for kw in senior_title_keywords:
        if kw in title_text:
            return {
                "min_experience_years": 6,
                "max_experience_years": None,
                "experience_level": "senior",
                "experience_display": "6+",
            }

    return {
        "min_experience_years": None,
        "max_experience_years": None,
        "experience_level": "unknown",
        "experience_display": "Unknown",
    }


def extract_work_mode(location: str | None, description: str | None):
    location_text = normalize_spaces(location).lower()
    desc_text = normalize_spaces(description).lower()
    combined = f"{location_text} {desc_text}"

    if any(token in combined for token in ["hybrid", "remote/onsite", "remote / onsite", "remote and onsite"]):
        return "Hybrid"

    if any(token in combined for token in ["remote", "work from home", "wfh", "telecommute", "telework"]):
        return "Remote"

    if any(token in combined for token in ["on-site", "onsite", "on site", "in office", "in-person", "in person"]):
        return "Onsite"

    return "Unknown"


def extract_job_type(title: str | None, description: str | None):
    combined = f"{normalize_spaces(title).lower()} {normalize_spaces(description).lower()}"

    if any(token in combined for token in ["full-time", "full time"]):
        return "Full-time"

    if any(token in combined for token in ["contract", "contractor", "1099", "c2c", "corp to corp"]):
        return "Contract"

    if any(token in combined for token in ["part-time", "part time"]):
        return "Part-time"

    if any(token in combined for token in ["intern", "internship"]):
        return "Internship"

    if any(token in combined for token in ["temporary", "temp"]):
        return "Temporary"

    return "Unknown"


def should_hide_due_to_experience(
    min_experience_years: int | None,
    max_experience_years: int | None,
    experience_level: str | None,
    experience_display: str | None,
):
    display = (experience_display or "").strip().lower()
    level = (experience_level or "").strip().lower()

    # Hide 6+
    if display == "6+":
        return True

    # Hide anything whose minimum required experience is 6 or above
    if min_experience_years is not None and min_experience_years >= 6:
        return True

    # Hide ranges like 5-7 or 6-8 when upper bound is 6 or above and range clearly targets senior requirements
    if max_experience_years is not None and max_experience_years >= 7:
        return True

    if level == "senior" and min_experience_years is None:
        return True

    return False


def normalize_job(job: dict):
    title = clean_text(job.get("title")) or "Untitled Job"
    description = clean_text(job.get("description"))
    location = clean_text(job.get("location")) or "Unknown"

    experience_info = extract_experience_info(title, description)
    work_mode = extract_work_mode(location, description)
    job_type = extract_job_type(title, description)
    auto_hide = should_hide_due_to_experience(
        experience_info["min_experience_years"],
        experience_info["max_experience_years"],
        experience_info["experience_level"],
        experience_info["experience_display"],
    )

    auto_skipped_reason = "experience_6_plus" if auto_hide else None

    return {
        "external_id": clean_text(job.get("external_id")),
        "title": title,
        "company": clean_text(job.get("company")) or "Unknown",
        "location": location,
        "url": clean_text(job.get("url")),
        "source": normalize_source_value(job.get("source")),
        "description": description,
        "posted_at": parse_posted_at(job.get("posted_at")),
        "min_experience_years": experience_info["min_experience_years"],
        "max_experience_years": experience_info["max_experience_years"],
        "experience_level": experience_info["experience_level"],
        "experience_display": experience_info["experience_display"],
        "work_mode": work_mode,
        "job_type": job_type,
        "auto_skipped_reason": auto_skipped_reason,
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

    min_experience_years = Column(Integer, nullable=True)
    max_experience_years = Column(Integer, nullable=True)
    experience_level = Column(String, nullable=True)
    experience_display = Column(String, nullable=True)
    work_mode = Column(String, nullable=True)
    job_type = Column(String, nullable=True)
    auto_skipped_reason = Column(String, nullable=True)


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
                applied_at TIMESTAMP NULL,
                min_experience_years INTEGER NULL,
                max_experience_years INTEGER NULL,
                experience_level VARCHAR NULL,
                experience_display VARCHAR NULL,
                work_mode VARCHAR NULL,
                job_type VARCHAR NULL,
                auto_skipped_reason VARCHAR NULL
            )
        """))

        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description TEXT"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'new'"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS applied_at TIMESTAMP"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS min_experience_years INTEGER"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS max_experience_years INTEGER"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS experience_level VARCHAR"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS experience_display VARCHAR"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS work_mode VARCHAR"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_type VARCHAR"))
        db.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS auto_skipped_reason VARCHAR"))

        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_external_id ON jobs (external_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_source ON jobs (source)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_title ON jobs (title)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_company ON jobs (company)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_location ON jobs (location)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_posted_at ON jobs (posted_at)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs (status)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_min_experience_years ON jobs (min_experience_years)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_experience_level ON jobs (experience_level)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_work_mode ON jobs (work_mode)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_job_type ON jobs (job_type)"))

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
def save_jobs(jobs):
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

            if key in seen_keys:
                skipped += 1
                continue

            seen_keys.add(key)

            # auto-skip 6+ experience jobs
            if job["auto_skipped_reason"]:
                job["status"] = "skipped"
            else:
                job["status"] = "new"

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

                updatable_fields = [
                    "title",
                    "company",
                    "location",
                    "url",
                    "description",
                    "posted_at",
                    "min_experience_years",
                    "max_experience_years",
                    "experience_level",
                    "experience_display",
                    "work_mode",
                    "job_type",
                    "auto_skipped_reason",
                ]

                for field in updatable_fields:
                    if getattr(existing, field) != job[field]:
                        setattr(existing, field, job[field])
                        changed = True

                # keep manual statuses unless current row is still new/skipped-from-auto
                existing_auto_skip = should_hide_due_to_experience(
                    job["min_experience_years"],
                    job["max_experience_years"],
                    job["experience_level"],
                    job["experience_display"],
                )

                if existing.status in {"new", "skipped"}:
                    desired_status = "skipped" if existing_auto_skip else "new"
                    if existing.status != desired_status:
                        existing.status = desired_status
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
        jsearch = db.query(Job).filter(Job.source == "jsearch").count()
        remotive = db.query(Job).filter(Job.source == "remotive").count()
        arbeitnow = db.query(Job).filter(Job.source == "arbeitnow").count()
        jobicy = db.query(Job).filter(Job.source == "jobicy").count()

        applied = db.query(Job).filter(Job.status == "applied").count()
        saved = db.query(Job).filter(Job.status == "saved").count()
        skipped = db.query(Job).filter(Job.status == "skipped").count()
        new_count = db.query(Job).filter(Job.status == "new").count()

        return {
            "all_jobs": total,
            "usajobs": usajobs,
            "adzuna": adzuna,
            "linkedin": linkedin,
            "jsearch": jsearch,
            "greenhouse": greenhouse,
            "lever": lever,
            "remotive": remotive,
            "arbeitnow": arbeitnow,
            "jobicy": jobicy,
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