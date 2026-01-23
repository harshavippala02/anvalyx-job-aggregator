import sqlite3
import os

# Always use a writable location on Render
DB_DIR = "/tmp/anvalyx"
DB_PATH = os.path.join(DB_DIR, "anvalyx.db")

def get_connection():
    # Ensure directory exists
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
