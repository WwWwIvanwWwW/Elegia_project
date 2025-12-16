from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.db import get_user_profile, update_user_tags
import re
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    logger.info(f"Команда /settings вызвана пользователем {message.from_user.id}")
    profile = get_user_profile(message.from_user.id)
    await message.answer(
        f"Настройки профиля:\n"
        f"- Интересы: `{', '.join(profile['preferred_tags']) or 'не заданы'}`\n"
        f"- Блок-лист: `{', '.join(profile['blocked_tags']) or 'не задан'}`\n\n"
        f"Чтобы добавить интерес или тег в блок-лист, просто пришли его сюда. "
        f"Например, напиши 'искусственный_интеллект' и я добавлю его в твои интересы.",
        parse_mode=None
    )

# Простой хендлер для добавления тега
@router.message()
async def handle_text_settings(message: Message):
    logger.info(f"handle_text_settings получил сообщение: {message.text}, is_command: {message.text.startswith('/') if message.text else False}")
    # Игнорируем пустые сообщения и команды
    if not message.text or message.text.startswith('/'):
        return

    user_id = message.from_user.id  # ← ОПРЕДЕЛЯЕМ user_id
    raw_text = message.text.strip()  # ← ОПРЕДЕЛЯЕМ raw_text

    # Фильтруем некорректные символы (только буквы, цифры, пробелы, дефисы, подчёркивания)
    if not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9 _\-]+$', raw_text):
        await message.answer("Пожалуйста, используйте только буквы, цифры, пробелы, дефисы или подчёркивания.", parse_mode=None)
        return

    # Нормализуем тег: нижний регистр, пробелы → подчёркивания
    tag = raw_text.lower().replace(" ", "_").replace("-", "_")

    # Добавляем в интересы
    update_user_tags(user_id, tag, "like")
    await message.answer(f"Тег '{tag}' добавлен в список твоих интересов.", parse_mode=None)