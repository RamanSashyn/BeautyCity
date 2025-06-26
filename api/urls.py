from django.urls import path
from . import views
from .views import login_view, index

urlpatterns = [
    path("", views.ping, name="ping"),
    path("login/", login_view, name="login"),
    path('', index, name="index"),
]
