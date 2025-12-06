import sqlite3
import os

DB_PATH = "data/news_hive.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        settings TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw_news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        raw_text TEXT,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_news (
        id INTEGER,
        user_id INTEGER,
        title TEXT,
        summary_brief TEXT,
        summary_full TEXT,
        summary_points TEXT,
        tags TEXT,
        category TEXT,
        rendered_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(id) REFERENCES raw_news(id),
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        PRIMARY KEY (id, user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cached_news (
        url TEXT PRIMARY KEY,
        title TEXT,
        summary_brief TEXT,
        summary_full TEXT,
        summary_points TEXT,
        tags TEXT,
        category TEXT,
        rendered_text TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news_tags (
        news_id INTEGER,
        tag TEXT,
        FOREIGN KEY(news_id) REFERENCES raw_news(id)
    )
    """)

    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_PATH)
