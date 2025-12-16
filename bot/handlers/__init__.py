# Сначала импортируем команды (они должны обрабатываться ДО общего текста)
from .start import router as start_router
from .help import router as help_router
from .settings import router as settings_router
from .search import router as search_router
from .digest import router as digest_router

# И только потом — общий текст (если он в settings)
# Но лучше вынести общий текст в отдельный роутер или убедиться,
# что в settings.py команды зарегистрированы ДО общего хендлера