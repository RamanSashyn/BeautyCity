import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from django.utils import timezone
from datetime import datetime, timedelta, time

from .models import Client, Salon, Service, Specialist, Category, TimeSlot, Appointment


def index_view(request):
    services = Service.objects.exclude(photo='')
    salons = Salon.objects.all()
    specialists = Specialist.objects.exclude(photo='')
    return render(request, "index.html", {
        "salons": salons,
        "services": services,
        "specialists": specialists,
    })


def service_view(request):
    salons = Salon.objects.all()
    categories = Category.objects.annotate(service_count=Count('service')) \
                                 .filter(service_count__gt=0, name__gt='') \
                                 .prefetch_related('service_set')
    specialists = Specialist.objects.prefetch_related('salons', 'services')

    slots = TimeSlot.objects.filter(is_booked=False, date__gte=timezone.now().date()).order_by('date', 'time')
    morning_slots = slots.filter(time__lt=time(12, 0))
    day_slots = slots.filter(time__gte=time(12, 0), time__lt=time(18, 0))
    evening_slots = slots.filter(time__gte=time(18, 0))

    if request.method == 'POST':
        slot_id = request.POST.get('slot_id')
        client_phone = request.POST.get('phone')
        service_id = request.POST.get('service_id')

        slot = TimeSlot.objects.get(id=slot_id)
        client_phone = Client.objects.get_or_create(phone=client_phone)
        service = Service.objects.get(id=service_id)

        start = datetime.combine(slot.date, slot.time)
        end = start + timedelta(minutes=service.duration_minutes)

        Appointment.objects.create(
            client=client,
            specialist=slot.specialist,
            service=service,
            salon=slot.salon,
            date_time_start=start,
            date_time_end=end,
            status='booked'
        )

        # Блокируем слот
        slot.is_booked = True
        slot.save()

        return redirect('success')

    slots = TimeSlot.objects.filter(is_booked=False, date__gte=timezone.now().date()).order_by('date', 'time')

    context = {
        'slots': slots,
    }

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
    salons_qs = Salon.objects.all()
    services_qs = Service.objects.all()
    specialists_qs = Specialist.objects.all()

    salon_id = request.GET.get('salon')
    service_id = request.GET.get('service')
    specialist_id = request.GET.get('specialist')

    if specialist_id:
        spec = specialists_qs.filter(pk=specialist_id).first()
        if spec:
            salons_qs = spec.salons.all()
            services_qs = spec.services.all()
            specialists_qs = specialists_qs.filter(pk=spec.id)

    if service_id:
        svc = services_qs.filter(pk=service_id).first()
        if svc:
            sl_allowed = Salon.objects.filter(specialist__services=svc).distinct()
            salons_qs = salons_qs.filter(id__in=sl_allowed.values_list('id', flat=True))

            sp_allowed = specialists_qs.filter(services=svc).distinct()
            specialists_qs = specialists_qs.filter(id__in=sp_allowed.values_list('id', flat=True))

            services_qs = services_qs.filter(pk=svc.id)

    if salon_id:
        sl = salons_qs.filter(pk=salon_id).first()
        if sl:
            svc_in_salon = Service.objects.filter(specialist__salons=sl).distinct()
            services_qs = services_qs.filter(id__in=svc_in_salon.values_list('id', flat=True))

            sp_in_salon = specialists_qs.filter(salons=sl).distinct()
            specialists_qs = specialists_qs.filter(id__in=sp_in_salon.values_list('id', flat=True))

            salons_qs = salons_qs.filter(pk=sl.id)

    def serialize(qs):
        return [{"id": o.id, "name": str(o)} for o in qs]

    return JsonResponse({
        "salons": serialize(salons_qs),
        "services": serialize(services_qs),
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

        client, created = Client.objects.get_or_create(phone=phone)
        request.session["client_id"] = client.id
        return redirect("/")

    return redirect("/")


def profile_view(request):
    client_id = request.session.get("client_id")
    if not client_id:
        return redirect("/")

    client = get_object_or_404(Client, id=client_id)

    if request.method == "POST":
        client.name = request.POST.get("name", "")
        client.gender = request.POST.get("gender", "")
        client.birthday = request.POST.get("birthday", "")
        client.save()
        return redirect("/")

    return render(request, "profile.html", {"client": client})


def logout_view(request):
    request.session.flush()
    return redirect("/")


def is_valid_phone(phone):
    pattern = r'^\+7\d{10}$'
    return re.match(pattern, phone)
