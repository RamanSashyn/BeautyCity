from datetime import time
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from api.models import Category, Salon, Service, Specialist, TimeSlot
from api.services import booking, filters


def index_view(request):
    services = Service.objects.exclude(photo="")
    salons = Salon.objects.all()
    specialists = Specialist.objects.exclude(photo="")

    map_salons = salons.filter(lat__isnull=False, lon__isnull=False)

    static_map_url = None
    if map_salons.exists():
        pts = "~".join(f"{s.lon},{s.lat},pm2rdm" for s in map_salons)
        params = {
            "l": "map",
            "size": "650,400",
            "lang": "ru_RU",
            "pt": pts,
            "apikey": settings.YANDEX_STATICMAP_KEY,
        }
        static_map_url = "https://static-maps.yandex.ru/1.x/?" + urlencode(params)

    points = [{"lat": s.lat, "lon": s.lon, "hint": s.name} for s in map_salons]

    return render(
        request,
        "index.html",
        {
            "salons": salons,
            "services": services,
            "specialists": specialists,
            "static_map_url": static_map_url,
            "points": points,
            "YANDEX_GEOCODE_KEY": settings.YANDEX_GEOCODE_KEY,
        },
    )


@require_GET
def service_view(request):
    salons = Salon.objects.all()
    categories = (
        Category.objects.annotate(service_count=Count("service"))
        .filter(service_count__gt=0, name__gt="")
        .prefetch_related("service_set")
    )
    specialists = Specialist.objects.prefetch_related("salons", "services")

    slots = TimeSlot.objects.filter(is_booked=False, date__gte=timezone.localdate()).order_by(
        "date", "time"
    )
    morning_slots = slots.filter(time__lt=time(12, 0))
    day_slots = slots.filter(time__gte=time(12, 0), time__lt=time(18, 0))
    evening_slots = slots.filter(time__gte=time(18, 0))

    return render(
        request,
        "service.html",
        {
            "salons": salons,
            "categories": categories,
            "specialists": specialists,
            "slots": slots,
            "morning_slots": morning_slots,
            "day_slots": day_slots,
            "evening_slots": evening_slots,
        },
    )


@require_GET
def filter_entities(request):
    """Взаимозависимые фильтры: что ещё можно выбрать при уже сделанном выборе."""
    params = request.GET
    entities = filters.find_entities(
        day=booking.parse_date_param(params.get("date")),
        slot_id=params.get("slot_id"),
        time_str=params.get("time"),
        salon_id=params.get("salon"),
        service_id=params.get("service"),
        specialist_id=params.get("specialist"),
    )
    return JsonResponse(entities.as_json())


def _slot_json(slot):
    return {
        "id": slot.id,
        "date": slot.date.strftime("%Y-%m-%d"),
        "time": slot.time.strftime("%H:%M"),
        "hour": slot.time.hour,
    }


def _group_slots_by_time(slots):
    groups = {}
    for slot in slots:
        groups.setdefault(slot.time, []).append(slot)
    return [
        {
            "time": slot_time.strftime("%H:%M"),
            "hour": slot_time.hour,
            "slots": [
                {
                    "id": slot.id,
                    "specialist_id": slot.specialist.id,
                    "specialist_name": str(slot.specialist),
                }
                for slot in group
            ],
        }
        for slot_time, group in groups.items()
    ]


@require_GET
def get_slots_by_specialist(request):
    """Свободные слоты на день.

    Если выбраны мастер и услуга, отдаёт плоский список слотов без пересечений с записями.
    Иначе слоты группируются по времени, внутри группы идут мастера.
    """
    specialist_id = request.GET.get("specialist_id")
    service_id = request.GET.get("service_id")
    day = booking.parse_date_param(request.GET.get("date"))

    slots = booking.free_slots(
        day, specialist_id=specialist_id, salon_id=request.GET.get("salon_id")
    )

    if service_id and specialist_id:
        service = get_object_or_404(Service, id=service_id)
        suitable = booking.exclude_overlapping(slots.order_by("time"), day, service)
        return JsonResponse([_slot_json(slot) for slot in suitable], safe=False)

    ordered = slots.select_related("specialist").order_by("time", "specialist_id")
    return JsonResponse(_group_slots_by_time(ordered), safe=False)
