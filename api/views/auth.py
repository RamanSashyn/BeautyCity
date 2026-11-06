from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect

from api.forms import LoginCodeForm, PhoneForm
from api.services import login_codes
from api.views.helpers import first_error


def _code_error_response(error):
    payload = {"ok": False, "error": error.message}
    if error.retry_after:
        payload["retry_after"] = error.retry_after
    return JsonResponse(payload, status=error.status)


def login_view(request):
    """Шаг 1 входа: принимает номер и отправляет на него одноразовый код."""
    if request.method != "POST":
        return redirect("/")

    form = PhoneForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "error": first_error(form)}, status=400)

    try:
        login_codes.issue_code(form.cleaned_data["tel"], request.META.get("REMOTE_ADDR"))
    except login_codes.LoginCodeError as error:
        return _code_error_response(error)

    return JsonResponse({"ok": True, "resend_after": settings.LOGIN_CODE_RESEND_SECONDS})


def login_verify_view(request):
    """Шаг 2 входа: проверяет код, и только после этого клиент попадает в сессию."""
    if request.method != "POST":
        return redirect("/")

    form = LoginCodeForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "error": first_error(form)}, status=400)

    try:
        client = login_codes.verify_code(form.cleaned_data["tel"], form.cleaned_data["code"])
    except login_codes.LoginCodeError as error:
        return _code_error_response(error)

    request.session.cycle_key()
    request.session["client_id"] = client.id
    return JsonResponse({"ok": True})


def logout_view(request):
    request.session.flush()
    return redirect("/")
