# agents/tags_agent.py
import json
import re
from agents.request import call_llm, load_prompt

with open("data/tags_taxonomy.json", "r", encoding="utf-8") as f:
    TAXONOMY = json.load(f)

def extract_first_json(text: str) -> dict:
    for pattern in [r"```json\s*({.*?})\s*```", r"```\s*({.*?})\s*```", r"({.*?})"]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    raise ValueError("No JSON")

async def run(text: str) -> dict:
    if not text or not text.strip():
        return {"category": "Прочее", "tags": ["без_тегов"]}
    
    prompt_template = load_prompt("tags")
    prompt = prompt_template % text
    response = await call_llm(prompt)

    try:
        result = extract_first_json(response)
    except ValueError:
        return {"category": "Новости", "tags": ["авто"]}

    # Нормализуем теги: пробелы → подчёркивания, убираем спецсимволы
    tags = []
    for tag in result.get("tags", ["без_тегов"]):
        if isinstance(tag, str):
            clean_tag = re.sub(r"[^\wа-яА-Я]", " ", tag)
            clean_tag = "_".join(clean_tag.lower().split())
            if clean_tag:
                tags.append(clean_tag)
        else:
            tags.append("тег")

    category = result.get("category", "Прочее")
    return {"category": category, "tags": tags[:5]}