from typing import Dict, Any
from agents.parser_agent import parse_news_agent as parse
from agents.summarizer_agent import run as summarize
from agents.tags_agent import run as tag
from agents.recommend_agent import run as recommend
from agents.render_agent import run as render
from database.db import cache_news
import logging
import asyncio

logger = logging.getLogger(__name__)

async def process_news_for_user(raw_news_item: Dict[str, Any], user_id: int, style: str = "full"):
    try:
        # 1. Парсинг
        parsed = await parse()
        await asyncio.sleep(2)  # Задержка после вызова LLM
        if not parsed.get("text"):
            logger.warning(f"Не удалось спарсить содержимое статьи: {raw_news_item['url']}")
            return None

        # 2. Суммаризация
        summary = await summarize(parsed["text"], style=style)
        await asyncio.sleep(2)  # Задержка после вызова LLM

        # 3. Тегирование
        '''
        tags_result = await tag(summary)
        await asyncio.sleep(2)  # Задержка после вызова LLM
        category = tags_result["category"]
        tags = tags_result["tags"]
        '''
        # 4. Персонализация
        '''
        is_relevant = await recommend(user_id, category, tags)
        await asyncio.sleep(2)  # Задержка после вызова LLM
        if not is_relevant:
            logger.info(f"Новость {parsed['url']} не релевантна пользователю {user_id}")
            return None
        '''
        # 5. Кэширование (до форматирования, чтобы не дублировать)
        cache_news(
            title=parsed["title"],
            summary=summary,
            url=parsed["url"],
            category=category,
            tags=tags,
            source=parsed["summary"],
            published_at=parsed.get("published_at", "unknown")
        )

        # 6. Форматирование
        rendered_text = await render(
            title=parsed["title"],
            summary=summary,
            category=category,
            tags=tags,
            url=parsed["url"],
            style=style
        )
        await asyncio.sleep(2)  # Задержка после вызова LLM
        return rendered_text

    except Exception as e:
        logger.error(f"Ошибка в pipeline для {raw_news_item.get('url', 'unknown')}: {e}")
        return None