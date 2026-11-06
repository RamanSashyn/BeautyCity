import pytest
from django.test import Client as DjangoClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def strict_client():
    """Клиент, который проверяет CSRF так же, как браузер."""
    return DjangoClient(enforce_csrf_checks=True)


def csrf_token(strict_client):
    """Берёт токен, как это делает страница: сначала GET, затем значение из cookie."""
    strict_client.get("/")
    return strict_client.cookies["csrftoken"].value


@pytest.mark.parametrize(
    ("url", "data"),
    [
        ("/api/login/", {"tel": "+79991234567"}),
        ("/api/login/verify/", {"tel": "+79991234567", "code": "123456"}),
        ("/api/book/", {"slot_id": 1, "salon_id": 1, "service_id": 1, "specialist_id": 1}),
        ("/api/service-finally/", {"fname": "Мария", "tel": "+79991234567"}),
        ("/api/settings/", {"name": "Мария"}),
    ],
)
def test_post_без_csrf_токена_отклоняется(strict_client, sms_outbox, url, data):
    response = strict_client.post(url, data)

    assert response.status_code == 403
    assert not sms_outbox
    assert "booking_data" not in strict_client.session


def test_вход_с_токеном_в_заголовке_работает(strict_client, sms_outbox):
    token = csrf_token(strict_client)

    response = strict_client.post(
        "/api/login/", {"tel": "+79991234567"}, headers={"X-CSRFToken": token}
    )

    assert response.status_code == 200
    assert len(sms_outbox) == 1


def test_выбор_слота_с_токеном_в_заголовке_работает(strict_client):
    token = csrf_token(strict_client)

    response = strict_client.post(
        "/api/book/",
        {"slot_id": 1, "salon_id": 1, "service_id": 1, "specialist_id": 1},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    assert strict_client.session["booking_data"]["slot_id"] == "1"


def test_подделанный_токен_отклоняется(strict_client):
    csrf_token(strict_client)

    response = strict_client.post(
        "/api/login/", {"tel": "+79991234567"}, headers={"X-CSRFToken": "подделка"}
    )

    assert response.status_code == 403


def test_формы_входа_и_страница_отдают_токен(client):
    html = client.get("/").content.decode()

    assert html.count('name="csrfmiddlewaretoken"') >= 2
    assert "data-csrf-token=" in html


def test_форма_выбора_услуги_содержит_токен(client):
    html = client.get("/api/service/").content.decode()

    form = html.split('class="service__form"')[1].split("</form>")[0]
    assert 'name="csrfmiddlewaretoken"' in form
