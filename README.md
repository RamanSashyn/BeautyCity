# BeautyCity

Веб-платформа для записи в салоны красоты. Проект на Django, с использованием HTML/JS шаблонов.

## Структура проекта

```
BeautyCity/
├── api/                  # Приложение: модели, формы, представления, сервисы и тесты
│   ├── views/            # Представления: вход, каталог, запись, личный кабинет
│   ├── services/         # Логика без HTTP: слоты и бронирование, фильтры, коды входа, SMS
│   └── tests/            # Тесты pytest
├── beautycity/           # Конфигурация проекта: настройки, urls, wsgi
├── static/               # Статика (css, js, img)
├── templates/            # HTML-шаблоны сайта
├── manage.py             # Управляющий скрипт Django
├── requirements.txt      # Зависимости приложения
├── requirements-dev.txt  # Зависимости для разработки: pytest, ruff
├── pyproject.toml        # Настройки ruff, pytest и coverage
└── .env                  # Переменные окружения (не отслеживается Git)
```

## Запуск проекта

1. **Клонируй репозиторий:**

```bash
git clone https://github.com/RamanSashyn/BeautyCity.git
cd BeautyCity
```

2. **Создай и активируй виртуальное окружение:**

```bash
python3 -m venv venv
source venv/bin/activate  # для Linux/macOS
venv\Scripts\activate     # для Windows
```

3. **Установи зависимости:**

```bash
pip install -r requirements.txt
```

4. **Настрой переменные окружения.** Создай файл `.env` в корне проекта (шаблон лежит в `.env.example`):

```
SECRET_KEY="...."
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
YANDEX_GEOCODE_KEY=ваш_yandex_geocode_ключ
YANDEX_STATICMAP_KEY=ваш_yandex_staticmap_ключ
```

| Переменная | Назначение |
| --- | --- |
| `SECRET_KEY` | секретный ключ Django (обязательна) |
| `DATABASE_URL` | адрес базы: `sqlite:///db.sqlite3` или `postgres://user:pass@host:5432/dbname` (обязательна) |
| `YANDEX_GEOCODE_KEY`, `YANDEX_STATICMAP_KEY` | ключи Яндекс.Карт, [получить](https://developer.tech.yandex.ru/services/) (обязательны) |
| `DEBUG` | `True` для разработки, по умолчанию `False` |
| `ALLOWED_HOSTS` | хосты через запятую, нужны при `DEBUG=False` |
| `TIME_ZONE`, `LANGUAGE_CODE` | по умолчанию `Asia/Krasnoyarsk` и `ru-ru` |
| `MEDIA_URL`, `MEDIA_ROOT` | адрес и каталог загружаемых файлов, по умолчанию `/media/` и `media` |
| `SMS_SENDER` | класс, отправляющий SMS с кодом входа, см. ниже |

5. **Примени миграции и создай администратора:**

```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Запусти сервер разработки:**

```bash
python manage.py runserver
```

7. **Открой сайт в браузере:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## Запуск через Docker

Нужны Docker и Docker Compose. Compose поднимает приложение (gunicorn) и PostgreSQL, миграции
применяются при старте.

```bash
cp .env.example .env      # затем задай SECRET_KEY, POSTGRES_PASSWORD и ключи Яндекса
docker compose up --build
```

Сайт откроется на [http://localhost:8000/](http://localhost:8000/). Администратора создают так:

```bash
docker compose exec web python manage.py createsuperuser
```

Адрес базы compose собирает из переменных `POSTGRES_DB`, `POSTGRES_USER` и `POSTGRES_PASSWORD`,
поэтому `DATABASE_URL` в `.env` для Docker задавать не нужно. База и загруженные файлы лежат в
томах `postgres_data` и `media`. Статику отдаёт WhiteNoise, а файлы из `media` в режиме
`DEBUG=False` должен раздавать внешний прокси.

## Данные

Салоны, услуги, мастеров и расписание заводят в админке: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).
Слоты времени для записи создаются автоматически при сохранении расписания мастера.

## Вход по номеру телефона

Вход идёт в два шага: клиент вводит номер, ему приходит одноразовый код, и только после
верного кода он попадает в личный кабинет.

- код состоит из 6 цифр и действует 5 минут, в базе хранится только его хеш;
- на один код даётся 5 попыток ввода;
- код можно запрашивать не чаще раза в минуту, не более 5 раз в час на номер и 20 раз в час с одного IP.

Отправкой SMS занимается класс из настройки `SMS_SENDER`. По умолчанию это
`api.services.sms.ConsoleSmsSender`: код выводится в лог, SMS не уходит. Этого достаточно для
разработки, но в продакшене код в логах оказываться не должен, поэтому нужно подключить
реального провайдера. Для этого напиши наследника `SmsSender`, возьми ключи из переменных
окружения и укажи путь к классу:

```python
from api.services.sms import SmsSender


class MyProviderSender(SmsSender):
    def send(self, phone: str, message: str) -> None:
        ...  # вызов API провайдера
```

```
SMS_SENDER=mypackage.sms.MyProviderSender
```

Ограничение по IP смотрит на адрес, с которого пришёл запрос. За обратным прокси это будет
адрес самого прокси, поэтому его нужно настроить так, чтобы Django видел настоящий адрес клиента.

## Тесты и проверки

```bash
pip install -r requirements-dev.txt
pytest --cov=api          # тесты и покрытие
ruff check .              # линтер
ruff format --check .     # проверка форматирования
python manage.py check
python manage.py makemigrations --check --dry-run
```

Тесты не требуют `.env`: по умолчанию они работают на SQLite в памяти. Чтобы прогнать их на
PostgreSQL, как в CI, задай `DATABASE_URL`. Эти же проверки запускаются в GitHub Actions на
каждый push в `master` и каждый pull request.
