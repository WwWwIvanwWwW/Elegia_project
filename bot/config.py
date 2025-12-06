import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = "tngtech/deepseek-r1t-chimera:free"
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
