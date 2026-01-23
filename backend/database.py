import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database", "anvalyx.db")

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE,
    title TEXT,
    company TEXT,
    location TEXT,
    category TEXT,
    salary_min REAL,
    salary_max REAL,
    url TEXT,
    source TEXT,
    created TEXT
);
    """)

    conn.commit()
    conn.close()

def insert_job(job):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO jobs
            (job_id, title, company, location, category,
             salary_min, salary_max, url, source, created)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job["job_id"],
            job["title"],
            job["company"],
            job["location"],
            job["category"],
            job["salary_min"],
            job["salary_max"],
            job["url"],
            job["source"],
            job["created"]
        ))

        conn.commit()
    except Exception as e:
        print("DB insert error:", e)

    conn.close()

def get_jobs(keyword=None, location=None, min_salary=0):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT title, company, location, category,
               salary_min, salary_max, url, created
        FROM jobs
        WHERE salary_min >= ?
    """
    params = [min_salary]

    if keyword:
        query += " AND title LIKE ?"
        params.append(f"%{keyword}%")

    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    query += " ORDER BY created DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for r in rows:
        jobs.append({
            "title": r[0],
            "company": r[1],
            "location": r[2],
            "category": r[3],
            "salary_min": r[4],
            "salary_max": r[5],
            "url": r[6],
            "created": r[7]
        })

    return jobs
