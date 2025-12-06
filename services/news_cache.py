# services/news_cache.py
import json
from database import get_db_connection

def get_cached_news(url: str) -> dict | None:
    """Возвращает кэшированную новость по URL или None, если не найдена."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, summary_brief, summary_full, summary_points, tags, category, rendered_text
        FROM cached_news WHERE url = ?
    """, (url,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "title": row[0],
            "summary_brief": row[1],
            "summary_full": row[2],
            "summary_points": row[3],
            "tags": json.loads(row[4]) if row[4] else [],
            "category": row[5],
            "rendered_text": row[6]
        }
    return None

def cache_news(url: str, news_dict: dict):
    """Сохраняет обработанную новость в кэш."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO cached_news (
            url, title, summary_brief, summary_full, summary_points,
            tags, category, rendered_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        url,
        news_dict["title"],
        news_dict["summary_brief"],
        news_dict["summary_full"],
        news_dict["summary_points"],
        json.dumps(news_dict["tags"]),
        news_dict["category"],
        news_dict["rendered_text"]
    ))
    conn.commit()
    conn.close()