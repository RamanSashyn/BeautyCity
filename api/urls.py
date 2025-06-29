from django.urls import path
from .views import (
    service_view,
    filter_entities,
    login_view,
    profile_view,
    logout_view,
    index_view,
    service_finally_view,
    book_appointment,
    show_appointment,
    get_slots_by_specialist,
    settings_view
)

urlpatterns = [
    path("service/", service_view, name="service_view"),
    path("filter/", filter_entities, name="filter_entities"),
    path("login/", login_view, name="login"),
    path("profile/", profile_view, name="profile"),
    path("logout/", logout_view, name="logout"),
    path('book/', book_appointment, name='book_appointment'),
    path("service-finally/", service_finally_view, name="service_finally"),
    path("service-finally/<int:appointment_id>/", show_appointment, name="show_appointment"),
    path("slots-by-specialist/", get_slots_by_specialist, name="slots_by_specialist"),
    path("settings/", settings_view, name="settings"),
]
