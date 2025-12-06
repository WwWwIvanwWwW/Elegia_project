import asyncio
import logging
from aiogram import Bot, Dispatcher
from bot.config import Config
from database import init_db
from bot.handlers import start, digest, settings, search, help

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()

    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_routers(start.router, digest.router, settings.router, search.router, help.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
