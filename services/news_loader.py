# services/news_loader.py
import feedparser
import json
import os
from datetime import datetime, timedelta

async def fetch_raw_news_sample() -> list[dict]:
    sources_path = "data/sources.json"
    if not os.path.exists(sources_path):
        return []

    with open(sources_path, "r", encoding="utf-8") as f:
        sources = json.load(f)["sources"]

    all_entries = []
    for source in sources:
        try:
            feed = feedparser.parse(source["rss_url"])
            for entry in feed.entries[:3]:
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                    if datetime.utcnow() - pub_date > timedelta(days=1):
                        continue

                title = getattr(entry, 'title', 'Без заголовка')
                summary = getattr(entry, 'summary', '')
                description = getattr(entry, 'description', '')

                # Используем summary или description как тело
                body = summary or description or ""

                # raw_text = заголовок + краткое описание
                raw_text = f"{title}\n\n{body}".strip()

                # Пропускаем, если совсем пусто
                if not raw_text or len(raw_text) < 10:
                    continue

                all_entries.append({
                    "url": entry.link,
                    "raw_text": raw_text
                })
                if len(all_entries) >= 2:
                    return all_entries
        except Exception as e:
            print(f"[Ошибка] {source.get('rss_url', 'unknown')}: {e}")
            continue
    return all_entries[:2]