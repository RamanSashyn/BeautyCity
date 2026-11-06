"""Фильтры каталога (/api/filter/) и выдача слотов (/api/slots-by-specialist/)."""

from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from api.models import Appointment, Salon, Service, Specialist, TimeSlot

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(db):
    """Два салона, две услуги и два мастера.

    Анна работает в «Центре» и делает маникюр (60 мин) и стрижку (30 мин),
    Борис работает в «Севере» и делает только стрижку.
    """
    centre = Salon.objects.create(name="Центр", address="ул. А, 1", phone_number="+7")
    north = Salon.objects.create(name="Север", address="ул. Б, 2", phone_number="+7")
    manicure = Service.objects.create(name="Маникюр", base_price=1500, duration_minutes=60)
    haircut = Service.objects.create(name="Стрижка", base_price=900, duration_minutes=30)
    anna = Specialist.objects.create(name="Анна")
    anna.salons.add(centre)
    anna.services.add(manicure, haircut)
    boris = Specialist.objects.create(name="Борис")
    boris.salons.add(north)
    boris.services.add(haircut)
    return SimpleNamespace(
        centre=centre,
        north=north,
        manicure=manicure,
        haircut=haircut,
        anna=anna,
        boris=boris,
        day=timezone.localdate() + timedelta(days=1),
    )


def add_slot(world, specialist, salon, hour, minute=0, booked=False):
    return TimeSlot.objects.create(
        date=world.day,
        time=time(hour, minute),
        specialist=specialist,
        salon=salon,
        is_booked=booked,
    )


def add_appointment(world, specialist, salon, service, hour, minute=0, minutes=60):
    start = timezone.make_aware(datetime.combine(world.day, time(hour, minute)))
    return Appointment.objects.create(
        guest_name="Гость",
        guest_phone="+79990000000",
        specialist=specialist,
        service=service,
        salon=salon,
        date_time_start=start,
        date_time_end=start + timedelta(minutes=minutes),
        status="booked",
    )


def ids(payload, key):
    return {item["id"] for item in payload[key]}


def get_filter(client, **params):
    response = client.get("/api/filter/", params)
    assert response.status_code == 200
    return response.json()


class TestФильтрПоСущностям:
    def test_без_параметров_отдаёт_всё(self, client, world):
        data = get_filter(client)

        assert ids(data, "salons") == {world.centre.id, world.north.id}
        assert ids(data, "services") == {world.manicure.id, world.haircut.id}
        assert ids(data, "specialists") == {world.anna.id, world.boris.id}

    def test_мастер_сужает_салоны_и_услуги(self, client, world):
        data = get_filter(client, specialist=world.anna.id)

        assert ids(data, "salons") == {world.centre.id}
        assert ids(data, "services") == {world.manicure.id, world.haircut.id}
        assert ids(data, "specialists") == {world.anna.id}

    def test_услуга_сужает_салоны_и_мастеров(self, client, world):
        data = get_filter(client, service=world.manicure.id)

        assert ids(data, "salons") == {world.centre.id}
        assert ids(data, "services") == {world.manicure.id}
        assert ids(data, "specialists") == {world.anna.id}

    def test_общая_услуга_оставляет_обоих_мастеров(self, client, world):
        data = get_filter(client, service=world.haircut.id)

        assert ids(data, "salons") == {world.centre.id, world.north.id}
        assert ids(data, "specialists") == {world.anna.id, world.boris.id}

    def test_салон_сужает_услуги_и_мастеров(self, client, world):
        data = get_filter(client, salon=world.north.id)

        assert ids(data, "salons") == {world.north.id}
        assert ids(data, "services") == {world.haircut.id}
        assert ids(data, "specialists") == {world.boris.id}

    def test_мастер_и_услуга_вместе(self, client, world):
        data = get_filter(client, specialist=world.boris.id, service=world.haircut.id)

        assert ids(data, "salons") == {world.north.id}
        assert ids(data, "services") == {world.haircut.id}
        assert ids(data, "specialists") == {world.boris.id}

    def test_неизвестный_мастер_игнорируется(self, client, world):
        data = get_filter(client, specialist=9999)

        assert ids(data, "specialists") == {world.anna.id, world.boris.id}

    def test_post_не_разрешён(self, client):
        assert client.post("/api/filter/").status_code == 405


class TestФильтрПоВремени:
    def test_отдаёт_салоны_и_мастеров_со_свободным_слотом(self, client, world):
        add_slot(world, world.anna, world.centre, 10)
        add_slot(world, world.boris, world.north, 10)
        add_slot(world, world.boris, world.north, 11)

        data = get_filter(client, date=world.day.isoformat(), time="10:00")

        assert ids(data, "salons") == {world.centre.id, world.north.id}
        assert ids(data, "specialists") == {world.anna.id, world.boris.id}
        assert ids(data, "services") == {world.manicure.id, world.haircut.id}

    def test_занятый_слот_не_учитывается(self, client, world):
        add_slot(world, world.anna, world.centre, 10, booked=True)
        add_slot(world, world.boris, world.north, 10)

        data = get_filter(client, date=world.day.isoformat(), time="10:00")

        assert ids(data, "specialists") == {world.boris.id}

    def test_салон_ограничивает_выдачу(self, client, world):
        add_slot(world, world.anna, world.centre, 10)
        add_slot(world, world.boris, world.north, 10)

        data = get_filter(client, date=world.day.isoformat(), time="10:00", salon=world.north.id)

        assert ids(data, "salons") == {world.north.id}
        assert ids(data, "specialists") == {world.boris.id}

    def test_услуга_оставляет_только_мастеров_с_этой_услугой(self, client, world):
        add_slot(world, world.anna, world.centre, 10)
        add_slot(world, world.boris, world.north, 10)

        data = get_filter(
            client, date=world.day.isoformat(), time="10:00", service=world.manicure.id
        )

        assert ids(data, "specialists") == {world.anna.id}

    def test_пересечение_с_записью_исключает_слот(self, client, world):
        add_slot(world, world.anna, world.centre, 10)
        add_appointment(world, world.anna, world.centre, world.haircut, 10, 30, minutes=30)

        data = get_filter(
            client, date=world.day.isoformat(), time="10:00", service=world.manicure.id
        )

        assert data == {"salons": [], "services": [], "specialists": []}

    def test_услуга_короче_свободного_окна_проходит(self, client, world):
        add_slot(world, world.anna, world.centre, 10)
        add_appointment(world, world.anna, world.centre, world.haircut, 10, 30, minutes=30)

        data = get_filter(
            client, date=world.day.isoformat(), time="10:00", service=world.haircut.id
        )

        assert ids(data, "specialists") == {world.anna.id}

    def test_неверное_время_игнорируется(self, client, world):
        data = get_filter(client, date=world.day.isoformat(), time="25:99")

        assert ids(data, "specialists") == {world.anna.id, world.boris.id}

    def test_формат_даты_день_месяц_год(self, client, world):
        add_slot(world, world.anna, world.centre, 10)

        data = get_filter(client, date=world.day.strftime("%d.%m.%Y"), time="10:00")

        assert ids(data, "specialists") == {world.anna.id}

    def test_мусор_вместо_даты_означает_сегодня(self, client, world):
        add_slot(world, world.anna, world.centre, 10)

        data = get_filter(client, date="завтра", time="10:00")

        assert data == {"salons": [], "services": [], "specialists": []}

    def test_прошедшее_время_сегодня_даёт_пустой_ответ(self, client, world, monkeypatch):
        frozen = datetime(2030, 1, 10, 12, 0, tzinfo=UTC)
        monkeypatch.setattr(timezone, "now", lambda: frozen)
        TimeSlot.objects.create(
            date=frozen.date(), time=time(10), specialist=world.anna, salon=world.centre
        )

        data = get_filter(client, date="2030-01-10", time="10:00")

        assert data == {"salons": [], "services": [], "specialists": []}


class TestФильтрПоСлоту:
    def test_слот_определяет_салон_мастера_и_его_услуги(self, client, world):
        slot = add_slot(world, world.anna, world.centre, 10)

        data = get_filter(client, slot_id=slot.id, date=world.day.isoformat())

        assert ids(data, "salons") == {world.centre.id}
        assert ids(data, "specialists") == {world.anna.id}
        assert ids(data, "services") == {world.manicure.id, world.haircut.id}

    def test_слот_на_другую_дату_игнорируется(self, client, world):
        slot = add_slot(world, world.anna, world.centre, 10)
        other_day = (world.day + timedelta(days=1)).isoformat()

        data = get_filter(client, slot_id=slot.id, date=other_day)

        assert ids(data, "specialists") == {world.anna.id, world.boris.id}

    def test_занятый_слот_игнорируется(self, client, world):
        slot = add_slot(world, world.anna, world.centre, 10, booked=True)

        data = get_filter(client, slot_id=slot.id, date=world.day.isoformat())

        assert ids(data, "specialists") == {world.anna.id, world.boris.id}


def get_slots(client, **params):
    response = client.get("/api/slots-by-specialist/", params)
    assert response.status_code == 200
    return response.json()


class TestВыдачаСлотов:
    def test_свободные_слоты_мастера_по_времени(self, client, world):
        add_slot(world, world.anna, world.centre, 11)
        add_slot(world, world.anna, world.centre, 10)
        add_slot(world, world.anna, world.centre, 12, booked=True)
        add_slot(world, world.boris, world.north, 10)

        groups = get_slots(
            client,
            date=world.day.isoformat(),
            specialist_id=world.anna.id,
            salon_id=world.centre.id,
        )

        assert [(g["time"], g["hour"]) for g in groups] == [("10:00", 10), ("11:00", 11)]
        assert {s["specialist_name"] for g in groups for s in g["slots"]} == {"Анна"}

    def test_без_мастера_слоты_группируются_по_времени(self, client, world):
        slot_anna = add_slot(world, world.anna, world.centre, 10)
        slot_boris = add_slot(world, world.boris, world.north, 10)
        add_slot(world, world.boris, world.north, 15)

        groups = get_slots(client, date=world.day.isoformat())

        assert [g["time"] for g in groups] == ["10:00", "15:00"]
        first = groups[0]["slots"]
        assert {s["id"] for s in first} == {slot_anna.id, slot_boris.id}
        assert {s["specialist_name"] for s in first} == {"Анна", "Борис"}

    def test_с_услугой_слоты_пересекающиеся_с_записью_скрываются(self, client, world):
        add_slot(world, world.anna, world.centre, 10)
        add_slot(world, world.anna, world.centre, 10, 30)
        add_slot(world, world.anna, world.centre, 12)
        add_appointment(world, world.anna, world.centre, world.manicure, 11, 0, minutes=60)

        slots = get_slots(
            client,
            date=world.day.isoformat(),
            specialist_id=world.anna.id,
            service_id=world.manicure.id,
        )

        # 10:00–11:00 примыкает к записи и проходит, 10:30–11:30 пересекается с ней.
        assert [s["time"] for s in slots] == ["10:00", "12:00"]

    def test_формат_даты_день_месяц_год(self, client, world):
        add_slot(world, world.anna, world.centre, 10)

        groups = get_slots(client, date=world.day.strftime("%d.%m.%Y"))

        assert [g["time"] for g in groups] == ["10:00"]

    def test_без_даты_берётся_сегодня(self, client, world):
        add_slot(world, world.anna, world.centre, 10)

        assert get_slots(client) == []

    def test_post_не_разрешён(self, client):
        assert client.post("/api/slots-by-specialist/").status_code == 405
