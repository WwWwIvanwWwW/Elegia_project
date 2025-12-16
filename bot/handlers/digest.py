from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from services.news_loader import load_news_from_sources
from services.news_pipeline import process_news_for_user
from database.db import update_user_tags
import logging
import asyncio

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("digest"))
async def cmd_digest(message: Message):
    user_id = message.from_user.id
    # Определяем стиль из сообщения, например, /digest full
    command_parts = message.text.split()
    style = command_parts[1] if len(command_parts) > 1 else "brief"

    logger.info(f"Команда /digest вызвана пользователем {user_id}, стиль: {style}")

    raw_news_list = await load_news_from_sources()
    raw_news_list = raw_news_list[:3]  # Обрабатываем только первые 3 статьи
    logger.info(f"Загружено {len(raw_news_list)} новостей")

    relevant_messages = []
    for i, raw in enumerate(raw_news_list, 1):
        logger.info(f"Обработка новости {i}: {raw.get('url', 'unknown')}")
        msg = await process_news_for_user(raw, user_id, style=style)
        if msg:
            relevant_messages.append(msg)
        if len(relevant_messages) >= 3: # Отправляем первые 3 релевантных
            logger.info(f"Достигнуто ограничение в 3 новостей для отправки, остановка цикла")
            break
        await asyncio.sleep(2)  # Задержка между обработкой статей

    logger.info(f"Всего сформировано релевантных сообщений: {len(relevant_messages)}")
    if not relevant_messages:
        await message.answer("К сожалению, на сегодня не нашлось новостей, соответствующих вашим интересам.")
    else:
        for msg in relevant_messages:
            await message.answer(msg)