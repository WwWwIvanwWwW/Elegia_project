# agents/summarizer_agent.py
from agents.request import call_llm, load_prompt
import json
import re

async def run(text: str) -> dict:
    if text is None:
        text = ""
    prompt_template = load_prompt("summarizer")
    prompt = prompt_template % text
    response = await call_llm(prompt)

    json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", response, re.DOTALL)
    if not json_match:
        json_match = re.search(r"({[^{}]*?})", response, re.DOTALL)

    if not json_match:
        # Возвращаем дефолт, если JSON не найден
        return {
            "brief": "Краткое содержание недоступно.",
            "full": text[:300] + "..." if len(text) > 300 else text,
            "points": ["Новость обработана автоматически."]
        }

    json_str = json_match.group(1)
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError:
        return {
            "brief": "Ошибка LLM: некорректный JSON.",
            "full": text[:200],
            "points": ["Не удалось сгенерировать пункты."]
        }

    result.setdefault("brief", "")
    result.setdefault("full", "")
    result.setdefault("points", [])
    return result