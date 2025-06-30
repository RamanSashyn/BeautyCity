# BeautyCity

Веб-платформа для записи в салоны красоты. Проект на Django, с использованием HTML/JS шаблонов.

## Структура проекта

```

BeautyCity/
├── api/                  # Django-приложение с моделями и логикой API
├── beautycity/           # Конфигурация проекта: настройки, urls, wsgi
├── manage.py             # Управляющий скрипт Django
├── static/               # Общая директория со статикой (css, js, img)
├── staticfiles/          # Сборка статики после collectstatic
├── templates/            # HTML-шаблоны сайта
├── db.sqlite3            # База данных (dev)
├── requirements.txt      # Список зависимостей проекта
├── .env                  # Переменные окружения (не отслеживается Git)
└── .gitignore            # Игнорируемые файлы Git

```

## Запуск проекта

1. **Клонируй репозиторий:**

```bash
git clone https://github.com/yourusername/BeautyCity.git
cd BeautyCity
````

2. **Создай и активируй виртуальное окружение:**

```bash
python3 -m venv venv
source venv/bin/activate  # для Linux/MacOS
venv\Scripts\activate     # для Windows
```

3. **Установи зависимости:**

```bash
pip install -r requirements.txt
```

3. **Настройка переменных окружения**

Создайте файл `.env` в корне проекта:

```
SECRET_KEY="...."
DEBUG=True
ALLOWED_HOSTS=example.com,localhost,127.0.0.1

# Настройки базы данных
DATABASE_URL="postgres://user:pass@host:5432/dbname"
DATABASE_URL="sqlite:///$(pwd)/db.sqlite3"

TIME_ZONE='Asia/Krasnoyarsk'
LANGUAGE_CODE='ru-ru'

STATIC_URL='/static/'
STATIC_ROOT='staticfiles'
STATICFILES_DIRS='static'

MEDIA_URL='/media/'
MEDIA_ROOT='media'

YANDEX_GEOCODE_KEY=ваш_yandex_geocode_ключ
YANDEX_STATICMAP_KEY=ваш_yandex_staticmap_ключ
```

Получите ключи Яндекс.Карт по ссылке: [https://developer.tech.yandex.ru/services/](https://developer.tech.yandex.ru/services/)

4. **Примени миграции:**

```bash
python manage.py migrate
```

5. **Запусти сервер разработки:**

```bash
python manage.py runserver
```

6. **Открой сайт в браузере:**

[http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## Подготовка данных из шаблонов

Проект умеет **извлекать данные из HTML и JS** и сохранять их в `data/` в формате JSON. Эти данные затем импортируются в базу.

### 1. Извлечение данных:

```bash
# Извлечь услуги и салоны из index.html
python extract_data.py

# Извлечь мастеров из JS (main.js)
python extract_masters.py

# Извлечь услуги по категориям из service.html
python extract_services_by_category.py
```

Все JSON сохраняются в папку `data/`.

---

### 2. Загрузка данных в базу

После выполнения миграций, импортируй данные:

```bash
python load_initial_data.py
```

Это создаст:

* Салоны (из `salons.json`)
* Услуги (из `services.json`)
* Мастеров с фото (из `masters.json`)
