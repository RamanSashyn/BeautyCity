from django.urls import path
from .views import service_view, filter_entities

urlpatterns = [
    path('service/', service_view,     name='service_view'),
    path('filter/',  filter_entities,  name='filter_entities'),
]