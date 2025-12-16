import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from dotenv import load_dotenv
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# Импортируем роутеры НАПРЯМУЮ
from bot.handlers.start import router as start_router
from bot.handlers.help import router as help_router
from bot.handlers.settings import router as settings_router
from bot.handlers.search import router as search_router
from bot.handlers.digest import router as digest_router

# Регистрируем роутеры
dp.include_router(start_router)
dp.include_router(help_router)  
dp.include_router(search_router)
dp.include_router(digest_router)
dp.include_router(settings_router)
# Инициализируем базу данных
from database.db import init_db
init_db()

async def main():
    print("Бот запущен...")
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="settings", description="Настройки"),
        BotCommand(command="search", description="Поиск новостей"),
        BotCommand(command="digest", description="Получить дайджест")
    ], scope=BotCommandScopeDefault())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())