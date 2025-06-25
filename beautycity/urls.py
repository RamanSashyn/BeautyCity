from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("", TemplateView.as_view(template_name="index.html")),
    path("admin.html", TemplateView.as_view(template_name="admin.html")),
    path("notes.html", TemplateView.as_view(template_name="notes.html")),
    path("popup.html", TemplateView.as_view(template_name="popup.html")),
    path("service.html", TemplateView.as_view(template_name="service.html")),
    path("serviceFinally.html", TemplateView.as_view(template_name="serviceFinally.html")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
