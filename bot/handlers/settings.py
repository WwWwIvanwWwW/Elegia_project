# bot/handlers/settings.py
from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from services.user_profile import get_user_settings, save_user_settings
from .start import main_menu  # ← ДОБАВИЛИ ИМПОРТ main_menu

router = Router()

class Settings(StatesGroup):
    choosing_style = State()

@router.message(F.text == "⚙️ Настройки")
@router.message(F.text == "/settings")
async def cmd_settings(message: types.Message, state: FSMContext):
    settings = get_user_settings(message.from_user.id)
    current = settings.get("style", "brief")
    display = "Краткий" if current == "brief" else "Полный"
    await message.answer(
        f"Текущий стиль дайджеста: <b>{display}</b>\n\n"
        "Выберите новый стиль:",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Краткий")],
                [types.KeyboardButton(text="Полный")],
                [types.KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(Settings.choosing_style)

@router.message(Settings.choosing_style)
async def process_style(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    if user_input == "Краткий":
        style = "brief"
    elif user_input == "Полный":
        style = "full"
    elif user_input == "⬅️ Назад":
        await state.clear()
        await message.answer("Настройки закрыты.", reply_markup=main_menu)
        return
    else:
        await message.answer("Пожалуйста, выберите стиль с помощью кнопок.")
        return

    save_user_settings(message.from_user.id, {"style": style})
    display = "Краткий" if style == "brief" else "Полный"
    await message.answer(
        f"✅ Стиль дайджеста изменён на: <b>{display}</b>",
        parse_mode="HTML",
        reply_markup=main_menu
    )
    await state.clear()