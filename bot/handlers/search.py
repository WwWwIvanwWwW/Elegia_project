# bot/handlers/search.py
from aiogram import Router, types, F
from aiogram.filters import Command
from services.news_search import search_news_by_tag

router = Router()

@router.message(F.text == "🔍 Поиск по тегу")
async def btn_search(message: types.Message):
    await message.answer(
        "🔍 Отправьте команду вида:\n<code>/search военная_операция</code>\n\n"
        "Или просто напишите <code>/search</code>, чтобы увидеть подсказку.",
        parse_mode="HTML"
    )

@router.message(Command("search"))
async def cmd_search(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "🔍 Пример использования:\n<code>/search внешняя_политика</code>\n"
            "Теги состоят из слов через подчёркивание (_).",
            parse_mode="HTML"
        )
        return

    # Приводим ввод к нижнему регистру и заменяем пробелы
    raw_tag = parts[1].strip()
    tag = raw_tag.lower().replace(" ", "_")

    results = search_news_by_tag(tag, limit=3)

    if not results:
        await message.answer(f"Ничего не найдено по тегу «<code>{tag}</code>».", parse_mode="HTML")
        return

    for msg in results:
        await message.answer(msg, parse_mode="MarkdownV2")