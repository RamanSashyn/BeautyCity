from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import Client
from django.views.decorators.csrf import csrf_exempt


def ping(request):
    return JsonResponse({"message": "pong"})


def index(request):
    return render(request, "index.html")


@csrf_exempt
def login_view(request):
    if request.method == "POST":
        phone = request.POST.get("tel")
        if not phone:
            return redirect("/")

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
