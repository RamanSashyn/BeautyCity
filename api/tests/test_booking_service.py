"""Сервис записи: разбор даты, пересечения и подбор свободных слотов."""

import threading
from datetime import date, datetime, time, timedelta

import pytest
from django.db import connection, connections
from django.utils import timezone

from api.models import Appointment, Salon, Service, Specialist, TimeSlot
from api.services import booking

pytestmark = pytest.mark.django_db

DAY = date(2030, 5, 20)


def aware(hour, minute=0, day=DAY):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def add_appointment(specialist, service, salon, hour, minute=0, minutes=60):
    start = aware(hour, minute)
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


def add_slot(specialist, salon, hour, minute=0, day=DAY):
    return TimeSlot.objects.create(
        date=day, time=time(hour, minute), specialist=specialist, salon=salon
    )


class TestParseDateParam:
    def test_iso_формат(self):
        assert booking.parse_date_param("2030-05-20") == DAY

    def test_день_месяц_год(self):
        assert booking.parse_date_param("20.05.2030") == DAY

    @pytest.mark.parametrize("value", [None, "", "завтра", "2030-02-30", "32.13.2030"])
    def test_пустое_и_нечитаемое_значение_означает_сегодня(self, value):
        assert booking.parse_date_param(value) == timezone.localdate()


class TestOverlaps:
    busy = [(aware(11), aware(12))]

    def test_пересечение_в_начале(self):
        assert booking.overlaps(aware(10, 30), aware(11, 30), self.busy)

    def test_пересечение_в_конце(self):
        assert booking.overlaps(aware(11, 30), aware(12, 30), self.busy)

    def test_услуга_внутри_занятого_времени(self):
        assert booking.overlaps(aware(11, 15), aware(11, 45), self.busy)

    def test_услуга_накрывает_запись(self):
        assert booking.overlaps(aware(10), aware(13), self.busy)

    def test_встык_до_записи_не_пересекается(self):
        assert not booking.overlaps(aware(10), aware(11), self.busy)

    def test_встык_после_записи_не_пересекается(self):
        assert not booking.overlaps(aware(12), aware(13), self.busy)

    def test_без_записей_пересечений_нет(self):
        assert not booking.overlaps(aware(10), aware(11), [])


def test_интервал_услуги_строится_от_слота_с_учётом_длительности():
    start, end = booking.slot_interval(DAY, time(10, 30), 90)

    assert start == aware(10, 30)
    assert end == aware(12)
    assert timezone.is_aware(start)


def test_занятость_мастера_учитывает_только_его_записи_за_день(salon, service, specialist):
    other = Specialist.objects.create(name="Борис")
    add_appointment(specialist, service, salon, 10)
    add_appointment(other, service, salon, 11)

    busy = booking.busy_intervals(specialist.id, DAY)

    assert busy == [(aware(10), aware(11))]
    assert booking.busy_intervals(specialist.id, DAY + timedelta(days=1)) == []


class TestFreeSlots:
    def test_только_свободные_слоты_нужного_дня(self, salon, specialist):
        free = add_slot(specialist, salon, 10)
        taken = add_slot(specialist, salon, 11)
        TimeSlot.objects.filter(pk=taken.pk).update(is_booked=True)
        add_slot(specialist, salon, 10, day=DAY + timedelta(days=1))

        assert list(booking.free_slots(DAY)) == [free]

    def test_фильтры_по_мастеру_и_салону(self, salon, specialist):
        other_salon = Salon.objects.create(name="Север", address="ул. Б, 2", phone_number="+7")
        other = Specialist.objects.create(name="Борис")
        mine = add_slot(specialist, salon, 10)
        add_slot(other, salon, 10)
        add_slot(specialist, other_salon, 11)

        found = booking.free_slots(DAY, specialist_id=specialist.id, salon_id=salon.id)

        assert list(found) == [mine]


class TestExcludeOverlapping:
    def test_слот_пересекающийся_с_записью_отбрасывается(self, salon, service, specialist):
        add_appointment(specialist, service, salon, 11, minutes=60)
        before = add_slot(specialist, salon, 10)
        overlapping = add_slot(specialist, salon, 10, 30)
        after = add_slot(specialist, salon, 12)

        suitable = booking.exclude_overlapping([before, overlapping, after], DAY, service)

        assert suitable == [before, after]

    def test_записи_одного_мастера_не_мешают_другому(self, salon, service, specialist):
        other = Specialist.objects.create(name="Борис")
        add_appointment(other, service, salon, 10)
        slot = add_slot(specialist, salon, 10)

        assert booking.exclude_overlapping([slot], DAY, service) == [slot]

    def test_услуга_через_полночь_отбрасывается_только_при_within_day(
        self, salon, service, specialist
    ):
        late = add_slot(specialist, salon, 23, 30)

        assert booking.exclude_overlapping([late], DAY, service) == [late]
        assert booking.exclude_overlapping([late], DAY, service, within_day=True) == []


class TestBookSlot:
    def book(self, slot, specialist, service, salon, **kwargs):
        return booking.book_slot(
            slot_id=slot.id, specialist=specialist, service=service, salon=salon, **kwargs
        )

    def test_запись_клиента_занимает_слот(self, owner, salon, service, specialist):
        slot = add_slot(specialist, salon, 10)

        appointment = self.book(slot, specialist, service, salon, client=owner)

        slot.refresh_from_db()
        assert slot.is_booked
        assert appointment.client == owner
        assert appointment.status == "booked"
        assert appointment.source == "site"
        assert appointment.date_time_start == aware(10)
        assert appointment.date_time_end == aware(11)

    def test_гостевая_запись_хранит_контакты_в_записи(self, salon, service, specialist):
        slot = add_slot(specialist, salon, 10)

        appointment = self.book(
            slot, specialist, service, salon, guest_name="Мария", guest_phone="+79990001122"
        )

        assert appointment.client is None
        assert (appointment.guest_name, appointment.guest_phone) == ("Мария", "+79990001122")

    def test_на_один_слот_нельзя_записаться_дважды(
        self, owner, stranger, salon, service, specialist
    ):
        slot = add_slot(specialist, salon, 10)
        self.book(slot, specialist, service, salon, client=owner)

        with pytest.raises(booking.SlotUnavailable):
            self.book(slot, specialist, service, salon, client=stranger)

        assert Appointment.objects.count() == 1
        assert Appointment.objects.get().client == owner

    def test_длинная_услуга_занимает_все_покрытые_слоты(
        self, owner, stranger, salon, service, specialist
    ):
        first = add_slot(specialist, salon, 10)
        second = add_slot(specialist, salon, 10, 30)
        service.duration_minutes = 60
        service.save()
        self.book(first, specialist, service, salon, client=owner)

        second.refresh_from_db()
        assert second.is_booked
        with pytest.raises(booking.SlotUnavailable):
            self.book(second, specialist, service, salon, client=stranger)

    def test_несуществующий_слот_недоступен(self, owner, salon, service, specialist):
        with pytest.raises(booking.SlotUnavailable):
            booking.book_slot(
                slot_id=999999, specialist=specialist, service=service, salon=salon, client=owner
            )

    def test_мастер_без_этой_услуги_не_принимает_запись(self, owner, salon, specialist):
        foreign = Service.objects.create(name="Окрашивание", base_price=3000, duration_minutes=120)
        slot = add_slot(specialist, salon, 10)

        with pytest.raises(booking.ServiceNotProvided):
            self.book(slot, specialist, foreign, salon, client=owner)

        slot.refresh_from_db()
        assert not slot.is_booked
        assert not Appointment.objects.exists()

    @pytest.mark.django_db(transaction=True)
    def test_параллельные_попытки_записать_один_слот_дают_одну_запись(
        self, owner, stranger, salon, service, specialist
    ):
        if connection.vendor != "postgresql":
            pytest.skip("блокировка строк проверяется только на PostgreSQL")
        slot = add_slot(specialist, salon, 10)
        barrier = threading.Barrier(2)
        results = []

        def attempt(client):
            try:
                barrier.wait()
                self.book(slot, specialist, service, salon, client=client)
                results.append("ok")
            except booking.SlotUnavailable:
                results.append("занято")
            finally:
                connections.close_all()

        threads = [threading.Thread(target=attempt, args=(c,)) for c in (owner, stranger)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert sorted(results) == ["ok", "занято"]
        assert Appointment.objects.count() == 1
