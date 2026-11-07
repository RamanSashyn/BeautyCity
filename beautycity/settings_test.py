"""Настройки для тестов: не требуют ни .env, ни внешних сервисов.

Значения берутся из окружения, а если их там нет, подставляются безопасные
тестовые (SQLite в памяти, фиктивные ключи Яндекса). В CI база переопределяется
переменной DATABASE_URL.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("YANDEX_GEOCODE_KEY", "test")
os.environ.setdefault("YANDEX_STATICMAP_KEY", "test")

from .settings import *  # noqa: E402, F403

SMS_SENDER = "api.services.sms.InMemorySmsSender"
