from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.db import get_news_by_tag_or_text
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("search"))
async def cmd_search(message: Message):
    logger.info(f"Команда /search вызвана пользователем {message.from_user.id} с текстом: {message.text}")
    query = message.text.split(maxsplit=1)
    if len(query) < 2:
        await message.answer("Пожалуйста, укажите тег или слово для поиска. Пример: `/search ИИ`")
        return

    query_text = query[1].strip()
    results = get_news_by_tag_or_text(query_text)

    if not results:
        await message.answer(f"Новости по запросу '{query_text}' не найдены.")
        return

    response = f"Найдено {len(results)} новостей по запросу '{query_text}':\n\n"
    for item in results:
        tags_str = " ".join([f"#{tag}" for tag in item["tags"]])
        response += f"🔹 [{item['title']}]({item['url']})\n{tags_str}\n\n"

    await message.answer(response)