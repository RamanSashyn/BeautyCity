FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Статика собирается при сборке образа. Настройки читают переменные окружения,
# поэтому на время сборки подставляются фиктивные значения, в образ они не попадают.
RUN SECRET_KEY=build DATABASE_URL=sqlite://:memory: \
    YANDEX_GEOCODE_KEY=build YANDEX_STATICMAP_KEY=build \
    python manage.py collectstatic --noinput

# Приложение работает не от root. Писать ему нужно только в каталог загружаемых файлов.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media \
    && chown app:app /app/media
USER app

EXPOSE 8000

CMD ["gunicorn", "beautycity.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
