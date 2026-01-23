import sqlite3
import os

DB_PATH = "/tmp/anvalyx.db"

def get_connection():
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

    cursor.execute("SELECT COUNT(*) FROM jobs")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.executemany("""
            INSERT INTO jobs (title, company, location, url)
            VALUES (?, ?, ?, ?)
        """, [
            ("Data Analyst", "Google", "USA", "https://careers.google.com"),
            ("Business Analyst", "Amazon", "USA", "https://amazon.jobs"),
            ("BI Analyst", "Microsoft", "USA", "https://careers.microsoft.com"),
            ("Analytics Engineer", "Meta", "USA", "https://www.metacareers.com"),
            ("Product Analyst", "Netflix", "USA", "https://jobs.netflix.com"),
        ])

    conn.commit()
    conn.close()

def get_all_jobs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, company, location, url FROM jobs")
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "title": r[1],
            "company": r[2],
            "location": r[3],
            "url": r[4],
        }
        for r in rows
    ]
