from django.shortcuts import get_object_or_404, redirect, render

from api.models import Appointment, Client


def profile_view(request):
    client_id = request.session.get("client_id")
    if not client_id:
        return redirect("/")

    client = get_object_or_404(Client, id=client_id)

    appointments = (
        Appointment.objects.filter(client=client)
        .select_related("specialist", "service", "salon")
        .order_by("-date_time_start")
    )

    return render(
        request,
        "profile.html",
        {
            "client": client,
            "appointments": appointments,
        },
    )


def settings_view(request):
    client_id = request.session.get("client_id")
    if not client_id:
        return redirect("/")
    client = get_object_or_404(Client, id=client_id)

    if request.method == "POST":
        client.name = request.POST.get("name", "")
        client.gender = request.POST.get("gender", "")
        client.birthday = request.POST.get("birthday", "")
        client.save()
        return redirect("settings")

    return render(request, "settings.html", {"client": client})
