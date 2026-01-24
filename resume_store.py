from database import SessionLocal, Resume


def save_resume(resume_text: str):
    db = SessionLocal()

    # Keep only ONE resume
    db.query(Resume).delete()
    db.add(Resume(content=resume_text))

    db.commit()
    db.close()


def get_resume():
    db = SessionLocal()
    resume = db.query(Resume).first()
    db.close()

    return resume.content if resume else ""
