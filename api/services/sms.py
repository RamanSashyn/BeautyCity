"""Отправка SMS. Конкретный провайдер подключается настройкой SMS_SENDER."""

import logging
from abc import ABC, abstractmethod
from typing import ClassVar

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class SmsSender(ABC):
    """Интерфейс отправителя SMS: для нового провайдера достаточно реализовать send()."""

    @abstractmethod
    def send(self, phone: str, message: str) -> None:
        """Отправляет сообщение на номер в формате +7XXXXXXXXXX."""


class ConsoleSmsSender(SmsSender):
    """Режим разработки: сообщение выводится в лог, SMS не уходит."""

    def send(self, phone: str, message: str) -> None:
        logger.info("SMS для %s: %s", phone, message)


class InMemorySmsSender(SmsSender):
    """Складывает сообщения в память, чтобы тесты могли прочитать код."""

    outbox: ClassVar[list[tuple[str, str]]] = []

    def send(self, phone: str, message: str) -> None:
        self.outbox.append((phone, message))


def get_sms_sender() -> SmsSender:
    """Создаёт отправителя из настройки SMS_SENDER."""
    return import_string(settings.SMS_SENDER)()
