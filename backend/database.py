import sqlite3
import os

# Writable directory for Render
DB_DIR = "/tmp/anvalyx"
DB_PATH = os.path.join(DB_DIR, "anvalyx.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT
        )
    """)

    conn.commit()
    conn.close()

def get_all_jobs():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, company, location, url
        FROM jobs
        ORDER BY id DESC
        LIMIT 50
    """)

    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for row in rows:
        jobs.append({
            "id": row[0],
            "title": row[1],
            "company": row[2],
            "location": row[3],
            "url": row[4],
        })

    return jobs
    
def insert_sample_jobs():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (title, company, location, url)
        VALUES
        ('Data Analyst', 'Google', 'United States', 'https://careers.google.com'),
        ('Business Analyst', 'Amazon', 'United States', 'https://amazon.jobs'),
        ('Analytics Engineer', 'Meta', 'United States', 'https://www.metacareers.com')
    """)

    conn.commit()
    conn.close()
