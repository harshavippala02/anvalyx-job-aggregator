import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Render provides DATABASE_URL automatically
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix for Render Postgres URL format
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=False)
    url = Column(String, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def seed_data():
    db = SessionLocal()

    # Avoid duplicate seeding
    if db.query(Job).first():
        db.close()
        return

    jobs = [
        Job(title="Data Analyst", company="Google", location="USA", url="https://careers.google.com"),
        Job(title="Business Analyst", company="Amazon", location="USA", url="https://amazon.jobs"),
        Job(title="BI Analyst", company="Microsoft", location="USA", url="https://careers.microsoft.com"),
        Job(title="Analytics Engineer", company="Meta", location="USA", url="https://www.metacareers.com"),
        Job(title="Product Analyst", company="Netflix", location="USA", url="https://jobs.netflix.com"),
    ]

    db.add_all(jobs)
    db.commit()
    db.close()


def get_all_jobs():
    db = SessionLocal()
    jobs = db.query(Job).all()
    result = [
        {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
        }
        for job in jobs
    ]
    db.close()
    return result
