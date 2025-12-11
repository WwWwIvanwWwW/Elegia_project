import requests
import json
import hashlib
from bs4 import BeautifulSoup
import logging
import time
import os
import feedparser  # Новая зависимость для парсинга RSS
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()  # Загрузить .env
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY не установлен")
DEEPSEEK_URL = "tngtech/deepseek-r1t-chimera:free"  # Пример URL, проверьте документацию

def extract_news_with_llm(json_data):
    """
    Использует LLM для извлечения summary из новостей.
    Ограничение: обрабатываем только первые 50 новостей, чтобы не превышать токен-лимит.
    """
    # Ограничиваем до 50 элементов
    json_data = json_data[:1]
    
    prompt = f"""
    Ты - помощник для анализа новостей. Вот список новостей в формате JSON: {json.dumps(json_data, ensure_ascii=False)}.
    Для каждой новости добавь поле "summary" с кратким описанием (1-2 предложения) на основе заголовка и URL (если нужно, сделай запрос к URL для деталей).
    Верни результат в виде валидного JSON-массива, без лишнего текста. Если не хватает места, обработай только первые 20 новостей.
    """
    
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'tngtech/deepseek-r1t2-chimera:free',  # Бесплатный вариант DeepSeek через OpenRouter
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 1000
    }
    
    try:
        response = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        content = response.json()["choices"][0]["message"]["content"]
        
        # Попытка распарсить JSON
        updated_news = json.loads(content)
        logger.debug(f"LLM успешно вернул {len(updated_news)} новостей с summary.")
        return updated_news
    except json.JSONDecodeError as e:
        logger.error(f"Не удалось распарсить JSON от LLM: {e}. Содержимое: {content[:500]}...")
        # Fallback: вернуть оригинальные данные без изменений
        return json_data
    except Exception as e:
        logger.error(f"Ошибка при вызове LLM: {e}")
        return json_data

def extract_news_with_beautifulsoup(url):
    """
    Fallback: парсит новости с главной страницы Lenta.ru с помощью BeautifulSoup.
    Обновлены селекторы на основе типичных классов (адаптируйте под реальную страницу).
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Обновленные селекторы (проверьте вручную на lenta.ru)
        # Пример: ищем заголовки и тексты в карточках новостей
        titles = soup.find_all('h3', class_=lambda x: x and 'card' in x and 'title' in x)  # Частичный поиск для гибкости
        texts = soup.find_all('div', class_=lambda x: x and 'card' in x and 'text' in x)
        
        logger.debug(f"Найдено {len(titles)} заголовков и {len(texts)} текстов.")
        
        news_list = []
        for i in range(min(len(titles), len(texts))):
            title = titles[i].get_text(strip=True)
            text = texts[i].get_text(strip=True)
            news_list.append({
                "title": title,
                "summary": text[:200] + "..." if len(text) > 200 else text,  # Краткое summary
                "url": ""  # URL не извлекаем, но можно добавить
            })
        
        logger.debug(f"Извлечено {len(news_list)} новостей с помощью BeautifulSoup.")
        return news_list
    except Exception as e:
        logger.error(f"Ошибка при парсинге с BeautifulSoup: {e}")
        return []

def parse_news_agent():
    """
    Основная функция: парсит RSS, пытается использовать LLM для summary, fallback на BS.
    """
    rss_url = "https://lenta.ru/rss/news"
    lenta_url = "https://lenta.ru/"
    
    # Парсинг RSS
    feed = feedparser.parse(rss_url)
    if feed.bozo:  # Проверка на ошибки
        logger.error("Ошибка парсинга RSS.")
        return []
    
    json_data = []
    for entry in feed.entries:
        json_data.append({
            "title": entry.title,
            "url": entry.link,
            "summary": ""  # Пустое, чтобы LLM заполнил
        })
    
    logger.debug(f"Из RSS извлечено {len(json_data)} новостей.")
    
    # Попытка с LLM
    updated_news = extract_news_with_llm(json_data)
    
    # Если LLM не сработал или вернул мало данных, fallback на BS
    if not updated_news:  # or len(updated_news) < 10
        logger.info("Переход к fallback с BeautifulSoup.")
        time.sleep(1)  # Задержка перед повтором
        bs_news = extract_news_with_beautifulsoup(lenta_url)
        if bs_news:
            updated_news = bs_news
    
    logger.debug(f"Итоговый результат: {len(updated_news)} новостей.")
    return updated_news

if __name__ == "__main__":
    news = parse_news_agent()
    print(json.dumps(news, ensure_ascii=False, indent=4))

