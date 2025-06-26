from django.urls import path
from .views import service_booking_view

urlpatterns = [
    path("service/", service_booking_view, name="service"),
]
