import sqlite3
import json
from contextlib import contextmanager
from typing import List, Dict, Any

DB_PATH = "data/news_hive.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            preferred_tags TEXT DEFAULT '[]',
            blocked_tags TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            source TEXT NOT NULL,
            published_at TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            news_id INTEGER NOT NULL,
            action TEXT NOT NULL, -- 'like', 'dislike'
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(news_id) REFERENCES news(id),
            UNIQUE(user_id, news_id)
        )
    ''')

    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Позволяет обращаться к столбцам по имени
    try:
        yield conn
    finally:
        conn.close()

def get_user_profile(telegram_id: int) -> Dict[str, List[str]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT preferred_tags, blocked_tags FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        if row:
            preferred_tags = json.loads(row["preferred_tags"])
            # For existing users with empty preferred tags, add "Всё" as default
            if not preferred_tags:
                preferred_tags = ["Всё"]
                # Update the database as well
                cursor.execute(
                    "UPDATE users SET preferred_tags = ? WHERE telegram_id = ?",
                    (json.dumps(preferred_tags), telegram_id)
                )
                conn.commit()

            return {
                "preferred_tags": preferred_tags,
                "blocked_tags": json.loads(row["blocked_tags"])
            }
        else:
            # Создаём профиль с тегом "Всё" по умолчанию для новых пользователей
            cursor.execute("INSERT INTO users (telegram_id, preferred_tags) VALUES (?, ?)",
                          (telegram_id, '["Всё"]'))
            conn.commit()
            return {"preferred_tags": ["Всё"], "blocked_tags": []}

def update_user_tags(telegram_id: int, tag: str, action: str):
    profile = get_user_profile(telegram_id)
    preferred = set(profile["preferred_tags"])
    blocked = set(profile["blocked_tags"])

    if action == "like":
        preferred.add(tag)
        blocked.discard(tag)
        # If user starts liking specific content, remove the general "Всё" tag
        if "Всё" in preferred and len(preferred) > 1:
            preferred.discard("Всё")
    elif action == "dislike":
        preferred.discard(tag)
        blocked.add(tag)

    # Ensure at least one preferred tag if the user has no specific preferences
    if not preferred:
        preferred.add("Всё")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET preferred_tags = ?, blocked_tags = ? WHERE telegram_id = ?",
            (json.dumps(list(preferred)), json.dumps(list(blocked)), telegram_id)
        )
        conn.commit()

def cache_news(title: str, summary: str, url: str, category: str, tags: List[str], source: str, published_at: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO news (title, summary, url, category, tags, source, published_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, summary, url, category, json.dumps(tags), source, published_at)
            )
            conn.commit()
        except sqlite3.OperationalError as e:
            print(f"Ошибка при кэшировании новости: {e}")

def get_news_by_tag_or_text(query: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Ищем по тегу (как подстрока в JSON-строке)
        search_pattern = f'%"{query}"%'
        cursor.execute('''
            SELECT * FROM news
            WHERE tags LIKE ?
            OR title LIKE ? OR summary LIKE ?
            LIMIT 10
        ''', (search_pattern, f'%{query}%', f'%{query}%'))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def update_user_interests(telegram_id: int, preferred_tags: List[str]):
    """Update user's preferred tags with new interests"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Get existing blocked tags to preserve them
        cursor.execute("SELECT blocked_tags FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        if row:
            blocked_tags = json.loads(row["blocked_tags"])
        else:
            # If user doesn't exist, create with empty lists
            cursor.execute("INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,))
            blocked_tags = []

        cursor.execute(
            "UPDATE users SET preferred_tags = ?, blocked_tags = ? WHERE telegram_id = ?",
            (json.dumps(preferred_tags), json.dumps(blocked_tags), telegram_id)
        )
        conn.commit()