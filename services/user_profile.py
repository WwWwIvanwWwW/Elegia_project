import json
from database import get_db_connection

def get_user_settings(user_id: int) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT settings FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return {"style": "brief"}

def save_user_settings(user_id: int, settings: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, settings) VALUES (?, ?)",
                   (user_id, json.dumps(settings)))
    conn.commit()
    conn.close()

def get_user_tags(user_id: int) -> list[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tags FROM processed_news
        WHERE user_id = ? ORDER BY created_at DESC LIMIT 20
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    all_tags = []
    for row in rows:
        if row[0]:
            all_tags.extend(json.loads(row[0]))
    return list(set(all_tags))
