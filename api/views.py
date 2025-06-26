from django.http import JsonResponse
from django.shortcuts import render, redirect
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
