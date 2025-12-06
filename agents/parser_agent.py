# agents/parser_agent.py
import json
import re
from agents.request import call_llm, load_prompt

def extract_first_json(text: str) -> dict:
    """Надёжно извлекает первый валидный JSON из любого текста (даже с вложенными объектами)."""
    # 1. Ищем JSON в Markdown-блоке: ```json {...} ``` или ```{...}```
    markdown_json = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
    if markdown_json:
        try:
            return json.loads(markdown_json.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Если не нашли — ищем "голый" JSON, балансируя фигурные скобки
    stack = []
    start = None
    for i, char in enumerate(text):
        if char == '{':
            if start is None:
                start = i
            stack.append(char)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack and start is not None:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        start = None
                        continue
    raise ValueError(f"Не удалось найти JSON в ответе parser_agent. Ответ: {text[:200]}...")

async def run(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        raw_text = "Новость без содержания"
    
    prompt_template = load_prompt("parser")
    prompt = prompt_template % raw_text
    response = await call_llm(prompt)

    try:
        result = extract_first_json(response)
    except ValueError:
        # Fallback: извлекаем заголовок и тело вручную
        lines = raw_text.strip().split('\n', 2)
        title = lines[0][:200] if lines else "Без заголовка"
        body = lines[1] if len(lines) > 1 else (lines[0] if lines else "")
        result = {
            "title": title,
            "body": body,
            "publication_date": None,
            "source_url": None
        }

    # Гарантируем, что все поля — строки
    result.setdefault("title", "")
    result.setdefault("body", "")
    if result["title"] is None:
        result["title"] = ""
    if result["body"] is None:
        result["body"] = ""

    return result