import feedparser
import logging
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_main_content(html_content: str) -> str:
    """
    Извлекает основной текст статьи из HTML с помощью BeautifulSoup.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    # Удаляем script и style элементы
    for script in soup(["script", "style"]):
        script.decompose()
    # Пытаемся найти основной контент статьи
    # Обычно это <article>, <main> или <div> с классами вроде content, article, post
    main_content = soup.find('article') or \
                   soup.find('main') or \
                   soup.find('div', class_=lambda x: x and ('content' in x or 'article' in x or 'post' in x)) or \
                   soup.find('body')
    if main_content:
        # Извлекаем текст из найденного блока
        text = main_content.get_text(separator=' ')
    else:
        # Если не найдено, берем весь body
        body = soup.find('body')
        text = body.get_text(separator=' ') if body else soup.get_text(separator=' ')

    # Очищаем текст от лишних пробелов
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)

    return text

async def load_news_from_sources():
    sources = [
        {
            "name": "Лента.ру",
            "url": "https://lenta.ru/rss/",
            "type": "rss"
        }
    ]

    all_news = []
    for source in sources:
        if source["type"] == "rss":
            try:
                feed = feedparser.parse(source["url"])
                logger.info(f"RSS {source['name']}: загружено {len(feed.entries)} статей")
                for entry in feed.entries[:5]:  # Только первые 5
                    # Загружаем полный текст статьи по URL
                    article_text = "Текст недоступен"
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Accept-Encoding': 'gzip, deflate',
                            'Connection': 'keep-alive',
                        }
                        async with aiohttp.ClientSession() as session:
                            async with session.get(entry.get("link", "#"), headers=headers) as response:
                                if response.status == 200:
                                    html_content = await response.text()
                                    # Извлекаем только основной текст из HTML
                                    article_text = extract_main_content(html_content)
                                    logger.info(f"Загруженный основной текст для {entry.get('link', '#')}: длина {len(article_text)} символов, начало: {article_text[:500]}...")  # Логируем длину и начало основного текста
                                else:
                                    logger.warning(f"Не удалось получить статью по URL {entry.get('link', '#')}: статус {response.status}")
                    except Exception as e:
                        logger.error(f"Ошибка при загрузке статьи {entry.get('link', '#')}: {e}")

                    all_news.append({
                        "title": entry.get("title", "Без заголовка"),
                        "text": article_text,  # Теперь это полный текст статьи
                        "url": entry.get("link", "#"),
                        "published_at": entry.get("published", ""),
                        "source": source["name"]
                    })
            except Exception as e:
                logger.error(f"Ошибка при загрузке RSS {source['url']}: {e}")
    return all_news