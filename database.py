import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = "civicfix.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            category TEXT,
            priority TEXT,
            area TEXT,
            lat REAL,
            lon REAL,
            status TEXT DEFAULT 'Pending',
            created_at TEXT,
            dup_count INTEGER DEFAULT 0,
            photo TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_complaint(text, category, priority, area, lat, lon, photo=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO complaints
           (text, category, priority, area, lat, lon, created_at, photo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (text, category, priority, area, lat, lon,
         datetime.now().strftime("%Y-%m-%d %H:%M"), photo),
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_all_complaints():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM complaints ORDER BY id DESC", conn)
    conn.close()
    return df


def update_status(complaint_id, new_status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = ? WHERE id = ?",
              (new_status, complaint_id))
    conn.commit()
    conn.close()


def get_complaint(complaint_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM complaints WHERE id = ?",
                           conn, params=(complaint_id,))
    conn.close()
    return df


def add_duplicate_count(complaint_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE complaints SET dup_count = dup_count + 1 WHERE id = ?",
              (complaint_id,))
    # 2 ya zyada duplicates ho gaye to priority High kar do
    c.execute("UPDATE complaints SET priority = 'High' WHERE id = ? AND dup_count >= 2",
              (complaint_id,))
    conn.commit()
    conn.close()