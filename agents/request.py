import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "tngtech/deepseek-r1t-chimera:free" # Убедитесь, что модель доступна

async def call_llm(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.1, # Меньше для более детерминированного вывода
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 429:
                    print(f"Ошибка API: {response.status} - Too Many Requests")
                    return "error"
                elif response.status != 200:
                    print(f"Ошибка API: {response.status}")
                    return "error"
                result = await response.json()
                return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Ошибка при вызове LLM: {e}")
        return "error"