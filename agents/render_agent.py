# agents/render_agent.py
import json
from agents.request import call_llm, load_prompt

def escape_markdown(text: str) -> str:
    """Экранирует символы MarkdownV2, кроме # (мы его не используем)"""
    if not text:
        return ""
    escape_chars = "_*[]()~`>+=|{}.!-"
    for char in escape_chars:
        text = text.replace(char, "\\" + char)
    return text

async def run(news_dict: dict, style: str = "brief") -> str:
    title = news_dict.get("title", "").strip()
    brief = news_dict.get("brief", "").strip()
    full = news_dict.get("full", "").strip()
    points = news_dict.get("points", [])
    category = news_dict.get("category", "Новости")
    tags = news_dict.get("tags", [])

    # Проверка на ошибки в содержании
    if not title or any(err in brief.lower() for err in ["ошибка", "not provided", "please provide"]):
        return f"📰 *{escape_markdown(title) or 'Новость'}*\n\n❌ Контент недоступен."

    if style == "brief":
        return f"📰 *{escape_markdown(title)}*\n\n{escape_markdown(brief)}"

    else:  # full
        # Формируем пункты
        if isinstance(points, str):
            points_list = [p.strip() for p in points.split("\n") if p.strip()]
        else:
            points_list = [p.strip() for p in points if p]
        points_text = "\n".join(f"• {escape_markdown(p)}" for p in points_list)

        # Формируем теги БЕЗ #
        tags_text = ", ".join(escape_markdown(t) for t in tags if t)

        # Добавляем подсказку поиска, только если есть теги
        search_hint = ""
        if tags:
            search_hint = f"\n\n🔍 Нажмите: `/search {tags[0]}`"

        return (
            f"📰 *{escape_markdown(title)}*\n\n"
            f"{escape_markdown(brief)}\n\n"
            f"{points_text}\n\n"
            f"🏛️ Категория: {escape_markdown(category)}\n"
            f"🔖 Теги: {tags_text}"
            f"{search_hint}"
        ).strip()