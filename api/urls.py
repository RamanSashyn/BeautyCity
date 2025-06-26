from django.urls import path
from . import views
from .views import login_view, index, profile_view, logout_view

urlpatterns = [
    path("", views.ping, name="ping"),
    path("login/", login_view, name="login"),
    path("", index, name="index"),
    path("profile/", profile_view, name="profile"),
    path("logout/", logout_view, name="logout"),
]
