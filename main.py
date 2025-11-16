#скачай pip install aiosqlite aiohttp
import aiohttp
import asyncio
import aiosqlite
import os

# === Настройки ===
OPENROUTER_API_KEY = "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"
OPENROUTER_API_KEY2 = "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" #Это твой бот, используй его
DB_PATH = "news.db"

# === Инициализация БД ===
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL UNIQUE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news_tags (
                news_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY(news_id) REFERENCES news(id) ON DELETE CASCADE,
                FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                UNIQUE(news_id, tag_id)
            )
        """)
        await db.commit()

# === Работа с OpenRouter ===
async def ask_openrouter(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 120
    }

async def ask_openrouter2(prompt: str) -> str: #Твой LLM агент
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY2}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "google/gemma-3-27b-it:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    err_text = await response.text()
                    print(f"❌ Ошибка OpenRouter: {response.status} – {err_text}")
                    return ""
        except Exception as e:
            print(f"⚠️ Ошибка сети: {e}")
            return ""

# === Добавление новости ===
async def add_news(news_text: str):
    prompt = (
        "Ты — система, генерирующая ключевые тэги для новостей. "
        "Проанализируй текст новости и верни максимум 5 коротких тегов на русском, "
        "в нижнем регистре, без пробелов (используй _ вместо пробелов), "
        "только существительные или устойчивые словосочетания, универсальные, "
        "разделённые запятыми, без пояснений. "
        "Если тег содержит недопустимые символы — убери их.\n\n"
        f"Текст: {news_text}"
    )
    tags_text = await ask_openrouter(prompt)
    if not tags_text:
        tags = ["прочее"]
    else:
        tags = [
            t.strip().lower().replace(" ", "_")
            for t in tags_text.split(",") if t.strip()
        ]
        tags = [t for t in tags if t.replace("_", "").isalnum()]
        if not tags:
            tags = ["прочее"]

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO news (text) VALUES (?)",
            (news_text,)
        )
        news_id = cursor.lastrowid
        if news_id == 0:
            async with db.execute("SELECT id FROM news WHERE text = ?", (news_text,)) as cur:
                row = await cur.fetchone()
                news_id = row[0]

        tag_ids = []
        for tag in tags:
            cur = await db.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                (tag,)
            )
            tag_id = cur.lastrowid
            if tag_id == 0:
                async with db.execute("SELECT id FROM tags WHERE name = ?", (tag,)) as cur2:
                    row = await cur2.fetchone()
                    tag_id = row[0]
            tag_ids.append(tag_id)

        for tid in tag_ids:
            await db.execute(
                "INSERT OR IGNORE INTO news_tags (news_id, tag_id) VALUES (?, ?)",
                (news_id, tid)
            )
        await db.commit()

    print(f"✅ Новость сохранена с тегами: {', '.join(tags)}")

# === Удаление одной новости по ID ===
async def delete_news_by_id(news_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Сначала проверим, существует ли новость
        async with db.execute("SELECT text FROM news WHERE id = ?", (news_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                print("❌ Новость с таким ID не найдена.")
                return
        # Удаление каскадом: записи из news_tags удалятся автоматически
        await db.execute("DELETE FROM news WHERE id = ?", (news_id,))
        await db.commit()
        print(f"✅ Новость ID={news_id} удалена.")

# === Удаление всех новостей и тегов ===
async def clear_all_data():
    confirm = input("⚠️ Вы уверены, что хотите удалить ВСЕ данные? Введите 'yes' для подтверждения: ").strip()
    if confirm.lower() != "yes":
        print("❌ Очистка отменена.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM news")  # каскадно удалятся и связи, и теги (если нет других ссылок)
        await db.execute("DELETE FROM sqlite_sequence WHERE name IN ('news', 'tags')")  # сброс ID
        await db.commit()
    print("✅ Вся база данных очищена.")

# === Показ всех новостей с ID (для админа) ===
async def show_all_news_with_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT n.id, n.text, GROUP_CONCAT(t.name, ', ') AS tag_list
            FROM news n
            LEFT JOIN news_tags nt ON n.id = nt.news_id
            LEFT JOIN tags t ON nt.tag_id = t.id
            GROUP BY n.id, n.text
            ORDER BY n.id
        """) as cursor:
            rows = await cursor.fetchall()

    if rows:
        print("\n📋 Все новости (для удаления):")
        for nid, text, tags in rows:
            tags_str = tags if tags else "без тегов"
            print(f"ID {nid}: {text}")
            print(f"    Теги: {tags_str}\n")
    else:
        print("📭 Новостей пока нет.")

# === Последние 5 новостей ===
async def show_last_5_news():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT n.text, GROUP_CONCAT(t.name, ', ') AS tag_list
            FROM news n
            LEFT JOIN news_tags nt ON n.id = nt.news_id
            LEFT JOIN tags t ON nt.tag_id = t.id
            GROUP BY n.id
            ORDER BY n.id DESC
            LIMIT 5
        """) as cursor:
            rows = await cursor.fetchall()

    if rows:
        print("\n🆕 Последние 5 новостей:")
        for i, (text, tags) in enumerate(rows, 1):
            tags_str = tags if tags else "без тегов"
            print(f"{i}. {text}")
            print(f"   Теги: {tags_str}\n")
    else:
        print("📭 Новостей пока нет.")

# === Поиск по тегу ===
async def search_by_tag(tag_query: str):
    tag_query = tag_query.strip().lower()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT n.text
            FROM news n
            JOIN news_tags nt ON n.id = nt.news_id
            JOIN tags t ON nt.tag_id = t.id
            WHERE t.name = ?
        """, (tag_query,)) as cursor:
            rows = await cursor.fetchall()

    if rows:
        print(f"\n🗞 Найдено {len(rows)} новостей по тегу '{tag_query}':")
        for i, (text,) in enumerate(rows, 1):
            print(f"{i}. {text}")
    else:
        print(f"❌ Новостей с тегом '{tag_query}' не найдено.")

# === Все теги ===
async def list_all_tags():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM tags ORDER BY name") as cursor:
            tags = [row[0] for row in await cursor.fetchall()]

    if tags:
        print("\n📦 Все теги:")
        for t in tags:
            print(f" - {t}")
    else:
        print("📭 Пока нет ни одной новости.")

# === Меню администратора ===
async def admin_menu():
    while True:
        print("\n" + "="*40)
        print("🔐 АДМИН-МЕНЮ:")
        print("1. Добавить новость")
        print("2. Удалить новость (по ID)")
        print("3. Удалить ВСЁ")
        print("4. Назад в главное меню")
        choice = input("Выберите действие (1–4): ").strip()

        if choice == "1":
            news = input("\nВведите текст новости:\n> ").strip()
            if news:
                await add_news(news)
            else:
                print("❌ Новость не может быть пустой.")
        elif choice == "2":
            await show_all_news_with_ids()
            try:
                nid = int(input("\nВведите ID новости для удаления: "))
                await delete_news_by_id(nid)
            except ValueError:
                print("❌ ID должен быть числом.")
        elif choice == "3":
            await clear_all_data()
        elif choice == "4":
            break
        else:
            print("⚠️ Неверный выбор.")

# === Главное меню ===
async def main():
    await init_db()
    while True:
        print("\n" + "="*40)
        print("📰 Меню:")
        print("1. Последние 5 новостей")
        print("2. Найти новости по тегу")
        print("3. Показать все теги")
        print("4. Выйти")
        user_input = input("Выберите действие (1–4): ").strip()

        if user_input.lower() == "admin":
            await admin_menu()
            continue

        if user_input == "1":
            await show_last_5_news()
        elif user_input == "2":
            tag = input("\nВведите тег для поиска:\n> ").strip()
            if tag.lower() == "admin":
                await admin_menu()
                continue
            if tag:
                await search_by_tag(tag)
            else:
                print("❌ Тег не может быть пустым.")
        elif user_input == "3":
            await list_all_tags()
        elif user_input == "4": #Завершение
            break
        else: #Это не нужно при создании бота-------------------------------------------------------------------------
            print("⚠️ Неверный выбор. Введите число от 1 до 4.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем.")