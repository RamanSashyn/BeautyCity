"""Расчёт свободных слотов, пересечений с записями и атомарное бронирование."""

from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_date

from api.models import Appointment, Client, Salon, Service, Specialist, TimeSlot

Interval = tuple[datetime, datetime]


def parse_date_param(value: str | None) -> date:
    """Читает дату из запроса: ГГГГ-ММ-ДД или ДД.ММ.ГГГГ.

    Пустое и нечитаемое значение означает сегодняшний день.
    """
    if value:
        try:
            parsed = parse_date(value)
        except ValueError:
            parsed = None
        if parsed:
            return parsed
        try:
            return datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            pass
    return timezone.localdate()


def slot_interval(day: date, slot_time: time, duration_minutes: int) -> Interval:
    """Начало и конец услуги, если она начнётся в слоте (время с часовым поясом)."""
    start = timezone.make_aware(datetime.combine(day, slot_time))
    return start, start + timedelta(minutes=duration_minutes)


def busy_intervals(specialist_id: int, day: date) -> list[Interval]:
    """Интервалы уже созданных записей мастера на день."""
    appointments = Appointment.objects.filter(
        specialist_id=specialist_id, date_time_start__date=day
    )
    return list(appointments.values_list("date_time_start", "date_time_end"))


def overlaps(start: datetime, end: datetime, busy: list[Interval]) -> bool:
    """Пересекается ли [start, end) с занятыми интервалами; встык не считается."""
    return any(busy_start < end and busy_end > start for busy_start, busy_end in busy)


def free_slots(
    day: date, *, specialist_id: str | None = None, salon_id: str | None = None
) -> QuerySet[TimeSlot]:
    """Свободные слоты на день, при желании только мастера и салона."""
    slots = TimeSlot.objects.filter(date=day, is_booked=False)
    if specialist_id:
        slots = slots.filter(specialist_id=specialist_id)
    if salon_id:
        slots = slots.filter(salon_id=salon_id)
    return slots


def exclude_overlapping(
    slots, day: date, service: Service, *, within_day: bool = False
) -> list[TimeSlot]:
    """Оставляет слоты, с которых услуга не пересекается с записями мастера.

    С within_day=True отбрасываются и слоты, где услуга заканчивается уже после полуночи.
    """
    busy_by_specialist: dict[int, list[Interval]] = {}
    suitable = []
    for slot in slots:
        start, end = slot_interval(day, slot.time, service.duration_minutes)
        if within_day and end.date() != day:
            continue
        if slot.specialist_id not in busy_by_specialist:
            busy_by_specialist[slot.specialist_id] = busy_intervals(slot.specialist_id, day)
        if not overlaps(start, end, busy_by_specialist[slot.specialist_id]):
            suitable.append(slot)
    return suitable


class BookingError(Exception):
    """Запись невозможна. Текст можно показывать пользователю."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SlotUnavailable(BookingError):
    """Слот не найден или уже занят."""


class ServiceNotProvided(BookingError):
    """Мастер не оказывает выбранную услугу."""


def specialist_provides_service(specialist: Specialist, service: Service) -> bool:
    return specialist.services.filter(id=service.id).exists()


@transaction.atomic
def book_slot(
    *,
    slot_id: int | str,
    specialist: Specialist,
    service: Service,
    salon: Salon,
    client: Client | None = None,
    guest_name: str = "",
    guest_phone: str = "",
    source: str = "site",
) -> Appointment:
    """Атомарно занимает слот и создаёт запись.

    Слот блокируется до конца транзакции (select_for_update), поэтому из двух одновременных
    попыток записаться на один слот вторая получит SlotUnavailable. Запись принадлежит
    клиенту либо, для гостя, хранит его имя и телефон в самой записи.
    """
    try:
        slot = TimeSlot.objects.select_for_update().get(id=slot_id, is_booked=False)
    except TimeSlot.DoesNotExist as error:
        raise SlotUnavailable("Это время уже занято.") from error

    if not specialist_provides_service(specialist, service):
        raise ServiceNotProvided("Указанный специалист не оказывает выбранную услугу.")

    start, end = slot_interval(slot.date, slot.time, service.duration_minutes)
    appointment = Appointment.objects.create(
        client=client,
        guest_name=guest_name,
        guest_phone=guest_phone,
        specialist=specialist,
        service=service,
        salon=salon,
        date_time_start=start,
        date_time_end=end,
        status="booked",
        source=source,
    )

    slot.is_booked = True
    slot.save(update_fields=["is_booked"])
    return appointment
