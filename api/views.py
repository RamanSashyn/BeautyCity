from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Count
from .models import Salon, Service, Specialist, Category

def service_view(request):
    salons = Salon.objects.all()
    categories = Category.objects \
        .annotate(service_count=Count('service')) \
        .filter(service_count__gt=0, name__gt='') \
        .prefetch_related('service_set')

    specialists = Specialist.objects.prefetch_related('salons', 'services')
    return render(request, 'service.html', {
        'salons':      salons,
        'categories':  categories,
        'specialists': specialists,
    })

@require_GET
def filter_entities(request):
    salons_qs      = Salon.objects.all()
    services_qs    = Service.objects.all()
    specialists_qs = Specialist.objects.all()

    salon_id      = request.GET.get('salon')
    service_id    = request.GET.get('service')
    specialist_id = request.GET.get('specialist')

    if specialist_id:
        spec = specialists_qs.filter(pk=specialist_id).first()
        if spec:
            salons_qs      = spec.salons.all()
            services_qs    = spec.services.all()
            specialists_qs = specialists_qs.filter(pk=spec.id)

    if service_id:
        svc = services_qs.filter(pk=service_id).first()
        if svc:
            sl_allowed = Salon.objects.filter(specialist__services=svc).distinct()
            salons_qs  = salons_qs.filter(id__in=sl_allowed.values_list('id', flat=True))

            sp_allowed      = specialists_qs.filter(services=svc).distinct()
            specialists_qs  = specialists_qs.filter(id__in=sp_allowed.values_list('id', flat=True))

            services_qs = services_qs.filter(pk=svc.id)

    if salon_id:
        sl = salons_qs.filter(pk=salon_id).first()
        if sl:
            svc_in_salon = Service.objects.filter(specialist__salons=sl).distinct()
            services_qs  = services_qs.filter(id__in=svc_in_salon.values_list('id', flat=True))

            sp_in_salon      = specialists_qs.filter(salons=sl).distinct()
            specialists_qs   = specialists_qs.filter(id__in=sp_in_salon.values_list('id', flat=True))

            salons_qs = salons_qs.filter(pk=sl.id)

    def serialize(qs):
        return [{"id": o.id, "name": str(o)} for o in qs]

    return JsonResponse({
        "salons":      serialize(salons_qs),
        "services":    serialize(services_qs),
        "specialists": serialize(specialists_qs),
    })
