"""Мелкие функции, общие для представлений."""

from api.models import Client


def first_error(form):
    return next(iter(form.errors.values()))[0]


def current_client(request):
    client_id = request.session.get("client_id")
    if client_id is None:
        return None
    return Client.objects.filter(id=client_id).first()
