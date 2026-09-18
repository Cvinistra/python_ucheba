import asyncio
import hashlib
import hmac
import html
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from urllib.parse import parse_qsl

sys.stdout.reconfigure(encoding="utf-8")

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InputMediaPhoto,
    FSInputFile,
    WebAppInfo,
    MenuButtonWebApp,
    MenuButtonDefault,
)

from aiohttp import web

from lessons_extra import LESSONS_EXTRA

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("python_academy")


# =========================================================
# КАРТИНКИ / ЛОГОТИПЫ
# =========================================================
#
# Для самых известных технологий берём настоящие, официальные логотипы
# (PNG высокого качества из github/explore) — они выглядят гораздо
# симпатичнее в карточке, чем сгенерированный текстовый бейдж.
# Для менее известных фреймворков/библиотек используем цветной
# бейдж с иконкой (shields.io) как аккуратный запасной вариант.

_GITHUB_TOPIC_LOGO = "https://raw.githubusercontent.com/github/explore/main/topics/{slug}/{slug}.png"


def topic_logo(slug: str) -> str:
    """Реальный логотип технологии из официальной подборки GitHub Topics."""
    return _GITHUB_TOPIC_LOGO.format(slug=slug)


def badge(label: str, color: str, icon: str = "") -> str:
    """
    Запасной вариант картинки — цветной бейдж (shields.io) с маленькой
    иконкой. Используется только там, где нет качественного логотипа.
    """
    text = label.replace("-", "--").replace(" ", "%20")
    params = "style=for-the-badge&logoColor=white"
    if icon:
        params += f"&logo={icon}"
    return f"https://img.shields.io/badge/{text}-{color}.png?{params}"


def photo(url: str) -> str:
    """Картинка передаётся прямой ссылкой (aiogram сам скачает её по URL)."""
    return url


# Псевдоним для обратной совместимости с картой FRAMEWORKS/LIBRARIES ниже.
logo = badge

PYTHON_LOGO = topic_logo("python")


def grid(buttons: list, columns: int = 2) -> list:
    """Раскладывает список кнопок по строкам (по умолчанию 2 в ряд)."""
    return [buttons[i:i + columns] for i in range(0, len(buttons), columns)]


# =========================================================
# НАСТРОЙКИ
# =========================================================
#
# ⚠️ ВАЖНО ПРО БЕЗОПАСНОСТЬ:
# Токен бота и ID администратора нужно передавать через переменные
# окружения, а не хранить прямо в коде. Если токен когда-либо
# попадал в открытый чат, файл или публичный репозиторий — его нужно
# считать скомпрометированным и обязательно перевыпустить (revoke)
# через @BotFather → выбрать бота → Bot Settings → Revoke current token.
#
# Как задать переменные окружения:
#   Linux/Mac:  export BOT_TOKEN="123:ABC"  export ADMIN_ID="123456789"
#   Windows:    set BOT_TOKEN=123:ABC       set ADMIN_ID=123456789
#   Или создать файл .env рядом с ботом и подключить python-dotenv.

TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not TOKEN:
    raise ValueError(
        "Не задан BOT_TOKEN. Установи переменную окружения BOT_TOKEN "
        "(см. комментарий выше) перед запуском бота."
    )

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Твой Telegram ID — только этому пользователю будут доступны команды
# /stats, /export и /send. Узнать свой ID можно командой /myid
# после запуска бота, затем задать переменную окружения ADMIN_ID.
ADMIN_ID = int(os.getenv("ADMIN_ID", "") or "0")


# =========================================================
# MINI APP (Telegram Web App)
# =========================================================
#
# MINIAPP_URL — публичный HTTPS-адрес, на котором лежит папка ./webapp
# (например https://mydomain.com/webapp/ или адрес, выданный хостингом).
# Пока переменная не задана, кнопки мини-приложения просто не показываются,
# а сам бот работает как раньше — на обычных инлайн-кнопках.
#
# Требования Telegram: адрес обязательно HTTPS (кроме localhost при
# тестировании через ngrok/аналоги — тогда достаточно https-туннеля).

MINIAPP_URL = os.getenv("MINIAPP_URL", "").strip()

# Локальный веб-сервер, который раздаёт файлы мини-приложения (./webapp)
# и принимает от него запросы (курс, прогресс, текущая вкладка).
WEBAPP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("PORT") or os.getenv("WEBAPP_PORT") or "10000")


# =========================================================
# БАЗА ДАННЫХ (SQLite, один файл academy.db рядом с ботом)
# =========================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academy.db")


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    # WAL заметно ускоряет одновременные чтение/запись у Telegram-бота
    # (несколько апдейтов могут обрабатываться "почти одновременно").
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    """Создаёт таблицы и индексы, если их ещё нет."""
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id         INTEGER PRIMARY KEY,
                username        TEXT,
                first_name      TEXT,
                first_seen      TEXT,
                last_seen       TEXT,
                current_tab     TEXT,   -- какая вкладка/экран открыта у пользователя сейчас
                current_tab_at  TEXT    -- когда он туда перешёл
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS views (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                kind        TEXT,   -- 'section' | 'topic' | 'framework' | 'library' | 'webapp' | 'menu'
                title       TEXT,   -- что именно открыл
                viewed_at   TEXT
            )
        """)
        # Индексы ускоряют /stats, /export и подсчёт прогресса — без них
        # SQLite делает полный перебор таблицы views на каждый запрос.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_views_user ON views(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_views_kind ON views(user_id, kind)")

        # --- Миграция для баз, созданных до появления колонок вкладки ---
        # (ALTER TABLE ADD COLUMN в SQLite не поддерживает IF NOT EXISTS,
        # поэтому проверяем список колонок вручную.)
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "current_tab" not in existing_cols:
            conn.execute("ALTER TABLE users ADD COLUMN current_tab TEXT")
        if "current_tab_at" not in existing_cols:
            conn.execute("ALTER TABLE users ADD COLUMN current_tab_at TEXT")

        conn.commit()


def _touch_user_sync(user_id: int, username: str, first_name: str) -> int:
    """Синхронная запись пользователя. Выполняется в отдельном потоке
    (см. touch_user), чтобы не блокировать event loop бота."""
    now = datetime.now().isoformat(timespec="seconds")
    with db_connect() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_seen=excluded.last_seen
        """, (user_id, username, first_name, now, now))
        conn.commit()
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


async def touch_user(user):
    """Добавляет пользователя в users или обновляет его последний визит."""
    try:
        total_users = await asyncio.to_thread(
            _touch_user_sync, user.id, user.username or "", user.first_name or ""
        )
        log.info(
            "👤 user_id=%s @%s (%s) | всего пользователей: %s",
            user.id, user.username or "—", user.first_name or "—", total_users,
        )
    except Exception:
        log.exception("Ошибка при записи пользователя в базу")


def _log_view_sync(user_id: int, kind: str, title: str) -> int:
    """Синхронная запись просмотра. Выполняется в отдельном потоке.

    Заодно обновляет current_tab прямо в строке пользователя — так в таблице
    users всегда видно, на какой "вкладке" (разделе/теме/фреймворке/...)
    он сейчас находится, без отдельного запроса к таблице views.
    """
    now = datetime.now().isoformat(timespec="seconds")
    tab_label = f"{kind}:{title}"
    with db_connect() as conn:
        # INSERT ... ON CONFLICT одновременно заводит пользователя (если
        # действие пришло раньше /start) и обновляет его текущую вкладку.
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, first_seen, last_seen, current_tab, current_tab_at)
            VALUES (?, '', '', ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_seen=excluded.last_seen,
                current_tab=excluded.current_tab,
                current_tab_at=excluded.current_tab_at
        """, (user_id, now, now, tab_label, now))

        conn.execute(
            "INSERT INTO views (user_id, kind, title, viewed_at) VALUES (?, ?, ?, ?)",
            (user_id, kind, title, now),
        )
        conn.commit()
        return conn.execute("SELECT COUNT(*) FROM views").fetchone()[0]


async def log_view(user_id: int, kind: str, title: str):
    """Записывает действие пользователя в views + обновляет его текущую вкладку."""
    try:
        total_views = await asyncio.to_thread(_log_view_sync, user_id, kind, title)
        log.info("👁 user_id=%s | %s: %s | всего просмотров: %s", user_id, kind, title, total_views)
    except Exception:
        log.exception("Ошибка при записи просмотра в базу")


def _touch_user_from_webapp_sync(user_id: int, username: str, first_name: str) -> int:
    """То же самое, что _touch_user_sync, но вызывается из веб-сервера
    мини-приложения (там нет объекта aiogram User, только сырые данные
    из initData)."""
    return _touch_user_sync(user_id, username, first_name)


async def touch_user_from_webapp(user_id: int, username: str, first_name: str):
    try:
        total_users = await asyncio.to_thread(
            _touch_user_from_webapp_sync, user_id, username or "", first_name or ""
        )
        log.info(
            "👤 (mini app) user_id=%s @%s (%s) | всего пользователей: %s",
            user_id, username or "—", first_name or "—", total_users,
        )
    except Exception:
        log.exception("Ошибка при записи пользователя мини-приложения в базу")


init_db()


# =========================================================
# КУРС PYTHON
# =========================================================

COURSE = {
    1: {
        "title": "🟢 Основы Python",
        "topics": [
            "Что такое Python",
            "Переменные",
            "Комментарии",
            "print()",
            "input()",
            "int / float",
            "str / bool",
            "type()"
        ]
    },

    2: {
        "title": "🔢 Операторы",
        "topics": [
            "Арифметические",
            "Сравнения",
            "Логические",
            "Присваивания",
            "in / not in",
            "is / is not",
            "Приоритет операторов"
        ]
    },

    3: {
        "title": "📦 Типы данных",
        "topics": [
            "int",
            "float",
            "str",
            "bool",
            "list",
            "tuple",
            "set",
            "dict",
            "None",
            "bytes"
        ]
    },

    4: {
        "title": "🔤 Строки",
        "topics": [
            "Создание строк",
            "Индексы",
            "Срезы",
            "len()",
            "upper()",
            "lower()",
            "strip()",
            "replace()",
            "split()",
            "join()",
            "find()",
            "count()",
            "startswith()",
            "endswith()",
            "f-строки"
        ]
    },

    5: {
        "title": "📋 Списки",
        "topics": [
            "Создание",
            "Индексы",
            "Срезы",
            "append()",
            "extend()",
            "insert()",
            "remove()",
            "pop()",
            "clear()",
            "index()",
            "count()",
            "sort()",
            "reverse()",
            "copy()",
            "list comprehension"
        ]
    },

    6: {
        "title": "📚 Кортежи",
        "topics": [
            "Создание",
            "Индексы",
            "Срезы",
            "count()",
            "index()",
            "Распаковка"
        ]
    },

    7: {
        "title": "🔵 Множества",
        "topics": [
            "set",
            "add()",
            "remove()",
            "discard()",
            "union()",
            "intersection()",
            "difference()",
            "frozenset"
        ]
    },

    8: {
        "title": "📖 Словари",
        "topics": [
            "Создание",
            "Ключи",
            "Значения",
            "items()",
            "keys()",
            "values()",
            "get()",
            "update()",
            "pop()",
            "dictionary comprehension"
        ]
    },

    9: {
        "title": "🔄 Циклы",
        "topics": [
            "for",
            "while",
            "range()",
            "for по списку",
            "for по строке",
            "for по словарю",
            "while True",
            "break",
            "continue",
            "else у цикла",
            "вложенные циклы"
        ]
    },

    10: {
        "title": "🔀 Условия",
        "topics": [
            "if",
            "elif",
            "else",
            "вложенные условия",
            "тернарный оператор",
            "match / case"
        ]
    },

    11: {
        "title": "🧩 Функции",
        "topics": [
            "def",
            "return",
            "параметры",
            "аргументы",
            "*args",
            "**kwargs",
            "значения по умолчанию",
            "keyword arguments",
            "lambda",
            "область видимости",
            "global",
            "nonlocal",
            "рекурсия"
        ]
    },

    12: {
        "title": "🧠 Comprehension",
        "topics": [
            "list comprehension",
            "dict comprehension",
            "set comprehension",
            "условия",
            "вложенные comprehension"
        ]
    },

    13: {
        "title": "⚠️ Ошибки и исключения",
        "topics": [
            "SyntaxError",
            "TypeError",
            "ValueError",
            "IndexError",
            "KeyError",
            "NameError",
            "try",
            "except",
            "else",
            "finally",
            "raise",
            "создание своих исключений"
        ]
    },

    14: {
        "title": "📁 Работа с файлами",
        "topics": [
            "open()",
            "read()",
            "readline()",
            "readlines()",
            "write()",
            "writelines()",
            "with",
            "txt",
            "JSON",
            "CSV"
        ]
    },

    15: {
        "title": "📦 Модули",
        "topics": [
            "import",
            "from ... import",
            "as",
            "math",
            "random",
            "datetime",
            "os",
            "sys",
            "pathlib",
            "создание своих модулей"
        ]
    },

    16: {
        "title": "🏗 ООП",
        "topics": [
            "Что такое класс",
            "class",
            "object",
            "__init__",
            "self",
            "атрибуты",
            "методы",
            "наследование",
            "super()",
            "полиморфизм",
            "инкапсуляция",
            "@property",
            "classmethod",
            "staticmethod",
            "dataclass",
            "магические методы"
        ]
    },

    17: {
        "title": "⚙️ Продвинутый Python",
        "topics": [
            "итераторы",
            "iter()",
            "next()",
            "генераторы",
            "yield",
            "декораторы",
            "замыкания",
            "map()",
            "filter()",
            "zip()",
            "enumerate()",
            "any()",
            "all()",
            "functools"
        ]
    },

    18: {
        "title": "🧵 Асинхронность",
        "topics": [
            "async",
            "await",
            "asyncio",
            "coroutine",
            "Task",
            "gather()",
            "sleep()",
            "Queue",
            "async context manager"
        ]
    },

    19: {
        "title": "💾 Базы данных",
        "topics": [
            "SQL",
            "SQLite",
            "sqlite3",
            "CREATE",
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "WHERE",
            "JOIN",
            "Python + SQLite"
        ]
    },

    20: {
        "title": "🌐 Интернет и API",
        "topics": [
            "HTTP",
            "GET",
            "POST",
            "JSON",
            "requests",
            "API",
            "REST API",
            "headers",
            "работа с API"
        ]
    },

    21: {
        "title": "🤖 Telegram-боты",
        "topics": [
            "aiogram",
            "Bot",
            "Dispatcher",
            "handlers",
            "Message",
            "CallbackQuery",
            "InlineKeyboard",
            "команды",
            "FSM",
            "состояния",
            "SQLite + бот",
            "API + бот"
        ]
    },

    22: {
        "title": "🖥 GUI",
        "topics": [
            "tkinter",
            "окна",
            "кнопки",
            "поля ввода",
            "события",
            "создание приложений"
        ]
    },

    23: {
        "title": "🎮 Игры",
        "topics": [
            "pygame",
            "игровой цикл",
            "движение",
            "столкновения",
            "изображения",
            "звук",
            "создание простой игры"
        ]
    },

    24: {
        "title": "🧪 Тестирование",
        "topics": [
            "unittest",
            "pytest",
            "assert",
            "тестирование функций",
            "фикстуры",
            "mock"
        ]
    },

    25: {
        "title": "📊 Работа с данными",
        "topics": [
            "NumPy",
            "Pandas",
            "Matplotlib",
            "таблицы",
            "DataFrame",
            "графики",
            "анализ данных"
        ]
    },

    26: {
        "title": "🌐 Веб-разработка",
        "topics": [
            "Flask",
            "FastAPI",
            "Django",
            "маршруты",
            "запросы",
            "шаблоны",
            "JSON API",
            "базы данных"
        ]
    },

    27: {
        "title": "📦 Установка пакетов",
        "topics": [
            "pip",
            "venv",
            "requirements.txt",
            "PyPI",
            "установка библиотек",
            "виртуальные окружения"
        ]
    },

    28: {
        "title": "💻 Git и GitHub",
        "topics": [
            "git init",
            "git add",
            "git commit",
            "git push",
            "git pull",
            "branches",
            "merge",
            "GitHub"
        ]
    },

    29: {
        "title": "🔐 Безопасность",
        "topics": [
            "токены",
            ".env",
            "переменные окружения",
            "пароли",
            "API keys",
            "основные ошибки безопасности"
        ]
    },

    30: {
        "title": "🚀 Проекты",
        "topics": [
            "Калькулятор",
            "Конвертер",
            "Игра",
            "Telegram-бот",
            "Бот с SQLite",
            "API",
            "Парсер",
            "Веб-приложение",
            "Большой проект"
        ]
    },

    31: {
        "title": "💰 Python и заработок",
        "topics": [
            "Фриланс",
            "Telegram-боты",
            "Парсеры",
            "Автоматизация",
            "Web-разработка",
            "Работа с API",
            "Портфолио",
            "GitHub"
        ]
    }
}


# Общее число тем в курсе — считается один раз при старте, а не на
# каждый вызов /progress.
TOTAL_TOPICS = sum(len(section["topics"]) for section in COURSE.values())


# =========================================================
# ФРЕЙМВОРКИ (14 шт, у каждого свой логотип-картинка)
# =========================================================

FRAMEWORKS = {
    'django': {
        "name": '🎸 Django',
        "logo": logo('Django', '092E20', 'django'),
        "url": 'https://www.djangoproject.com/',
        "desc": (
            'Django — самый популярный full-stack фреймворк для Python.\n\nИз коробки даёт ORM, админ-панель, систему аутентификации, маршрутизацию и шаблонизатор.\n\nХорош для крупных проектов: интернет-магазинов, CRM, соцсетей.\n\n<code>pip install django</code>'
        ),
        "commands": [
            ('django-admin startproject name', 'создать новый проект'),
            ('python manage.py runserver', 'запустить сервер разработки'),
            ('python manage.py migrate', 'применить миграции базы данных'),
            ('python manage.py createsuperuser', 'создать администратора'),
        ],
    },
    'flask': {
        "name": '🌶 Flask',
        "logo": logo('Flask', '000000', 'flask'),
        "url": 'https://flask.palletsprojects.com/',
        "desc": (
            'Flask — микрофреймворк: минимум встроенного функционала, максимум свободы.\n\nТы сам выбираешь, какие библиотеки подключать (ORM, авторизацию и т.д.).\n\nОтлично подходит для небольших сервисов и обучения.\n\n<code>pip install flask</code>'
        ),
        "commands": [
            ('@app.route("/")', 'привязать функцию к URL-адресу'),
            ('app.run(debug=True)', 'запустить сервер в режиме отладки'),
            ('render_template(...)', 'отрендерить HTML-шаблон'),
            ('request.form / request.args', 'получить данные из запроса'),
        ],
    },
    'fastapi': {
        "name": '⚡ FastAPI',
        "logo": logo('FastAPI', '009688', 'fastapi'),
        "url": 'https://fastapi.tiangolo.com/',
        "desc": (
            'FastAPI — современный асинхронный фреймворк для создания API.\n\nАвтоматически генерирует документацию (Swagger), валидирует данные через Pydantic и работает очень быстро.\n\nСтандарт для новых Python-бэкендов в 2024–2026.\n\n<code>pip install fastapi uvicorn</code>'
        ),
        "commands": [
            ('@app.get("/")', 'обработчик GET-запроса'),
            ('uvicorn main:app --reload', 'запустить сервер с автообновлением'),
            ('class X(BaseModel)', 'описать и провалидировать входные данные'),
            ('/docs', 'автоматическая Swagger-документация'),
        ],
    },
    'pyramid': {
        "name": '🏛 Pyramid',
        "logo": logo('Pyramid', 'C6E0F5'),
        "url": 'https://trypyramid.com/',
        "desc": (
            'Pyramid — гибкий фреймворк «золотой середины» между Flask и Django.\n\nМожно начать с малого проекта и постепенно наращивать функциональность без переписывания архитектуры.\n\n<code>pip install pyramid</code>'
        ),
        "commands": [
            ('config.add_route(...)', 'зарегистрировать маршрут'),
            ('config.add_view(...)', 'привязать view к маршруту'),
            ('pserve development.ini', 'запустить сервер разработки'),
        ],
    },
    'tornado': {
        "name": '🌪 Tornado',
        "logo": logo('Tornado', '2E5266'),
        "url": 'https://www.tornadoweb.org/',
        "desc": (
            'Tornado — асинхронный веб-фреймворк и сервер.\n\nУмеет держать тысячи одновременных соединений — хорош для чатов, long-polling и веб-сокетов.\n\n<code>pip install tornado</code>'
        ),
        "commands": [
            ('tornado.web.Application([...])', 'создать приложение с маршрутами'),
            ('IOLoop.current().start()', 'запустить событийный цикл'),
            ('def get(self) / def post(self)', 'обработка HTTP-методов'),
        ],
    },
    'aiohttp': {
        "name": '🔌 aiohttp',
        "logo": logo('aiohttp', '2C5BB4'),
        "url": 'https://docs.aiohttp.org/',
        "desc": (
            'aiohttp — библиотека-фреймворк для асинхронных HTTP-клиентов и серверов на базе asyncio.\n\nЧасто используется как сервер для Telegram-ботов и как клиент для запросов к внешним API.\n\n<code>pip install aiohttp</code>'
        ),
        "commands": [
            ('web.Application()', 'создать веб-приложение'),
            ('app.router.add_get(...)', 'зарегистрировать маршрут'),
            ('web.run_app(app)', 'запустить сервер'),
            ('ClientSession().get(url)', 'HTTP-клиент для запросов'),
        ],
    },
    'sanic': {
        "name": '🚀 Sanic',
        "logo": logo('Sanic', 'FF0D68'),
        "url": 'https://sanic.dev/',
        "desc": (
            'Sanic — async-фреймворк, спроектированный ради максимальной скорости.\n\nСинтаксис похож на Flask, но всё построено на async/await.\n\n<code>pip install sanic</code>'
        ),
        "commands": [
            ('Sanic("name")', 'создать приложение'),
            ('@app.route("/")', 'зарегистрировать маршрут'),
            ('app.run(host, port)', 'запустить сервер'),
        ],
    },
    'bottle': {
        "name": '🍾 Bottle',
        "logo": logo('Bottle', '4B8BBE'),
        "url": 'https://bottlepy.org/',
        "desc": (
            'Bottle — крошечный фреймворк из одного файла, без внешних зависимостей.\n\nИдеален для прототипов и обучения основам веб-разработки.\n\n<code>pip install bottle</code>'
        ),
        "commands": [
            ('@route("/")', 'зарегистрировать маршрут'),
            ('run(host=..., port=...)', 'запустить встроенный сервер'),
            ('request.query / request.forms', 'получить данные запроса'),
        ],
    },
    'cherrypy': {
        "name": '🍒 CherryPy',
        "logo": logo('CherryPy', 'A32638'),
        "url": 'https://cherrypy.dev/',
        "desc": (
            'CherryPy — объектно-ориентированный фреймворк: веб-приложение пишется как обычный Python-объект с методами-страницами.\n\n<code>pip install cherrypy</code>'
        ),
        "commands": [
            ('cherrypy.quickstart(Root())', 'быстрый запуск приложения'),
            ('@cherrypy.expose', 'сделать метод доступным как страницу'),
            ('cherrypy.config.update(...)', 'настроить сервер'),
        ],
    },
    'falcon': {
        "name": '🦅 Falcon',
        "logo": logo('Falcon', '593196'),
        "url": 'https://falconframework.org/',
        "desc": (
            'Falcon — минималистичный фреймворк специально для REST API с упором на скорость и низкие накладные расходы.\n\n<code>pip install falcon</code>'
        ),
        "commands": [
            ('falcon.App()', 'создать приложение'),
            ('resp.media = {...}', 'отправить JSON-ответ'),
            ('def on_get(self, req, resp)', 'обработчик GET-запроса'),
        ],
    },
    'aiogram': {
        "name": '🤖 aiogram',
        "logo": logo('aiogram', '2CA5E0', 'telegram'),
        "url": 'https://docs.aiogram.dev/',
        "desc": (
            'aiogram — асинхронная библиотека для Telegram-ботов на Python. Именно на ней написан этот бот.\n\nБыстрая, поддерживает FSM (состояния), middleware и фильтры.\n\n<code>pip install aiogram</code>'
        ),
        "commands": [
            ('Bot(token="...")', 'создать объект бота'),
            ('Dispatcher()', 'диспетчер, распределяющий апдейты по хендлерам'),
            ('@dp.message(...) / @dp.callback_query(...)', 'регистрация обработчиков'),
            ('dp.start_polling(bot)', 'запустить бота в режиме polling'),
        ],
    },
    'telebot': {
        "name": '📨 pyTelegramBotAPI',
        "logo": logo('pyTelegramBotAPI', '2CA5E0', 'telegram'),
        "url": 'https://pytba.readthedocs.io/',
        "desc": (
            'pyTelegramBotAPI (telebot) — одна из самых старых и простых библиотек для Telegram-ботов.\n\nСинхронная (без async/await) — отлично подходит для новичков.\n\n<code>pip install pytelegrambotapi</code>'
        ),
        "commands": [
            ('telebot.TeleBot("TOKEN")', 'создать бота'),
            ('@bot.message_handler(commands=["start"])', 'обработчик команды'),
            ('bot.send_message(chat_id, "text")', 'отправить сообщение'),
            ('bot.polling()', 'запустить бота'),
        ],
    },
    'ptb': {
        "name": '🐦 python-telegram-bot',
        "logo": logo('python--telegram--bot', '2CA5E0', 'telegram'),
        "url": 'https://docs.python-telegram-bot.org/',
        "desc": (
            'python-telegram-bot (PTB) — мощная и одна из старейших библиотек для Telegram-ботов.\n\nПоддерживает и синхронный, и асинхронный стиль работы.\n\n<code>pip install python-telegram-bot</code>'
        ),
        "commands": [
            ('Application.builder().token(...).build()', 'создать приложение'),
            ('CommandHandler("start", func)', 'обработка команд'),
            ('app.add_handler(...)', 'зарегистрировать хендлер'),
            ('app.run_polling()', 'запустить бота'),
        ],
    },
    'pyrogram': {
        "name": '✈️ Pyrogram',
        "logo": logo('Pyrogram', '2CA5E0', 'telegram'),
        "url": 'https://docs.pyrogram.org/',
        "desc": (
            'Pyrogram — современный асинхронный фреймворк, работающий напрямую через MTProto API.\n\nПоддерживает и ботов через Bot API, и обычные пользовательские аккаунты.\n\n<code>pip install pyrogram</code>'
        ),
        "commands": [
            ('Client("name", bot_token="...")', 'создать клиента'),
            ('@app.on_message(filters.command("start"))', 'обработчик команды'),
            ('app.run()', 'запустить клиента'),
            ('message.reply("text")', 'ответить на сообщение'),
        ],
    },
    'telethon': {
        "name": '📡 Telethon',
        "logo": logo('Telethon', '2CA5E0', 'telegram'),
        "url": 'https://docs.telethon.dev/',
        "desc": (
            'Telethon — асинхронная библиотека для работы с Telegram через MTProto.\n\nЧаще используется для юзер-ботов и автоматизации личного аккаунта, а не обычных ботов.\n\n<code>pip install telethon</code>'
        ),
        "commands": [
            ('TelegramClient("session", api_id, api_hash)', 'создать клиента'),
            ('client.start()', 'авторизация и запуск'),
            ('@client.on(events.NewMessage)', 'обработчик новых сообщений'),
            ('client.send_message(chat, "text")', 'отправить сообщение'),
        ],
    },
}


# =========================================================
# БИБЛИОТЕКИ (10 шт, у каждой свой логотип-картинка)
# =========================================================

LIBRARIES = {
    'numpy': {
        "name": '🔢 NumPy',
        "logo": logo('NumPy', '013243', 'numpy'),
        "url": 'https://numpy.org/',
        "desc": (
            'NumPy — базовая библиотека для численных вычислений.\n\nДаёт быстрые многомерные массивы (ndarray) и математические функции.\n\nФундамент почти всей экосистемы Data Science в Python.\n\n<code>pip install numpy</code>'
        ),
        "commands": [
            ('np.array([...])', 'создать массив'),
            ('np.zeros((n, m)) / np.ones(...)', 'массив из нулей/единиц'),
            ('array.reshape(...)', 'изменить форму массива'),
            ('np.dot(a, b)', 'умножение матриц'),
        ],
    },
    'pandas': {
        "name": '🐼 Pandas',
        "logo": logo('Pandas', '150458', 'pandas'),
        "url": 'https://pandas.pydata.org/',
        "desc": (
            'Pandas — работа с табличными данными: DataFrame и Series.\n\nЧтение CSV/Excel/SQL, фильтрация, группировка, сводные таблицы.\n\n<code>pip install pandas</code>'
        ),
        "commands": [
            ('pd.read_csv("file.csv")', 'прочитать CSV в DataFrame'),
            ('df.head() / df.describe()', 'просмотр и статистика данных'),
            ('df.groupby("col").mean()', 'группировка и агрегация'),
            ('df.to_excel("file.xlsx")', 'сохранить в Excel'),
        ],
    },
    'requests': {
        "name": '🌐 Requests',
        "logo": logo('Requests', '2C5BB4'),
        "url": 'https://requests.readthedocs.io/',
        "desc": (
            'Requests — самая удобная библиотека для HTTP-запросов в Python.\n\n<code>import requests\nr = requests.get("https://api.example.com")\nprint(r.json())</code>'
        ),
        "commands": [
            ('requests.get(url) / requests.post(url, data=...)', 'HTTP-запросы'),
            ('response.json()', 'разобрать JSON-ответ'),
            ('response.status_code', 'код ответа сервера'),
            ('requests.Session()', 'переиспользуемая сессия с настройками'),
        ],
    },
    'bs4': {
        "name": '🍜 BeautifulSoup',
        "logo": logo('BeautifulSoup', '4B8BBE'),
        "url": 'https://www.crummy.com/software/BeautifulSoup/',
        "desc": (
            'BeautifulSoup — парсинг HTML и XML страниц.\n\nЧасто используется вместе с requests для написания веб-парсеров.\n\n<code>pip install beautifulsoup4</code>'
        ),
        "commands": [
            ('BeautifulSoup(html, "html.parser")', 'распарсить HTML'),
            ('soup.find("div", class_="x")', 'найти один элемент'),
            ('soup.find_all("a")', 'найти все подходящие элементы'),
            ('tag.get("href")', 'получить атрибут тега'),
        ],
    },
    'matplotlib': {
        "name": '📈 Matplotlib',
        "logo": logo('Matplotlib', '11557C', 'python'),
        "url": 'https://matplotlib.org/',
        "desc": (
            'Matplotlib — построение графиков: линии, столбцы, гистограммы, диаграммы рассеяния.\n\nОснова для более высокоуровневых библиотек вроде Seaborn.\n\n<code>pip install matplotlib</code>'
        ),
        "commands": [
            ('plt.plot(x, y)', 'построить линейный график'),
            ('plt.bar / plt.hist / plt.scatter(...)', 'другие типы графиков'),
            ('plt.title / xlabel / ylabel(...)', 'подписи графика'),
            ('plt.savefig("file.png")', 'сохранить график в файл'),
        ],
    },
    'tensorflow': {
        "name": '🧠 TensorFlow',
        "logo": logo('TensorFlow', 'FF6F00', 'tensorflow'),
        "url": 'https://www.tensorflow.org/',
        "desc": (
            'TensorFlow — фреймворк от Google для машинного обучения и нейронных сетей промышленного масштаба.\n\n<code>pip install tensorflow</code>'
        ),
        "commands": [
            ('tf.constant(...) / tf.Variable(...)', 'создать тензор'),
            ('tf.keras.Sequential([...])', 'построить нейросеть слой за слоем'),
            ('model.compile(...) / model.fit(...)', 'настроить и обучить модель'),
            ('model.predict(...)', 'получить предсказание модели'),
        ],
    },
    'pytorch': {
        "name": '🔥 PyTorch',
        "logo": logo('PyTorch', 'EE4C2C', 'pytorch'),
        "url": 'https://pytorch.org/',
        "desc": (
            'PyTorch — библиотека для глубокого обучения от Meta, самая популярная в исследовательском сообществе.\n\n<code>pip install torch</code>'
        ),
        "commands": [
            ('torch.tensor([...])', 'создать тензор'),
            ('class Net(nn.Module)', 'описать архитектуру нейросети'),
            ('loss.backward()', 'обратное распространение ошибки'),
            ('optimizer.step()', 'обновить веса модели'),
        ],
    },
    'sqlalchemy': {
        "name": '🗄 SQLAlchemy',
        "logo": logo('SQLAlchemy', 'D71F00'),
        "url": 'https://www.sqlalchemy.org/',
        "desc": (
            'SQLAlchemy — ORM: позволяет работать с базами данных на Python-объектах вместо сырого SQL.\n\n<code>pip install sqlalchemy</code>'
        ),
        "commands": [
            ('create_engine("sqlite:///db.sqlite")', 'подключиться к базе данных'),
            ('Session()', 'открыть сессию для запросов'),
            ('session.query(Model).filter(...)', 'выборка данных'),
            ('session.add(obj) / session.commit()', 'сохранить изменения'),
        ],
    },
    'pytest': {
        "name": '✅ Pytest',
        "logo": logo('Pytest', '0A9EDC', 'pytest'),
        "url": 'https://docs.pytest.org/',
        "desc": (
            'Pytest — стандарт де-факто для тестирования Python-кода.\n\nПростой синтаксис assert, фикстуры, параметризация тестов.\n\n<code>pip install pytest</code>'
        ),
        "commands": [
            ('def test_x(): assert ...', 'обычная тест-функция'),
            ('pytest', 'запустить все тесты в проекте'),
            ('@pytest.fixture', 'подготовить данные для тестов'),
            ('@pytest.mark.parametrize', 'параметризация тестов'),
        ],
    },
    'selenium': {
        "name": '🕹 Selenium',
        "logo": logo('Selenium', '43B02A', 'selenium'),
        "url": 'https://www.selenium.dev/',
        "desc": (
            'Selenium — автоматизация браузера: клики, заполнение форм, тестирование сайтов и парсинг JS-страниц.\n\n<code>pip install selenium</code>'
        ),
        "commands": [
            ('webdriver.Chrome()', 'запустить браузер'),
            ('driver.get(url)', 'перейти по ссылке'),
            ('driver.find_element(By.ID, "x")', 'найти элемент на странице'),
            ('element.click() / element.send_keys("text")', 'взаимодействие с элементом'),
        ],
    },
}


# Там, где существует официальный красивый логотип (из подборки
# GitHub Topics), подменяем сгенерированный бейдж на настоящую
# картинку — карточки выглядят заметно приятнее.
_REAL_FRAMEWORK_LOGOS = {
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "aiogram": "telegram",
    "telebot": "telegram",
    "ptb": "telegram",
    "pyrogram": "telegram",
    "telethon": "telegram",
}
_REAL_LIBRARY_LOGOS = {
    "numpy": "numpy",
    "pandas": "pandas",
    "tensorflow": "tensorflow",
    "pytorch": "pytorch",
    "selenium": "selenium",
}

for _key, _slug in _REAL_FRAMEWORK_LOGOS.items():
    if _key in FRAMEWORKS:
        FRAMEWORKS[_key]["logo"] = topic_logo(_slug)

for _key, _slug in _REAL_LIBRARY_LOGOS.items():
    if _key in LIBRARIES:
        LIBRARIES[_key]["logo"] = topic_logo(_slug)


# =========================================================
# ГЛАВНОЕ МЕНЮ (кнопки по 2 в ряд)
# =========================================================

def main_menu():

    buttons = [
        InlineKeyboardButton(
            text=f"{number}. {section['title']}",
            callback_data=f"section_{number}"
        )
        for number, section in COURSE.items()
    ]

    rows = grid(buttons, 2)

    rows.append([
        InlineKeyboardButton(text="🧩 Фреймворки", callback_data="frameworks"),
        InlineKeyboardButton(text="📚 Библиотеки", callback_data="libraries"),
    ])
    rows.append([
        InlineKeyboardButton(text="📊 Мой прогресс", callback_data="progress")
    ])

    # Кнопка мини-приложения показывается только если задан MINIAPP_URL.
    if MINIAPP_URL:
        rows.append([
            InlineKeyboardButton(
                text="🚀 Открыть Mini App",
                web_app=WebAppInfo(url=MINIAPP_URL),
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# =========================================================
# МЕНЮ РАЗДЕЛА (темы по 2 в ряд)
# =========================================================

def section_menu(section_number):

    topics = COURSE[section_number]["topics"]

    buttons = [
        InlineKeyboardButton(
            text=f"📖 {index + 1}. {topic}",
            callback_data=f"topic_{section_number}_{index}"
        )
        for index, topic in enumerate(topics)
    ]

    rows = grid(buttons, 2)
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад к курсу", callback_data="course")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# =========================================================
# МЕНЮ «ФРЕЙМВОРКИ» И «БИБЛИОТЕКИ» (по 2 в ряд)
# =========================================================

def frameworks_menu():
    buttons = [
        InlineKeyboardButton(text=data["name"], callback_data=f"framework_{key}")
        for key, data in FRAMEWORKS.items()
    ]
    rows = grid(buttons, 2)
    rows.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="course")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def libraries_menu():
    buttons = [
        InlineKeyboardButton(text=data["name"], callback_data=f"library_{key}")
        for key, data in LIBRARIES.items()
    ]
    rows = grid(buttons, 2)
    rows.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="course")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def commands_block(commands: list) -> str:
    """Форматирует список (команда, описание) в HTML-блок для карточки."""
    if not commands:
        return ""
    lines = ["\n\n🧭 <b>Основные команды:</b>"]
    for cmd, desc in commands:
        lines.append(f"• <code>{html.escape(cmd)}</code> — {desc}")
    return "\n".join(lines)


def item_caption(data: dict) -> str:
    """Собирает полный текст карточки: название + описание + команды."""
    return f"<b>{data['name']}</b>\n\n{data['desc']}{commands_block(data.get('commands', []))}"


def item_back_kb(back_to: str, url: str | None = None):
    """Клавиатура карточки фреймворка/библиотеки: ссылка на сайт (если есть) + назад + в меню."""
    rows = []
    if url:
        rows.append([InlineKeyboardButton(text="🔗 Официальный сайт", url=url)])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="course"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# =========================================================
# /START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):
    await touch_user(message.from_user)
    # После /start пользователь находится на главном экране курса.
    await log_view(message.from_user.id, "menu", "course")

    await message.answer_photo(
        photo=PYTHON_LOGO,
        caption=(
            "🐍 <b>PYTHON ACADEMY</b>\n\n"
            "Добро пожаловать в самый полный курс Python прямо в Telegram!\n\n"
            f"📚 {len(COURSE)} разделов и {TOTAL_TOPICS} тем — от самых основ "
            "до Telegram-ботов, асинхронности, API, баз данных, GUI, "
            "игр на pygame и Data Science.\n\n"
            f"🧩 Витрина из {len(FRAMEWORKS)} фреймворков и {len(LIBRARIES)} "
            "библиотек с описаниями, логотипами и основными командами.\n\n"
            "📊 Бот запоминает твой прогресс — загляни в «Мой прогресс», "
            "чтобы увидеть, сколько тем уже пройдено.\n\n"
            "🚀 Выбирай раздел и начинай обучение!"
        ),
        reply_markup=main_menu(),
    )


# =========================================================
# КНОПКА "КУРС"
# =========================================================

@dp.callback_query(F.data == "course")
async def course(callback: CallbackQuery):
    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "menu", "course")

    # edit_media на случай, если до этого была открыта карточка
    # фреймворка/библиотеки с другой картинкой — возвращаем лого Python.
    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=PYTHON_LOGO,
            caption="📚 <b>КУРС PYTHON</b>\n\nВыбери раздел:",
            parse_mode="HTML",
        ),
        reply_markup=main_menu(),
    )

    await callback.answer()


# =========================================================
# ОТКРЫТИЕ РАЗДЕЛА
# =========================================================

@dp.callback_query(F.data.startswith("section_"))
async def open_section(callback: CallbackQuery):

    try:
        section_number = int(callback.data.split("_")[1])
        section = COURSE[section_number]
    except (ValueError, KeyError, IndexError):
        await callback.answer("Раздел не найден", show_alert=True)
        return

    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "section", f"{section_number}. {section['title']}")

    await callback.message.edit_caption(
        caption=(
            f"<b>{section_number}. {section['title']}</b>\n\n"
            "Выбери тему:"
        ),
        reply_markup=section_menu(section_number),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ОТКРЫТИЕ ТЕМЫ
# =========================================================

@dp.callback_query(F.data.startswith("topic_"))
async def open_topic(callback: CallbackQuery):

    parts = callback.data.split("_")

    try:
        section_number = int(parts[1])
        topic_index = int(parts[2])
        section = COURSE[section_number]
        topic = section["topics"][topic_index]
    except (ValueError, KeyError, IndexError):
        await callback.answer("Тема не найдена", show_alert=True)
        return

    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "topic", topic)

    text = get_topic_text(section_number, topic)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К темам",
                    callback_data=f"section_{section_number}"
                ),
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="course"
                ),
            ]
        ]
    )

    await callback.message.edit_caption(
        caption=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ФРЕЙМВОРКИ — витрина
# =========================================================

@dp.callback_query(F.data == "frameworks")
async def show_frameworks(callback: CallbackQuery):
    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "menu", "frameworks")
    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=PYTHON_LOGO,
            caption=(
                "🧩 <b>Фреймворки Python</b>\n\n"
                "Выбери фреймворк, чтобы увидеть его логотип и подробное описание:"
            ),
            parse_mode="HTML",
        ),
        reply_markup=frameworks_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("framework_"))
async def open_framework(callback: CallbackQuery):
    key = callback.data.split("_", 1)[1]
    data = FRAMEWORKS.get(key)

    if not data:
        await callback.answer("Фреймворк не найден", show_alert=True)
        return

    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "framework", data["name"])

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=photo(data["logo"]),
            caption=item_caption(data),
            parse_mode="HTML",
        ),
        reply_markup=item_back_kb("frameworks", data.get("url")),
    )
    await callback.answer()


# =========================================================
# БИБЛИОТЕКИ — витрина
# =========================================================

@dp.callback_query(F.data == "libraries")
async def show_libraries(callback: CallbackQuery):
    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "menu", "libraries")
    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=PYTHON_LOGO,
            caption=(
                "📚 <b>Библиотеки Python</b>\n\n"
                "Выбери библиотеку, чтобы увидеть её логотип и подробное описание:"
            ),
            parse_mode="HTML",
        ),
        reply_markup=libraries_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("library_"))
async def open_library(callback: CallbackQuery):
    key = callback.data.split("_", 1)[1]
    data = LIBRARIES.get(key)

    if not data:
        await callback.answer("Библиотека не найдена", show_alert=True)
        return

    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "library", data["name"])

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=photo(data["logo"]),
            caption=item_caption(data),
            parse_mode="HTML",
        ),
        reply_markup=item_back_kb("libraries", data.get("url")),
    )
    await callback.answer()


# =========================================================
# ПРОГРЕСС
# =========================================================

def _count_done_topics_sync(user_id: int) -> int:
    with db_connect() as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT title) FROM views WHERE user_id = ? AND kind = 'topic'",
            (user_id,),
        ).fetchone()[0]


def progress_bar(done: int, total: int, length: int = 10) -> str:
    """Рисует текстовый прогресс-бар из эмодзи, например ▓▓▓▓░░░░░░ 40%."""
    if total <= 0:
        return ""
    ratio = min(done / total, 1.0)
    filled = round(ratio * length)
    return "▓" * filled + "░" * (length - filled) + f" {round(ratio * 100)}%"


@dp.callback_query(F.data == "progress")
async def progress(callback: CallbackQuery):
    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "menu", "progress")

    done = await asyncio.to_thread(_count_done_topics_sync, callback.from_user.id)

    await callback.message.edit_caption(
        caption=(
            "📊 <b>ТВОЙ ПРОГРЕСС</b>\n\n"
            f"{progress_bar(done, TOTAL_TOPICS)}\n\n"
            f"🟢 Пройдено: <b>{done}</b> из {TOTAL_TOPICS} тем\n"
            f"📚 Разделов в курсе: {len(COURSE)}\n"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📚 К курсу",
                        callback_data="course"
                    )
                ]
            ]
        ),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# МОЙ TELEGRAM ID
# =========================================================

@dp.message(F.text == "/myid")
async def my_id(message: Message):
    await message.answer(
        f"🆔 Твой Telegram ID: <code>{message.from_user.id}</code>\n\n"
        "Вставь это число в переменную окружения ADMIN_ID, чтобы получить "
        "доступ к командам /stats, /export и /send.",
        parse_mode="HTML"
    )


# =========================================================
# АДМИН-КОМАНДЫ (только для ADMIN_ID)
#   /stats — статистика
#   /export — выгрузка БД
#   /send USER_ID текст — личное сообщение конкретному пользователю
# =========================================================

def _stats_sync():
    with db_connect() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_views = conn.execute("SELECT COUNT(*) FROM views").fetchone()[0]

        top_users = conn.execute("""
            SELECT u.user_id, u.username, u.first_name, COUNT(v.id) AS cnt
            FROM users u
            LEFT JOIN views v ON v.user_id = u.user_id
            GROUP BY u.user_id
            ORDER BY cnt DESC
            LIMIT 10
        """).fetchall()

        last_views = conn.execute("""
            SELECT u.first_name, u.username, v.kind, v.title, v.viewed_at
            FROM views v
            JOIN users u ON u.user_id = v.user_id
            ORDER BY v.id DESC
            LIMIT 15
        """).fetchall()

    return total_users, total_views, top_users, last_views


@dp.message(F.text == "/stats")
async def admin_stats(message: Message):
    if ADMIN_ID == 0 or message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У тебя нет прав администратора.")
        return

    total_users, total_views, top_users, last_views = await asyncio.to_thread(_stats_sync)

    text = (
        f"👥 <b>Пользователей всего:</b> {total_users}\n"
        f"👁 <b>Всего просмотров:</b> {total_views}\n\n"
        "<b>🏆 Топ-10 самых активных:</b>\n"
    )
    for user_id, username, first_name, cnt in top_users:
        uname = f"@{username}" if username else (first_name or str(user_id))
        text += f"• {uname} — {cnt}\n"

    text += "\n<b>🕓 Последние действия:</b>\n"
    for first_name, username, kind, title, viewed_at in last_views:
        uname = f"@{username}" if username else (first_name or "???")
        text += f"• {viewed_at} — {uname}: [{kind}] {title}\n"

    # Telegram режет сообщения длиннее 4096 символов
    await message.answer(text[:4000], parse_mode="HTML")


@dp.message(F.text.startswith("/send"))
async def admin_send_message(message: Message):
    """Админ: отправить личное сообщение конкретному пользователю по Telegram ID.

    Формат:
    /send USER_ID текст сообщения
    """
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await message.answer("⛔ У тебя нет прав администратора.")
        return

    parts = (message.text or "").split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "📨 <b>Отправка сообщения пользователю</b>\n\n"
            "Формат:\n"
            "<code>/send USER_ID текст сообщения</code>\n\n"
            "Пример:\n"
            "<code>/send 123456789 Привет! Это сообщение от администратора.</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ USER_ID должен быть числом.")
        return

    message_text = parts[2].strip()
    if not message_text:
        await message.answer("❌ Текст сообщения не может быть пустым.")
        return

    try:
        await bot.send_message(target_user_id, message_text)
    except Exception as exc:
        await message.answer(
            "❌ Не удалось отправить сообщение.\n\n"
            f"Причина: <code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )
        return

    await message.answer(
        "✅ Сообщение отправлено.\n"
        f"👤 Пользователь: <code>{target_user_id}</code>"
    )


@dp.message(F.text == "/export")
async def admin_export(message: Message):
    if ADMIN_ID == 0 or message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У тебя нет прав администратора.")
        return

    await message.answer_document(
        FSInputFile(DB_PATH),
        caption=(
            "📦 Файл базы данных academy.db.\n"
            "Открой его любым SQLite-просмотрщиком, например "
            "DB Browser for SQLite (бесплатно), чтобы удобно "
            "смотреть таблицы users и views."
        ),
    )


# =========================================================
# ТЕКСТ УРОКА
# =========================================================

def get_topic_text(section_number, topic):

    lessons = {

        "Что такое Python": (
            "🐍 <b>Что такое Python?</b>\n\n"
            "Python — популярный язык программирования "
            "с простым и понятным синтаксисом.\n\n"
            "На Python можно создавать:\n"
            "🤖 Telegram-ботов\n"
            "🌐 сайты и API\n"
            "🎮 игры\n"
            "📊 программы для анализа данных\n"
            "⚙️ автоматизацию\n\n"
            "<b>Пример:</b>\n\n"
            "<code>print(\"Привет, мир!\")</code>"
        ),

        "Переменные": (
            "📦 <b>Переменные</b>\n\n"
            "Переменная хранит некоторое значение.\n\n"
            "<code>name = \"Alex\"\n"
            "age = 14\n"
            "height = 1.75</code>\n\n"
            "Теперь Python знает, что:\n"
            "name → строка\n"
            "age → целое число\n"
            "height → дробное число."
        ),

        "print()": (
            "🖨 <b>print()</b>\n\n"
            "Функция print() выводит информацию "
            "на экран.\n\n"
            "<code>print(\"Привет!\")\n"
            "print(123)\n"
            "print(2 + 2)</code>\n\n"
            "Результат:\n"
            "<code>Привет!\n"
            "123\n"
            "4</code>"
        ),

        "input()": (
            "⌨️ <b>input()</b>\n\n"
            "input() позволяет получить текст "
            "от пользователя.\n\n"
            "<code>name = input(\"Как тебя зовут? \")\n"
            "print(\"Привет\", name)</code>"
        ),

        "int": (
            "🔢 <b>int</b>\n\n"
            "int — целое число.\n\n"
            "<code>age = 14\n"
            "number = 100\n\n"
            "print(type(age))</code>\n\n"
            "Результат:\n"
            "<code>&lt;class 'int'&gt;</code>"
        ),

        "float": (
            "🔢 <b>float</b>\n\n"
            "float используется для дробных чисел.\n\n"
            "<code>price = 19.99\n"
            "temperature = 36.6</code>"
        ),

        "str": (
            "🔤 <b>str</b>\n\n"
            "str — строковый тип данных.\n\n"
            "<code>name = \"Python\"\n"
            "message = \"Привет!\"</code>"
        ),

        "bool": (
            "✅ <b>bool</b>\n\n"
            "bool хранит одно из двух значений:\n\n"
            "<code>True</code>\n"
            "<code>False</code>\n\n"
            "Например:\n"
            "<code>is_admin = True</code>"
        ),

        "if": (
            "🔀 <b>Условие if</b>\n\n"
            "if позволяет выполнить код, если "
            "условие истинно.\n\n"
            "<code>age = 14\n\n"
            "if age >= 14:\n"
            "    print(\"Можно!\")</code>"
        ),

        "for": (
            "🔄 <b>Цикл for</b>\n\n"
            "for позволяет повторять код.\n\n"
            "<code>for i in range(5):\n"
            "    print(i)</code>\n\n"
            "Результат:\n"
            "<code>0\n"
            "1\n"
            "2\n"
            "3\n"
            "4</code>"
        ),

        "while": (
            "🔄 <b>Цикл while</b>\n\n"
            "while повторяет код, пока условие "
            "остаётся истинным.\n\n"
            "<code>number = 0\n\n"
            "while number &lt; 5:\n"
            "    print(number)\n"
            "    number += 1</code>"
        ),

        "def": (
            "🧩 <b>Функции</b>\n\n"
            "Функция создаётся с помощью def.\n\n"
            "<code>def hello():\n"
            "    print(\"Привет!\")\n\n"
            "hello()</code>"
        ),

        "return": (
            "↩️ <b>return</b>\n\n"
            "return возвращает результат функции.\n\n"
            "<code>def add(a, b):\n"
            "    return a + b\n\n"
            "result = add(2, 3)\n"
            "print(result)</code>\n\n"
            "Результат: <b>5</b>"
        ),

        "class": (
            "🏗 <b>Классы</b>\n\n"
            "Класс позволяет создавать собственные "
            "типы объектов.\n\n"
            "<code>class Player:\n"
            "    def __init__(self, name):\n"
            "        self.name = name\n\n"
            "player = Player(\"Alex\")</code>"
        ),

        "async": (
            "🧵 <b>Асинхронность</b>\n\n"
            "async используется для создания "
            "асинхронных функций.\n\n"
            "<code>async def hello():\n"
            "    print(\"Привет!\")</code>\n\n"
            "Вместе с async обычно используется await."
        ),

        "aiogram": (
            "🤖 <b>aiogram</b>\n\n"
            "aiogram — библиотека Python для создания "
            "Telegram-ботов.\n\n"
            "В этом курсе ты научишься работать с:\n"
            "• Bot\n"
            "• Dispatcher\n"
            "• Message\n"
            "• CallbackQuery\n"
            "• InlineKeyboard\n"
            "• FSM\n"
            "• SQLite\n\n"
            "И именно на aiogram сейчас работает "
            "этот бот."
        ),

        "SQLite": (
            "💾 <b>SQLite</b>\n\n"
            "SQLite — лёгкая база данных, "
            "которая хранится в одном файле.\n\n"
            "Её удобно использовать для Telegram-ботов.\n\n"
            "Например, можно хранить:\n"
            "👤 пользователей\n"
            "📚 прогресс обучения\n"
            "⭐ очки\n"
            "🏆 достижения"
        ),

        "API": (
            "🌐 <b>API</b>\n\n"
            "API позволяет одной программе "
            "взаимодействовать с другой.\n\n"
            "Например, Python-программа может "
            "получить данные от сервера через API.\n\n"
            "Часто данные передаются в формате JSON."
        ),

        "pip": (
            "📦 <b>pip</b>\n\n"
            "pip используется для установки "
            "Python-библиотек.\n\n"
            "Например:\n\n"
            "<code>pip install aiogram</code>\n\n"
            "После этого библиотеку можно "
            "использовать в программе."
        ),

        "git init": (
            "💻 <b>Git</b>\n\n"
            "Git помогает сохранять историю "
            "изменений проекта.\n\n"
            "Создание Git-репозитория:\n\n"
            "<code>git init</code>\n\n"
            "После этого проект можно загружать "
            "на GitHub."
        ),

        "Фриланс": (
            "💰 <b>Python и заработок</b>\n\n"
            "Python можно использовать для создания:\n\n"
            "🤖 Telegram-ботов\n"
            "⚙️ автоматизации\n"
            "🌐 сайтов\n"
            "🔌 API\n"
            "📊 обработки данных\n"
            "🕷 парсеров\n\n"
            "Для первых заказов особенно полезно "
            "собрать портфолио из нескольких проектов."
        )
    }

    if topic in lessons:
        return lessons[topic]

    if topic in LESSONS_EXTRA:
        return render_extra_lesson(topic, LESSONS_EXTRA[topic])

    # Подстраховка на случай, если в будущем в COURSE добавят тему,
    # для которой ещё не написан урок.
    return (
        f"📖 <b>{topic}</b>\n\n"
        f"Это тема из раздела №{section_number}.\n\n"
        "🚧 Полноценный урок для этой темы "
        "будет добавлен в следующей версии.\n\n"
        "Здесь будут:\n"
        "📚 теория\n"
        "💻 примеры кода\n"
        "🧠 объяснение\n"
        "✏️ практическое задание\n"
        "❓ мини-тест"
    )


def render_extra_lesson(topic: str, data: tuple) -> str:
    """Форматирует запись из LESSONS_EXTRA в единый красивый вид урока.

    Запись может состоять из 2-4 элементов (эмодзи, текст[, код[, результат]]) —
    код и результат необязательны для тем без наглядного примера.
    """
    emoji, explanation, *rest = data
    code = rest[0] if len(rest) > 0 else None
    output = rest[1] if len(rest) > 1 else None

    parts = [f"{emoji} <b>{html.escape(topic)}</b>\n\n{explanation}"]

    if code:
        parts.append(f"\n\n<code>{html.escape(code)}</code>")

    if output:
        parts.append(f"\n\n<b>Результат:</b>\n<code>{html.escape(output)}</code>")

    return "".join(parts)


# =========================================================
# /APP — быстрая ссылка на мини-приложение
# =========================================================

@dp.message(F.text == "/app")
async def open_app_command(message: Message):
    if not MINIAPP_URL:
        await message.answer(
            "🚧 Mini App пока не подключён.\n\n"
            "Администратору: задай переменную окружения MINIAPP_URL, "
            "указывающую на публичный https-адрес папки webapp/."
        )
        return

    await touch_user(message.from_user)
    await log_view(message.from_user.id, "webapp", "home")

    await message.answer(
        "🚀 Открой курс в мини-приложении — там удобнее листать разделы, "
        "фреймворки и библиотеки прямо внутри Telegram.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🚀 Открыть Mini App",
                    web_app=WebAppInfo(url=MINIAPP_URL),
                )
            ]]
        ),
    )


# =========================================================
# WEB APP: проверка подлинности initData
# =========================================================
#
# Мини-приложение при каждом запросе к нашему серверу передаёт initData —
# строку, которую Telegram подписывает своим ключом на основе токена бота.
# Проверка ниже — стандартная схема из документации Telegram
# (https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app),
# она нужна, чтобы никто не мог прислать серверу чужой user_id.

def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """Возвращает распарсенные поля initData, если подпись верна, иначе None."""
    if not init_data or not bot_token:
        return None
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(bot_token.encode(), b"WebAppData", hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    return parsed


def _extract_webapp_user(parsed: dict) -> dict | None:
    """Достаёт объект user из уже провалидированного initData."""
    raw_user = parsed.get("user")
    if not raw_user:
        return None
    try:
        return json.loads(raw_user)
    except (TypeError, ValueError):
        return None


# =========================================================
# WEB APP: HTTP API для файлов мини-приложения (./webapp)
# =========================================================
#
# Эндпоинты:
#   GET  /api/course            — структура курса/фреймворков/библиотек
#   GET  /api/lesson/{s}/{i}    — текст конкретного урока (готовый HTML)
#   POST /api/progress          — сколько тем уже пройдено (нужен initData)
#   POST /api/tab               — "я сейчас на вкладке X" (нужен initData);
#                                  именно этот эндпоинт пишет current_tab
#                                  в таблицу users рядом с пользователем.

def _cors(response: web.Response) -> web.Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


async def api_options(request: web.Request) -> web.Response:
    return _cors(web.Response())


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def api_course(request: web.Request) -> web.Response:
    payload = {
        "course": {
            str(number): {"title": section["title"], "topics": section["topics"]}
            for number, section in COURSE.items()
        },
        "frameworks": {
            key: {
                "name": data["name"],
                "logo": data["logo"],
                "url": data.get("url", ""),
                "desc": data["desc"],
            }
            for key, data in FRAMEWORKS.items()
        },
        "libraries": {
            key: {
                "name": data["name"],
                "logo": data["logo"],
                "url": data.get("url", ""),
                "desc": data["desc"],
            }
            for key, data in LIBRARIES.items()
        },
        "total_topics": TOTAL_TOPICS,
    }
    return _cors(web.json_response(payload))


async def api_lesson(request: web.Request) -> web.Response:
    try:
        section_number = int(request.match_info["section"])
        topic_index = int(request.match_info["index"])
        topic = COURSE[section_number]["topics"][topic_index]
    except (ValueError, KeyError, IndexError):
        return _cors(web.json_response({"error": "not found"}, status=404))

    text = get_topic_text(section_number, topic)
    return _cors(web.json_response({"topic": topic, "html": text}))


async def _read_webapp_user(request: web.Request) -> tuple[dict | None, dict]:
    """Общая часть для /api/progress и /api/tab: парсит тело запроса и
    проверяет initData. Возвращает (user_dict, body) или (None, body)."""
    try:
        body = await request.json()
    except Exception:
        return None, {}

    parsed = validate_init_data(body.get("initData", ""), TOKEN)
    if not parsed:
        return None, body

    user = _extract_webapp_user(parsed)
    return user, body


async def api_progress(request: web.Request) -> web.Response:
    user, _ = await _read_webapp_user(request)
    if not user or not user.get("id"):
        return _cors(web.json_response({"error": "invalid initData"}, status=401))

    user_id = user["id"]
    await touch_user_from_webapp(user_id, user.get("username", ""), user.get("first_name", ""))
    done = await asyncio.to_thread(_count_done_topics_sync, user_id)

    return _cors(web.json_response({"done": done, "total": TOTAL_TOPICS}))


async def api_tab(request: web.Request) -> web.Response:
    """Мини-приложение сообщает, какая вкладка сейчас открыта.

    Пишем это через тот же log_view(), которым пользуется сам бот —
    он одной записью обновляет и историю просмотров (views), и колонку
    current_tab прямо в строке пользователя (users)."""
    user, body = await _read_webapp_user(request)
    if not user or not user.get("id"):
        return _cors(web.json_response({"error": "invalid initData"}, status=401))

    user_id = user["id"]
    tab = str(body.get("tab", ""))[:200] or "unknown"

    await touch_user_from_webapp(user_id, user.get("username", ""), user.get("first_name", ""))
    await log_view(user_id, "webapp", tab)

    return _cors(web.json_response({"ok": True}))


def build_webapp() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/api/course", api_course)
    app.router.add_get("/api/lesson/{section}/{index}", api_lesson)
    app.router.add_post("/api/progress", api_progress)
    app.router.add_post("/api/tab", api_tab)
    for path in ("/api/course", "/api/lesson/{section}/{index}", "/api/progress", "/api/tab"):
        app.router.add_route("OPTIONS", path, api_options)

    if os.path.isdir(WEBAPP_DIR):
        # Доступны оба адреса: / и /webapp/. Это позволяет указать
        # MINIAPP_URL как https://domain/ или https://domain/webapp/.
        app.router.add_static("/webapp", WEBAPP_DIR, show_index=True)
        app.router.add_static("/", WEBAPP_DIR, show_index=True)
    else:
        log.warning(
            "Папка мини-приложения %s не найдена — статика отдаваться не будет "
            "(API всё равно работает).", WEBAPP_DIR,
        )

    return app


# =========================================================
# ЗАПУСК
# =========================================================

async def main():
    print("🐍 Python Academy запущен!")

    runner = None

    if MINIAPP_URL:
        app = build_webapp()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
        await site.start()
        log.info("🌐 Веб-сервер Mini App запущен: http://%s:%s (наружу отдавай через %s)",
                  WEBAPP_HOST, WEBAPP_PORT, MINIAPP_URL)

        # Кнопка "app" слева от поля ввода — открывает мини-приложение
        # для ВСЕХ пользователей бота (можно сузить через chat_id).
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="Курс", web_app=WebAppInfo(url=MINIAPP_URL))
            )
        except Exception:
            log.exception("Не удалось установить кнопку меню Mini App")
    else:
        log.info("MINIAPP_URL не задан — Mini App отключён, кнопки не показываются.")
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        except Exception:
            pass

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        if runner:
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())