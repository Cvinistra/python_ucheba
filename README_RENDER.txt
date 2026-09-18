Python Academy Mini App v3

Что добавлено:
- кнопка меню Telegram открывает /index.html, а / тоже открывает приложение;
- вкладка «Фреймворки»: у каждого фреймворка доступны команды, по каждой можно открыть описание «что делает» и скопировать команду;
- вкладка «Мини-коды»: калькулятор, turtle-квадрат, turtle-спираль, игра «Угадай число», кубик, To-Do;
- админская вкладка видна только ADMIN_ID;
- админ может смотреть список пользователей, текущую вкладку, число действий, последние действия и отправлять сообщение пользователю;
- текущий экран Mini App пишется в users.current_tab/current_tab_at;
- просмотр урока пишется в views как topic, поэтому прогресс внутри Mini App учитывается;
- Mini App передаёт Telegram initData в заголовке, сервер его проверяет.

Render:
Build Command: pip install -r requirements.txt
Start Command: python bot_final.py

Environment:
BOT_TOKEN=...
ADMIN_ID=...
MINIAPP_URL=https://python-ucheba.onrender.com/

WEBAPP_HOST/WEBAPP_PORT задавать не нужно: код использует PORT Render (10000 по умолчанию).
