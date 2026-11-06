import re

import pytest
import requests

from api.services.sms import InMemorySmsSender


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Salon.save() ходит в геокодер Яндекса: в тестах сети нет."""

    def fail(*args, **kwargs):
        raise requests.ConnectionError("сеть отключена в тестах")

    monkeypatch.setattr("api.models.requests.get", fail)


@pytest.fixture(autouse=True)
def sms_outbox():
    """Очищает и отдаёт «исходящие SMS» тестового отправителя."""
    InMemorySmsSender.outbox.clear()
    return InMemorySmsSender.outbox


@pytest.fixture
def sent_code(sms_outbox):
    """Возвращает код из последней отправленной SMS."""

    def get() -> str:
        _phone, text = sms_outbox[-1]
        return re.search(r"\d+", text).group()

    return get


@pytest.fixture
def django_client_factory():
    """Создаёт независимые клиенты (отдельные сессии) для сценариев с несколькими браузерами."""
    from django.test import Client as DjangoClient

    return DjangoClient
