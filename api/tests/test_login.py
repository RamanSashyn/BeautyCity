from datetime import timedelta

import pytest
from django.utils import timezone

from api.models import Client, LoginCode

pytestmark = pytest.mark.django_db

PHONE = "+79991234567"


def request_code(client, phone=PHONE, **extra):
    return client.post("/api/login/", {"tel": phone}, **extra)


def verify(client, code, phone=PHONE):
    return client.post("/api/login/verify/", {"tel": phone, "code": code})


def wrong_code(real_code):
    return "000000" if real_code != "000000" else "111111"


def test_без_кода_сессия_не_создаётся(client):
    response = request_code(client)

    assert response.status_code == 200
    assert "client_id" not in client.session
    assert not Client.objects.filter(phone=PHONE).exists()


def test_код_уходит_через_sms_и_хранится_в_виде_хеша(client, sms_outbox, sent_code):
    request_code(client)

    assert len(sms_outbox) == 1
    assert sms_outbox[0][0] == PHONE
    code = sent_code()
    assert len(code) == 6
    assert LoginCode.objects.get(phone=PHONE).code_hash != code


def test_верный_код_выполняет_вход(client, sent_code):
    request_code(client)

    response = verify(client, sent_code())

    assert response.status_code == 200
    client_obj = Client.objects.get(phone=PHONE)
    assert client.session["client_id"] == client_obj.id


def test_неверный_код_не_выполняет_вход(client, sent_code):
    request_code(client)

    response = verify(client, wrong_code(sent_code()))

    assert response.status_code == 400
    assert "client_id" not in client.session
    assert not Client.objects.filter(phone=PHONE).exists()


def test_вход_без_запроса_кода_невозможен(client):
    response = verify(client, "123456")

    assert response.status_code == 400
    assert "client_id" not in client.session


def test_просроченный_код_отклоняется(client, sent_code):
    request_code(client)
    code = sent_code()
    LoginCode.objects.update(created_at=timezone.now() - timedelta(minutes=5, seconds=1))

    response = verify(client, code)

    assert response.status_code == 400
    assert "client_id" not in client.session


def test_код_за_минуту_до_истечения_ещё_действует(client, sent_code):
    request_code(client)
    code = sent_code()
    LoginCode.objects.update(created_at=timezone.now() - timedelta(minutes=4, seconds=59))

    assert verify(client, code).status_code == 200


def test_шестая_попытка_отклоняется_даже_с_верным_кодом(client, sent_code):
    request_code(client)
    code = sent_code()

    for _ in range(5):
        assert verify(client, wrong_code(code)).status_code == 400
    response = verify(client, code)

    assert response.status_code == 429
    assert "client_id" not in client.session


def test_пятая_попытка_с_верным_кодом_ещё_проходит(client, sent_code):
    request_code(client)
    code = sent_code()

    for _ in range(4):
        verify(client, wrong_code(code))

    assert verify(client, code).status_code == 200


def test_код_одноразовый(client, django_client_factory, sent_code):
    request_code(client)
    code = sent_code()
    assert verify(client, code).status_code == 200

    other = django_client_factory()
    response = verify(other, code)

    assert response.status_code == 400
    assert "client_id" not in other.session


def test_действует_только_последний_код(client, sms_outbox, sent_code):
    request_code(client)
    first = sent_code()
    LoginCode.objects.update(created_at=timezone.now() - timedelta(minutes=2))
    request_code(client)
    second = sent_code()
    if first == second:
        pytest.skip("коды случайно совпали")

    assert verify(client, first).status_code == 400
    assert verify(client, second).status_code == 200


def test_повторный_запрос_кода_раньше_чем_через_минуту_отклоняется(client, sms_outbox):
    request_code(client)

    response = request_code(client)

    assert response.status_code == 429
    assert len(sms_outbox) == 1


def test_лимит_кодов_на_номер_в_час(client, sms_outbox):
    for _ in range(5):
        assert request_code(client).status_code == 200
        LoginCode.objects.update(created_at=timezone.now() - timedelta(minutes=2))

    response = request_code(client)

    assert response.status_code == 429
    assert len(sms_outbox) == 5


def test_лимит_кодов_на_ip(client, sms_outbox):
    for number in range(20):
        response = request_code(client, f"+7999000{number:04d}", REMOTE_ADDR="10.0.0.1")
        assert response.status_code == 200

    blocked = request_code(client, "+79990009999", REMOTE_ADDR="10.0.0.1")
    other_ip = request_code(client, "+79990009999", REMOTE_ADDR="10.0.0.2")

    assert blocked.status_code == 429
    assert other_ip.status_code == 200


@pytest.mark.parametrize("phone", ["", "89991234567", "+7999123456", "+7999123456a", "abc"])
def test_некорректный_номер_отклоняется(client, sms_outbox, phone):
    response = request_code(client, phone)

    assert response.status_code == 400
    assert not sms_outbox


def test_запрос_без_номера_не_падает(client):
    response = client.post("/api/login/", {})

    assert response.status_code == 400


def test_get_запрос_перенаправляет_на_главную(client):
    response = client.get("/api/login/")

    assert response.status_code == 302
    assert response.url == "/"
