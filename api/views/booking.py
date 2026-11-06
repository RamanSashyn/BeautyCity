from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from api.forms import BookingContactForm
from api.models import Appointment, Salon, Service, Specialist, TimeSlot
from api.services import booking
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


def service_finally_view(request):
    data = request.session.get("booking_data")
    if not data:
        return redirect("service_view")

    slot = TimeSlot.objects.filter(id=data["slot_id"], is_booked=False).first()
    if slot is None:
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

    if not booking.specialist_provides_service(specialist, service):
        return page(error="Указанный специалист не оказывает выбранную услугу.")

    if request.method != "POST":
        return page()

    form_data = request.POST.copy()
    if client:
        # Вошедший клиент записывается на себя: номер из формы не используется.
        form_data["tel"] = client.phone
    form = BookingContactForm(form_data)
    if not form.is_valid():
        return page(
            error=first_error(form),
            name=form_data.get("fname", ""),
            phone=form_data.get("tel", ""),
            question=form_data.get("contactsTextarea", ""),
        )

    name = form.cleaned_data["fname"]
    # Гость не трогает существующих клиентов: его контакты лежат в самой записи.
    owner = (
        {"client": client}
        if client
        else {"guest_name": name, "guest_phone": form.cleaned_data["tel"]}
    )
    try:
        appointment = booking.book_slot(
            slot_id=slot.id, specialist=specialist, service=service, salon=salon, **owner
        )
    except booking.SlotUnavailable:
        return redirect("service_view")
    except booking.BookingError as error:
        return page(error=error.message)

    if client and client.name != name:
        client.name = name
        client.save(update_fields=["name"])

    del request.session["booking_data"]
    request.session["last_appointment_id"] = appointment.id
    return redirect("show_appointment", appointment_id=appointment.id)


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
