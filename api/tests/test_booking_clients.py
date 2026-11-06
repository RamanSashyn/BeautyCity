import pytest

from api.models import Appointment, Client, TimeSlot
from api.tests.helpers import confirm_booking, start_booking

pytestmark = pytest.mark.django_db


def test_гостевая_запись_не_меняет_имя_существующего_клиента(
    client, owner, slot, salon, service, specialist
):
    start_booking(client, slot, salon, service, specialist)

    confirm_booking(client, name="Злоумышленник", phone=owner.phone)

    owner.refresh_from_db()
    assert owner.name == "Ирина"
    assert owner.phone == "+79990000001"


def test_гостевая_запись_не_попадает_в_записи_владельца_номера(
    client, owner, slot, salon, service, specialist
):
    start_booking(client, slot, salon, service, specialist)

    confirm_booking(client, name="Злоумышленник", phone=owner.phone)

    assert not Appointment.objects.filter(client=owner).exists()
    appointment = Appointment.objects.get()
    assert appointment.client is None
    assert appointment.guest_name == "Злоумышленник"
    assert appointment.guest_phone == owner.phone


def test_гостевая_запись_не_создаёт_клиента(client, slot, salon, service, specialist):
    start_booking(client, slot, salon, service, specialist)

    confirm_booking(client, name="Мария", phone="+79990001122")

    assert not Client.objects.exists()
    assert Appointment.objects.get().guest_phone == "+79990001122"


def test_вошедший_клиент_записывается_на_себя_и_чужой_номер_игнорируется(
    client, login, owner, stranger, slot, salon, service, specialist
):
    login(client, owner)
    start_booking(client, slot, salon, service, specialist)

    confirm_booking(client, name="Ирина", phone=stranger.phone)

    appointment = Appointment.objects.get()
    assert appointment.client == owner
    assert not Appointment.objects.filter(client=stranger).exists()
    stranger.refresh_from_db()
    assert stranger.name == "Пётр"


def test_вошедшему_клиенту_без_имени_сохраняется_имя_из_формы(
    client, login, slot, salon, service, specialist
):
    nameless = Client.objects.create(phone="+79990000003")
    login(client, nameless)
    start_booking(client, slot, salon, service, specialist)

    confirm_booking(client, name="Анастасия", phone=nameless.phone)

    nameless.refresh_from_db()
    assert nameless.name == "Анастасия"


def test_запись_занимает_слот_и_очищает_выбор_в_сессии(client, slot, salon, service, specialist):
    start_booking(client, slot, salon, service, specialist)

    confirm_booking(client)

    slot.refresh_from_db()
    assert slot.is_booked
    assert "booking_data" not in client.session


def test_повторное_подтверждение_не_создаёт_вторую_запись(client, slot, salon, service, specialist):
    start_booking(client, slot, salon, service, specialist)
    confirm_booking(client)

    response = confirm_booking(client)

    assert response.status_code == 302
    assert Appointment.objects.count() == 1


@pytest.mark.parametrize(
    ("name", "phone", "message"),
    [
        ("", "+79990001122", "Введите имя и телефон"),
        ("Мария", "", "Введите имя и телефон"),
        ("Мария", "89990001122", "Введите корректный номер телефона"),
    ],
)
def test_неверные_данные_не_создают_запись(
    client, slot, salon, service, specialist, name, phone, message
):
    start_booking(client, slot, salon, service, specialist)

    response = confirm_booking(client, name=name, phone=phone)

    assert response.status_code == 200
    assert message in response.content.decode()
    assert not Appointment.objects.exists()
    assert not TimeSlot.objects.get(pk=slot.pk).is_booked


def test_прямой_post_на_страницу_услуг_не_создаёт_запись(client, slot, service):
    response = client.post(
        "/api/service/",
        {"slot_id": slot.id, "service_id": service.id, "phone": "+79990001122"},
    )

    assert response.status_code == 405
    assert not Appointment.objects.exists()
