import re
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.utils.dateparse import parse_date

from .models import (
    Client, Salon, Service, Specialist,
    Category, TimeSlot, Appointment
)


def index_view(request):
    services    = Service.objects.exclude(photo='')
    salons      = Salon.objects.all()
    specialists = Specialist.objects.exclude(photo='')

    map_salons = salons.filter(lat__isnull=False, lon__isnull=False)

    static_map_url = None
    if map_salons.exists():
        pts = '~'.join(f"{s.lon},{s.lat},pm2rdm" for s in map_salons)
        params = {
            'l':      'map',
            'size':   '650,400',
            'lang':   'ru_RU',
            'pt':     pts,
            'apikey': settings.YANDEX_STATICMAP_KEY,
        }
        static_map_url = 'https://static-maps.yandex.ru/1.x/?' + urlencode(params)

    points = [
        {'lat': s.lat, 'lon': s.lon, 'hint': s.name}
        for s in map_salons
    ]

    return render(request, 'index.html', {
        'salons':           salons,
        'services':         services,
        'specialists':      specialists,
        'static_map_url':   static_map_url,
        'points':           points, 
        'YANDEX_GEOCODE_KEY': settings.YANDEX_GEOCODE_KEY,
    })


def service_view(request):
    salons = Salon.objects.all()
    categories = Category.objects.annotate(service_count=Count('service')) \
                                 .filter(service_count__gt=0, name__gt='') \
                                 .prefetch_related('service_set')
    specialists = Specialist.objects.prefetch_related('salons', 'services')

    slots = TimeSlot.objects.filter(is_booked=False, date__gte=timezone.localdate()) \
                            .order_by('date', 'time')
    morning_slots = slots.filter(time__lt=time(12, 0))
    day_slots     = slots.filter(time__gte=time(12, 0), time__lt=time(18, 0))
    evening_slots = slots.filter(time__gte=time(18, 0))

    if request.method == 'POST':
        slot_id      = request.POST.get('slot_id')
        client_phone = request.POST.get('phone')
        service_id   = request.POST.get('service_id')

        slot = get_object_or_404(TimeSlot, id=slot_id, is_booked=False)
        client, _ = Client.objects.get_or_create(phone=client_phone)
        service = get_object_or_404(Service, id=service_id)

        start = datetime.combine(slot.date, slot.time)
        end   = start + timedelta(minutes=service.duration_minutes)

        Appointment.objects.create(
            client=client,
            specialist=slot.specialist,
            service=service,
            salon=slot.salon,
            date_time_start=start,
            date_time_end=end,
            status='booked'
        )

        slot.is_booked = True
        slot.save()

        return redirect('success')

    return render(request, 'service.html', {
        'salons': salons,
        'categories': categories,
        'specialists': specialists,
        'slots': slots,
        'morning_slots': morning_slots,
        'day_slots': day_slots,
        'evening_slots': evening_slots,
    })


@require_GET
def filter_entities(request):
    slot_id       = request.GET.get('slot_id')
    date_str      = request.GET.get('date')
    salon_id      = request.GET.get('salon')
    service_id    = request.GET.get('service')
    specialist_id = request.GET.get('specialist')
    time_str      = request.GET.get('time')

    date_filter = parse_date(date_str) if date_str else None
    if not date_filter and date_str:
        try:
            date_filter = datetime.strptime(date_str, '%d.%m.%Y').date()
        except ValueError:
            date_filter = timezone.localdate()
    if not date_filter:
        date_filter = timezone.localdate()

    if slot_id:
        slot = TimeSlot.objects.filter(
            id=slot_id,
            date=date_filter,
            is_booked=False
        ).select_related('salon', 'specialist').first()
        if slot:
            services_for_spec = slot.specialist.services.all()
            return JsonResponse({
                "salons":      [{"id": slot.salon_id,      "name": str(slot.salon)}],
                "services":    [{"id": s.id, "name": str(s)} for s in services_for_spec],
                "specialists": [{"id": slot.specialist_id, "name": str(slot.specialist)}],
            })

    if time_str:
        try:
            time_filter = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            time_filter = None

        if time_filter:
            slots_time = TimeSlot.objects.filter(
                date=date_filter,
                time=time_filter,
                is_booked=False
            )

            if salon_id:
                slots_time = slots_time.filter(salon_id=salon_id)
            if service_id:
                slots_time = slots_time.filter(specialist__services__id=service_id)

                service = get_object_or_404(Service, id=service_id)
                duration = timedelta(minutes=service.duration_minutes)
                tz = timezone.get_current_timezone()

                valid_ids = []
                for slot in slots_time:
                    start_naive = datetime.combine(date_filter, slot.time)
                    start = timezone.make_aware(start_naive, tz)
                    end = start + duration

                    if end.date() != date_filter:
                        continue

                    appts = Appointment.objects.filter(
                        specialist_id=slot.specialist_id,
                        date_time_start__date=date_filter
                    ).values_list('date_time_start', 'date_time_end')

                    overlap = False
                    for a_start, a_end in appts:
                        if a_start < end and a_end > start:
                            overlap = True
                            break

                    if not overlap:
                        valid_ids.append(slot.id)

                slots_time = slots_time.filter(id__in=valid_ids)

            salon_ids      = slots_time.values_list('salon_id', flat=True).distinct()
            specialist_ids = slots_time.values_list('specialist_id', flat=True).distinct()

            services_qs    = Service.objects.filter(specialist__id__in=specialist_ids).distinct()
            salons_qs      = Salon.objects.filter(id__in=salon_ids)
            specialists_qs = Specialist.objects.filter(id__in=specialist_ids)

            return JsonResponse({
                "salons":      [{"id": s.id, "name": str(s)} for s in salons_qs],
                "services":    [{"id": s.id, "name": str(s)} for s in services_qs],
                "specialists": [{"id": s.id, "name": str(s)} for s in specialists_qs],
            })

    salons_qs      = Salon.objects.all()
    services_qs    = Service.objects.all()
    specialists_qs = Specialist.objects.all()

    if specialist_id:
        spec = specialists_qs.filter(pk=specialist_id).first()
        if spec:
            salons_qs      = spec.salons.all()
            services_qs    = spec.services.all()
            specialists_qs = specialists_qs.filter(pk=spec.id)

    if service_id:
        svc = services_qs.filter(pk=service_id).first()
        if svc:
            sl_allowed = Salon.objects.filter(specialist__services=svc).distinct()
            salons_qs  = salons_qs.filter(id__in=sl_allowed.values_list('id', flat=True))
            sp_allowed = specialists_qs.filter(services=svc).distinct()
            specialists_qs = specialists_qs.filter(id__in=sp_allowed.values_list('id', flat=True))
            services_qs = services_qs.filter(pk=svc.id)

    if salon_id:
        sl = salons_qs.filter(pk=salon_id).first()
        if sl:
            svc_in_salon = Service.objects.filter(specialist__salons=sl).distinct()
            services_qs  = services_qs.filter(id__in=svc_in_salon.values_list('id', flat=True))
            sp_in_salon  = specialists_qs.filter(salons=sl).distinct()
            specialists_qs = specialists_qs.filter(id__in=sp_in_salon.values_list('id', flat=True))
            salons_qs    = salons_qs.filter(pk=sl.id)

    def serialize(qs):
        return [{"id": o.id, "name": str(o)} for o in qs]

    return JsonResponse({
        "salons":      serialize(salons_qs),
        "services":    serialize(services_qs),
        "specialists": serialize(specialists_qs),
    })


@csrf_exempt
def login_view(request):
    if request.method == "POST":
        phone = request.POST.get("tel")
        if not is_valid_phone(phone):
            return render(request, "index.html", {
                "phone_error": "Введите корректный номер телефона в формате +7XXXXXXXXXX"
            })
        client, _ = Client.objects.get_or_create(phone=phone)
        request.session["client_id"] = client.id
        return redirect("/")
    return redirect("/")


def profile_view(request):
    client_id = request.session.get("client_id")
    if not client_id:
        return redirect("/")
    client = get_object_or_404(Client, id=client_id)
    if request.method == "POST":
        client.name     = request.POST.get("name", "")
        client.gender   = request.POST.get("gender", "")
        client.birthday = request.POST.get("birthday", "")
        client.save()
        return redirect("/")
    return render(request, "profile.html", {"client": client})


def logout_view(request):
    request.session.flush()
    return redirect("/")


def is_valid_phone(phone):
    return re.match(r'^\+7\d{10}$', phone)


@csrf_exempt
def book_appointment(request):
    if request.method == 'POST':
        request.session['booking_data'] = {
            'slot_id':       request.POST.get('slot_id'),
            'salon_id':      request.POST.get('salon_id'),
            'service_id':    request.POST.get('service_id'),
            'specialist_id': request.POST.get('specialist_id'),
        }
        return JsonResponse({'success': True, 'redirect_url': '/api/service-finally/'})
    return JsonResponse({'success': False, 'error': 'Invalid method'})


def service_finally_view(request):
    data = request.session.get('booking_data')
    if not data:
        return redirect('service_view')
    slot       = get_object_or_404(TimeSlot,   id=data['slot_id'],   is_booked=False)
    salon      = get_object_or_404(Salon,      id=data['salon_id'])
    service    = get_object_or_404(Service,    id=data['service_id'])
    specialist = get_object_or_404(Specialist, id=data['specialist_id'])

    if request.method == 'POST':
        name     = request.POST.get('fname')
        phone    = request.POST.get('tel')
        question = request.POST.get('contactsTextarea')
        if not name or not phone:
            return render(request, 'serviceFinally.html', {
                'error':      'Введите имя и телефон',
                'service':    service, 'salon': salon,
                'specialist': specialist, 'slot': slot
            })
        if not is_valid_phone(phone):
            return render(request, 'serviceFinally.html', {
                'error':      'Введите корректный номер телефона в формате +7XXXXXXXXXX',
                'service':    service, 'salon': salon,
                'specialist': specialist, 'slot': slot,
                'name': name, 'phone': phone, 'question': question
            })
        client, _ = Client.objects.get_or_create(phone=phone)
        client.name = name
        client.save()
        start = datetime.combine(slot.date, slot.time)
        end   = start + timedelta(minutes=service.duration_minutes)
        appointment = Appointment.objects.create(
            client=client, specialist=specialist, service=service,
            salon=salon, date_time_start=start,
            date_time_end=end, status='booked', source='site'
        )
        slot.is_booked = True
        slot.save()
        del request.session['booking_data']
        return redirect(f'/api/service-finally/{appointment.id}/')

    return render(request, 'serviceFinally.html', {
        'service': service, 'salon': salon,
        'specialist': specialist, 'slot': slot
    })


def show_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    return render(request, 'serviceFinally.html', {'appointment': appointment})


@require_GET
def get_slots_by_specialist(request):
    specialist_id = request.GET.get("specialist_id")
    salon_id      = request.GET.get("salon_id")
    service_id    = request.GET.get("service_id")
    date_str      = request.GET.get("date")

    date_filter = parse_date(date_str) if date_str else None
    if not date_filter and date_str:
        try:
            date_filter = datetime.strptime(date_str, '%d.%m.%Y').date()
        except ValueError:
            date_filter = timezone.localdate()
    if not date_filter:
        date_filter = timezone.localdate()

    qs = TimeSlot.objects.filter(date=date_filter, is_booked=False)
    if specialist_id:
        qs = qs.filter(specialist_id=specialist_id)
    if salon_id:
        qs = qs.filter(salon_id=salon_id)

    tz = timezone.get_current_timezone()

    if service_id and specialist_id:
        service = get_object_or_404(Service, id=service_id)
        duration = timedelta(minutes=service.duration_minutes)

        appts = Appointment.objects.filter(
            specialist_id=specialist_id,
            date_time_start__date=date_filter
        ).values_list('date_time_start', 'date_time_end')

        def overlaps(slot):
            start_naive = datetime.combine(date_filter, slot.time)
            start = timezone.make_aware(start_naive, tz)
            end = start + duration
            for a_start, a_end in appts:
                if a_start < end and a_end > start:
                    return True
            return False

        slots = [s for s in qs.order_by("time") if not overlaps(s)]
        result = [{
            "id":   s.id,
            "date": s.date.strftime("%Y-%m-%d"),
            "time": s.time.strftime("%H:%M"),
            "hour": s.time.hour,
        } for s in slots]

    else:
        all_slots = qs.order_by("time", "specialist_id")
        time_groups = {}
        for slot in all_slots:
            time_groups.setdefault(slot.time, []).append(slot)

        result = []
        for t, group in time_groups.items():
            result.append({
                "time": t.strftime("%H:%M"),
                "hour": t.hour,
                "slots": [
                    {
                        "id": s.id,
                        "specialist_id": s.specialist.id,
                        "specialist_name": str(s.specialist)
                    } for s in group
                ]
            })

    return JsonResponse(result, safe=False)
