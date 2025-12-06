import aiohttp
import os
from bot.config import Config

PROMPTS_DIR = "data/prompts"

async def call_llm(prompt: str, model: str = Config.OPENROUTER_MODEL) -> str:
    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/yourname/news_hive",
        "X-Title": "NewsHive Bot",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(Config.OPENROUTER_URL, headers=headers, json=payload) as resp:
            if resp.status != 200:
                raise Exception(f"LLM error: {await resp.text()}")
            data = await resp.json()
            return data["choices"][0]["message"]["content"].strip()

def load_prompt(agent_name: str) -> str:
    path = os.path.join(PROMPTS_DIR, f"{agent_name}_prompt.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
