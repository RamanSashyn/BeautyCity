from django.urls import path
from .views import (
    service_view,
    filter_entities,
    login_view,
    profile_view,
    logout_view,
    index_view,
)

urlpatterns = [
    path("service/", service_view, name="service_view"),
    path("filter/", filter_entities, name="filter_entities"),
    path("login/", login_view, name="login"),
    path("profile/", profile_view, name="profile"),
    path("logout/", logout_view, name="logout"),
]
