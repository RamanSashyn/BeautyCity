#️ BeautyCity

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

## Что уже сделано

* 🔹 Проект структурирован по Django-стандартам
* 🔹 Шаблоны и статика разделены
* 🔹 Подключена верстка
* 🔹 Обработана статика: все пути `img/`, `css/`, `js/` обновлены под Django
* 🔹 Настроен `.gitignore` и `requirements.txt`

## План на будущее

* Модели для услуг, мастеров, расписания
* Админка с кастомной логикой
* Форма записи и валидация
* API для интеграции с фронтом

## Советы

* Все шаблоны лежат в `templates/`
* Вся статика — в `static/`