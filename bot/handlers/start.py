from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.db import get_user_profile
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    logger.info(f"Команда /start вызвана пользователем {message.from_user.id}")
    profile = get_user_profile(message.from_user.id)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Я NewsHive, твой персональный ассистент в мире новостей.\n"
        f"Я использую ИИ, чтобы подбирать для тебя самые интересные статьи.\n\n"
        f"Текущие настройки:\n"
        f"- Интересы: {', '.join(profile['preferred_tags']) or 'не заданы'}\n"
        f"- Блок-лист: {', '.join(profile['blocked_tags']) or 'не задан'}\n\n"
        f"Команды:\n"
        f"- /digest - получить дайджест\n"
        f"- /settings - настроить интересы\n"
        f"- /search <тег или слово> - поиск новостей\n"
        f"- /help - справка"
    )