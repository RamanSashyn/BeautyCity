from datetime import datetime, timedelta

from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from api.forms import BookingContactForm
from api.models import Appointment, Salon, Service, Specialist, TimeSlot
from api.views.helpers import current_client, first_error


def book_appointment(request):
    if request.method == "POST":
        request.session["booking_data"] = {
            "slot_id": request.POST.get("slot_id"),
            "salon_id": request.POST.get("salon_id"),
            "service_id": request.POST.get("service_id"),
            "specialist_id": request.POST.get("specialist_id"),
        }
        redirect_url = reverse("service_finally")
        return JsonResponse({"success": True, "redirect_url": redirect_url})
    return JsonResponse({"success": False, "error": "Invalid method"})


@transaction.atomic
def service_finally_view(request):
    data = request.session.get("booking_data")
    if not data:
        return redirect("service_view")

    try:
        slot = TimeSlot.objects.select_for_update().get(id=data["slot_id"], is_booked=False)
    except TimeSlot.DoesNotExist:
        return redirect("service_view")

    salon = get_object_or_404(Salon, id=data["salon_id"])
    service = get_object_or_404(Service, id=data["service_id"])
    specialist = get_object_or_404(Specialist, id=data["specialist_id"])

    client = current_client(request)
    context = {"service": service, "salon": salon, "specialist": specialist, "slot": slot}
    if client:
        context.update(name=client.name, phone=client.phone, phone_readonly=True)

    def page(**extra):
        return render(request, "serviceFinally.html", {**context, **extra})

    if not specialist.services.filter(id=service.id).exists():
        return page(error="Указанный специалист не оказывает выбранную услугу.")

    if request.method == "POST":
        data = request.POST.copy()
        if client:
            # Вошедший клиент записывается на себя: номер из формы не используется.
            data["tel"] = client.phone
        form = BookingContactForm(data)
        if not form.is_valid():
            return page(
                error=first_error(form),
                name=data.get("fname", ""),
                phone=data.get("tel", ""),
                question=data.get("contactsTextarea", ""),
            )

        name = form.cleaned_data["fname"]
        if client:
            if client.name != name:
                client.name = name
                client.save(update_fields=["name"])
            owner = {"client": client}
        else:
            # Гость не трогает существующих клиентов: контакты лежат в самой записи.
            owner = {"guest_name": name, "guest_phone": form.cleaned_data["tel"]}

        start = datetime.combine(slot.date, slot.time)
        end = start + timedelta(minutes=service.duration_minutes)

        appointment = Appointment.objects.create(
            **owner,
            specialist=specialist,
            service=service,
            salon=salon,
            date_time_start=start,
            date_time_end=end,
            status="booked",
            source="site",
        )

        slot.is_booked = True
        slot.save()

        del request.session["booking_data"]
        request.session["last_appointment_id"] = appointment.id
        return redirect("show_appointment", appointment_id=appointment.id)

    return page()


def _can_view_appointment(request, appointment):
    """Запись видит её владелец или тот, кто только что её создал в этой сессии."""
    if appointment.id == request.session.get("last_appointment_id"):
        return True
    client_id = request.session.get("client_id")
    return client_id is not None and appointment.client_id == client_id


def show_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if not _can_view_appointment(request, appointment):
        # Чужая и несуществующая запись неразличимы: ID последовательные.
        raise Http404
    return render(request, "serviceFinally.html", {"appointment": appointment})
