"""Подбор салонов, услуг и мастеров для фильтров на странице записи.

Фильтры взаимозависимы: выбор салона сужает услуги и мастеров, выбор услуги сужает
салоны и мастеров и так далее. Каждая функция ниже отвечает за один вид сужения.
"""

from dataclasses import dataclass
from datetime import date, datetime, time

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone

from api.models import Salon, Service, Specialist, TimeSlot
from api.services import booking


@dataclass
class Entities:
    """Что сейчас можно выбрать: салоны, услуги и мастера."""

    salons: QuerySet
    services: QuerySet
    specialists: QuerySet

    @classmethod
    def everything(cls) -> "Entities":
        return cls(Salon.objects.all(), Service.objects.all(), Specialist.objects.all())

    @classmethod
    def nothing(cls) -> "Entities":
        return cls(Salon.objects.none(), Service.objects.none(), Specialist.objects.none())

    def as_json(self) -> dict:
        def serialize(queryset):
            return [{"id": obj.id, "name": str(obj)} for obj in queryset]

        return {
            "salons": serialize(self.salons),
            "services": serialize(self.services),
            "specialists": serialize(self.specialists),
        }


def parse_time_param(value: str) -> time | None:
    """Читает время ЧЧ:ММ, при ошибке возвращает None."""
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return None


def find_free_slot(slot_id: str, day: date, now: datetime) -> TimeSlot | None:
    """Свободный слот на день; сегодня учитываются только слоты позже текущего времени."""
    slots = TimeSlot.objects.filter(id=slot_id, date=day, is_booked=False)
    if day == now.date():
        slots = slots.filter(time__gt=now.time())
    return slots.select_related("salon", "specialist").first()


def entities_for_slot(slot: TimeSlot) -> Entities:
    """Выбран конкретный слот: остаются его салон, мастер и услуги мастера."""
    return Entities(
        salons=Salon.objects.filter(pk=slot.salon_id),
        services=slot.specialist.services.all(),
        specialists=Specialist.objects.filter(pk=slot.specialist_id),
    )


def entities_for_time(
    day: date,
    slot_time: time,
    now: datetime,
    *,
    salon_id: str | None = None,
    service_id: str | None = None,
) -> Entities:
    """Выбрано время: остаются те, у кого на это время есть свободный слот."""
    if day == now.date() and slot_time <= now.time():
        return Entities.nothing()

    slots = TimeSlot.objects.filter(date=day, time=slot_time, is_booked=False)
    if salon_id:
        slots = slots.filter(salon_id=salon_id)
    if service_id:
        slots = slots.filter(specialist__services__id=service_id)
        service = get_object_or_404(Service, id=service_id)
        suitable = booking.exclude_overlapping(slots, day, service, within_day=True)
        slots = slots.filter(id__in=[slot.id for slot in suitable])

    salon_ids = slots.values_list("salon_id", flat=True).distinct()
    specialist_ids = slots.values_list("specialist_id", flat=True).distinct()
    return Entities(
        salons=Salon.objects.filter(id__in=salon_ids),
        services=Service.objects.filter(specialist__id__in=specialist_ids).distinct(),
        specialists=Specialist.objects.filter(id__in=specialist_ids),
    )


def narrow_by_specialist(entities: Entities, specialist_id: str) -> Entities:
    """Мастер определяет свои салоны и услуги."""
    specialist = entities.specialists.filter(pk=specialist_id).first()
    if specialist is None:
        return entities
    return Entities(
        salons=specialist.salons.all(),
        services=specialist.services.all(),
        specialists=entities.specialists.filter(pk=specialist.id),
    )


def narrow_by_service(entities: Entities, service_id: str) -> Entities:
    """Услуга оставляет только салоны и мастеров, которые её оказывают."""
    service = entities.services.filter(pk=service_id).first()
    if service is None:
        return entities
    salons_with_service = Salon.objects.filter(specialist__services=service).distinct()
    specialists_with_service = entities.specialists.filter(services=service).distinct()
    return Entities(
        salons=entities.salons.filter(id__in=salons_with_service.values_list("id", flat=True)),
        services=entities.services.filter(pk=service.id),
        specialists=entities.specialists.filter(
            id__in=specialists_with_service.values_list("id", flat=True)
        ),
    )


def narrow_by_salon(entities: Entities, salon_id: str) -> Entities:
    """Салон оставляет только услуги и мастеров, которые в нём работают."""
    salon = entities.salons.filter(pk=salon_id).first()
    if salon is None:
        return entities
    services_in_salon = Service.objects.filter(specialist__salons=salon).distinct()
    specialists_in_salon = entities.specialists.filter(salons=salon).distinct()
    return Entities(
        salons=entities.salons.filter(pk=salon.id),
        services=entities.services.filter(id__in=services_in_salon.values_list("id", flat=True)),
        specialists=entities.specialists.filter(
            id__in=specialists_in_salon.values_list("id", flat=True)
        ),
    )


def find_entities(
    *,
    day: date,
    now: datetime | None = None,
    slot_id: str | None = None,
    time_str: str | None = None,
    salon_id: str | None = None,
    service_id: str | None = None,
    specialist_id: str | None = None,
) -> Entities:
    """Главная точка входа: слот и время важнее остальных фильтров, дальше сужения по очереди."""
    now = now or timezone.now()

    if slot_id:
        slot = find_free_slot(slot_id, day, now)
        if slot:
            return entities_for_slot(slot)

    if time_str:
        slot_time = parse_time_param(time_str)
        if slot_time:
            return entities_for_time(day, slot_time, now, salon_id=salon_id, service_id=service_id)

    entities = Entities.everything()
    if specialist_id:
        entities = narrow_by_specialist(entities, specialist_id)
    if service_id:
        entities = narrow_by_service(entities, service_id)
    if salon_id:
        entities = narrow_by_salon(entities, salon_id)
    return entities
