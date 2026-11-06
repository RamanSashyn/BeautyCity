import re
from datetime import time, timedelta

import pytest
import requests
from django.test import Client as DjangoClient
from django.utils import timezone

from api.models import Appointment, Client, Salon, Service, Specialist, TimeSlot
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
    return DjangoClient


@pytest.fixture
def salon(db):
    return Salon.objects.create(
        name="Центр", address="Красноярск, пр. Мира, 1", phone_number="+73912000000"
    )


@pytest.fixture
def service(db):
    return Service.objects.create(name="Маникюр", base_price=1500, duration_minutes=60)


@pytest.fixture
def specialist(salon, service):
    specialist = Specialist.objects.create(name="Анна")
    specialist.salons.add(salon)
    specialist.services.add(service)
    return specialist


@pytest.fixture
def make_slot(specialist, salon):
    """Создаёт свободный слот: по умолчанию завтра в 10:00 у основного мастера."""

    def make(hour=10, minute=0, day_offset=1, **kwargs):
        return TimeSlot.objects.create(
            date=timezone.localdate() + timedelta(days=day_offset),
            time=time(hour, minute),
            specialist=kwargs.get("specialist", specialist),
            salon=kwargs.get("salon", salon),
        )

    return make


@pytest.fixture
def slot(make_slot):
    return make_slot()


@pytest.fixture
def owner(db):
    return Client.objects.create(phone="+79990000001", name="Ирина")


@pytest.fixture
def stranger(db):
    return Client.objects.create(phone="+79990000002", name="Пётр")


@pytest.fixture
def make_appointment(specialist, service, salon):
    """Создаёт запись на завтра в 10:00 (или позже, если указан day_offset)."""

    def make(client_obj, **kwargs):
        start = timezone.localtime().replace(hour=10, minute=0, second=0, microsecond=0)
        start += timedelta(days=kwargs.pop("day_offset", 1))
        return Appointment.objects.create(
            client=client_obj,
            specialist=kwargs.pop("specialist", specialist),
            service=kwargs.pop("service", service),
            salon=kwargs.pop("salon", salon),
            date_time_start=start,
            date_time_end=start + timedelta(minutes=60),
            status="booked",
            **kwargs,
        )

    return make


@pytest.fixture
def login():
    """Кладёт клиента в сессию так, как это делает успешный вход по коду."""

    def do_login(django_client, client_obj):
        session = django_client.session
        session["client_id"] = client_obj.id
        session.save()

    return do_login
