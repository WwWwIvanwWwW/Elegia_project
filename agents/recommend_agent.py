# agents/recommend_agent.py
from agents.request import call_llm, load_prompt

async def run(user_tags: list[str], article_tags: list[str]) -> bool:
    if not user_tags or not article_tags:
        return True
    user_tags_str = ", ".join(str(t) for t in user_tags)
    article_tags_str = ", ".join(str(t) for t in article_tags)
    prompt_template = load_prompt("recommend")
    prompt = prompt_template % (user_tags_str, article_tags_str)
    response = await call_llm(prompt)
    return "relevant" in response.lower()