import pytest
import requests


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Salon.save() ходит в геокодер Яндекса: в тестах сети нет."""

    def fail(*args, **kwargs):
        raise requests.ConnectionError("сеть отключена в тестах")

    monkeypatch.setattr("api.models.requests.get", fail)
