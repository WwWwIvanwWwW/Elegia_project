from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("help"))
async def cmd_help(message: Message):
    logger.info(f"Команда /help вызвана пользователем {message.from_user.id}")
    await message.answer(
        "**Доступные команды:**\n"
        "/start - Приветствие и информация о боте\n"
        "/digest [brief|full|points] - Получить персонализированный дайджест новостей (по умолчанию 'brief')\n"
        "/settings - Просмотр и настройка интересов и блок-листа\n"
        "/search <запрос> - Найти новости по тегу или ключевому слову\n"
        "/help - Это сообщение\n\n"
        "Просто пришли слово или тег в /settings, чтобы добавить его в список интересов."
    )