import pytest

from api.tests.helpers import confirm_booking, start_booking

pytestmark = pytest.mark.django_db


def appointment_url(appointment):
    return f"/api/service-finally/{appointment.id}/"


def test_владелец_видит_свою_запись(client, login, owner, make_appointment):
    appointment = make_appointment(owner)
    login(client, owner)

    response = client.get(appointment_url(appointment))

    assert response.status_code == 200


def test_чужая_запись_даёт_404(client, login, owner, stranger, make_appointment):
    appointment = make_appointment(owner)
    login(client, stranger)

    response = client.get(appointment_url(appointment))

    assert response.status_code == 404


def test_аноним_не_видит_запись(client, owner, make_appointment):
    appointment = make_appointment(owner)

    response = client.get(appointment_url(appointment))

    assert response.status_code == 404


def test_несуществующая_запись_даёт_такой_же_404(client, login, stranger):
    login(client, stranger)

    response = client.get("/api/service-finally/999999/")

    assert response.status_code == 404


def test_гость_видит_страницу_созданной_записи_сразу_после_бронирования(
    client, slot, salon, service, specialist
):
    start_booking(client, slot, salon, service, specialist)
    response = confirm_booking(client)

    assert response.status_code == 302
    page = client.get(response.url)
    assert page.status_code == 200


def test_другой_гость_не_видит_запись_первого(
    client, django_client_factory, slot, salon, service, specialist
):
    start_booking(client, slot, salon, service, specialist)
    url = confirm_booking(client).url

    other_guest = django_client_factory()

    assert other_guest.get(url).status_code == 404


def test_клиент_видит_только_что_созданную_запись(
    client, login, owner, slot, salon, service, specialist
):
    login(client, owner)
    start_booking(client, slot, salon, service, specialist)
    url = confirm_booking(client, name="Ирина", phone=owner.phone).url

    assert client.get(url).status_code == 200
