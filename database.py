import os
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    company = Column(String(255))
    location = Column(String(255))
    url = Column(Text)
    source = Column(String(50))


def init_db():
    Base.metadata.create_all(bind=engine)


def save_jobs(jobs: list[dict]):
    db = SessionLocal()
    try:
        for job in jobs:
            exists = db.query(Job).filter(
                Job.title == job["title"],
                Job.company == job["company"]
            ).first()

            if not exists:
                db.add(Job(**job))
        db.commit()
    finally:
        db.close()


def get_all_jobs():
    db = SessionLocal()
    try:
        rows = db.query(Job).order_by(Job.id.desc()).limit(200).all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "company": r.company,
                "location": r.location,
                "url": r.url,
                "source": r.source,
            }
            for r in rows
        ]
    finally:
        db.close()

