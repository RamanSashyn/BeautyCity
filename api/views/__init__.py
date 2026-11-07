"""Представления разбиты по областям: вход, каталог, запись, личный кабинет."""

from .auth import login_verify_view, login_view, logout_view
from .booking import book_appointment, service_finally_view, show_appointment
from .catalog import filter_entities, get_slots_by_specialist, index_view, service_view
from .profile import profile_view, settings_view

__all__ = [
    "book_appointment",
    "filter_entities",
    "get_slots_by_specialist",
    "index_view",
    "login_verify_view",
    "login_view",
    "logout_view",
    "profile_view",
    "service_finally_view",
    "service_view",
    "settings_view",
    "show_appointment",
]
