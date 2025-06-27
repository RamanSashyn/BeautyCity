from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from api.views import index_view, service_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("service/", service_view, name="service"),
    path("admin.html", TemplateView.as_view(template_name="admin.html")),
    path("notes.html", TemplateView.as_view(template_name="notes.html")),
    path("popup.html", TemplateView.as_view(template_name="popup.html")),
    path("serviceFinally.html", TemplateView.as_view(template_name="serviceFinally.html")),
    path("", index_view, name="home"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
