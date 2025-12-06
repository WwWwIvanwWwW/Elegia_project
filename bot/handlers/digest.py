# bot/handlers/digest.py
from aiogram import Router, types, F
from aiogram.filters import Command
from services.news_loader import fetch_raw_news_sample
from services.news_pipeline import process_news_for_user
from services.user_profile import get_user_settings
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("digest"))
@router.message(F.text == "📰 Получить дайджест")
async def cmd_digest(message: types.Message):
    await message.answer("🔄 Готовлю ваш дайджест...")
    try:
        raw_news_list = await fetch_raw_news_sample()
        # Ограничение из-за лимита free-моделей (50 запросов/день)
        raw_news_list = raw_news_list[:1]  # обрабатываем только 1 новость

        if not raw_news_list:
            await message.answer("Новости не найдены.")
            return

        user_id = message.from_user.id
        settings = get_user_settings(user_id)
        style = settings.get("style", "brief")

        sent_any = False
        for i, raw in enumerate(raw_news_list):
            logger.info(f"Обработка новости {i+1}: {raw['url']}")
            try:
                msg = await process_news_for_user(raw, user_id, style=style)
                if msg:
                    await message.answer(msg, parse_mode="MarkdownV2")
                    sent_any = True
            except Exception as e:
                logger.exception(f"Ошибка при обработке новости: {e}")
                await message.answer("❌ Произошла ошибка при обработке одной из новостей.")

        if not sent_any:
            await message.answer("Нет новых релевантных новостей.")
            
    except Exception as e:
        logger.exception("Критическая ошибка в /digest")
        await message.answer("⚠️ Не удалось загрузить новости. Попробуйте позже.")