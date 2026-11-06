"""Личный кабинет: профиль, настройки, выход."""

from datetime import date

import pytest

pytestmark = pytest.mark.django_db


def test_профиль_без_входа_перенаправляет_на_главную(client):
    response = client.get("/api/profile/")

    assert response.status_code == 302
    assert response.url == "/"


def test_профиль_показывает_только_записи_клиента(
    client, login, owner, stranger, make_appointment, service
):
    make_appointment(owner, service=service)
    make_appointment(stranger, day_offset=2)
    login(client, owner)

    response = client.get("/api/profile/")

    assert response.status_code == 200
    appointments = list(response.context["appointments"])
    assert [a.client for a in appointments] == [owner]


def test_записи_в_профиле_идут_от_новых_к_старым(client, login, owner, make_appointment):
    later = make_appointment(owner, day_offset=3)
    earlier = make_appointment(owner, day_offset=1)
    login(client, owner)

    appointments = list(client.get("/api/profile/").context["appointments"])

    assert appointments == [later, earlier]


def test_гостевые_записи_в_профиль_не_попадают(client, login, owner, make_appointment):
    guest = make_appointment(None, guest_name="Гость", guest_phone="+79990000009")
    login(client, owner)

    appointments = list(client.get("/api/profile/").context["appointments"])

    assert guest not in appointments


def test_после_вызова_профиля_с_удалённым_клиентом_ответ_404(client, login, owner):
    login(client, owner)
    owner.delete()

    assert client.get("/api/profile/").status_code == 404


def test_настройки_без_входа_перенаправляют_на_главную(client):
    response = client.get("/api/settings/")

    assert response.status_code == 302
    assert response.url == "/"


def test_настройки_открываются_вошедшему_клиенту(client, login, owner):
    login(client, owner)

    response = client.get("/api/settings/")

    assert response.status_code == 200
    assert response.context["client"] == owner


def test_настройки_сохраняют_имя_пол_и_день_рождения(client, login, owner):
    login(client, owner)

    response = client.post(
        "/api/settings/",
        {"name": "Ирина Иванова", "gender": "female", "birthday": "1990-05-17"},
    )

    assert response.status_code == 302
    owner.refresh_from_db()
    assert owner.name == "Ирина Иванова"
    assert owner.gender == "female"
    assert owner.birthday == date(1990, 5, 17)


def test_настройки_не_дают_менять_телефон(client, login, owner):
    login(client, owner)

    client.post(
        "/api/settings/",
        {"name": "Ирина", "gender": "", "birthday": "1990-05-17", "phone": "+79998887766"},
    )

    owner.refresh_from_db()
    assert owner.phone == "+79990000001"


def test_настройки_не_меняют_чужого_клиента(client, login, owner, stranger):
    login(client, owner)

    client.post("/api/settings/", {"name": "Взлом", "gender": "", "birthday": "1990-05-17"})

    stranger.refresh_from_db()
    assert stranger.name == "Пётр"


def test_выход_очищает_сессию(client, login, owner):
    login(client, owner)

    response = client.get("/api/logout/")

    assert response.status_code == 302
    assert "client_id" not in client.session
    assert client.get("/api/profile/").status_code == 302
