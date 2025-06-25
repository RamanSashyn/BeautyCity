from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("", TemplateView.as_view(template_name="index.html")),
    path("admin.html", TemplateView.as_view(template_name="admin.html")),
    path("notes.html", TemplateView.as_view(template_name="notes.html")),
    path("popup.html", TemplateView.as_view(template_name="popup.html")),
    path("service.html", TemplateView.as_view(template_name="service.html")),
    path(
        "serviceFinally.html", TemplateView.as_view(template_name="serviceFinally.html")
    ),
]
