import pytest


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/", "/api/service/", "/api/filter/"])
def test_публичные_страницы_открываются(client, url):
    response = client.get(url)

    assert response.status_code == 200
