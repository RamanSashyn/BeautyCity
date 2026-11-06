"""Одноразовые коды для входа по телефону: выпуск, проверка, ограничение частоты."""

import hmac
import logging
import secrets
from datetime import timedelta
from hashlib import sha256

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from api.models import Client, LoginCode
from api.services.sms import get_sms_sender

logger = logging.getLogger(__name__)


class LoginCodeError(Exception):
    """Ошибка выпуска или проверки кода. Текст можно показывать пользователю."""

    status = 400

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class RateLimited(LoginCodeError):
    status = 429


class InvalidCode(LoginCodeError):
    status = 400


class ExpiredCode(LoginCodeError):
    status = 400


class TooManyAttempts(LoginCodeError):
    status = 429


class DeliveryFailed(LoginCodeError):
    status = 503


def _hash_code(phone: str, code: str) -> str:
    """Хеш с секретным ключом: по базе код не восстановить и не подобрать без SECRET_KEY."""
    return hmac.new(settings.SECRET_KEY.encode(), f"{phone}:{code}".encode(), sha256).hexdigest()


def _generate_code() -> str:
    length = settings.LOGIN_CODE_LENGTH
    return f"{secrets.randbelow(10**length):0{length}d}"


def _check_rate_limits(phone: str, ip: str | None, now) -> None:
    window_start = now - timedelta(hours=1)
    recent = LoginCode.objects.filter(created_at__gte=window_start)
    by_phone = recent.filter(phone=phone).order_by("-created_at")

    last = by_phone.first()
    if last is not None:
        wait = settings.LOGIN_CODE_RESEND_SECONDS - int((now - last.created_at).total_seconds())
        if wait > 0:
            raise RateLimited(
                f"Код уже отправлен. Повторить можно через {wait} с.", retry_after=wait
            )

    if by_phone.count() >= settings.LOGIN_CODE_PHONE_HOURLY_LIMIT:
        raise RateLimited("Слишком много запросов кода для этого номера. Попробуйте позже.")

    if ip and recent.filter(ip_address=ip).count() >= settings.LOGIN_CODE_IP_HOURLY_LIMIT:
        raise RateLimited("Слишком много запросов кода. Попробуйте позже.")


def issue_code(phone: str, ip: str | None) -> None:
    """Создаёт код для номера и отправляет его через SmsSender.

    Бросает RateLimited, если номер или IP запрашивают коды слишком часто.
    """
    now = timezone.now()
    _check_rate_limits(phone, ip, now)

    code = _generate_code()
    try:
        with transaction.atomic():
            LoginCode.objects.create(phone=phone, code_hash=_hash_code(phone, code), ip_address=ip)
            get_sms_sender().send(phone, f"Код входа в BeautyCity: {code}")
    except Exception as exc:
        logger.exception("Не удалось отправить код входа")
        raise DeliveryFailed("Не удалось отправить SMS. Попробуйте позже.") from exc

    LoginCode.objects.filter(created_at__lt=now - timedelta(days=1)).delete()


def verify_code(phone: str, code: str) -> Client:
    """Проверяет код и возвращает клиента (создаёт его при первом входе).

    Действует только последний выданный код: он живёт LOGIN_CODE_TTL_SECONDS и допускает
    не более LOGIN_CODE_MAX_ATTEMPTS попыток ввода. После верного ввода код удаляется.
    """
    with transaction.atomic():
        login_code = (
            LoginCode.objects.select_for_update()
            .filter(phone=phone)
            .order_by("-created_at")
            .first()
        )
        if login_code is None:
            raise InvalidCode("Сначала запросите код.")

        age = (timezone.now() - login_code.created_at).total_seconds()
        if age > settings.LOGIN_CODE_TTL_SECONDS:
            raise ExpiredCode("Срок действия кода истёк. Запросите новый.")

        if login_code.attempts >= settings.LOGIN_CODE_MAX_ATTEMPTS:
            raise TooManyAttempts("Слишком много попыток. Запросите новый код.")

        login_code.attempts += 1
        login_code.save(update_fields=["attempts"])

        is_valid = hmac.compare_digest(login_code.code_hash, _hash_code(phone, code))
        if is_valid:
            login_code.delete()

    if not is_valid:
        raise InvalidCode("Неверный код.")

    client, _ = Client.objects.get_or_create(phone=phone)
    return client
