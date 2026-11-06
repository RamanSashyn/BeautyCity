"""Публичные страницы: главная, выбор услуги, запись, модель Salon."""

from datetime import time, timedelta

import pytest
from django.utils import timezone

from api.models import Category, Salon, TimeSlot

pytestmark = pytest.mark.django_db


class FakeGeocoderResponse:
    def __init__(self, pos="92.85 56.01"):
        self.pos = pos

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "response": {
                "GeoObjectCollection": {
                    "featureMember": [{"GeoObject": {"Point": {"pos": self.pos}}}]
                }
            }
        }


@pytest.fixture
def geocoder_ok(monkeypatch):
    monkeypatch.setattr("api.models.requests.get", lambda *args, **kwargs: FakeGeocoderResponse())


def test_главная_без_салонов_открывается_без_карты(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.context["static_map_url"] is None
    assert response.context["points"] == []


def test_главная_строит_карту_по_координатам_салонов(client, geocoder_ok):
    Salon.objects.create(name="Центр", address="Красноярск", phone_number="+7")

    context = client.get("/").context

    assert context["points"] == [{"lat": 56.01, "lon": 92.85, "hint": "Центр"}]
    assert "pt=92.85%2C56.01%2Cpm2rdm" in context["static_map_url"]
    assert "apikey=test" in context["static_map_url"]


def test_салон_без_ответа_геокодера_сохраняется_без_координат(salon):
    assert salon.pk is not None
    assert salon.lat is None
    assert salon.lon is None


def test_салон_получает_координаты_от_геокодера(geocoder_ok):
    salon = Salon.objects.create(name="Север", address="Красноярск", phone_number="+7")

    assert (salon.lon, salon.lat) == (92.85, 56.01)


def test_страница_выбора_услуги_показывает_только_будущие_свободные_слоты(
    client, salon, specialist, make_slot
):
    free = make_slot(10)
    booked = make_slot(11)
    booked.is_booked = True
    booked.save()
    TimeSlot.objects.create(
        date=timezone.localdate() - timedelta(days=1),
        time=time(9),
        specialist=specialist,
        salon=salon,
    )

    context = client.get("/api/service/").context

    assert list(context["slots"]) == [free]
    assert list(context["morning_slots"]) == [free]
    assert not list(context["evening_slots"])


def test_страница_выбора_услуги_показывает_категории_с_услугами(client, service):
    category = Category.objects.create(name="Ногти")
    service.category = category
    service.save()
    Category.objects.create(name="Пустая")

    context = client.get("/api/service/").context

    assert [c.name for c in context["categories"]] == ["Ногти"]


def test_выбор_слота_только_через_post(client):
    response = client.get("/api/book/")

    assert response.json()["success"] is False


def test_подтверждение_без_выбранного_слота_ведёт_к_выбору(client):
    response = client.get("/api/service-finally/")

    assert response.status_code == 302
    assert response.url == "/api/service/"
