from django.urls import path

from .views import (
    book_appointment,
    filter_entities,
    get_slots_by_specialist,
    login_verify_view,
    login_view,
    logout_view,
    profile_view,
    service_finally_view,
    service_view,
    settings_view,
    show_appointment,
)

urlpatterns = [
    path("service/", service_view, name="service_view"),
    path("filter/", filter_entities, name="filter_entities"),
    path("login/", login_view, name="login"),
    path("login/verify/", login_verify_view, name="login_verify"),
    path("profile/", profile_view, name="profile"),
    path("logout/", logout_view, name="logout"),
    path("book/", book_appointment, name="book_appointment"),
    path("service-finally/", service_finally_view, name="service_finally"),
    path("service-finally/<int:appointment_id>/", show_appointment, name="show_appointment"),
    path("slots-by-specialist/", get_slots_by_specialist, name="slots_by_specialist"),
    path("settings/", settings_view, name="settings"),
]
