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

TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")

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

def _parse_admin_ids() -> set[int]:
    ids = set()
    if ADMIN_ID:
        ids.add(ADMIN_ID)
    for raw in os.getenv("ADMIN_IDS", "").split(","):
        raw = raw.strip()
        if raw.isdigit():
            ids.add(int(raw))
    return ids

ADMIN_IDS = _parse_admin_ids()

def is_admin_user(user_id: int) -> bool:
    return int(user_id) in ADMIN_IDS


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

def normalize_miniapp_url(url: str) -> str:
    if not url:
        return ""
    clean = url.rstrip("/")
    sep = "&" if "?" in clean else "?"
    return clean + sep + "v=6" if clean.lower().endswith(".html") else clean + "/index.html?v=6"

MINIAPP_LAUNCH_URL = normalize_miniapp_url(MINIAPP_URL)

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quiz_id TEXT NOT NULL,
                option_index INTEGER NOT NULL,
                correct INTEGER NOT NULL,
                answered_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_user ON quiz_attempts(user_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_support_status ON support_messages(status, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_support_user ON support_messages(user_id)")

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
# МИНИ-КОДЫ — короткие готовые проекты
# =========================================================

MINI_CODES = {
    "calculator": {
        "title": "🧮 Калькулятор",
        "category": "Для новичка",
        "description": "Простой калькулятор: ввод двух чисел и выбор действия.",
        "code": "a = float(input(\"Первое число: \"))\noperator = input(\"Действие (+ - * /): \" )\nb = float(input(\"Второе число: \"))\n\nif operator == \"+\":\n    print(a + b)\nelif operator == \"-\":\n    print(a - b)\nelif operator == \"*\":\n    print(a * b)\nelif operator == \"/\":\n    if b == 0:\n        print(\"На ноль делить нельзя\")\n    else:\n        print(a / b)\nelse:\n    print(\"Неизвестное действие\")",
        "result": "Введи 5, затем +, затем 7 → 12",
    },
    "turtle_square": {
        "title": "🐢 Черепаха: квадрат",
        "category": "Turtle",
        "description": "Рисует квадрат с помощью библиотеки turtle.",
        "code": "import turtle\n\npen = turtle.Turtle()\nfor _ in range(4):\n    pen.forward(120)\n    pen.right(90)\n\nturtle.done()",
        "result": "Откроется окно с нарисованным квадратом.",
    },
    "turtle_spiral": {
        "title": "🐢 Черепаха: спираль",
        "category": "Turtle",
        "description": "Постепенно увеличивает длину шага и рисует геометрическую спираль.",
        "code": "import turtle\n\npen = turtle.Turtle()\nfor size in range(10, 180, 8):\n    pen.forward(size)\n    pen.right(91)\n\nturtle.done()",
        "result": "Откроется окно с геометрической спиралью.",
    },
    "guess_number": {
        "title": "🎯 Угадай число",
        "category": "Игра",
        "description": "Компьютер загадывает число от 1 до 100, а игрок пытается его угадать.",
        "code": "import random\n\nsecret = random.randint(1, 100)\n\nwhile True:\n    guess = int(input(\"Твоя догадка: \"))\n    if guess < secret:\n        print(\"Больше\")\n    elif guess > secret:\n        print(\"Меньше\")\n    else:\n        print(\"🎉 Угадал!\")\n        break",
        "result": "После каждой попытки программа подсказывает: больше или меньше.",
    },
    "dice": {
        "title": "🎲 Бросок кубика",
        "category": "Мини-игра",
        "description": "Показывает случайное число от 1 до 6.",
        "code": "import random\n\nroll = random.randint(1, 6)\nprint(f\"Выпало: {roll}\")",
        "result": "Например: Выпало: 4",
    },
    "todo": {
        "title": "✅ Мини To-Do",
        "category": "Списки",
        "description": "Маленький менеджер задач: добавить, посмотреть и удалить задачу.",
        "code": "tasks = []\n\nwhile True:\n    command = input(\"add/list/done/exit: \" ).strip()\n\n    if command == \"add\":\n        tasks.append(input(\"Задача: \"))\n    elif command == \"list\":\n        for i, task in enumerate(tasks, 1):\n            print(i, task)\n    elif command == \"done\":\n        index = int(input(\"Номер задачи: \")) - 1\n        if 0 <= index < len(tasks):\n            tasks.pop(index)\n    elif command == \"exit\":\n        break",
        "result": "Получается небольшой консольный менеджер задач.",
    },
}



# =========================================================
# КАТЕГОРИИ ФРЕЙМВОРКОВ / БИБЛИОТЕК
# =========================================================

FRAMEWORK_CATEGORIES = {
    "web": {"title": "🌐 Веб-разработка", "description": "Серверы, сайты, REST API и веб-приложения."},
    "telegram": {"title": "🤖 Telegram", "description": "Фреймворки и SDK для Telegram-ботов и клиентов."},
    "gui": {"title": "🖥 GUI / приложения", "description": "Десктопные и кроссплатформенные приложения."},
    "data": {"title": "📊 Data / Apps", "description": "Интерактивные приложения и интерфейсы для данных."},
}

FRAMEWORK_ITEM_CATEGORIES = {
    "django":"web", "flask":"web", "fastapi":"web", "pyramid":"web", "tornado":"web",
    "aiohttp":"web", "sanic":"web", "bottle":"web", "cherrypy":"web", "falcon":"web",
    "starlette":"web", "quart":"web", "litestar":"web", "reflex":"web",
    "aiogram":"telegram", "telebot":"telegram", "ptb":"telegram", "pyrogram":"telegram", "telethon":"telegram",
    "kivy":"gui", "streamlit":"data", "dash":"data",
}

# Дополняем существующую витрину новыми, устойчиво используемыми инструментами.
FRAMEWORKS.update({
    "starlette": {
        "name": "⭐ Starlette", "logo": topic_logo("starlette"), "url": "https://www.starlette.io/",
        "category": "web",
        "desc": "Лёгкий ASGI-инструментарий для асинхронных веб-приложений и API. Полезен для понимания middleware, маршрутов и ASGI.",
        "commands": [
            ("Route('/', endpoint=home)", "создать маршрут"),
            ("Middleware(...)", "подключить промежуточную обработку"),
            ("uvicorn main:app", "запустить ASGI-приложение"),
        ],
    },
    "quart": {
        "name": "🟣 Quart", "logo": badge("Quart", "5B3A8C", "quart"), "url": "https://quart.palletsprojects.com/",
        "category": "web",
        "desc": "Асинхронный веб-фреймворк с интерфейсом, похожим на Flask, для async/await-приложений.",
        "commands": [
            ("@app.get('/')", "создать GET-маршрут"),
            ("await request.get_json()", "прочитать JSON-запрос"),
            ("await app.run_task()", "запустить приложение в async-контексте"),
        ],
    },
    "litestar": {
        "name": "🪶 Litestar", "logo": badge("Litestar", "27AE60", "python"), "url": "https://litestar.dev/",
        "category": "web",
        "desc": "Современный ASGI-фреймворк для API и веб-приложений с типизацией и зависимостями.",
        "commands": [
            ("@get('/')", "описать GET-обработчик"),
            ("class Controller", "объединить связанные маршруты"),
            ("Litestar(route_handlers=[...])", "создать приложение"),
        ],
    },
    "reflex": {
        "name": "⚛️ Reflex", "logo": badge("Reflex", "3A3A3A", "react"), "url": "https://reflex.dev/",
        "category": "web",
        "desc": "Подход к созданию веб-интерфейсов на Python с состоянием приложения и компонентами.",
        "commands": [
            ("rx.app", "создать приложение"),
            ("rx.state.State", "описать состояние интерфейса"),
            ("rx.button(...) ", "добавить кнопку в UI"),
        ],
    },
    "kivy": {
        "name": "📱 Kivy", "logo": badge("Kivy", "4A90E2", "kivy"), "url": "https://kivy.org/",
        "category": "gui",
        "desc": "Кроссплатформенный Python-фреймворк для графических интерфейсов и приложений.",
        "commands": [
            ("class MyApp(App)", "создать приложение"),
            ("Label(text='Привет')", "создать текстовый элемент"),
            ("MyApp().run()", "запустить приложение"),
        ],
    },
    "streamlit": {
        "name": "📊 Streamlit", "logo": badge("Streamlit", "FF4B4B", "streamlit"), "url": "https://streamlit.io/",
        "category": "data",
        "desc": "Инструмент для быстрых интерактивных приложений и прототипов на Python, особенно удобных для данных.",
        "commands": [
            ("st.title('...')", "показать заголовок"),
            ("st.write(data)", "вывести данные или объект"),
            ("st.button('Запуск')", "создать кнопку"),
        ],
    },
    "dash": {
        "name": "📈 Dash", "logo": badge("Dash", "119DFF", "plotly"), "url": "https://dash.plotly.com/",
        "category": "data",
        "desc": "Фреймворк для интерактивных аналитических веб-приложений и дашбордов.",
        "commands": [
            ("dcc.Graph(figure=...)", "встроить график"),
            ("html.Div([...])", "создать блок интерфейса"),
            ("@callback(...) ", "связать ввод и обновление интерфейса"),
        ],
    },
})
for _key, _data in FRAMEWORKS.items():
    _data.setdefault("category", FRAMEWORK_ITEM_CATEGORIES.get(_key, "web"))

LIBRARY_CATEGORIES = {
    "web": {"title": "🌐 Интернет и парсинг", "description": "HTTP, HTML, API и автоматизация браузера."},
    "data": {"title": "📊 Данные и ML", "description": "Числа, таблицы, графики и машинное обучение."},
    "db": {"title": "🗄 Базы данных", "description": "ORM и работа с базами данных."},
    "testing": {"title": "🧪 Тестирование", "description": "Проверка программ и браузерная автоматизация."},
    "files": {"title": "📁 Файлы и изображения", "description": "Документы, изображения и удобный вывод."},
    "dev": {"title": "🛠 Инструменты разработчика", "description": "Валидация, переменные окружения, CLI и полезные инструменты."},
}

LIBRARY_ITEM_CATEGORIES = {
    "numpy":"data", "pandas":"data", "matplotlib":"data", "tensorflow":"data", "pytorch":"data",
    "requests":"web", "bs4":"web", "selenium":"testing", "sqlalchemy":"db", "pytest":"testing",
    "openpyxl":"files", "pillow":"files", "scipy":"data", "sklearn":"data", "pydantic":"dev",
    "python_dotenv":"dev", "rich":"dev", "typer":"dev", "lxml":"web",
}

LIBRARIES.update({
    "openpyxl": {
        "name":"📗 openpyxl", "logo":badge("openpyxl","2F6B3A","python"), "url":"https://openpyxl.readthedocs.io/",
        "category":"files", "desc":"Работа с книгами Excel .xlsx: чтение, создание таблиц, ячеек и листов.",
        "commands":[
            ("load_workbook('data.xlsx')", "открыть существующий Excel-файл"),
            ("Workbook()", "создать новую книгу"),
            ("ws['A1'] = 42", "записать значение в ячейку"),
        ],
    },
    "pillow": {
        "name":"🖼 Pillow", "logo":badge("Pillow","5A67D8","python"), "url":"https://pillow.readthedocs.io/",
        "category":"files", "desc":"Библиотека для открытия, изменения и сохранения изображений.",
        "commands":[
            ("Image.open('photo.png')", "открыть изображение"),
            ("img.resize((800, 600))", "изменить размер"),
            ("img.save('out.png')", "сохранить результат"),
        ],
    },
    "scipy": {
        "name":"🔬 SciPy", "logo":badge("SciPy","8CAAE6","scipy"), "url":"https://scipy.org/",
        "category":"data", "desc":"Набор научных алгоритмов поверх NumPy: оптимизация, статистика, обработка сигналов и многое другое.",
        "commands":[
            ("from scipy import stats", "подключить статистические инструменты"),
            ("stats.norm.pdf(x)", "вычислить плотность нормального распределения"),
            ("scipy.optimize...", "решать задачи оптимизации"),
        ],
    },
    "sklearn": {
        "name":"🤖 scikit-learn", "logo":badge("scikit-learn","F7931E","scikit-learn"), "url":"https://scikit-learn.org/",
        "category":"data", "desc":"Инструменты классического машинного обучения: модели, подготовка данных, метрики и пайплайны.",
        "commands":[
            ("train_test_split(X, y)", "разделить данные на обучение и проверку"),
            ("model.fit(X, y)", "обучить модель"),
            ("model.predict(X)", "получить прогноз"),
        ],
    },
    "pydantic": {
        "name":"✅ Pydantic", "logo":badge("Pydantic","E92063","pydantic"), "url":"https://docs.pydantic.dev/",
        "category":"dev", "desc":"Типизированная валидация и преобразование структурированных данных.",
        "commands":[
            ("class User(BaseModel)", "описать модель данных"),
            ("User.model_validate(data)", "проверить входные данные"),
            ("user.model_dump()", "получить обычный dict"),
        ],
    },
    "python_dotenv": {
        "name":"🔐 python-dotenv", "logo":badge("dotenv","4B5563","python"), "url":"https://pypi.org/project/python-dotenv/",
        "category":"dev", "desc":"Удобное чтение переменных окружения из локального .env-файла во время разработки.",
        "commands":[
            ("load_dotenv()", "загрузить переменные из .env"),
            ("os.getenv('BOT_TOKEN')", "получить переменную из окружения"),
        ],
    },
    "rich": {
        "name":"✨ Rich", "logo":badge("Rich","000000","python"), "url":"https://rich.readthedocs.io/",
        "category":"dev", "desc":"Красивый вывод в терминале: таблицы, прогресс-бары, подсветка и панели.",
        "commands":[
            ("console.print('[bold]Привет[/bold]')", "вывести форматированный текст"),
            ("Table()", "создать таблицу в терминале"),
            ("Progress()", "показать прогресс"),
        ],
    },
    "typer": {
        "name":"⌨️ Typer", "logo":badge("Typer","009688","python"), "url":"https://typer.tiangolo.com/",
        "category":"dev", "desc":"Создание командных утилит CLI с помощью обычных Python-функций и аннотаций.",
        "commands":[
            ("app = typer.Typer()", "создать CLI-приложение"),
            ("@app.command()", "добавить команду"),
            ("typer.run(main)", "запустить простую CLI-команду"),
        ],
    },
    "lxml": {
        "name":"🧱 lxml", "logo":badge("lxml","0B6E4F","python"), "url":"https://lxml.de/",
        "category":"web", "desc":"Быстрая работа с XML и HTML-деревьями.",
        "commands":[
            ("etree.fromstring(xml)", "разобрать XML"),
            ("xpath('//div')", "найти элементы через XPath"),
        ],
    },
})
for _key, _data in LIBRARIES.items():
    _data.setdefault("category", LIBRARY_ITEM_CATEGORIES.get(_key, "dev"))


def grouped_catalog(data: dict, category_map: dict) -> list[dict]:
    result = []
    for key, meta in category_map.items():
        items = []
        for item_key, item in data.items():
            if item.get("category") == key:
                items.append({"key": item_key, "name": item.get("name", item_key)})
        if items:
            result.append({"id": key, **meta, "items": items})
    return result


# =========================================================
# ПУТЬ ОБУЧЕНИЯ / ПРАКТИКА / ВИКТОРИНА
# =========================================================

LEARNING_PLAN = [
    {
        "id":"start", "title":"🌱 1. Старт: как мыслит Python", "level":"Начальный",
        "description":"Поймёшь, как Python выполняет программу, как запускать код, читать синтаксис и не бояться ошибок.",
        "modules":[
            {"title":"1. Знакомство с Python","topics":["Что такое Python","print()","Комментарии","Переменные"]},
            {"title":"2. Типы и значения","topics":["int / float","str / bool","type()","None","bytes"]},
            {"title":"3. Ввод и преобразования","topics":["input()","int / float","str / bool","type()"]},
        ],
        "tips":["Пиши каждый пример руками и меняй значения.","Перед запуском предположи результат — так ты тренируешь модель выполнения.","Читай ошибки снизу вверх: тип исключения и последняя строка обычно самые полезные подсказки."],
        "checkpoint":"После этапа ты должен уметь написать программу, которая принимает данные, преобразует их, вычисляет результат и выводит ответ."
    },
    {
        "id":"logic", "title":"🧠 2. Логика программ", "level":"Начальный",
        "description":"Научишься превращать условия из обычной речи в точные ветвления и повторения.",
        "modules":[
            {"title":"4. Условия","topics":["if","elif","else","вложенные условия","тернарный оператор","match / case"]},
            {"title":"5. Циклы","topics":["for","while","range()","break","continue","else у цикла","вложенные циклы"]},
            {"title":"6. Коллекции","topics":["list","tuple","set","dict","Индексы","Срезы","append()","get()"]},
        ],
        "tips":["Сначала сформулируй алгоритм словами, потом переводи его в код.","Для циклов всегда понимай: что меняется на каждой итерации и когда цикл остановится.","Учись выбирать структуру данных под задачу, а не запоминать методы по отдельности."],
        "checkpoint":"Ты готов идти дальше, когда можешь самостоятельно написать меню программы, перебрать коллекцию и обработать несколько сценариев."
    },
    {
        "id":"strings", "title":"🔤 3. Строки и работа с текстом", "level":"Начальный",
        "description":"Научишься чистить, искать, разбивать, форматировать и собирать строки.",
        "modules":[
            {"title":"7. Базовые операции","topics":["Создание строк","Индексы","Срезы","len()"]},
            {"title":"8. Методы строк","topics":["upper()","lower()","strip()","replace()","split()","join()","find()","count()"]},
            {"title":"9. Форматирование","topics":["f-строки","startswith()","endswith()"]},
        ],
        "tips":["Для текста постоянно проверяй, где пробелы и регистр.","Разделяй этапы: очистить → проверить → преобразовать → вывести.","Тренируйся на реальных строках: именах, CSV-строках, URL и сообщениях."],
        "checkpoint":"Сделай мини-парсер строки: очисти ввод, найди ключевые слова, посчитай совпадения и собери красивый результат."
    },
    {
        "id":"functions", "title":"🧩 4. Функции и декомпозиция", "level":"Начальный → Средний",
        "description":"Перестанешь писать программу одним большим блоком и научишься делить задачу на понятные функции.",
        "modules":[
            {"title":"10. Функции","topics":["def","return","параметры","аргументы","значения по умолчанию","keyword arguments"]},
            {"title":"11. Гибкие функции","topics":["*args","**kwargs","lambda"]},
            {"title":"12. Область видимости","topics":["область видимости","global","nonlocal","рекурсия"]},
        ],
        "tips":["Функция должна иметь ясную ответственность.","Возвращай результат через return, если его нужно использовать дальше.","Если функция стала слишком большой, раздели её на несколько маленьких функций."],
        "checkpoint":"Возьми любой старый проект и вынеси ввод, вычисления и вывод в разные функции."
    },
    {
        "id":"collections", "title":"🗃 5. Коллекции и структуры данных", "level":"Средний",
        "description":"Разберёшься, почему list, tuple, set и dict ведут себя по-разному и как выбирать подходящую структуру.",
        "modules":[
            {"title":"13. Списки и кортежи","topics":["list","tuple","Индексы","Срезы","append()","extend()","pop()","copy()"]},
            {"title":"14. Множества и словари","topics":["set","add()","union()","intersection()","dict","keys()","values()","items()","get()","update()"]},
            {"title":"15. Генерация данных","topics":["list comprehension","dict comprehension","set comprehension","вложенные comprehension"]},
        ],
        "tips":["Думай о доступе к данным: по позиции, по ключу или по уникальности элементов.","Не используй comprehension, если обычный цикл делает код понятнее.","Перед изменением вложенных структур проверяй, копия это или ссылка."],
        "checkpoint":"Сделай телефонную книгу на dict и отчёт по уникальным значениям через set."
    },
    {
        "id":"errors", "title":"🛡 6. Ошибки, отладка, файлы", "level":"Средний",
        "description":"Научишься превращать ошибки из препятствия в инструмент диагностики и сохранять данные между запусками.",
        "modules":[
            {"title":"16. Исключения","topics":["SyntaxError","TypeError","ValueError","IndexError","KeyError","try","except","finally","raise","создание своих исключений"]},
            {"title":"17. Файлы","topics":["open()","read()","readline()","readlines()","write()","writelines()","with"]},
            {"title":"18. Форматы","topics":["JSON","CSV"]},
        ],
        "tips":["Не скрывай исключения через голый except: обрабатывай ожидаемые случаи.","Для файлов используй with, чтобы ресурс закрывался автоматически.","Логируй контекст ошибки, а не только её текст."],
        "checkpoint":"Сделай CLI-заметки: добавление, просмотр и сохранение заметок в JSON."
    },
    {
        "id":"modules", "title":"📦 7. Модули, пакеты и окружение", "level":"Средний",
        "description":"Поймёшь, как превращать один файл в поддерживаемый проект и как управлять зависимостями.",
        "modules":[
            {"title":"19. Импорты","topics":["import","from ... import","as","создание своих модулей"]},
            {"title":"20. Стандартная библиотека","topics":["math","random","datetime","os","sys","pathlib"]},
            {"title":"21. Окружение проекта","topics":["pip","venv","requirements.txt","PyPI"]},
        ],
        "tips":["Создавай виртуальное окружение для каждого проекта.","requirements.txt должен отражать реальные зависимости проекта.","Не путай имя пакета на PyPI с именем модуля, который импортируется."],
        "checkpoint":"Собери маленький проект из нескольких .py-файлов и создай для него requirements.txt."
    },
    {
        "id":"oop", "title":"🏗 8. ООП и архитектура объектов", "level":"Средний",
        "description":"Разберёшься, когда нужны классы, как моделировать данные и поведение и как уменьшать связанность.",
        "modules":[
            {"title":"22. Основы ООП","topics":["Что такое класс","object","__init__","self","атрибуты","методы"]},
            {"title":"23. Переиспользование","topics":["наследование","super()","полиморфизм","инкапсуляция"]},
            {"title":"24. Продвинутые возможности","topics":["@property","classmethod","staticmethod","dataclass","магические методы"]},
        ],
        "tips":["Начинай проектирование с данных и сценариев использования, а не с классов.","Предпочитай простые объекты сложной иерархии наследования.","Проверяй инварианты объекта в одном понятном месте."],
        "checkpoint":"Сделай модель интернет-магазина: Product, Cart, Order и несколько операций над ними."
    },
    {
        "id":"advanced", "title":"⚡ 9. Продвинутый Python", "level":"Продвинутый",
        "description":"Поймёшь итераторы, генераторы, декораторы, замыкания и функциональные приёмы.",
        "modules":[
            {"title":"25. Итераторы и генераторы","topics":["итераторы","iter()","next()","генераторы","yield"]},
            {"title":"26. Функции высшего порядка","topics":["декораторы","замыкания","map()","filter()","zip()","enumerate()","any()","all()","functools"]},
            {"title":"27. Производительность","topics":["генераторы","кэширование","функциональные инструменты"]},
        ],
        "tips":["Изучай новые конструкции через маленькие эксперименты.","Не оптимизируй без измерения: сначала профилируй узкое место.","Старайся понимать, какой объект создаётся и когда он освобождается."],
        "checkpoint":"Напиши генератор обработки большого файла построчно без загрузки всего файла в память."
    },
    {
        "id":"async", "title":"🧵 10. Асинхронность", "level":"Продвинутый",
        "description":"Освоишь async/await и поймёшь, когда асинхронная архитектура ускоряет I/O-задачи.",
        "modules":[
            {"title":"28. Основы async","topics":["async","await","coroutine","asyncio","sleep()"]},
            {"title":"29. Конкурентный запуск","topics":["Task","gather()","Queue"]},
            {"title":"30. Асинхронный I/O","topics":["async context manager","aiohttp","HTTP API"]},
        ],
        "tips":["async не делает CPU-вычисления автоматически быстрее.","Для сетевых запросов и ожидания файлов/БД асинхронность может дать большой выигрыш.","Следи за тем, чтобы внутри async-кода случайно не блокировать event loop."],
        "checkpoint":"Сделай программу, которая одновременно запрашивает несколько API и собирает ответы."
    },
    {
        "id":"webdb", "title":"🌐 11. Web, HTTP, API и базы данных", "level":"Продвинутый",
        "description":"Соберёшь связку клиент → HTTP → сервер → бизнес-логика → база данных.",
        "modules":[
            {"title":"31. SQL и SQLite","topics":["SQL","sqlite3","CREATE","SELECT","INSERT","UPDATE","DELETE","WHERE","JOIN","Python + SQLite"]},
            {"title":"32. HTTP и REST","topics":["HTTP","GET","POST","JSON","requests","REST API","headers","работа с API"]},
            {"title":"33. Веб-фреймворки","topics":["Flask","FastAPI","Django","маршруты","запросы","шаблоны","JSON API","базы данных"]},
        ],
        "tips":["Понимай HTTP-метод, статус и тело ответа, прежде чем углубляться во фреймворк.","Данные от пользователя всегда валидируй.","SQL-запросы с пользовательским вводом делай параметризованными."],
        "checkpoint":"Сделай REST API для заметок с SQLite и отдельными маршрутами GET/POST."
    },
    {
        "id":"telegram", "title":"🤖 12. Telegram-боты и Mini Apps", "level":"Продвинутый",
        "description":"Научишься строить бота, который хранит состояние и связывается с веб-интерфейсом.",
        "modules":[
            {"title":"34. Архитектура бота","topics":["aiogram","Bot","Dispatcher","handlers","Message","CallbackQuery"]},
            {"title":"35. Интерфейс и состояние","topics":["InlineKeyboard","команды","FSM","состояния"]},
            {"title":"36. Mini App","topics":["SQLite + бот","API + бот","Telegram Web App","initData","current_tab"]},
        ],
        "tips":["Разделяй обработчики Telegram и бизнес-логику.","Храни только необходимое пользовательское состояние.","Mini App должен проверять данные Telegram на сервере."],
        "checkpoint":"Собери бота с меню, SQLite, Mini App и записью последнего экрана пользователя."
    },
    {
        "id":"quality", "title":"🧪 13. Тестирование и качество", "level":"Продвинутый",
        "description":"Перейдёшь от 'работает у меня' к коду, который можно уверенно изменять.",
        "modules":[
            {"title":"37. Тесты","topics":["unittest","pytest","assert","тестирование функций"]},
            {"title":"38. Изоляция","topics":["фикстуры","mock"]},
            {"title":"39. Чистота проекта","topics":["создание своих модулей","dataclass","typing-подход"]},
        ],
        "tips":["Сначала тестируй чистую бизнес-логику, потом интеграцию.","Хороший тест проверяет поведение, а не случайную реализацию.","После исправления бага полезно добавить тест, который не даст ему вернуться."],
        "checkpoint":"Покрой тестами калькулятор минимум на обычные случаи и ошибки."
    },
    {
        "id":"projects", "title":"🚀 14. Большие проекты и путь к профи", "level":"Профи",
        "description":"Соединяем Python, Git, базы, API и интерфейс в законченные приложения.",
        "modules":[
            {"title":"40. Проектирование","topics":["Калькулятор","Конвертер","Игра","Telegram-бот","Бот с SQLite","API","Парсер","Веб-приложение"]},
            {"title":"41. Git и GitHub","topics":["git init","git add","git commit","git push","git pull","branches","merge","GitHub"]},
            {"title":"42. Портфолио","topics":["README","структура проекта","requirements.txt","деплой","демо"]},
        ],
        "tips":["Заканчивай маленькие проекты до перехода к огромным.","Коммить изменения небольшими логичными шагами.","Каждый проект должен отвечать на вопрос: какую проблему он решает?"],
        "checkpoint":"Собери один законченный проект и оформи его README, установку, запуск и примеры работы."
    },
]

PRACTICE_TASKS = [{'id': 't1', 'title': 'Чётное или нечётное', 'difficulty': '🟢 Легко', 'prompt': 'Попроси пользователя ввести целое число и выведи, чётное оно или нечётное.', 'hint': 'Используй остаток от деления %.', 'solution': 'n = int(input("Число: "))\nif n % 2 == 0:\n    print("Чётное")\nelse:\n    print("Нечётное")'}, {'id': 't2', 'title': 'Максимум из двух', 'difficulty': '🟢 Легко', 'prompt': 'Введи два числа и выведи большее из них.', 'hint': 'Сравни числа через if/else или max().', 'solution': 'a = int(input())\nb = int(input())\nprint(max(a, b))'}, {'id': 't3', 'title': 'Сумма списка', 'difficulty': '🟢 Легко', 'prompt': 'Создай список чисел и посчитай сумму его элементов без ручного сложения.', 'hint': 'Попробуй sum().', 'solution': 'numbers = [3, 7, 2, 9]\nprint(sum(numbers))'}, {'id': 't4', 'title': 'Подсчёт гласных', 'difficulty': '🟡 Средне', 'prompt': 'Посчитай, сколько гласных букв в строке.', 'hint': 'Используй строку vowels = "аеёиоуыэюя" и цикл for.', 'solution': 'text = input().lower()\ncount = sum(ch in "аеёиоуыэюя" for ch in text)\nprint(count)'}, {'id': 't5', 'title': 'Разворот строки', 'difficulty': '🟡 Средне', 'prompt': 'Выведи строку в обратном порядке.', 'hint': 'Вспомни срез [::-1].', 'solution': 'text = input()\nprint(text[::-1])'}, {'id': 't6', 'title': 'Функция приветствия', 'difficulty': '🟡 Средне', 'prompt': 'Напиши функцию greet(name), которая возвращает приветствие с именем.', 'hint': 'Функция должна использовать return.', 'solution': 'def greet(name):\n    return f"Привет, {name}!"'}, {'id': 't7', 'title': 'Словарь пользователя', 'difficulty': '🟡 Средне', 'prompt': 'Создай словарь с name и age, затем безопасно получи значение age через get().', 'hint': 'get() принимает ключ и значение по умолчанию.', 'solution': 'user = {"name": "Alex", "age": 14}\nprint(user.get("age", 0))'}, {'id': 't8', 'title': 'Чтение JSON', 'difficulty': '🟠 Сложнее', 'prompt': 'Сохрани словарь в JSON-файл, а затем прочитай его обратно.', 'hint': 'Нужен модуль json и dump/load.', 'solution': 'import json\ndata = {"name": "Alex"}\nwith open("data.json", "w", encoding="utf-8") as f:\n    json.dump(data, f, ensure_ascii=False)'}, {'id': 't9', 'title': 'SQLite запрос', 'difficulty': '🟠 Сложнее', 'prompt': 'Подключись к SQLite и выполни SELECT из таблицы users.', 'hint': 'Используй sqlite3.connect() и execute().', 'solution': 'import sqlite3\nconn = sqlite3.connect("app.db")\nrows = conn.execute("SELECT * FROM users").fetchall()\nprint(rows)\nconn.close()'}, {'id': 't10', 'title': 'Асинхронная пауза', 'difficulty': '🟠 Сложнее', 'prompt': 'Напиши async-функцию, которая ждёт одну секунду через asyncio.sleep().', 'hint': 'Внутри async def можно использовать await.', 'solution': 'import asyncio\n\nasync def main():\n    await asyncio.sleep(1)\n    print("Готово")\n\nasyncio.run(main())'}, {'id': 't11', 'title': 'API JSON', 'difficulty': '🔴 Продвинуто', 'prompt': 'Сделай GET-запрос через requests и выведи JSON-ответ.', 'hint': 'У ответа есть метод json().', 'solution': 'import requests\nresponse = requests.get("https://api.example.com/data")\nprint(response.json())'}, {'id': 't12', 'title': 'Telegram обработчик', 'difficulty': '🔴 Продвинуто', 'prompt': 'Создай простой handler в aiogram, который отвечает на текст «Привет».', 'hint': 'Используй декоратор @dp.message и F.text.', 'solution': '@dp.message(F.text == "Привет")\nasync def hello(message: Message):\n    await message.answer("Привет!")'}]

QUIZ_QUESTIONS = [{'id': 'q1', 'title': 'Условия', 'code': 'age = 20\n\nif age >= 18\n    print("Взрослый")', 'options': ['Добавить : после условия if', 'Заменить >= на =', 'Удалить отступ перед print()', 'Добавить скобки вокруг age'], 'correct': 0, 'explanation': 'После условия if в Python нужен двоеточие :.'}, {'id': 'q2', 'title': 'Сравнение', 'code': 'x = 10\nif x = 10:\n    print("yes")', 'options': ['x == 10', 'x := 10', 'x >= 10', 'x is 10'], 'correct': 0, 'explanation': 'Для сравнения значений используется ==, а = — присваивание.'}, {'id': 'q3', 'title': 'Список', 'code': 'numbers = [1, 2, 3]\nprint(numbers[3])', 'options': ['print(numbers[2])', 'print(numbers[1])', 'print(numbers[-3])', 'print(numbers[0])'], 'correct': 0, 'explanation': 'Последний элемент списка с тремя значениями имеет индекс 2.'}, {'id': 'q4', 'title': 'Функция', 'code': 'def add(a, b)\n    return a + b', 'options': ['Добавить : после )', 'Добавить ; после )', 'Заменить return на print', 'Удалить отступ перед return'], 'correct': 0, 'explanation': 'После объявления функции тоже нужен двоеточие :.'}, {'id': 'q5', 'title': 'Переменная', 'code': 'name = "Alex"\nprint(nmae)', 'options': ['print(name)', 'print("name")', 'print(Name)', 'print(name())'], 'correct': 0, 'explanation': 'Имя переменной написано с опечаткой: nmae вместо name.'}, {'id': 'q6', 'title': 'Длина числа', 'code': 'age = 14\nprint(len(age))', 'options': ['print(len(str(age)))', 'print(age.len())', 'print(length(age))', 'print(len(int(age)))'], 'correct': 0, 'explanation': 'len() работает с последовательностями; число можно сначала превратить в строку.'}, {'id': 'q7', 'title': 'Словарь', 'code': 'user = {"name": "Alex"}\nprint(user["age"])', 'options': ['print(user.get("age"))', 'print(user.get["age"])', 'print(user.age)', 'print(user("age"))'], 'correct': 0, 'explanation': 'get() безопасно получает значение по ключу, которого может не быть.'}, {'id': 'q8', 'title': 'Импорт', 'code': 'import maths\nprint(math.sqrt(16))', 'options': ['import math', 'import mathematics as math', 'from math import sqrt', 'import math as maths'], 'correct': 0, 'explanation': 'Модуль стандартной библиотеки называется math, а не maths.'}, {'id': 'q9', 'title': 'Цикл', 'code': 'for i in range(3)\n    print(i)', 'options': ['Добавить : после range(3)', 'Заменить for на while', 'Удалить отступ перед print(i)', 'Добавить i = 0 перед for'], 'correct': 0, 'explanation': 'После заголовка цикла for нужен двоеточие :.'}, {'id': 'q10', 'title': 'Строка', 'code': 'text = "Python"\nprint(text.upper)', 'options': ['print(text.upper())', 'print(upper(text))', 'print(text.upper[])', 'print(text->upper())'], 'correct': 0, 'explanation': 'Метод upper нужно вызвать со скобками: upper().'}, {'id': 'q11', 'title': 'Список', 'code': 'items = []\nitems.apend(1)\nprint(items)', 'options': ['items.append(1)', 'items.add(1)', 'items.insert(1)', 'items.push(1)'], 'correct': 0, 'explanation': 'У списка Python метод называется append().'}, {'id': 'q12', 'title': 'Файл', 'code': 'with open("data.txt", "r" encoding="utf-8") as f:\n    print(f.read())', 'options': ['with open("data.txt", "r", encoding="utf-8") as f:', 'with open("data.txt", r, encoding="utf-8") as f:', 'with open("data.txt"; "r"; encoding="utf-8") as f:', 'with open("data.txt", "r"), encoding="utf-8" as f:'], 'correct': 0, 'explanation': 'Аргументы функции open() разделяются запятыми.'}, {'id': 'q13', 'title': 'Comprehension', 'code': 'even = [x for x in range(10) x % 2 == 0]', 'options': ['even = [x for x in range(10) if x % 2 == 0]', 'even = [x if for x in range(10) % 2 == 0]', 'even = [x in range(10) if x % 2 == 0]', 'even = (x for x in range(10) if x % 2 == 0]'], 'correct': 0, 'explanation': 'В list comprehension условие вводится через if.'}, {'id': 'q14', 'title': 'Asyncio', 'code': 'async def main():\n    asyncio.sleep(1)\n    print("done")', 'options': ['await asyncio.sleep(1)', 'asyncio.await sleep(1)', 'await asyncio.sleep', 'async sleep(1)'], 'correct': 0, 'explanation': 'Асинхронную операцию внутри async-функции нужно ожидать через await.'}, {'id': 'q15', 'title': 'SQLite', 'code': 'conn = sqlite3.connect("app.db")\nconn.execute("INSERT INTO users (name) VALUES (?)", "Alex")', 'options': ['conn.execute("INSERT INTO users (name) VALUES (?)", ("Alex",))', 'conn.execute("INSERT INTO users (name) VALUES (?)", [Alex])', 'conn.execute("INSERT INTO users (name) VALUES (?)", Alex)', 'conn.execute("INSERT INTO users (name) VALUES (?)", {"Alex"})'], 'correct': 0, 'explanation': 'Параметры для DB-API передаются как последовательность значений, здесь кортеж из одного элемента.'}]

# Вопросы не должны всегда иметь правильный ответ под номером 1.
for _i, _q in enumerate(QUIZ_QUESTIONS):
    _shift = (_i * 3) % 4
    if _shift:
        _q["options"] = _q["options"][_shift:] + _q["options"][:_shift]
        _q["correct"] = (_q["correct"] - _shift) % 4

# Дополнительные задания: от простых до проектных.
PRACTICE_TASKS.extend([
    {"id":"t13","title":"Фильтр положительных чисел","difficulty":"🟡 Средне","prompt":"Из списка чисел создай новый список только с положительными значениями.","hint":"Подойдёт обычный цикл или list comprehension.","solution":"numbers = [-3, 4, 0, 8, -1]\npositive = [x for x in numbers if x > 0]\nprint(positive)"},
    {"id":"t14","title":"Частотность слов","difficulty":"🟡 Средне","prompt":"Посчитай, сколько раз каждое слово встречается в строке.","hint":"Разбей строку через split() и храни счётчик в dict.","solution":"text = input().lower().split()\ncounts = {}\nfor word in text:\n    counts[word] = counts.get(word, 0) + 1\nprint(counts)"},
    {"id":"t15","title":"Безопасный ввод числа","difficulty":"🟠 Сложнее","prompt":"Напиши функцию, которая просит число и повторяет ввод, пока пользователь не введёт корректное целое.","hint":"Используй while True и try/except ValueError.","solution":"def read_int():\n    while True:\n        try:\n            return int(input(\"Число: \"))\n        except ValueError:\n            print(\"Введите целое число\")"},
    {"id":"t16","title":"JSON-заметки","difficulty":"🟠 Сложнее","prompt":"Сохрани список заметок в JSON и загрузи его при следующем запуске.","hint":"Используй json.dump/json.load и with.","solution":"import json\n\nnotes = [\"Изучить циклы\", \"Решить задачу\"]\nwith open(\"notes.json\", \"w\", encoding=\"utf-8\") as f:\n    json.dump(notes, f, ensure_ascii=False, indent=2)"},
    {"id":"t17","title":"SQLite CRUD","difficulty":"🔴 Продвинуто","prompt":"Создай таблицу tasks и реализуй INSERT + SELECT через sqlite3.","hint":"Сначала CREATE TABLE IF NOT EXISTS, затем INSERT и SELECT.","solution":"import sqlite3\n\nconn = sqlite3.connect(\"tasks.db\")\nconn.execute(\"CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT)\")\nconn.execute(\"INSERT INTO tasks (title) VALUES (?)\", (\"Изучить SQL\",))\nconn.commit()\nprint(conn.execute(\"SELECT * FROM tasks\").fetchall())\nconn.close()"},
    {"id":"t18","title":"Мини-API","difficulty":"🔴 Продвинуто","prompt":"Сделай GET endpoint, который возвращает JSON со списком задач.","hint":"В FastAPI достаточно функции с декоратором @app.get и возврата dict/list.","solution":"from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get(\"/tasks\")\ndef tasks():\n    return [{\"id\": 1, \"title\": \"Изучить Python\"}]"},
])

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
        InlineKeyboardButton(text="📊 Мой прогресс", callback_data="progress"),
        InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")
    ])

    # Кнопка мини-приложения показывается только если задан MINIAPP_URL.
    if MINIAPP_URL:
        rows.append([
            InlineKeyboardButton(
                text="🚀 Открыть Mini App",
                web_app=WebAppInfo(url=MINIAPP_LAUNCH_URL),
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

def _catalog_category_buttons(prefix: str, categories: dict, callback_prefix: str) -> list[list[InlineKeyboardButton]]:
    buttons = [InlineKeyboardButton(text=v["title"], callback_data=f"{callback_prefix}{k}") for k, v in categories.items()
               if any(x.get("category") == k for x in (FRAMEWORKS if prefix == "framework" else LIBRARIES).values())]
    return grid(buttons, 1)


def frameworks_menu(category: str | None = None):
    if category:
        data_items = {k:v for k,v in FRAMEWORKS.items() if v.get("category") == category}
        buttons = [InlineKeyboardButton(text=data["name"], callback_data=f"framework_{key}") for key, data in data_items.items()]
        rows = grid(buttons, 2)
        rows.append([InlineKeyboardButton(text="⬅️ Категории", callback_data="frameworks")])
    else:
        rows = _catalog_category_buttons("framework", FRAMEWORK_CATEGORIES, "fwcat_")
        rows.append([InlineKeyboardButton(text="📚 Все фреймворки", callback_data="fwcat_all")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="course")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def libraries_menu(category: str | None = None):
    if category:
        data_items = {k:v for k,v in LIBRARIES.items() if v.get("category") == category}
        buttons = [InlineKeyboardButton(text=data["name"], callback_data=f"library_{key}") for key, data in data_items.items()]
        rows = grid(buttons, 2)
        rows.append([InlineKeyboardButton(text="⬅️ Категории", callback_data="libraries")])
    else:
        rows = _catalog_category_buttons("library", LIBRARY_CATEGORIES, "lbcat_")
        rows.append([InlineKeyboardButton(text="📚 Все библиотеки", callback_data="lbcat_all")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="course")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def commands_menu(kind: str, key: str, commands: list):
    rows = []
    for i, (cmd, _desc) in enumerate(commands):
        rows.append([InlineKeyboardButton(text=f"{i+1}. {cmd[:45]}", callback_data=f"{kind}cmd_{key}_{i}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{kind}_{key}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def command_detail_kb(kind: str, key: str, index: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Все команды", callback_data=f"{kind}cmds_{key}"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="course"),
    ]])


def commands_block(commands: list) -> str:
    """Форматирует список (команда, описание) в HTML-блок для карточки."""
    if not commands:
        return ""
    lines = ["\n\n🧭 <b>Основные команды:</b>"]
    for cmd, desc in commands:
        lines.append(f"• <code>{html.escape(cmd)}</code> — {html.escape(desc)}")
    return "\n".join(lines)


def item_caption(data: dict) -> str:
    return f"<b>{data['name']}</b>\n\n{data['desc']}{commands_block(data.get('commands', []))}"


def item_back_kb(back_to: str, url: str | None = None, kind: str | None = None, key: str | None = None):
    rows = []
    data_commands = (FRAMEWORKS.get(key, {}) if kind == "framework" else LIBRARIES.get(key, {})).get("commands", [])
    if kind and key and data_commands:
        rows.append([InlineKeyboardButton(text="🧭 Посмотреть команды", callback_data=f"{kind}cmds_{key}")])
    if url:
        rows.append([InlineKeyboardButton(text="🔗 Официальный сайт", url=url)])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to), InlineKeyboardButton(text="🏠 Главное меню", callback_data="course")])
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
                "Сначала выбери направление — внутри будут только подходящие фреймворки."
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
        reply_markup=item_back_kb("frameworks", data.get("url"), "framework", key),
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
                "Выбери направление — внутри будут только подходящие библиотеки."
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
        reply_markup=item_back_kb("libraries", data.get("url"), "library", key),
    )
    await callback.answer()



@dp.callback_query(F.data.startswith("fwcat_"))
async def framework_category(callback: CallbackQuery):
    category = callback.data.split("_", 1)[1]
    if category == "all":
        category = None
    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "framework_category", category or "all")
    if category:
        title = FRAMEWORK_CATEGORIES.get(category, {}).get("title", "Фреймворки")
        caption = f"🧩 <b>{html.escape(title)}</b>\n\nВыбери технологию."
    else:
        caption = "🧩 <b>Все фреймворки</b>\n\nВыбери технологию."
    await callback.message.edit_caption(caption=caption, reply_markup=frameworks_menu(category), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("lbcat_"))
async def library_category(callback: CallbackQuery):
    category = callback.data.split("_", 1)[1]
    if category == "all":
        category = None
    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "library_category", category or "all")
    if category:
        title = LIBRARY_CATEGORIES.get(category, {}).get("title", "Библиотеки")
        caption = f"📚 <b>{html.escape(title)}</b>\n\nВыбери библиотеку."
    else:
        caption = "📚 <b>Все библиотеки</b>\n\nВыбери библиотеку."
    await callback.message.edit_caption(caption=caption, reply_markup=libraries_menu(category), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("frameworkcmds_"))
async def framework_commands(callback: CallbackQuery):
    key = callback.data.split("_", 1)[1]
    data = FRAMEWORKS.get(key)
    if not data:
        await callback.answer("Фреймворк не найден", show_alert=True); return
    await callback.message.edit_caption(
        caption=f"🧭 <b>Команды: {html.escape(data['name'])}</b>\n\nНажми на команду, чтобы увидеть подробное объяснение.",
        reply_markup=commands_menu("framework", key, data.get("commands", [])),
        parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("frameworkcmd_"))
async def framework_command_detail(callback: CallbackQuery):
    payload = callback.data[len("frameworkcmd_"):]
    try:
        key, idx_raw = payload.rsplit("_", 1)
        idx = int(idx_raw)
    except (ValueError, IndexError):
        await callback.answer("Команда не найдена", show_alert=True); return
    data = FRAMEWORKS.get(key)
    commands = data.get("commands", []) if data else []
    if not data or idx < 0 or idx >= len(commands):
        await callback.answer("Команда не найдена", show_alert=True); return
    cmd, desc = commands[idx]
    await touch_user(callback.from_user); await log_view(callback.from_user.id, "framework_command", f"{data['name']}: {cmd}")
    await callback.message.edit_caption(
        caption=f"🧩 <b>{html.escape(data['name'])}</b>\n\n<code>{html.escape(cmd)}</code>\n\n<b>Что делает:</b> {html.escape(desc)}\n\n💡 <b>Как учить:</b> попробуй поменять аргументы команды и проверить, как изменится поведение.",
        reply_markup=command_detail_kb("framework", key, idx), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("librarycmds_"))
async def library_commands(callback: CallbackQuery):
    key = callback.data.split("_", 1)[1]
    data = LIBRARIES.get(key)
    if not data:
        await callback.answer("Библиотека не найдена", show_alert=True); return
    await callback.message.edit_caption(
        caption=f"🧭 <b>Команды: {html.escape(data['name'])}</b>\n\nНажми на команду, чтобы увидеть подробное объяснение.",
        reply_markup=commands_menu("library", key, data.get("commands", [])),
        parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("librarycmd_"))
async def library_command_detail(callback: CallbackQuery):
    payload = callback.data[len("librarycmd_"):]
    try:
        key, idx_raw = payload.rsplit("_", 1)
        idx = int(idx_raw)
    except (ValueError, IndexError):
        await callback.answer("Команда не найдена", show_alert=True); return
    data = LIBRARIES.get(key)
    commands = data.get("commands", []) if data else []
    if not data or idx < 0 or idx >= len(commands):
        await callback.answer("Команда не найдена", show_alert=True); return
    cmd, desc = commands[idx]
    await touch_user(callback.from_user); await log_view(callback.from_user.id, "library_command", f"{data['name']}: {cmd}")
    await callback.message.edit_caption(
        caption=f"📦 <b>{html.escape(data['name'])}</b>\n\n<code>{html.escape(cmd)}</code>\n\n<b>Что делает:</b> {html.escape(desc)}\n\n💡 <b>Совет:</b> попробуй найти в документации ещё один способ решить ту же задачу.",
        reply_markup=command_detail_kb("library", key, idx), parse_mode="HTML")
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



SUPPORT_WAITING: set[int] = set()


def _save_support_sync(user_id: int, username: str, first_name: str, text: str) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with db_connect() as conn:
        cur = conn.execute(
            "INSERT INTO support_messages (user_id, username, first_name, text, created_at, status) VALUES (?, ?, ?, ?, ?, 'open')",
            (user_id, username or "", first_name or "", text, now),
        )
        conn.commit()
        return int(cur.lastrowid)


async def send_support_to_admins(user, text: str):
    ticket_id = await asyncio.to_thread(_save_support_sync, user.id, user.username or "", user.first_name or "", text)
    uname = f"@{user.username}" if user.username else "None"
    recipients = ADMIN_IDS or ({ADMIN_ID} if ADMIN_ID else set())
    admin_text = (
        f"🆘 <b>Новое обращение #{ticket_id}</b>\n\n"
        f"👤 {html.escape(uname)}\n"
        f"🆔 <code>{user.id}</code>\n"
        f"Имя: {html.escape(user.first_name or 'None')}\n\n"
        f"💬 {html.escape(text)}\n\n"
        f"Ответить: <code>/reply_support {ticket_id} ваш ответ</code>"
    )
    for admin_id in recipients:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            log.exception("Не удалось доставить обращение администратору %s", admin_id)
    return ticket_id


@dp.callback_query(F.data == "support")
async def support_start(callback: CallbackQuery):
    await touch_user(callback.from_user)
    await log_view(callback.from_user.id, "menu", "support")
    SUPPORT_WAITING.add(callback.from_user.id)
    await callback.message.answer(
        "🆘 <b>Поддержка</b>\n\nНапиши одним сообщением, что произошло или какой вопрос у тебя возник.\n\nСообщение получат все администраторы.",
        parse_mode="HTML",
    )
    await callback.answer("Напиши сообщение поддержки")


@dp.message(F.text == "/support")
async def support_command(message: Message):
    await touch_user(message.from_user)
    SUPPORT_WAITING.add(message.from_user.id)
    await message.answer(
        "🆘 <b>Поддержка</b>\n\nНапиши сообщение следующим сообщением. Его получат все администраторы.",
        parse_mode="HTML")


@dp.message(lambda message: bool(message.from_user and message.from_user.id in SUPPORT_WAITING and message.text and not message.text.startswith("/")))
async def support_message(message: Message):
    SUPPORT_WAITING.discard(message.from_user.id)
    text = (message.text or "").strip()
    if not text:
        await message.answer("❌ Сообщение пустое. Попробуй ещё раз через /support.")
        return
    ticket_id = await send_support_to_admins(message.from_user, text)
    await message.answer(f"✅ Сообщение отправлено администраторам. Номер обращения: <b>#{ticket_id}</b>", parse_mode="HTML")


@dp.message(F.text.startswith("/reply_support"))
async def support_reply(message: Message):
    if not is_admin_user(message.from_user.id):
        await message.answer("⛔ У тебя нет прав администратора.")
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Формат: /reply_support НОМЕР текст ответа")
        return
    try: ticket_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Номер обращения должен быть числом.")
        return
    reply_text = parts[2].strip()
    with db_connect() as conn:
        row = conn.execute("SELECT user_id FROM support_messages WHERE id=?", (ticket_id,)).fetchone()
    if not row:
        await message.answer("❌ Обращение не найдено.")
        return
    try:
        await bot.send_message(int(row[0]), f"🆘 <b>Ответ поддержки</b>\n\n{html.escape(reply_text)}", parse_mode="HTML")
    except Exception as exc:
        await message.answer(f"❌ Не удалось отправить ответ: <code>{html.escape(str(exc))}</code>", parse_mode="HTML")
        return
    with db_connect() as conn:
        conn.execute("UPDATE support_messages SET status='answered' WHERE id=?", (ticket_id,))
        conn.commit()
    await message.answer(f"✅ Ответ по обращению #{ticket_id} отправлен.")

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
        uname = f"@{username}" if username else "None"
        text += f"• {uname} — {cnt}\n"

    text += "\n<b>🕓 Последние действия:</b>\n"
    for first_name, username, kind, title, viewed_at in last_views:
        uname = f"@{username}" if username else "None"
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


# =========================================================
# РАСШИРЕННЫЕ УРОКИ
# =========================================================

LESSON_GUIDES = {
    "Что такое Python": {
        "core": "Python — не просто набор команд. Программа — это последовательность инструкций и данных, которую интерпретатор выполняет по правилам языка.",
        "why": "Важно сначала понять модель выполнения: Python читает программу, создаёт объекты, вызывает функции и меняет состояние программы. Это помогает потом понимать переменные, функции и исключения.",
        "example": 'name = "Alex"\nage = 14\nprint(f"{name}: {age}")',
        "breakdown": "1) создаются две переменные; 2) f-строка собирает текст; 3) print выводит готовую строку.",
        "mistakes": ["Учить синтаксис без практики.", "Копировать код, не меняя его.", "Игнорировать сообщения об ошибках."],
        "practice": "Измени пример так, чтобы он спрашивал имя и возраст, а затем выводил фразу о пользователе."
    },
    "Переменные": {
        "core": "Имя переменной связывает понятное обозначение с объектом-значением. Само имя не 'содержит коробку' — оно ссылается на объект.",
        "why": "Так код получает состояние, которым можно управлять: счётчик, пользователь, список задач, ответ API.",
        "example": 'score = 0\nscore = score + 10\nprint(score)',
        "breakdown": "Сначала score ссылается на 0, затем выражение вычисляется и имя score начинает ссылаться на 10.",
        "mistakes": ["Путать = и ==.", "Использовать непонятные имена вроде x1, x2, x3.", "Переиспользовать имя для значения другого смысла."],
        "practice": "Создай переменные price, count и total и вычисли стоимость нескольких товаров."
    },
    "input()": {
        "core": "input() всегда возвращает строку. Если дальше нужен number, его нужно явно преобразовать через int() или float().",
        "why": "Большинство программ взаимодействует с внешними данными: пользователем, файлом, HTTP-запросом. Преобразование ввода — важная часть обработки данных.",
        "example": 'age = int(input("Сколько лет? "))\nprint(age + 1)',
        "breakdown": "input получает текст → int пытается превратить его в целое → результат сохраняется в age → к нему можно применять арифметику.",
        "mistakes": ["Забыть преобразование строки в число.", "Не учитывать ValueError при плохом вводе.", "Смешивать ввод и бизнес-логику в одной огромной функции."],
        "practice": "Сделай ввод цены и количества с расчётом итоговой суммы."
    },
    "if": {
        "core": "if выбирает ветку выполнения по булеву условию. Условие должно вычислиться в True или False.",
        "why": "Условия превращают программу из линейного списка команд в алгоритм, который умеет реагировать на разные ситуации.",
        "example": 'temperature = 7\nif temperature < 10:\n    print("Нужно взять куртку")\nelse:\n    print("Можно полегче")',
        "breakdown": "Python вычисляет temperature < 10. Если результат True, выполняется первый блок; иначе — второй.",
        "mistakes": ["Забыть двоеточие.", "Неверно расставить отступы.", "Использовать = вместо == при сравнении."],
        "practice": "Напиши проверку пароля: если длина меньше 8 — покажи подсказку, иначе сообщи, что пароль подходит по длине."
    },
    "for": {
        "core": "for перебирает элементы и выполняет тело цикла для каждого значения. Это не только счётчик: цикл работает с любым итерируемым объектом.",
        "why": "Циклы убирают повторяющийся код и позволяют обрабатывать коллекции, строки, файлы и результаты запросов.",
        "example": 'names = ["Alex", "Anna", "Max"]\nfor name in names:\n    print(name)',
        "breakdown": "На каждой итерации name получает очередной элемент списка, затем выполняется тело цикла.",
        "mistakes": ["Не понимать, какой объект перебирается.", "Изменять коллекцию во время перебора без понимания последствий.", "Делать вложенность глубже, чем нужно."],
        "practice": "Выведи только слова длиннее пяти символов из списка."
    },
    "list": {
        "core": "list — изменяемая упорядоченная коллекция. Элементы доступны по индексу, а порядок сохраняется.",
        "why": "Список удобен, когда нужно хранить последовательность: товары корзины, сообщения, результаты, задачи.",
        "example": 'tasks = ["учёба", "спорт"]\ntasks.append("код")\nprint(tasks[0])',
        "breakdown": "Создали список → append добавил элемент в конец → индекс 0 дал первый элемент.",
        "mistakes": ["Использовать index за пределами списка.", "Путать append и extend.", "Случайно менять исходный список через общую ссылку."],
        "practice": "Создай список оценок, добавь две оценки и посчитай среднее значение."
    },
    "dict": {
        "core": "dict хранит пары ключ → значение. Это структура для быстрого доступа к данным по понятному ключу.",
        "why": "Словари особенно полезны для объектов с именованными полями: пользователь, товар, настройки, ответ API.",
        "example": 'user = {"name": "Alex", "age": 14}\nprint(user["name"])\nprint(user.get("city", "не указано"))',
        "breakdown": "Доступ через [] ожидает существующий ключ, а get позволяет задать значение по умолчанию.",
        "mistakes": ["Получать отсутствующий ключ через [] без обработки.", "Хранить всё в одном огромном словаре без структуры.", "Не различать keys(), values() и items()."],
        "practice": "Создай словарь товара с name, price и count и вычисли общую стоимость."
    },
    "def": {
        "core": "Функция encapsulates действие: получает входные данные, выполняет логику и при необходимости возвращает результат.",
        "why": "Функции уменьшают дублирование и позволяют тестировать части программы отдельно.",
        "example": 'def area(width, height):\n    return width * height\n\nprint(area(5, 3))',
        "breakdown": "При вызове area(5, 3) параметры получают значения 5 и 3, тело считает произведение, return отдаёт 15 вызывающему коду.",
        "mistakes": ["Путать параметры и аргументы.", "Забывать return.", "Делать функцию, которая одновременно читает ввод, пишет в файл и рисует UI без необходимости."],
        "practice": "Напиши функцию discount(price, percent), возвращающую цену после скидки."
    },
    "return": {
        "core": "return завершает выполнение функции и передаёт значение наружу. Это отличается от print(), который только выводит текст.",
        "why": "Возвращаемое значение можно сохранить, передать другой функции, протестировать или использовать в выражении.",
        "example": 'def is_even(n):\n    return n % 2 == 0\n\nprint(is_even(8))',
        "breakdown": "Функция не печатает ответ сама — она возвращает bool, а вызывающий код решает, что с ним делать.",
        "mistakes": ["Использовать print вместо return.", "Ожидать значение после return без аргумента — тогда вернётся None.", "Пытаться вернуть несколько несвязанных результатов без структуры."],
        "practice": "Сделай функцию max_of_three(a, b, c), которая возвращает максимальное число."
    },
    "try": {
        "core": "try/except позволяет обработать ожидаемую ошибку рядом с операцией, которая действительно может завершиться неудачей.",
        "why": "Внешний ввод, файлы, сети и базы данных могут вернуть неожиданные данные или временно не работать.",
        "example": 'try:\n    age = int(input("Возраст: "))\nexcept ValueError:\n    print("Нужно ввести целое число")',
        "breakdown": "Опасный участок находится в try. Если возникает ValueError, управление переходит в соответствующий except.",
        "mistakes": ["except Exception вокруг всего приложения.", "Скрывать ошибку и продолжать в некорректном состоянии.", "Обрабатывать не тот тип исключения."],
        "practice": "Сделай безопасный ввод делимого и делителя с отдельной обработкой ValueError и ZeroDivisionError."
    },
    "open()": {
        "core": "open() создаёт файловый объект. Режим r читает, w перезаписывает, a добавляет в конец.",
        "why": "Файлы позволяют хранить данные между запусками и обмениваться данными с другими программами.",
        "example": 'with open("notes.txt", "w", encoding="utf-8") as f:\n    f.write("Первая заметка")',
        "breakdown": "with автоматически закрывает файл после блока, даже если внутри возникнет исключение.",
        "mistakes": ["Забыть encoding для текстовых файлов.", "Открыть w и случайно стереть файл.", "Оставить файл открытым."],
        "practice": "Сделай программу, которая добавляет новую заметку в notes.txt и затем выводит все заметки."
    },
    "class": {
        "core": "class описывает новый тип объектов: какие данные они хранят и какие операции над ними поддерживают.",
        "why": "Классы полезны, когда в программе много однотипных сущностей с общими правилами поведения.",
        "example": 'class User:\n    def __init__(self, name):\n        self.name = name\n\nuser = User("Alex")',
        "breakdown": "__init__ получает имя при создании объекта и сохраняет его в self.name. user теперь отдельный экземпляр класса User.",
        "mistakes": ["Создавать класс для любой двухстрочной задачи.", "Не понимать разницу между классом и экземпляром.", "Помещать в класс глобальное состояние без необходимости."],
        "practice": "Создай класс BankAccount с balance и методами deposit() и withdraw()."
    },
    "async": {
        "core": "async def объявляет корутину. await позволяет уступить управление event loop до завершения другой операции.",
        "why": "Это полезно, когда программа много времени проводит в ожидании I/O: HTTP, база, файлы, таймеры.",
        "example": 'import asyncio\n\nasync def main():\n    await asyncio.sleep(1)\n    print("Готово")\n\nasyncio.run(main())',
        "breakdown": "sleep не блокирует обычным способом весь event loop: другие задачи могут выполняться, пока эта корутина ожидает.",
        "mistakes": ["Вызывать coroutine без await.", "Считать async магическим ускорителем любого кода.", "Запускать блокирующий код внутри async без причины."],
        "practice": "Запусти три async-задачи через asyncio.gather и сравни с последовательным ожиданием."
    },
    "SQL": {
        "core": "SQL описывает операции над реляционными данными: создание структуры, выборку, изменение и удаление записей.",
        "why": "Почти любое прикладное приложение хранит данные. Умение сформулировать запрос важнее, чем просто помнить синтаксис.",
        "example": 'SELECT name, age\nFROM users\nWHERE age >= 18\nORDER BY name;',
        "breakdown": "SELECT выбирает поля, FROM задаёт таблицу, WHERE фильтрует строки, ORDER BY задаёт порядок результата.",
        "mistakes": ["Делать SELECT * без необходимости.", "Собирать SQL строковой конкатенацией из пользовательского ввода.", "Забывать условие WHERE в UPDATE/DELETE."],
        "practice": "Напиши запрос, который выводит пользователей старше 18 лет по алфавиту."
    },
    "HTTP": {
        "core": "HTTP — протокол запросов и ответов. Клиент отправляет метод, URL, заголовки и при необходимости тело; сервер отвечает статусом, заголовками и телом.",
        "why": "Понимание HTTP помогает одинаково уверенно работать с requests, FastAPI, Flask и Telegram Mini App API.",
        "example": 'GET /users/42 HTTP/1.1\nAccept: application/json',
        "breakdown": "GET просит ресурс, URL указывает адрес, Accept сообщает предпочитаемый формат ответа.",
        "mistakes": ["Не проверять HTTP-статус.", "Смешивать GET и POST без понимания семантики.", "Передавать секреты в URL без необходимости."],
        "practice": "Сделай requests.get(), проверь status_code и только потом прочитай JSON."
    },
    "aiogram": {
        "core": "aiogram разделяет получение обновлений, маршрутизацию обработчиков и бизнес-логику Telegram-бота.",
        "why": "Когда бот растёт, разделение handlers, данных и сервисов делает код поддерживаемым.",
        "example": '@dp.message(F.text == "Привет")\nasync def hello(message: Message):\n    await message.answer("Привет!")',
        "breakdown": "Декоратор связывает событие с функцией. Dispatcher выбирает подходящий handler, функция использует объект Message.",
        "mistakes": ["Хранить весь проект в одном handler.", "Забывать await у асинхронных операций.", "Не разделять callback_data по смыслу."],
        "practice": "Сделай handler с двумя кнопками и отдельным обработчиком для каждой callback_data."
    },
    "pip": {
        "core": "pip устанавливает Python-пакеты в текущее окружение. Лучше использовать виртуальное окружение проекта.",
        "why": "Разные проекты требуют разные версии библиотек; изоляция снижает количество конфликтов.",
        "example": 'python -m venv .venv\n# Windows: .venv\\Scripts\\activate\n# Linux/macOS: source .venv/bin/activate\npip install requests',
        "breakdown": "Создаётся отдельное окружение → оно активируется → пакет устанавливается именно туда → зависимости можно зафиксировать.",
        "mistakes": ["Устанавливать всё глобально.", "Не фиксировать зависимости.", "Не понимать, какой Python и pip сейчас активны."],
        "practice": "Создай виртуальное окружение и установи в него requests, а затем создай requirements.txt."
    },
    "git init": {
        "core": "git init создаёт локальный репозиторий Git в папке проекта. Дальше Git позволяет фиксировать изменения и работать с ветками.",
        "why": "Контроль версий нужен, чтобы безопасно менять код, видеть историю и работать с GitHub.",
        "example": 'git init\ngit add .\ngit commit -m "Initial commit"',
        "breakdown": "init создаёт репозиторий → add добавляет изменения в staging → commit фиксирует состояние.",
        "mistakes": ["Коммитить секреты и .env.", "Делать огромные коммиты без понятного сообщения.", "Пушить не ту ветку или не проверять diff."],
        "practice": "Создай репозиторий для учебного проекта и сделай три небольших осмысленных коммита."
    },
}


def enrich_lesson(topic: str, base_html: str) -> str:
    guide = LESSON_GUIDES.get(topic)
    if not guide:
        return base_html + (
            "<hr>"
            "<h3>🧠 Как закрепить</h3>"
            "<p>После чтения объяснения измени пример, запусти его и попробуй специально сломать одну строку. Затем исправь её по тексту ошибки.</p>"
            "<h3>📝 Самопроверка</h3>"
            "<p>1) Что принимает конструкция? 2) Что она возвращает? 3) В каком случае она выдаст ошибку? 4) Где ты применишь её в проекте?</p>"
        )
    mistakes = "".join(f"<li>{html.escape(x)}</li>" for x in guide["mistakes"])
    return (
        base_html
        + "<hr>"
        + f"<h3>🧠 Глубокое понимание</h3><p>{html.escape(guide['core'])}</p>"
        + f"<h3>🎯 Зачем это нужно</h3><p>{html.escape(guide['why'])}</p>"
        + f"<h3>💻 Ещё один пример</h3><pre class=\"code\">{html.escape(guide['example'])}</pre>"
        + f"<h3>🔍 Разбор по шагам</h3><p>{html.escape(guide['breakdown'])}</p>"
        + f"<h3>⚠️ Частые ошибки</h3><ul>{mistakes}</ul>"
        + f"<h3>🧪 Попробуй сам</h3><p>{html.escape(guide['practice'])}</p>"
        + "<h3>✅ Контрольные вопросы</h3><ol><li>Что является входом?</li><li>Какой результат получается?</li><li>Что произойдёт при неверных данных?</li><li>Как ты изменил бы пример для своего проекта?</li></ol>"
    )

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
        return enrich_lesson(topic, lessons[topic])

    if topic in LESSONS_EXTRA:
        return enrich_lesson(topic, render_extra_lesson(topic, LESSONS_EXTRA[topic]))

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
                    web_app=WebAppInfo(url=MINIAPP_LAUNCH_URL),
                )
            ]]
        ),
    )


# =========================================================
# WEB APP: проверка подлинности initData
# =========================================================

def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """Validate Telegram Mini App initData using the documented HMAC scheme.

    We also support clients that include the newer `signature` field by trying
    both canonical forms: all fields except `hash` (Telegram's bot-token
    validation) and, when `signature` is present, a compatibility form that
    excludes both `hash` and `signature`.
    """
    if not init_data or not bot_token:
        return None
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return None

    data = {}
    for key, value in pairs:
        if key in data and key not in {"hash", "signature"}:
            # Duplicate signed fields are not expected; reject them instead of
            # silently changing the signed payload.
            return None
        data[key] = value

    received_hash = data.pop("hash", None)
    if not received_hash:
        return None

    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    def calc(exclude_signature: bool) -> str:
        check = dict(data)
        if exclude_signature:
            check.pop("signature", None)
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(check.items())
        )
        return hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    computed = calc(False)
    if hmac.compare_digest(computed, received_hash):
        return data

    if "signature" in data:
        computed_compat = calc(True)
        if hmac.compare_digest(computed_compat, received_hash):
            return data

    return None


def validate_init_data_reason(init_data: str, bot_token: str) -> str:
    if not init_data:
        return "empty initData"
    if not bot_token:
        return "server BOT_TOKEN is empty"
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return "malformed initData"
    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        return "hash is missing"
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    def calc(exclude_signature=False):
        check = dict(data)
        if exclude_signature:
            check.pop("signature", None)
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(check.items()))
        return hmac.new(secret_key, check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if hmac.compare_digest(calc(False), received_hash):
        return "valid"
    if "signature" in data and hmac.compare_digest(calc(True), received_hash):
        return "valid (signature compatibility mode)"
    return "HMAC mismatch — check BOT_TOKEN and Mini App bot"


def _extract_webapp_user(parsed: dict) -> dict | None:
    raw_user = parsed.get("user")
    if not raw_user:
        return None
    try:
        return json.loads(raw_user)
    except (TypeError, ValueError):
        return None


def _build_course_payload() -> dict:
    return {
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
                "commands": data.get("commands", []),
                "category": data.get("category", "web"),
            }
            for key, data in FRAMEWORKS.items()
        },
        "framework_groups": grouped_catalog(FRAMEWORKS, FRAMEWORK_CATEGORIES),
        "libraries": {
            key: {
                "name": data["name"],
                "logo": data["logo"],
                "url": data.get("url", ""),
                "desc": data["desc"],
                "commands": data.get("commands", []),
                "category": data.get("category", "dev"),
            }
            for key, data in LIBRARIES.items()
        },
        "library_groups": grouped_catalog(LIBRARIES, LIBRARY_CATEGORIES),
        "mini_codes": MINI_CODES,
        "learning_plan": LEARNING_PLAN,
        "practice_tasks": PRACTICE_TASKS,
        "quizzes": [
            {"id": q["id"], "title": q["title"], "code": q["code"], "options": q["options"]}
            for q in QUIZ_QUESTIONS
        ],
        "total_topics": TOTAL_TOPICS,
    }


def _request_init_data(request: web.Request, body: dict | None = None) -> str:
    if body is not None:
        return str(body.get("initData", ""))
    return request.headers.get("X-Telegram-Init-Data", "")


def _cors(response: web.Response) -> web.Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


async def api_options(request: web.Request) -> web.Response:
    return _cors(web.Response())


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def api_debug_init(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        body = {}
    init_data = _request_init_data(request, body)
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True)) if init_data else {}
    except Exception:
        parsed = {}
    safe_keys = sorted(parsed.keys())
    return _cors(web.json_response({
        "has_init_data": bool(init_data),
        "keys": safe_keys,
        "has_hash": "hash" in parsed,
        "has_signature": "signature" in parsed,
        "has_user": "user" in parsed,
        "validation": validate_init_data_reason(init_data, TOKEN),
    }))


async def api_course(request: web.Request) -> web.Response:
    return _cors(web.json_response(_build_course_payload()))


async def api_me(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        body = {}
    parsed = validate_init_data(_request_init_data(request, body), TOKEN)
    user = _extract_webapp_user(parsed or {}) if parsed else None
    if not user or not user.get("id"):
        init_data = _request_init_data(request, body)
        reason = validate_init_data_reason(init_data, TOKEN)
        return _cors(web.json_response({"error": "invalid initData", "reason": reason}, status=401))

    uid = int(user["id"])
    await touch_user_from_webapp(uid, user.get("username", ""), user.get("first_name", ""))
    return _cors(web.json_response({
        "user": user,
        "is_admin": ADMIN_ID != 0 and uid == ADMIN_ID,
    }))


async def api_lesson(request: web.Request) -> web.Response:
    try:
        section_number = int(request.match_info["section"])
        topic_index = int(request.match_info["index"])
        topic = COURSE[section_number]["topics"][topic_index]
    except (ValueError, KeyError, IndexError):
        return _cors(web.json_response({"error": "not found"}, status=404))

    text = get_topic_text(section_number, topic)

    # Уроки из Mini App учитываются в views как topic.
    parsed = validate_init_data(_request_init_data(request), TOKEN)
    user = _extract_webapp_user(parsed or {}) if parsed else None
    if user and user.get("id"):
        uid = int(user["id"])
        await touch_user_from_webapp(uid, user.get("username", ""), user.get("first_name", ""))
        await log_view(uid, "topic", f"{section_number}:{topic}")

    return _cors(web.json_response({"topic": topic, "html": text}))


async def _read_webapp_user(request: web.Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    parsed = validate_init_data(_request_init_data(request, body), TOKEN)
    user = _extract_webapp_user(parsed or {}) if parsed else None
    return user, body


async def api_progress(request: web.Request) -> web.Response:
    user, _ = await _read_webapp_user(request)
    if not user or not user.get("id"):
        return _cors(web.json_response({"error": "invalid initData"}, status=401))

    uid = int(user["id"])
    await touch_user_from_webapp(uid, user.get("username", ""), user.get("first_name", ""))
    done = await asyncio.to_thread(_count_done_topics_sync, uid)
    def _quiz_stats_sync():
        with db_connect() as conn:
            row = conn.execute("SELECT COUNT(*), COALESCE(SUM(correct),0) FROM quiz_attempts WHERE user_id=?", (uid,)).fetchone()
            return int(row[0]), int(row[1])
    quiz_total, quiz_correct = await asyncio.to_thread(_quiz_stats_sync)
    return _cors(web.json_response({"done": done, "total": TOTAL_TOPICS, "quiz_total": quiz_total, "quiz_correct": quiz_correct}))


async def _save_quiz_attempt_sync(user_id: int, quiz_id: str, option_index: int, correct: bool):
    now = datetime.now().isoformat(timespec="seconds")
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO quiz_attempts (user_id, quiz_id, option_index, correct, answered_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, quiz_id, option_index, 1 if correct else 0, now),
        )
        conn.commit()


async def api_quiz_answer(request: web.Request) -> web.Response:
    user, body = await _read_webapp_user(request)
    if not user or not user.get("id"):
        return _cors(web.json_response({"error": "invalid initData"}, status=401))

    quiz_id = str(body.get("quiz_id", ""))
    try:
        option_index = int(body.get("option_index"))
    except (TypeError, ValueError):
        return _cors(web.json_response({"error": "invalid option"}, status=400))

    question = next((q for q in QUIZ_QUESTIONS if q["id"] == quiz_id), None)
    if not question:
        return _cors(web.json_response({"error": "quiz not found"}, status=404))
    if option_index < 0 or option_index >= len(question["options"]):
        return _cors(web.json_response({"error": "invalid option"}, status=400))

    uid = int(user["id"])
    await touch_user_from_webapp(uid, user.get("username", ""), user.get("first_name", ""))
    correct = option_index == question["correct"]
    await asyncio.to_thread(_save_quiz_attempt_sync, uid, quiz_id, option_index, correct)
    await log_view(uid, "quiz", quiz_id + (":correct" if correct else ":wrong"))

    return _cors(web.json_response({
        "correct": correct,
        "correct_option": question["correct"],
        "explanation": question["explanation"],
    }))



async def api_support(request: web.Request) -> web.Response:
    user, body = await _read_webapp_user(request)
    if not user or not user.get("id"):
        return _cors(web.json_response({"error": "invalid initData"}, status=401))
    text = str(body.get("text", "")).strip()[:4000]
    if not text:
        return _cors(web.json_response({"error": "empty message"}, status=400))
    uid = int(user["id"])
    username = user.get("username", "")
    first_name = user.get("first_name", "")
    ticket_id = await send_support_to_admins(type("WebUser", (), {"id": uid, "username": username, "first_name": first_name})(), text)
    await log_view(uid, "support", f"ticket:{ticket_id}")
    return _cors(web.json_response({"ok": True, "ticket_id": ticket_id}))

async def api_tab(request: web.Request) -> web.Response:
    user, body = await _read_webapp_user(request)
    if not user or not user.get("id"):
        return _cors(web.json_response({"error": "invalid initData"}, status=401))

    uid = int(user["id"])
    tab = str(body.get("tab", ""))[:200] or "unknown"
    await touch_user_from_webapp(uid, user.get("username", ""), user.get("first_name", ""))
    await log_view(uid, "webapp", tab)
    return _cors(web.json_response({"ok": True}))


def _admin_users_sync(query: str = "", limit: int = 200):
    query = query.strip().lower()
    limit = max(1, min(limit, 200))
    with db_connect() as conn:
        if query:
            rows = conn.execute(
                "SELECT u.user_id,u.username,u.first_name,u.last_seen,u.current_tab,u.current_tab_at,COUNT(v.id) "
                "FROM users u LEFT JOIN views v ON v.user_id=u.user_id "
                "WHERE LOWER(COALESCE(u.username,'')) LIKE ? OR LOWER(COALESCE(u.first_name,'')) LIKE ? "
                "OR CAST(u.user_id AS TEXT) LIKE ? GROUP BY u.user_id "
                "ORDER BY COALESCE(u.last_seen,'') DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT u.user_id,u.username,u.first_name,u.last_seen,u.current_tab,u.current_tab_at,COUNT(v.id) "
                "FROM users u LEFT JOIN views v ON v.user_id=u.user_id "
                "GROUP BY u.user_id ORDER BY COALESCE(u.last_seen,'') DESC LIMIT ?",
                (limit,),
            ).fetchall()

    keys = ["user_id", "username", "first_name", "last_seen", "current_tab", "current_tab_at", "views_count"]
    return [dict(zip(keys, row)) for row in rows]


def _admin_user_views_sync(user_id: int, limit: int = 50):
    with db_connect() as conn:
        user = conn.execute(
            "SELECT user_id,username,first_name,last_seen,current_tab,current_tab_at FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        views = conn.execute(
            "SELECT kind,title,viewed_at FROM views WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return user, views


async def api_admin(request: web.Request) -> web.Response:
    user, body = await _read_webapp_user(request)
    if not user or ADMIN_ID == 0 or int(user.get("id", 0)) != ADMIN_ID:
        return _cors(web.json_response({"error": "forbidden"}, status=403))

    action = str(body.get("action", "users"))

    if action == "users":
        users = await asyncio.to_thread(_admin_users_sync, str(body.get("query", ""))[:80], 200)
        with db_connect() as conn:
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_views = conn.execute("SELECT COUNT(*) FROM views").fetchone()[0]
        return _cors(web.json_response({
            "users": users,
            "total_users": total_users,
            "total_views": total_views,
        }))

    if action == "user":
        try:
            user_id = int(body.get("user_id"))
        except (TypeError, ValueError):
            return _cors(web.json_response({"error": "invalid user_id"}, status=400))
        raw_user, raw_views = await asyncio.to_thread(_admin_user_views_sync, user_id)
        if not raw_user:
            return _cors(web.json_response({"error": "user not found"}, status=404))
        keys = ["user_id", "username", "first_name", "last_seen", "current_tab", "current_tab_at"]
        return _cors(web.json_response({
            "user": dict(zip(keys, raw_user)),
            "views": [dict(zip(["kind", "title", "viewed_at"], row)) for row in raw_views],
        }))

    if action == "send":
        try:
            user_id = int(body.get("user_id"))
        except (TypeError, ValueError):
            return _cors(web.json_response({"error": "invalid user_id"}, status=400))
        message_text = str(body.get("text", ""))[:4000].strip()
        if not message_text:
            return _cors(web.json_response({"error": "empty message"}, status=400))
        try:
            await bot.send_message(user_id, message_text, parse_mode=None)
        except Exception as exc:
            return _cors(web.json_response({"error": str(exc)}, status=400))
        return _cors(web.json_response({"ok": True}))

    if action == "support":
        with db_connect() as conn:
            rows = conn.execute(
                "SELECT id,user_id,username,first_name,text,created_at,status FROM support_messages ORDER BY id DESC LIMIT 100"
            ).fetchall()
        keys = ["id","user_id","username","first_name","text","created_at","status"]
        return _cors(web.json_response({"tickets": [dict(zip(keys, r)) for r in rows]}))

    if action == "support_reply":
        try:
            ticket_id = int(body.get("ticket_id"))
        except (TypeError, ValueError):
            return _cors(web.json_response({"error": "invalid ticket_id"}, status=400))
        message_text = str(body.get("text", ""))[:4000].strip()
        if not message_text:
            return _cors(web.json_response({"error": "empty message"}, status=400))
        with db_connect() as conn:
            row = conn.execute("SELECT user_id FROM support_messages WHERE id=?", (ticket_id,)).fetchone()
        if not row:
            return _cors(web.json_response({"error": "ticket not found"}, status=404))
        try:
            await bot.send_message(int(row[0]), f"🆘 <b>Ответ поддержки</b>\n\n{html.escape(message_text)}", parse_mode="HTML")
        except Exception as exc:
            return _cors(web.json_response({"error": str(exc)}, status=400))
        with db_connect() as conn:
            conn.execute("UPDATE support_messages SET status='answered' WHERE id=?", (ticket_id,))
            conn.commit()
        return _cors(web.json_response({"ok": True}))

    return _cors(web.json_response({"error": "unknown action"}, status=400))


def build_webapp() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/api/debug-init", api_debug_init)
    app.router.add_get("/api/course", api_course)
    app.router.add_post("/api/me", api_me)
    app.router.add_get("/api/lesson/{section}/{index}", api_lesson)
    app.router.add_post("/api/progress", api_progress)
    app.router.add_post("/api/tab", api_tab)
    app.router.add_post("/api/support", api_support)
    app.router.add_post("/api/quiz", api_quiz_answer)
    app.router.add_post("/api/admin", api_admin)

    for path in ("/api/course", "/api/me", "/api/lesson/{section}/{index}", "/api/progress", "/api/tab", "/api/support", "/api/quiz", "/api/admin"):
        app.router.add_route("OPTIONS", path, api_options)

    if os.path.isdir(WEBAPP_DIR):
        async def index(request: web.Request) -> web.Response:
            return web.FileResponse(os.path.join(WEBAPP_DIR, "index.html"))

        # /, /index.html и /webapp/ открывают само приложение, а не Index of /.
        app.router.add_get("/", index)
        app.router.add_get("/index.html", index)
        app.router.add_get("/webapp/", index)
        app.router.add_get("/webapp/index.html", index)

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
                menu_button=MenuButtonWebApp(text="Курс", web_app=WebAppInfo(url=MINIAPP_LAUNCH_URL))
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