# services/news_pipeline.py
import json
from agents.parser_agent import run as parse
from agents.summarizer_agent import run as summarize
from agents.tags_agent import run as tags_agent
from agents.recommend_agent import run as recommend
from agents.render_agent import run as render
from services.user_profile import get_user_tags
from services.news_cache import get_cached_news, cache_news
from database import get_db_connection

async def process_news_for_user(raw_news: dict, user_id: int, style: str = "brief") -> str | None:
    url = raw_news["url"]
    
    # Проверка кэша
    cached = get_cached_news(url)
    if cached:
        user_tags = get_user_tags(user_id)
        is_relevant = await recommend(user_tags, cached["tags"])
        if is_relevant:
            news_data = {
                "title": cached["title"],
                "brief": cached["summary_brief"],
                "full": cached["summary_full"],
                "points": cached["summary_points"].split("\n") if cached["summary_points"] else [],
                "category": cached["category"],
                "tags": cached["tags"]
            }
            return await render(news_data, style=style)
        return None

    # Полный pipeline
    parsed = await parse(raw_news["raw_text"])
    summary = await summarize(parsed["body"])
    tags_result = await tags_agent(parsed["body"])
    tags = tags_result["tags"]
    category = tags_result["category"]
    
    user_tags = get_user_tags(user_id)
    is_relevant = await recommend(user_tags, tags)
    if not is_relevant:
        return None

    news_data = {
        "title": parsed["title"],
        "brief": summary["brief"],
        "full": summary["full"],
        "points": summary["points"],
        "category": category,
        "tags": tags
    }

    # Сохраняем в кэш
    rendered_text = await render(news_data, style="full")
    cache_news(url, {
        "title": parsed["title"],
        "summary_brief": summary["brief"],
        "summary_full": summary["full"],
        "summary_points": "\n".join(summary["points"]) if isinstance(summary["points"], list) else summary["points"],
        "tags": tags,
        "category": category,
        "rendered_text": rendered_text
    })

    
    # 🔥 ДОБАВЛЯЕМ СОХРАНЕНИЕ ТЕГОВ В news_tags
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM raw_news WHERE url = ?", (url,))
    row = cursor.fetchone()
    if row:
        news_id = row[0]
        cursor.execute("DELETE FROM news_tags WHERE news_id = ?", (news_id,))
        for tag in tags:
            cursor.execute("INSERT INTO news_tags (news_id, tag) VALUES (?, ?)", (news_id, tag.lower()))
    conn.commit()
    conn.close()

    return await render(news_data, style=style)