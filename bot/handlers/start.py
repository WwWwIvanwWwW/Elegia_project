# bot/handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()

# Создаём клавиатуру
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📰 Получить дайджест")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="🔍 Поиск по тегу")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я NewsHive — ваш персональный дайджест новостей.\n"
        "Используйте команды или кнопки ниже:",
        reply_markup=main_menu
    )