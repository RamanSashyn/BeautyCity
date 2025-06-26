from django.shortcuts import render, redirect
from .forms import BookingForm


def service_booking_view(request):
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            appointment = form.save()
            return redirect("booking_success")  # позже подключим
    else:
        form = BookingForm()
    return render(request, "service.html", {"form": form})
