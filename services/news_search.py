# services/news_search.py
import sqlite3
from database import get_db_connection

def search_news_by_tag(tag: str, limit: int = 5) -> list[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    # tag уже в нижнем регистре!
    cursor.execute("""
        SELECT pn.rendered_text
        FROM news_tags nt
        JOIN processed_news pn ON nt.news_id = pn.id
        WHERE nt.tag = ?
        ORDER BY pn.created_at DESC
        LIMIT ?
    """, (tag, limit))  # ← без .lower() — tag уже нижний
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]